# =========================================================================
# Pasta: igz_tb_scenes/core/
# Arquivo: controller.py
# Descrição: O cérebro da aplicação. Conecta a Model (Cenas) à UI e ao Host.
# =========================================================================
import os
import shutil
import tempfile
import traceback
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QVector3D
from PySide6.QtWidgets import QApplication, QMessageBox, QFileDialog, QDialog, QListWidget, QListWidgetItem, QVBoxLayout, QLabel, QDialogButtonBox
from .config import load_config, save_config
from .model import Scene, sequence_duration, sample_sequence
from .ffmpeg import _find_ffmpeg, run_ffmpeg
from .dialogs import ScenesConfigDialog, ScenesExportDialog, DependencyDialog

class SceneSequenceAnimation:
    def __init__(self, controller, cenas, fps=30.0, suavizacao="Smooth", loop=False):
        self.controller = controller
        self.cenas = list(cenas)
        self.fps = float(fps) if fps and fps > 0 else 30.0
        self.suavizacao = suavizacao
        self.loop = bool(loop)
        self.interrompido = False
        self.frame_count = 0
        self.tempo = 0.0
        self.total = sequence_duration(self.cenas)
        self.timer = QTimer(controller.main_window)
        self.timer.setInterval(max(1, int(round(1000.0 / self.fps))))
        self.timer.timeout.connect(self._next_frame)
        
    def iniciar(self):
        self.interrompido = False
        self.tempo = 0.0
        self.frame_count = 0
        if self.total <= 0.0: self.total = 1.0
        self.timer.start()
        
    def parar(self):
        if self.timer.isActive(): self.timer.stop()
        self.controller.animacao_ativa = None
        
    def sinalizar_interrupcao(self):
        self.interrompido = True
        if self.timer.isActive(): self.timer.stop()
        
    def _next_frame(self):
        if self.interrompido or not self.cenas:
            self.parar()
            return
        eye, tgt, fov = sample_sequence(self.cenas, self.tempo, self.suavizacao)
        self.controller.aplicar_camera(eye, tgt, fov)
        self.frame_count += 1
        self.tempo += 1.0 / self.fps
        if self.tempo > self.total:
            if self.loop: self.tempo = 0.0
            else:
                self.timer.stop()
                self.controller.animacao_ativa = None

