# =========================================================================
# Pasta: igz_tb_scenes/core/
# Arquivo: dialogs.py
# Descrição: Janelas de diálogo (Dependências, Configurações, Exportação).
# =========================================================================
import os
import subprocess
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QGridLayout, 
    QPushButton, QHBoxLayout, QProgressBar, QPlainTextEdit, QDialogButtonBox, 
    QFileDialog, QFormLayout, QSpinBox, QComboBox, QDoubleSpinBox, QTableWidget, 
    QTableWidgetItem, QAbstractItemView, QCheckBox, QWidget)
from .config import set_config_value
from .ffmpeg import _ffmpeg_status, _ffmpeg_local_dir, FfmpegDownloadWorker
from .model import sequence_duration

class DependencyDialog(QDialog):
    def __init__(self, _t, parent=None):
        super().__init__(parent)
        self._t = _t
        self.setWindowTitle(self._t("Scenes - Video Dependencies"))
        self.resize(580, 440)
        self._dl_thread = None
        root = QVBoxLayout(self)
        intro = QLabel(self._t("MP4 export uses <b>FFmpeg</b>.\nCheck the status below and download it if it is missing."))
        intro.setWordWrap(True)
        root.addWidget(intro)
        grid = QGridLayout()
        root.addLayout(grid)
        grid.addWidget(QLabel("<b>FFmpeg</b>"), 0, 0)
        self.lbl_ff = QLabel("")
        self.lbl_ff.setWordWrap(True)
        grid.addWidget(self.lbl_ff, 0, 1)
        caixa_ff = QHBoxLayout()
        self.btn_dl = QPushButton(self._t("Download FFmpeg"))
        self.btn_dl.setToolTip(self._t("Downloads and extracts FFmpeg (~90 MB) to the plugin's local folder."))
        self.btn_dl.clicked.connect(self._baixar_ffmpeg)
        caixa_ff.addWidget(self.btn_dl)
        self.btn_local = QPushButton(self._t("Browse..."))
        self.btn_local.setToolTip(self._t("Select an already installed ffmpeg(.exe)."))
        self.btn_local.clicked.connect(self._procurar_ffmpeg)
        caixa_ff.addWidget(self.btn_local)
        grid.addLayout(caixa_ff, 0, 2)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        root.addWidget(self.progress)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        root.addWidget(self.log, 1)
        btns = QDialogButtonBox(QDialogButtonBox.Close, self)
        self.btn_refresh = btns.addButton(self._t("Refresh status"), QDialogButtonBox.ActionRole)
        self.btn_refresh.clicked.connect(self._atualizar_status)
        self.btn_pasta = btns.addButton(self._t("Open folder"), QDialogButtonBox.ActionRole)
        self.btn_pasta.clicked.connect(self._abrir_pasta)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)
        self._atualizar_status()
        
    def _append_log(self, text):
        if text: self.log.appendPlainText(str(text))
        
    def _atualizar_status(self):
        ok_ff, p_ff = _ffmpeg_status()
        self.lbl_ff.setText((self._t("available") if ok_ff else self._t("MISSING")) + (f"\n{p_ff}" if p_ff else ""))
        self.btn_dl.setEnabled(not ok_ff)
        self._append_log(f"Status -> FFmpeg: {'OK' if ok_ff else self._t('absent')}")
        
    def _baixar_ffmpeg(self):
        self._append_log(self._t("Downloading FFmpeg... (may take a while / ~90 MB)"))
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.btn_dl.setEnabled(False)
        self._dl_thread = FfmpegDownloadWorker(_ffmpeg_local_dir(), self._t, self)
        self._dl_thread.progresso.connect(self._dl_progresso)
        self._dl_thread.concluido.connect(self._dl_fim)
        self._dl_thread.start()
        
    def _dl_progresso(self, pct, msg):
        if pct < 0: self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(pct)
        if msg: self._append_log(msg)
        
    def _dl_fim(self, ok, msg):
        self.progress.setRange(0, 100)
        self.progress.setValue(100 if ok else 0)
        if ok: self._append_log(self._t("FFmpeg ready at: {path}", path=msg))
        else: self._append_log(self._t("FFmpeg failure: {msg}", msg=(msg or "")))
        self._atualizar_status()
        
    def _procurar_ffmpeg(self):
        path, _ = QFileDialog.getOpenFileName(self, self._t("Select the ffmpeg executable"), "", "FFmpeg (ffmpeg.exe ffmpeg);;" + self._t("All files (*.*)"))
        if path:
            set_config_value("ffmpeg_path", path)
            self._append_log(self._t("FFmpeg set: {path}", path=path))
            self._atualizar_status()
            
    def _abrir_pasta(self):
        d = _ffmpeg_local_dir()
        try:
            os.makedirs(d, exist_ok=True)
            if sys.platform.startswith("win"): os.startfile(d)
            elif sys.platform == "darwin": subprocess.Popen(["open", d])
            else: subprocess.Popen(["xdg-open", d])
        except Exception:
            self._append_log(self._t("Dependencies folder: {path}", path=d))
            
    def reject(self):
        if self._dl_thread is not None and self._dl_thread.isRunning():
            self._dl_thread.cancelar()
            self._dl_thread.wait(2000)
        super().reject()

