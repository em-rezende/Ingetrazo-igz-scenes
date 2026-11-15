# =========================================================================
# Pasta: igz_tb_scenes/
# Arquivo: __init__.py
# Descrição: Ponto de entrada do plugin.
# =========================================================================
import json
import os
import sys
import traceback
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPalette
from PySide6.QtWidgets import QApplication

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)  # Garante que a pasta core/ seja encontrada

__version__ = "1.1.0"

try:
    from .core import config, math_utils, model, ffmpeg, dialogs, controller, panel, toolbar, dialog_helpers
except ImportError:
    import core.config as config
    import core.math_utils as math_utils
    import core.model as model
    import core.ffmpeg as ffmpeg
    import core.dialogs as dialogs
    import core.controller as controller
    import core.panel as panel
    import core.toolbar as toolbar
    import core.dialog_helpers as dialog_helpers

DEBUG = True
def _log(s):
    if DEBUG:
        print(f"[igz_tb_scenes] {s}", file=sys.stderr, flush=True)

# =========================================================================
# i18n (Internacionalização)
# =========================================================================
try:
    from core.i18n import tr as _tr_i18n
    from core.i18n import current_language as _current_language
except Exception:
    def _tr_i18n(s, **kw): return s.format(**kw) if kw else s
    def _current_language(): return "en"

_I18N_DIR = os.path.join(_HERE, "i18n")
_I18N_CACHE: dict[str, dict] = {}

def _load_i18n_json(lang_key: str) -> dict:
    if lang_key in _I18N_CACHE: return _I18N_CACHE[lang_key]
    data: dict = {}
    try:
        path = os.path.join(_I18N_DIR, f"{lang_key}.json")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                data = {str(k): str(v) for k, v in raw.items() if not str(k).startswith("_")}
    except Exception:
        _log(f"_load_i18n_json({lang_key!r}) falhou")
    _I18N_CACHE[lang_key] = data
    return data

def _lang_key() -> str:
    try:
        lang = str(_current_language() or "en").strip().replace("_", "-")
    except Exception:
        return "en"
    if lang in ("en", "pt-BR", "es", "it", "de"): return lang
    base = lang.split("-")[0].lower()
    for key in ("pt-BR", "es", "it", "de"):
        if key.lower().split("-")[0] == base: return key
    return "en"

def _t(text: str, **kw) -> str:
    try:
        x = _tr_i18n(text)
        if isinstance(x, str) and x != text: return x.format(**kw) if kw else x
    except Exception:
        pass
    lang = _lang_key()
    if lang != "en":
        data = _load_i18n_json(lang)
        out = data.get(text, text)
    else:
        out = text
    return out.format(**kw) if kw else out

# =========================================================================
# SETUP DO PLUGIN
# =========================================================================
_TOOLBAR_CREATED = False

def setup(app) -> None:
    global _TOOLBAR_CREATED
    if _TOOLBAR_CREATED: return
    try:
        mw = None
        qapp = QApplication.instance()
        if qapp is not None:
            for w in qapp.topLevelWidgets():
                if hasattr(w, "addToolBar"):
                    mw = w
                    break
        if mw is None:
            mw = (getattr(app, "main_window", None) or getattr(app, "window", None) or (app if hasattr(app, "addToolBar") else None))
        if mw is None or not hasattr(mw, "addToolBar"):
            _log("setup: main window não encontrada; abortando.")
            return
            
        vp = toolbar.find_viewport(mw) or getattr(app, "viewport", None)
        if vp is None: _log("setup: viewport não encontrada.")
        else: _log(f"setup: viewport = {vp.__class__.__name__}")
        
        # Chama a criação da toolbar passando todas as dependências necessárias
        tb = toolbar.create_toolbar(
            main_window=mw,
            viewport=vp,
            app=app,
            _t=_t,
            _HERE=_HERE,
            os=os,
            QIcon=QIcon,
            _norm_smooth=dialog_helpers._norm_smooth,
            _log=_log
        )
        
        mw.addToolBar(Qt.TopToolBarArea, tb)
        _TOOLBAR_CREATED = True
        _log("setup: toolbar 'igz_tb_scenes' adicionada com sucesso.")
    except Exception:
        traceback.print_exc()

__all__ = ["setup"]