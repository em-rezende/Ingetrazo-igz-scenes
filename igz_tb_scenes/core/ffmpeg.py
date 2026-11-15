# =========================================================================
# Pasta: igz_tb_scenes/core/
# Arquivo: ffmpeg.py
# Descrição: Backend de vídeo, download do FFmpeg e execução.
# =========================================================================
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from PySide6.QtCore import QThread, Signal
from .config import load_config, set_config_value, _config_dir

def _ffmpeg_local_dir() -> str:
    return os.path.join(_config_dir(), "ffmpeg")

def _find_ffmpeg():
    cfg = load_config()
    p = cfg.get("ffmpeg_path")
    if p and os.path.isfile(p): return p
    p = shutil.which("ffmpeg")
    if p: return p
    local = _ffmpeg_local_dir()
    if os.path.isdir(local):
        for root, _, files in os.walk(local):
            for fn in files:
                if fn.lower() in ("ffmpeg.exe", "ffmpeg"): return os.path.join(root, fn)
    candidates = [r"C:\ffmpeg\bin\ffmpeg.exe", os.path.join(os.environ.get("ProgramFiles", ""), "ffmpeg", "bin", "ffmpeg.exe"), "/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]
    for c in candidates:
        if c and os.path.isfile(c): return c
    return None

def _ffmpeg_status():
    p = _find_ffmpeg()
    return (bool(p), p or "")

def _fps_str(fps):
    try: f = float(fps)
    except Exception: return "24"
    if abs(f - round(f)) < 1e-9: return str(int(round(f)))
    return ("%.6f" % f).rstrip("0").rstrip(".")

def run_ffmpeg(ffmpeg, png_dir, out_file, fps, main_window, _t, _log, QMessageBox):
    if not ffmpeg or not png_dir or not os.path.isdir(png_dir): return False
    pattern = os.path.join(png_dir, "f_%05d.png")
    cmd = [ffmpeg, "-y", "-framerate", _fps_str(fps), "-i", pattern, "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p", out_file or ""]
    try: 
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except Exception:
        proc = None
    if (proc is not None and proc.returncode == 0 and out_file and os.path.isfile(out_file) and os.path.getsize(out_file) > 0): 
        return True
    if proc is not None: 
        _log("FFmpeg falhou (rc=%s): %s" % (proc.returncode, (proc.stdout or "")[-800:]))
    QMessageBox.warning(main_window, "Scenes", "Falha ao executar o FFmpeg. Os frames PNG foram mantidos em:\n" + png_dir)
    return False

class FfmpegDownloadWorker(QThread):
    progresso = Signal(int, str)
    concluido = Signal(bool, str)
    URLS = ["https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip", "https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-win64-gpl.zip"]
    
    def __init__(self, dest_dir, _t_func, parent=None):
        super().__init__(parent)
        self.dest_dir = dest_dir
        self._t = _t_func
        self._cancel = False
        
    def cancelar(self): self._cancel = True
    
    def _baixar(self, url, zip_path):
        req = urllib.request.Request(url, headers={"User-Agent": "igz_tb_scenes/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp, open(zip_path, "wb") as out:
            total = int(resp.headers.get("Content-Length", 0) or 0)
            lido = 0
            while True:
                if self._cancel: raise RuntimeError(self._t("canceled by user"))
                chunk = resp.read(65536)
                if not chunk: break
                out.write(chunk)
                lido += len(chunk)
                if total: self.progresso.emit(int(lido * 100 / total), self._t("Downloading FFmpeg..."))
                else: self.progresso.emit(-1, self._t("Downloading FFmpeg..."))
                
    def _extrair(self, zip_path):
        with zipfile.ZipFile(zip_path, "r") as zf: zf.extractall(self.dest_dir)
        for root, _, files in os.walk(self.dest_dir):
            for fn in files:
                if fn.lower() == "ffmpeg.exe": return os.path.join(root, fn)
        return ""
        
    def run(self):
        os.makedirs(self.dest_dir, exist_ok=True)
        zip_path = os.path.join(self.dest_dir, "ffmpeg_download.zip")
        erros = []
        for url in self.URLS:
            if self._cancel:
                self.concluido.emit(False, self._t("Canceled."))
                return
            try:
                self.progresso.emit(0, self._t("Downloading from {host}...", host=url.split("/")[2]))
                self._baixar(url, zip_path)
                self.progresso.emit(-1, self._t("Extracting..."))
                exe = self._extrair(zip_path)
                if exe:
                    set_config_value("ffmpeg_path", exe)
                    try: os.remove(zip_path)
                    except Exception: pass
                    self.concluido.emit(True, exe)
                    return
                erros.append(self._t("{url}: ffmpeg.exe not found in the package", url=url))
            except Exception as exc:
                erros.append(f"{url}: {exc}")
        self.concluido.emit(False, "\n".join(erros) or self._t("Download failed."))