class ScenesController:
    def __init__(self, viewport, main_window, app, _t, _norm_smooth, _log):
        self.viewport = viewport
        self.main_window = main_window
        self.app = app
        self._t = _t
        self._norm_smooth = _norm_smooth
        self._log = _log
        self.cenas = []
        self.indice_selecionado = -1
        self.panel = None
        self.dock = None
        cfg = load_config()
        self.fps = float(cfg.get("fps", 30.0))
        self.suavizacao = self._norm_smooth(cfg.get("suavizacao", "Smooth"))
        self.loop = bool(cfg.get("loop", False))
        self.transicao_padrao_s = float(cfg.get("transicao_padrao_s", 2.0))
        self.hold_padrao_s = float(cfg.get("hold_padrao_s", 1.0))
        self.export_w = int(cfg.get("export_w", 0) or 0)
        self.export_h = int(cfg.get("export_h", 0) or 0)
        self.animacao_ativa = None
        self._carregando_doc = False
        self.carregar_do_documento()
        self._ligar_eventos_documento()

    def get_camera_eye(self) -> list:
        vp = self.viewport
        if vp and hasattr(vp, "camera"):
            cam = vp.camera
            if hasattr(cam, "eye") and callable(cam.eye):
                try: return [cam.eye().x(), cam.eye().y(), cam.eye().z()]
                except Exception: pass
        return [0.0, -10.0, 5.0]
        
    def get_camera_target(self) -> list:
        vp = self.viewport
        if vp and hasattr(vp, "camera"):
            cam = vp.camera
            if hasattr(cam, "target"):
                t = cam.target
                if hasattr(t, "x"): return [t.x(), t.y(), t.z()]
        return [0.0, 0.0, 0.0]
        
    def get_camera_fov(self) -> float:
        vp = self.viewport
        if vp and hasattr(vp, "camera"):
            cam = vp.camera
            for attr in ("fov_deg", "fov", "field_of_view"):
                if hasattr(cam, attr):
                    try:
                        v = getattr(cam, attr)
                        if callable(v): v = v()
                        return float(v)
                    except Exception: pass
        return 30.0
        
    def set_camera(self, eye, target):
        vp = self.viewport
        if not vp or not hasattr(vp, "camera"): return
        cam = vp.camera
        eye_vec = QVector3D(eye[0], eye[1], eye[2])
        target_vec = QVector3D(target[0], target[1], target[2])
        dir_vec = target_vec - eye_vec
        if hasattr(cam, "look_from"):
            try: cam.look_from(eye_vec, dir_vec)
            except Exception: pass
        else:
            try: cam.target = target_vec
            except Exception: pass
        try: vp.update()
        except Exception: pass
        
    def aplicar_camera(self, eye, target, fov=None):
        self.set_camera(eye, target)
        if fov is not None and self.viewport and hasattr(self.viewport, "camera"):
            cam = self.viewport.camera
            for attr in ("fov_deg", "fov", "field_of_view"):
                if hasattr(cam, attr):
                    try:
                        setattr(cam, attr, float(fov))
                        break
                    except Exception: pass
        try: self.viewport.update()
        except Exception: pass
        
    def adicionar_cena_atual(self):
        eye = self.get_camera_eye()
        target = self.get_camera_target()
        fov = self.get_camera_fov()
        nome = self._t("Scene {n}", n=len(self.cenas) + 1)
        sc = Scene(nome, eye, target, fov, hold_s=self.hold_padrao_s, transicao_s=self.transicao_padrao_s)
        self.cenas.append(sc)
        self.indice_selecionado = len(self.cenas) - 1
        self.refresh_panel()
        self.salvar_no_documento()
        self._flash(self._t("{name} added (eye=({ex:.2f}, {ey:.2f}, {ez:.2f}), fov={fov:.1f}).", name=nome, ex=eye[0], ey=eye[1], ez=eye[2], fov=fov))
        
    def remover_cena_selecionada(self):
        if not self.cenas:
            QMessageBox.information(self.main_window, "Scenes", self._t("There are no scenes to remove."))
            return
        idx = self.indice_selecionado
        if not (0 <= idx < len(self.cenas)):
            if len(self.cenas) == 1: idx = 0
            else:
                idx = self._escolher_cena(self._t("Choose the scene to remove:"))
                if idx < 0: return
        nome = self.cenas[idx].nome
        del self.cenas[idx]
        self.indice_selecionado = min(idx, len(self.cenas) - 1)
        self.refresh_panel()
        self.salvar_no_documento()
        self._flash(self._t("{name} removed.", name=nome))
        
    def limpar_cenas(self):
        if not self.cenas: return
        resp = QMessageBox.question(self.main_window, "Scenes", self._t("Remove ALL {n} scenes?", n=len(self.cenas)), QMessageBox.Yes | QMessageBox.No)
        if resp != QMessageBox.Yes: return
        self.cenas = []
        self.indice_selecionado = -1
        self.refresh_panel()
        self.salvar_no_documento()
        self._flash(self._t("All scenes were removed."))
        
    def _escolher_cena(self, titulo):
        dlg = QDialog(self.main_window)
        dlg.setWindowTitle("Scenes")
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel(titulo))
        lista = QListWidget(dlg)
        for i, sc in enumerate(self.cenas): QListWidgetItem(f"{i + 1}. {sc.nome}", lista)
        if 0 <= self.indice_selecionado < len(self.cenas): lista.setCurrentRow(self.indice_selecionado)
        else: lista.setCurrentRow(0)
        lay.addWidget(lista)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dlg)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)
        if dlg.exec() == QDialog.Accepted and lista.currentRow() >= 0: return lista.currentRow()
        return -1
        
    def _flash(self, msg, ms=6000):
        try:
            if self.viewport is not None and hasattr(self.viewport, "flash_status"): self.viewport.flash_status(msg, ms)
        except Exception: pass
        
    def _obter_document_data(self):
        app = getattr(self, "app", None)
        if app is None: return None
        fn = getattr(app, "document_data", None)
        if not callable(fn): return None
        try: return fn({})
        except TypeError:
            try: return fn(default={})
            except Exception: traceback.print_exc(); return None
        except Exception: traceback.print_exc(); return None
        
    def _gravar_document_data(self, data):
        app = getattr(self, "app", None)
        if app is None: return
        fn = getattr(app, "set_document_data", None)
        if not callable(fn): return
        try: fn(data)
        except Exception: traceback.print_exc()
        
    def _snapshot(self) -> dict:
        return {"cenas": [sc.to_dict() for sc in self.cenas], "fps": self.fps, "suavizacao": self.suavizacao, "loop": self.loop, "transicao_padrao_s": self.transicao_padrao_s, "hold_padrao_s": self.hold_padrao_s, "export_w": self.export_w, "export_h": self.export_h}
        
    def carregar_do_documento(self):
        data = self._obter_document_data()
        if not isinstance(data, dict) or not data: return
        self._carregando_doc = True
        try:
            cenas = data.get("cenas")
            if isinstance(cenas, list):
                novas = [Scene.from_dict(d) for d in cenas if isinstance(d, dict)]
                self.cenas = novas
                if not novas: self.indice_selecionado = -1
                elif not (0 <= self.indice_selecionado < len(novas)): self.indice_selecionado = len(novas) - 1
            try:
                if "fps" in data: self.fps = float(data["fps"])
                if "suavizacao" in data: self.suavizacao = str(data["suavizacao"])
                if "loop" in data: self.loop = bool(data["loop"])
                if "transicao_padrao_s" in data: self.transicao_padrao_s = float(data["transicao_padrao_s"])
                if "hold_padrao_s" in data: self.hold_padrao_s = float(data["hold_padrao_s"])
                if "export_w" in data: self.export_w = int(data["export_w"] or 0)
                if "export_h" in data: self.export_h = int(data["export_h"] or 0)
            except Exception: traceback.print_exc()
        finally: self._carregando_doc = False
        
    def salvar_no_documento(self):
        if self._carregando_doc: return
        self._gravar_document_data(self._snapshot())
        
    def _ligar_eventos_documento(self):
        app = getattr(self, "app", None)
        if app is None: return
        fn = getattr(app, "on_document_changed", None)
        if not callable(fn): return
        try: fn(self._ao_mudar_documento)
        except Exception: traceback.print_exc()
        
    def _ao_mudar_documento(self, *args, **kwargs):
        self.carregar_do_documento()
        self.refresh_panel()
        
    def save_prefs(self):
        try:
            cfg = load_config()
            cfg.update({"fps": self.fps, "suavizacao": self.suavizacao, "loop": self.loop, "transicao_padrao_s": self.transicao_padrao_s, "hold_padrao_s": self.hold_padrao_s, "export_w": self.export_w, "export_h": self.export_h})
            save_config(cfg)
        except Exception: traceback.print_exc()
        self.salvar_no_documento()
        
    def refresh_panel(self):
        try:
            if self.panel is not None: self.panel.atualizar()
        except Exception: traceback.print_exc()
        
    def tocar_animacao(self):
        if len(self.cenas) < 1:
            QMessageBox.information(self.main_window, "Scenes", self._t("Add at least one scene (2 or more recommended)."))
            return
        if self.viewport is None:
            QMessageBox.warning(self.main_window, "Scenes", self._t("Viewport not found."))
            return
        if self.animacao_ativa: self.animacao_ativa.sinalizar_interrupcao()
        self.animacao_ativa = SceneSequenceAnimation(self, self.cenas, self.fps, self.suavizacao, self.loop)
        self.animacao_ativa.iniciar()
        self._flash(self._t("Playing scene animation..."))
        
    def parar_animacao(self):
        if self.animacao_ativa:
            self.animacao_ativa.sinalizar_interrupcao()
            self.animacao_ativa = None
        self._flash("")
        
    def configurar_tempos(self):
        # IMPORTANTE: Importa do arquivo correto e passa as dependências
        from .dialog_helpers import _fill_smooth_combo, _current_smooth
        dlg = ScenesConfigDialog(
            self, 
            self._t, 
            _fill_smooth_combo, 
            _current_smooth, 
            self.main_window
        )
        if dlg.exec() == QDialog.Accepted:
            dlg.aplicar()
            self.save_prefs()
            self.refresh_panel()
            self._flash(self._t("Timing and frame settings updated."))
            
    def _escolher_backend_mp4(self):
        while True:
            if _find_ffmpeg() is not None: return "ffmpeg"
            box = QMessageBox(self.main_window)
            box.setWindowTitle("Scenes")
            box.setIcon(QMessageBox.Information)
            box.setText(self._t("FFmpeg was not found."))
            box.setInformativeText(self._t("Do you want to configure/download FFmpeg now?\nOtherwise, the animation will be exported as a PNG image sequence."))
            b_cfg = box.addButton(self._t("Configure / Download..."), QMessageBox.AcceptRole)
            b_png = box.addButton(self._t("Export PNG"), QMessageBox.ActionRole)
            b_cancel = box.addButton(self._t("Cancel"), QMessageBox.RejectRole)
            box.setDefaultButton(b_cfg)
            box.exec()
            clicado = box.clickedButton()
            if clicado is b_cfg:
                DependencyDialog(self._t, self.main_window).exec()
                continue
            if clicado is b_png: return "png"
            return None
            
    def exportar_animacao(self, modo=None):
        if not self.cenas:
            QMessageBox.information(self.main_window, "Scenes", self._t("There are no scenes to export."))
            return
        if self.viewport is None:
            QMessageBox.warning(self.main_window, "Scenes", self._t("Viewport not found."))
            return
        dlg = ScenesExportDialog(self, self._t, self.main_window, modo_inicial=modo)
        if dlg.exec() != QDialog.Accepted: return
        modo = dlg.modo_saida()
        fps = dlg.fps()
        size = dlg.tamanho()
        try:
            self.export_w, self.export_h = int(size[0]), int(size[1])
            self.save_prefs()
        except Exception: pass
        if modo == "PNG":
            out_dir = QFileDialog.getExistingDirectory(self.main_window, self._t("Folder to save the PNG images"))
            if not out_dir: return
            self._render("png", fps, out_dir, None, size)
            return
        out_file, _ = QFileDialog.getSaveFileName(self.main_window, self._t("Save MP4 video"), self._t("animation.mp4"), self._t("MP4 video (*.mp4)"))
        if not out_file: return
        if not out_file.lower().endswith(".mp4"): out_file += ".mp4"
        backend = self._escolher_backend_mp4()
        if backend is None: return
        if backend == "png":
            out_dir = QFileDialog.getExistingDirectory(self.main_window, self._t("Folder to save the PNG images"))
            if not out_dir: return
            self._render("png", fps, out_dir, None, size)
            return
        self._render(backend, fps, None, out_file, size)
        
    def _render(self, backend, fps, out_dir, out_file, out_size=None):
        vp = self.viewport
        cenas = self.cenas
        suav = self.suavizacao
        try: fps = float(fps)
        except Exception: fps = float(self.fps)
        total = sequence_duration(cenas)
        n_frames = max(1, int(round(total * fps)))
        ffmpeg = None
        tmp_frames = None
        if backend != "png":
            ffmpeg = _find_ffmpeg()
            if not ffmpeg: backend = "png"
        if backend == "ffmpeg": tmp_frames = tempfile.mkdtemp(prefix="igz_scenes_frames_")
        if backend == "png" and not out_dir:
            out_dir = QFileDialog.getExistingDirectory(self.main_window, self._t("Folder to save the PNG images"))
            if not out_dir: return
        gravados = 0
        try:
            for idx in range(n_frames):
                t = idx / fps
                eye, tgt, fov = sample_sequence(cenas, t, suav)
                self.aplicar_camera(eye, tgt, fov)
                QApplication.processEvents()
                pix = (vp.grabFramebuffer() if hasattr(vp, "grabFramebuffer") else None)
                if pix is None: continue
                if out_size:
                    try:
                        tw = int(out_size[0])
                        th = int(out_size[1])
                        if tw > 0 and th > 0 and (tw != pix.width() or th != pix.height()): pix = pix.scaled(tw, th, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                    except Exception: traceback.print_exc()
                gravados += 1
                if tmp_frames is not None: pix.save(os.path.join(tmp_frames, f"f_{gravados:05d}.png"), "PNG")
                else: pix.save(os.path.join(out_dir, f"scene_{gravados:05d}.png"), "PNG")
        except Exception: traceback.print_exc()
        resultado = ""
        if backend == "ffmpeg":
            if tmp_frames and run_ffmpeg(ffmpeg, tmp_frames, out_file, fps, self.main_window, self._t, self._log, QMessageBox): resultado = out_file
        else: resultado = out_dir
        if backend == "ffmpeg":
            if resultado and tmp_frames: shutil.rmtree(tmp_frames, ignore_errors=True)
            elif not resultado and tmp_frames:
                QMessageBox.warning(self.main_window, "Scenes", self._t("Could not generate the MP4 video.\nThe PNG frames were kept in:\n") + tmp_frames)
        dest = resultado or (out_file if backend == "ffmpeg" else out_dir)
        QMessageBox.information(self.main_window, "Scenes", self._t("Export finished: {n} frames.", n=gravados) + (f"\n{dest}" if dest else ""))