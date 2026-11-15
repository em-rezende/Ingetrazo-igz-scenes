# =========================================================================
# Pasta: igz_tb_scenes/core/
# Arquivo: panel.py
# Descrição: Painel lateral (UI) com todas as ferramentas de cenas.
# =========================================================================
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QScrollArea, QFrame, QLabel, 
    QGroupBox, QListWidget, QPushButton, QHBoxLayout, QCheckBox, QFormLayout, 
    QSpinBox, QComboBox, QDoubleSpinBox, QTableWidget, QTableWidgetItem, 
    QAbstractItemView, QSplitter)
from .dialog_helpers import _fill_smooth_combo, _current_smooth
from .model import sequence_duration
from .ffmpeg import _ffmpeg_status
from .dialogs import DependencyDialog

class ScenesPanel(QWidget):
    def __init__(self, controller, _t, parent=None):
        super().__init__(parent)
        self.controller = controller
        self._t = _t
        self._build()
        self.atualizar()
        
    def _build(self):
        c = self.controller
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)
        inner = QWidget()
        scroll.setWidget(inner)
        root = QVBoxLayout(inner)
        root.setContentsMargins(8, 8, 8, 8)
        root.addWidget(QLabel(f"<b>{self._t('Scenes')}</b>"))
        nota = QLabel("<i>" + self._t("Scenes are saved inside the project's .igz file.") + "</i>")
        nota.setWordWrap(True)
        root.addWidget(nota)
        gb = QGroupBox(self._t("Scenes"))
        v = QVBoxLayout(gb)
        self.lista = QListWidget()
        self.lista.currentRowChanged.connect(self._selecionar)
        _fm_lista = self.lista.fontMetrics()
        self.lista.setFixedHeight(5 * (_fm_lista.height() + 4) + 2 * self.lista.frameWidth() + 2)
        v.addWidget(self.lista)
        h = QHBoxLayout()
        self.btn_add = QPushButton(self._t("Add"))
        self.btn_add.clicked.connect(self._add)
        self.btn_rem = QPushButton(self._t("Remove"))
        self.btn_rem.clicked.connect(self._rem)
        self.btn_clr = QPushButton(self._t("Clear"))
        self.btn_clr.clicked.connect(self._clr)
        for b in (self.btn_add, self.btn_rem, self.btn_clr): h.addWidget(b)
        v.addLayout(h)
        gb2 = QGroupBox(self._t("Playback"))
        v2 = QVBoxLayout(gb2)
        h2 = QHBoxLayout()
        self.btn_play = QPushButton(self._t("Play"))
        self.btn_play.clicked.connect(self._play)
        self.btn_stop = QPushButton(self._t("Stop"))
        self.btn_stop.clicked.connect(self._stop)
        h2.addWidget(self.btn_play)
        h2.addWidget(self.btn_stop)
        v2.addLayout(h2)
        self.chk_loop = QCheckBox(self._t("Loop"))
        self.chk_loop.setChecked(bool(c.loop))
        self.chk_loop.toggled.connect(self._loop)
        v2.addWidget(self.chk_loop)
        self.lbl_dur = QLabel("")
        v2.addWidget(self.lbl_dur)
        gb3 = QGroupBox(self._t("Timings and Frames"))
        v3 = QVBoxLayout(gb3)
        form = QFormLayout()
        self.sb_fps = QSpinBox()
        self.sb_fps.setRange(1, 240)
        self.sb_fps.setValue(int(round(c.fps)))
        form.addRow("FPS:", self.sb_fps)
        self.cb_suav = QComboBox()
        _fill_smooth_combo(self.cb_suav, c.suavizacao, self._t)
        form.addRow(self._t("Interpolation:"), self.cb_suav)
        self.sb_trans = QDoubleSpinBox()
        self.sb_trans.setRange(0.0, 3600.0)
        self.sb_trans.setDecimals(2)
        self.sb_trans.setSuffix(" s")
        self.sb_trans.setValue(c.transicao_padrao_s)
        form.addRow(self._t("Default transition:"), self.sb_trans)
        self.sb_hold = QDoubleSpinBox()
        self.sb_hold.setRange(0.0, 3600.0)
        self.sb_hold.setDecimals(2)
        self.sb_hold.setSuffix(" s")
        self.sb_hold.setValue(c.hold_padrao_s)
        form.addRow(self._t("Default hold:"), self.sb_hold)
        v3.addLayout(form)
        self.tabela = QTableWidget(0, 3)
        self.tabela.setHorizontalHeaderLabels([self._t("Scene"), self._t("Hold (s)"), self._t("Transition (s)")])
        self.tabela.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)
        _cab_tab = self.tabela.horizontalHeader().sizeHint().height() or 26
        _lin_tab = self.tabela.verticalHeader().defaultSectionSize() or 30
        self.tabela.setFixedHeight(_cab_tab + 4 * _lin_tab + 2 * self.tabela.frameWidth() + 2)
        v3.addWidget(self.tabela)
        self.btn_apply = QPushButton(self._t("Apply settings"))
        self.btn_apply.clicked.connect(self._apply)
        v3.addWidget(self.btn_apply)
        gb4 = QGroupBox(self._t("Export"))
        v4 = QVBoxLayout(gb4)
        self.cb_formato = QComboBox()
        self.cb_formato.addItems([self._t("PNG image sequence"), self._t("MP4 video")])
        v4.addWidget(self.cb_formato)
        self.btn_export = QPushButton(self._t("Export Animation"))
        self.btn_export.clicked.connect(self._export)
        v4.addWidget(self.btn_export)
        gb5 = QGroupBox(self._t("Video Dependencies"))
        v5 = QVBoxLayout(gb5)
        self.lbl_dep = QLabel("")
        self.lbl_dep.setWordWrap(True)
        v5.addWidget(self.lbl_dep)
        self.btn_dep = QPushButton(self._t("Configure / Download..."))
        self.btn_dep.clicked.connect(self._deps)
        v5.addWidget(self.btn_dep)
        base = QWidget()
        vb = QVBoxLayout(base)
        vb.setContentsMargins(0, 0, 0, 0)
        vb.addWidget(gb2)
        vb.addWidget(gb4)
        vb.addWidget(gb5)
        self.split = QSplitter(Qt.Vertical)
        self.split.setChildrenCollapsible(False)
        self.split.addWidget(gb)
        self.split.addWidget(gb3)
        self.split.addWidget(base)
        self.split.setStretchFactor(0, 0)
        self.split.setStretchFactor(1, 0)
        self.split.setStretchFactor(2, 1)
        self.split.setSizes([180, 340, 260])
        root.addWidget(self.split)
        
    def _selecionar(self, row): self.controller.indice_selecionado = row
    def _add(self): self.controller.adicionar_cena_atual()
    def _rem(self): self.controller.remover_cena_selecionada()
    def _clr(self): self.controller.limpar_cenas()
    def _play(self): self.controller.tocar_animacao()
    def _stop(self): self.controller.parar_animacao()
    def _loop(self, checked): self.controller.loop = bool(checked)
    
    def _apply(self):
        c = self.controller
        c.fps = float(self.sb_fps.value())
        c.suavizacao = _current_smooth(self.cb_suav)
        c.transicao_padrao_s = self.sb_trans.value()
        c.hold_padrao_s = self.sb_hold.value()
        for r in range(self.tabela.rowCount()):
            if r >= len(c.cenas): break
            try: c.cenas[r].hold_s = float(self.tabela.item(r, 1).text())
            except Exception: pass
            try: c.cenas[r].transicao_s = float(self.tabela.item(r, 2).text())
            except Exception: pass
        c.save_prefs()
        self.atualizar()
        c._flash(self._t("Settings applied."))
        
    def _export(self):
        modo = "MP4" if self.cb_formato.currentIndex() == 1 else "PNG"
        self.controller.exportar_animacao(modo)
        
    def _deps(self):
        DependencyDialog(self._t, self.window()).exec()
        self.atualizar()
        
    def atualizar(self):
        c = self.controller
        self.lista.blockSignals(True)
        self.lista.clear()
        for i, sc in enumerate(c.cenas): self.lista.addItem(f"{i + 1}. {sc.nome}")
        if 0 <= c.indice_selecionado < len(c.cenas): self.lista.setCurrentRow(c.indice_selecionado)
        self.lista.blockSignals(False)
        self.tabela.setRowCount(0)
        for sc in c.cenas:
            r = self.tabela.rowCount()
            self.tabela.insertRow(r)
            item = QTableWidgetItem(sc.nome)
            item.setFlags(Qt.ItemIsEnabled)
            self.tabela.setItem(r, 0, item)
            self.tabela.setItem(r, 1, QTableWidgetItem(f"{sc.hold_s:.2f}"))
            self.tabela.setItem(r, 2, QTableWidgetItem(f"{sc.transicao_s:.2f}"))
        self.tabela.resizeColumnsToContents()
        total = sequence_duration(c.cenas)
        self.lbl_dur.setText(self._t("{n} scene(s) — {total:.2f}s — ~{frames} frames", n=len(c.cenas), total=total, frames=max(1, int(round(total * c.fps)))))
        self.sb_fps.setValue(int(round(c.fps)))
        _fill_smooth_combo(self.cb_suav, c.suavizacao, self._t)
        self.sb_trans.setValue(c.transicao_padrao_s)
        self.sb_hold.setValue(c.hold_padrao_s)
        self.chk_loop.setChecked(bool(c.loop))
        ok_ff, _ = _ffmpeg_status()
        self.lbl_dep.setText(f"FFmpeg: {self._t('available') if ok_ff else self._t('missing')}")