# =========================================================================
# Pasta: igz_tb_scenes/core/
# Arquivo: config.py
# Descrição: Gerenciamento de arquivos de configuração e persistência.
# =========================================================================
import json
import os
import traceback
from PySide6.QtCore import QStandardPaths

_CONFIG_CACHE = {"dir": None, "file": None}

def _config_dir() -> str:
    if _CONFIG_CACHE["dir"]: 
        return _CONFIG_CACHE["dir"]
    base = ""
    try:
        base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    except Exception:
        pass
    if not base: 
        base = os.path.join(os.path.expanduser("~"), ".ingetrazo")
    d = os.path.join(base, "igz_tb_scenes")
    _CONFIG_CACHE["dir"] = d
    _CONFIG_CACHE["file"] = os.path.join(d, "config.json")
    return d

def _config_file() -> str:
    _config_dir()
    return _CONFIG_CACHE["file"]

def load_config() -> dict:
    try:
        with open(_config_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def save_config(data: dict) -> None:
    try:
        d = _config_dir()
        os.makedirs(d, exist_ok=True)
        tmp = _config_file() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, _config_file())
    except Exception:
        traceback.print_exc()

def set_config_value(key, value) -> None:
    data = load_config()
    data[key] = value
    save_config(data)