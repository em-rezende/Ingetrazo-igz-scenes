# =========================================================================
# Pasta: igz_tb_scenes/core/
# Arquivo: toolbar.py
# Descrição: Criação da Toolbar e integração com o host.
# =========================================================================
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon, QPalette
from PySide6.QtWidgets import QToolBar, QSizePolicy, QDockWidget, QTabBar, QWidget
from .controller import ScenesController
from .panel import ScenesPanel
from .dialogs import DependencyDialog
from .ffmpeg import _find_ffmpeg

def _load_themed_icon(base_name: str, main_window, _HERE, os, QIcon):
    _ICONS_DIR = os.path.join(_HERE, "icons") if os.path.isdir(os.path.join(_HERE, "icons")) else None
    if not _ICONS_DIR: return QIcon()
    if base_name.endswith(".svg"): base_name = base_name[:-4]
    is_dark = True
    try:
        if main_window is not None:
            bg_color = main_window.palette().color(QPalette.Window)
            is_dark = bg_color.lightness() < 128
    except Exception: pass
    if not is_dark:
        light_path = os.path.join(_ICONS_DIR, f"{base_name}_light.svg")
        if os.path.isfile(light_path): return QIcon(light_path)
    default_path = os.path.join(_ICONS_DIR, f"{base_name}.svg")
    if os.path.isfile(default_path): return QIcon(default_path)
    return QIcon()

def _bring_dock_to_front(window, dock):
    if dock is None: return
    try: siblings = dock.tabifiedDockWidgets()
    except Exception: siblings = []
    try:
        for sib in siblings: sib.lower()
    except Exception: pass
    try: dock.setVisible(True)
    except Exception: pass
    try: dock.raise_()
    except Exception: pass
    if siblings:
        try:
            title = dock.windowTitle()
            for tb in window.findChildren(QTabBar):
                for i in range(tb.count()):
                    if tb.tabText(i) == title:
                        tb.setCurrentIndex(i)
                        return
        except Exception: pass

def _dock_is_front(dock):
    if dock is None: return False
    try:
        if not dock.isVisible(): return False
    except Exception: return False
    try: siblings = dock.tabifiedDockWidgets()
    except Exception: siblings = []
    return not bool(siblings)

def find_viewport(main_window):
    if not main_window: return None
    if hasattr(main_window, "viewport"): return main_window.viewport
    for child in main_window.findChildren(QWidget):
        name = child.__class__.__name__.lower()
        if ("viewport" in name or "gl" in name or "canvas" in name or "scene" in name): return child
    return None

def _attach_scenes_panel(mw, panel, app, _t, _load_themed_icon_func, _log):
    if mw is None: return None
    add_panel = getattr(app, "add_panel", None) if app is not None else None
    if callable(add_panel):
        try:
            dock = add_panel(_t("Scenes"), panel, name="igz_tb_scenes", stretch=1)
            try:
                set_icon = getattr(app, "_set_panel_icon", None)
                icon = _load_themed_icon_func("scene_panel_tab", mw)
                if callable(set_icon) and not icon.isNull(): set_icon(dock, icon)
            except Exception: pass
            try: dock.hide()
            except Exception: pass
            _log("Painel 'Cenas' registrado via app.add_panel.")
            return dock
        except Exception: 
            import traceback; traceback.print_exc()
    if hasattr(mw, "addDockWidget"):
        dock = QDockWidget(_t("Scenes"), mw)
        dock.setObjectName("igz_tb_scenes_dock")
        dock.setWidget(panel)
        mw.addDockWidget(Qt.RightDockWidgetArea, dock)
        dock.hide()
        _log("Painel 'Cenas' criado como dock próprio (fallback).")
        return dock
    return None

def create_toolbar(main_window, viewport, app, _t, _HERE, os, QIcon, _norm_smooth, _log):
    if viewport is None: viewport = find_viewport(main_window)
    
    # Instancia o Controller
    controller = ScenesController(viewport, main_window, app, _t, _norm_smooth, _log)
    
    toolbar = QToolBar("Scenes", main_window)
    toolbar.setObjectName("igz_tb_scenes")
    toolbar.setWindowTitle(_t("Scenes"))
    
    def make_action(nome, icone_base, tooltip, callback):
        icon = _load_themed_icon(icone_base, main_window, _HERE, os, QIcon)
        action = QAction(icon, nome, main_window)
        action.setToolTip(tooltip)
        action.setStatusTip(tooltip)
        action.triggered.connect(lambda checked=False: callback())
        return action

    toolbar.addAction(make_action(_t("Add Current Scene"), "scene_add", _t("Captures the current camera's eye, target and fov as a new scene."), controller.adicionar_cena_atual))
    toolbar.addAction(make_action(_t("Remove Selected Scene"), "scene_remove", _t("Removes the currently selected scene from the list."), controller.remover_cena_selecionada))
    toolbar.addAction(make_action(_t("Clear Scenes"), "scene_remove_all", _t("Removes ALL scenes from the list."), controller.limpar_cenas))
    toolbar.addSeparator()
    toolbar.addAction(make_action(_t("Play Scene Animation"), "scene_play", _t("Smoothly plays through the scenes stored in the viewport."), controller.tocar_animacao))
    toolbar.addAction(make_action(_t("Stop Animation"), "scene_stop", _t("Stops the running scene animation."), controller.parar_animacao))
    toolbar.addSeparator()
    toolbar.addAction(make_action(_t("Configure Timings and Frames"), "scene_configure", _t("Configures FPS, interpolation, loop and per-scene timings."), controller.configurar_tempos))
    toolbar.addAction(make_action(_t("Export Animation"), "scene_export", _t("Exports the animation as a PNG sequence or MP4 video."), controller.exportar_animacao))
    
    if _find_ffmpeg() is None:
        toolbar.addAction(make_action(_t("Video Dependencies"), "scene_ffmpeg", _t("Configure/download FFmpeg to export MP4."), lambda: DependencyDialog(_t, main_window).exec()))
        
    # Instancia o Painel
    panel = ScenesPanel(controller, _t, main_window)
    controller.panel = panel
    
    dock = _attach_scenes_panel(main_window, panel, app, _t, lambda b, m: _load_themed_icon(b, m, _HERE, os, QIcon), _log)
    controller.dock = dock
    
    toolbar.addSeparator()
    if dock is not None:
        icon_panel = _load_themed_icon("scene_panel", main_window, _HERE, os, QIcon)
        action_panel = QAction(icon_panel, _t("Scenes Panel"), main_window)
        action_panel.setToolTip(_t("Show/hide the scenes panel."))
        action_panel.setCheckable(True)
        try: action_panel.setChecked(dock.isVisible())
        except Exception: action_panel.setChecked(False)
        
        def _toggle_or_show_scenes(_checked=False):
            try:
                if _dock_is_front(dock):
                    dock.hide()
                    return
                _bring_dock_to_front(main_window, dock)
                try:
                    w = dock.widget()
                    if w is not None: w.setFocus()
                except Exception: pass
                try:
                    main_window.raise_()
                    main_window.activateWindow()
                except Exception: pass
            except Exception as exc:
                _log(f"_toggle_or_show_scenes falhou: {exc}")
                
        action_panel.triggered.connect(_toggle_or_show_scenes)
        try: dock.visibilityChanged.connect(action_panel.setChecked)
        except Exception: pass
        toolbar.addAction(action_panel)
    else:
        _log("create_toolbar: painel 'Cenas' não anexado.")
        
    toolbar.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
    return toolbar