class ScenesConfigDialog(QDialog):
    def __init__(self, controller, _t, _fill_smooth_combo, _current_smooth, parent=None):
        super().__init__(parent)
        self._t = _t
        self.setWindowTitle(self._t("Scenes - Timings and Frames"))
        self.controller = controller
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.sb_fps = QSpinBox()
        self.sb_fps.setRange(1, 240)
        self.sb_fps.setValue(int(round(controller.fps)))
        form.addRow(self._t("Frames per second (FPS):"), self.sb_fps)
        self.cb_suav = QComboBox()
        _fill_smooth_combo(self.cb_suav, controller.suavizacao, self._t)
        form.addRow(self._t("Camera interpolation:"), self.cb_suav)
        self.cb_loop = QComboBox()
        self.cb_loop.addItems([self._t("No"), self._t("Yes")])
        self.cb_loop.setCurrentText(self._t("Yes") if controller.loop else self._t("No"))
        form.addRow(self._t("Loop?"), self.cb_loop)
        self.sb_trans = QDoubleSpinBox()
        self.sb_trans.setRange(0.0, 3600.0)
        self.sb_trans.setDecimals(2)
        self.sb_trans.setValue(controller.transicao_padrao_s)
        self.sb_trans.setSuffix(" s")
        form.addRow(self._t("Default transition:"), self.sb_trans)
        self.sb_hold = QDoubleSpinBox()
        self.sb_hold.setRange(0.0, 3600.0)
        self.sb_hold.setDecimals(2)
        self.sb_hold.setValue(controller.hold_padrao_s)
        self.sb_hold.setSuffix(" s")
        form.addRow(self._t("Default hold:"), self.sb_hold)
        layout.addLayout(form)
        layout.addWidget(QLabel(self._t("Scene timings (edit columns 2 and 3):")))
        self.tabela = QTableWidget(0, 3)
        self.tabela.setHorizontalHeaderLabels([self._t("Scene"), self._t("Hold (s)"), self._t("Transition (s)")])
        self.tabela.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)
        for sc in controller.cenas:
            r = self.tabela.rowCount()
            self.tabela.insertRow(r)
            item_nome = QTableWidgetItem(sc.nome)
            item_nome.setFlags(Qt.ItemIsEnabled)
            self.tabela.setItem(r, 0, item_nome)
            self.tabela.setItem(r, 1, QTableWidgetItem(f"{sc.hold_s:.2f}"))
            self.tabela.setItem(r, 2, QTableWidgetItem(f"{sc.transicao_s:.2f}"))
        self.tabela.resizeColumnsToContents()
        layout.addWidget(self.tabela)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._current_smooth = _current_smooth
        
    def aplicar(self):
        c = self.controller
        c.fps = float(self.sb_fps.value())
        c.suavizacao = self._current_smooth(self.cb_suav)
        c.loop = self.cb_loop.currentText() == self._t("Yes")
        c.transicao_padrao_s = self.sb_trans.value()
        c.hold_padrao_s = self.sb_hold.value()
        for r in range(self.tabela.rowCount()):
            if r >= len(c.cenas): break
            sc = c.cenas[r]
            try: sc.hold_s = float(self.tabela.item(r, 1).text())
            except Exception: pass
            try: sc.transicao_s = float(self.tabela.item(r, 2).text())
            except Exception: pass

