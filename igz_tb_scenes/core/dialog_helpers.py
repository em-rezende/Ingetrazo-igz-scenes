# =========================================================================
# Pasta: igz_tb_scenes/core/
# Arquivo: dialog_helpers.py
# Descrição: Funções auxiliares para combos de suavização.
# =========================================================================
_SMOOTH_KEYS = ("Smooth", "Linear", "Catmull-Rom")

def _norm_smooth(value):
    v = str(value or "").strip()
    low = v.lower()
    if low in ("", "suave", "smooth"): return "Smooth"
    if low == "linear": return "Linear"
    if low in ("catmull-rom", "catmull_rom", "catmullrom"): return "Catmull-Rom"
    return v or "Smooth"

def _fill_smooth_combo(combo, current, _t=None):
    if _t is None:
        _t = lambda x: x  # fallback de segurança
    combo.clear()
    for key in _SMOOTH_KEYS: combo.addItem(_t(key), key)
    idx = combo.findData(_norm_smooth(current))
    combo.setCurrentIndex(idx if idx >= 0 else 0)

def _current_smooth(combo):
    data = combo.currentData()
    return str(data) if data is not None else _norm_smooth(combo.currentText())