class ScenesExportDialog(QDialog):
    def __init__(self, controller, _t, parent=None, modo_inicial=None):
        super().__init__(parent)
        self._t = _t
        self.setWindowTitle(self._t("Scenes - Export Animation"))
        self.controller = controller
        layout = QFormLayout(self)
        self.cb_formato = QComboBox()
        self.cb_formato.addItems([self._t("PNG image sequence"), self._t("MP4 video")])
        if str(modo_inicial).upper() == "MP4": self.cb_formato.setCurrentIndex(1)
        layout.addRow(self._t("Output format:"), self.cb_formato)
        self.sb_fps = QSpinBox()
        self.sb_fps.setRange(1, 240)
        self.sb_fps.setValue(int(round(controller.fps)))
        layout.addRow("FPS:", self.sb_fps)
        vp = controller.viewport
        self._vp_w = vp.width() if vp is not None else 0
        self._vp_h = vp.height() if vp is not None else 0
        if self._vp_w <= 0: self._vp_w = 1920
        if self._vp_h <= 0: self._vp_h = 1080
        cfg_w = int(getattr(controller, "export_w", 0) or 0)
        cfg_h = int(getattr(controller, "export_h", 0) or 0)
        w0 = cfg_w if cfg_w > 0 else self._vp_w
        h0 = cfg_h if cfg_h > 0 else self._vp_h
        self.sb_w = QSpinBox()
        self.sb_w.setRange(16, 7680)
        self.sb_w.setValue(int(w0))
        self.sb_w.setSuffix(" px")
        self.sb_h = QSpinBox()
        self.sb_h.setRange(16, 7680)
        self.sb_h.setValue(int(h0))
        self.sb_h.setSuffix(" px")
        linha_tam = QHBoxLayout()
        linha_tam.addWidget(QLabel(self._t("W")))
        linha_tam.addWidget(self.sb_w)
        linha_tam.addWidget(QLabel(self._t("x  H")))
        linha_tam.addWidget(self.sb_h)
        holder = QWidget()
        holder.setLayout(linha_tam)
        layout.addRow(self._t("Size (W × H):"), holder)
        self.chk_lock = QCheckBox(self._t("Keep screen aspect ratio"))
        self.chk_lock.setChecked(True)
        layout.addRow("", self.chk_lock)
        self.btn_reset = QPushButton(self._t("Current screen size"))
        self.btn_reset.clicked.connect(self._usar_viewport)
        layout.addRow("", self.btn_reset)
        self.lbl_info = QLabel("")
        layout.addRow(self._t("Summary:"), self.lbl_info)
        self._atualizar()
        self.cb_formato.currentIndexChanged.connect(self._atualizar)
        self.sb_fps.valueChanged.connect(self._atualizar)
        self.sb_w.valueChanged.connect(self._w_mudou)
        self.sb_h.valueChanged.connect(self._h_mudou)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
    def _usar_viewport(self):
        self.sb_w.blockSignals(True); self.sb_h.blockSignals(True)
        self.sb_w.setValue(int(self._vp_w)); self.sb_h.setValue(int(self._vp_h))
        self.sb_w.blockSignals(False); self.sb_h.blockSignals(False)
        self.chk_lock.setChecked(True)
        self._atualizar()
        
    def _w_mudou(self, val):
        if self.chk_lock.isChecked() and self._vp_w > 0:
            self.sb_h.blockSignals(True)
            self.sb_h.setValue(max(16, int(round(val * self._vp_h / self._vp_w))))
            self.sb_h.blockSignals(False)
        self._atualizar()
        
    def _h_mudou(self, val):
        if self.chk_lock.isChecked() and self._vp_h > 0:
            self.sb_w.blockSignals(True)
            self.sb_w.setValue(max(16, int(round(val * self._vp_w / self._vp_h))))
            self.sb_w.blockSignals(False)
        self._atualizar()
        
    def _atualizar(self):
        total = sequence_duration(self.controller.cenas)
        fps = self.sb_fps.value()
        w, h = self.tamanho()
        self.lbl_info.setText(self._t("{n} scene(s) - {total:.2f}s - ~{frames} frames - {w}x{h} px", n=len(self.controller.cenas), total=total, frames=max(1, int(round(total * fps))), w=w, h=h))
        
    def modo_saida(self) -> str: return "MP4" if self.cb_formato.currentIndex() == 1 else "PNG"
    def fps(self) -> float: return float(self.sb_fps.value())
    def tamanho(self): return int(self.sb_w.value()), int(self.sb_h.value())