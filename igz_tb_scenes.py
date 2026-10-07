# =========================================================================
# Extension: igz_tb_scenes — Gerenciador de Cenas (Scenes)
# Author: Ezequiel M Rezende
# Version: 1.0.0
# License: GPL-3.0-or-later (same as IngeTrazo)
#
# Plugin INDEPENDENTE (não modifica a igz_tb_camera). Reaproveita apenas o
# PADRÃO do igz_tb_camera.py como referência: captura de eye/target, caixas
# QDialog/QFormLayout e exportação de frames por grabFramebuffer. Mantém
# compatibilidade total com OrbitPickerTool, ZAxisOverlay, órbitas/helix e
# ajuste de Z, que continuam na extensão igz_tb_camera.
# =========================================================================
from __future__ import annotations

import math
import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
import urllib.request
import zipfile

from PySide6.QtCore import (
    Qt,
    QTimer,
    QStandardPaths,
    QThread,
    Signal,
)
from PySide6.QtGui import (
    QAction,
    QIcon,
    QVector3D,
    QPalette,
)
from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
    QToolBar,
    QSizePolicy,
    QDialog,
    QFormLayout,
    QVBoxLayout,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox,
    QDialogButtonBox,
    QFileDialog,
    QWidget,
    QListWidget,
    QListWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QLabel,
    QDockWidget,
    QGroupBox,
    QPushButton,
    QCheckBox,
    QProgressBar,
    QPlainTextEdit,
    QHBoxLayout,
    QGridLayout,
    QSplitter,
    QTabWidget,
    QScrollArea,
    QFrame,
)


DEBUG = True


def _log(s):
    if DEBUG:
        print(f"[igz_tb_scenes] {s}", file=sys.stderr, flush=True)


_EPS = 1e-8


# =========================================================================
# INTERNACIONALIZAÇÃO (i18n) — idioma-fonte: inglês (en-US)
# Usa o ``core.i18n`` do IngeTrazo quando disponível; fora dele, cai para as
# traduções locais em ``_TEXTS``. As chaves são as strings-fonte em inglês.
# =========================================================================
try:
    from core.i18n import tr as _tr_i18n
    from core.i18n import current_language as _current_language
except Exception:  # rodando fora do IngeTrazo: cai para o inglês
    def _tr_i18n(s, **kw):
        return s.format(**kw) if kw else s

    def _current_language():
        return "en"


#: Traduções desta extensão (chave = string-fonte em inglês).
_TEXTS = {"pt-BR": {}, "es": {}, "it": {}, "de": {}}


def _lang_key():
    """Idioma atual (ex.: 'pt-BR'); tolera variantes como 'pt_BR'/'pt'."""
    try:
        lang = str(_current_language() or "en").strip().replace("_", "-")
    except Exception:
        return "en"
    if lang in _TEXTS:
        return lang
    base = lang.split("-")[0].lower()
    for key in _TEXTS:
        if key.lower().split("-")[0] == base:
            return key
    return lang


def _t(text, **kw):
    """Devolve ``text`` (fonte em inglês) no idioma atual da interface."""
    try:
        x = _tr_i18n(text)
        if isinstance(x, str) and x != text:
            return x.format(**kw) if kw else x
    except Exception:
        pass
    out = _TEXTS.get(_lang_key(), {}).get(text, text)
    return out.format(**kw) if kw else out


#: Valores canônicos de suavização (nunca traduzidos; só o rótulo é).
_SMOOTH_KEYS = ("Smooth", "Linear", "Catmull-Rom")


def _norm_smooth(value):
    v = str(value or "").strip()
    low = v.lower()
    if low in ("", "suave", "smooth"):
        return "Smooth"
    if low == "linear":
        return "Linear"
    if low in ("catmull-rom", "catmull_rom", "catmullrom"):
        return "Catmull-Rom"
    return v or "Smooth"


def _fill_smooth_combo(combo, current):
    """Preenche um QComboBox com os modos de suavização (rótulo traduzido)."""
    combo.clear()
    for key in _SMOOTH_KEYS:
        combo.addItem(_t(key), key)
    idx = combo.findData(_norm_smooth(current))
    combo.setCurrentIndex(idx if idx >= 0 else 0)


def _current_smooth(combo):
    """Valor canônico selecionado no combo de suavização."""
    data = combo.currentData()
    return str(data) if data is not None else _norm_smooth(combo.currentText())


# --- Frases da interface (chave = string-fonte em inglês) ---
_TEXTS["pt-BR"].update({
    # Títulos de janelas / diálogos
    "Scenes - Timings and Frames": "Scenes - Tempos e Quadros",
    "Scenes - Export Animation": "Scenes - Exportar Animação",
    "Scenes - Video Dependencies": "Scenes - Dependências de Vídeo",
    # Diálogo de tempos e quadros
    "Frames per second (FPS):": "Quadros por segundo (FPS):",
    "Camera interpolation:": "Interpolação da câmera:",
    "Loop?": "Repetir em loop?",
    "Default transition:": "Transição padrão:",
    "Default hold:": "Permanência padrão:",
    "Scene timings (edit columns 2 and 3):": "Tempos por cena (edite as colunas 2 e 3):",
    "Hold (s)": "Permanência (s)",
    "Transition (s)": "Transição (s)",
    # Suavização / Sim-Não
    "Smooth": "Suave",
    "Linear": "Linear",
    "Yes": "Sim",
    "No": "Não",
    # Diálogo de exportação
    "PNG image sequence": "Sequência de Imagens PNG",
    "MP4 video": "Vídeo MP4",
    "Output format:": "Formato de saída:",
    "W": "L",
    "x  H": "x  A",
    "Size (W × H):": "Tamanho (L x A):",
    "Keep screen aspect ratio": "Manter proporção da tela",
    "Current screen size": "Tamanho da tela atual",
    "Summary:": "Resumo:",
    "{n} scene(s) - {total:.2f}s - ~{frames} frames - {w}x{h} px": "{n} cena(s) - {total:.2f}s - ~{frames} frames - {w}x{h} px",
    # Exportação
    "There are no scenes to export.": "Não há cenas para exportar.",
    "Viewport not found.": "Viewport não encontrada.",
    "Folder to save the PNG images": "Pasta para salvar as imagens PNG",
    "Save MP4 video": "Salvar vídeo MP4",
    "animation.mp4": "animacao.mp4",
    "MP4 video (*.mp4)": "Vídeo MP4 (*.mp4)",
    "FFmpeg was not found.": "O FFmpeg não foi encontrado.",
    "Do you want to configure/download FFmpeg now?\nOtherwise, the animation will be exported as a PNG image sequence.": "Deseja configurar/baixar o FFmpeg agora?\nSe preferir, a animação será exportada como sequência de imagens PNG.",
    "Configure / Download...": "Configurar / Baixar...",
    "Export PNG": "Exportar PNG",
    "Cancel": "Cancelar",
    "Could not generate the MP4 video.\nThe PNG frames were kept in:\n": "Não foi possível gerar o vídeo MP4.\nOs frames PNG foram mantidos em:\n",
    "Export finished: {n} frames.": "Exportação concluída: {n} frames.",
    "Failed to run FFmpeg. The PNG frames were kept in:\n": "Falha ao executar o FFmpeg. Os frames PNG foram mantidos em:\n",
    # Controlador
    "There are no scenes to remove.": "Não há cenas para remover.",
    "Choose the scene to remove:": "Escolha a cena a remover:",
    "{name} removed.": "{name} removida.",
    "Remove ALL {n} scenes?": "Remover TODAS as {n} cenas?",
    "All scenes were removed.": "Todas as cenas foram removidas.",
    "Add at least one scene (2 or more recommended).": "Adicione pelo menos uma cena (recomendado: 2 ou mais).",
    "Playing scene animation...": "Reproduzindo animação de cenas...",
    "Timing and frame settings updated.": "Configuração de tempos e quadros atualizada.",
    "Scene": "Cena",
    "Scene {n}": "Cena {n}",
    "{name} added (eye=({ex:.2f}, {ey:.2f}, {ez:.2f}), fov={fov:.1f}).": "{name} adicionada (eye=({ex:.2f}, {ey:.2f}, {ez:.2f}), fov={fov:.1f}).",
})


_TEXTS["pt-BR"].update({
    # Painel lateral
    "Scenes": "Cenas",
    "Scenes are saved inside the project's .igz file.": "As cenas são salvas dentro do arquivo .igz do projeto.",
    "Add": "Adicionar",
    "Remove": "Remover",
    "Clear": "Limpar",
    "Playback": "Reprodução",
    "Play": "Tocar",
    "Stop": "Parar",
    "Loop": "Repetir em loop",
    "Timings and Frames": "Tempos e Quadros",
    "Interpolation:": "Interpolação:",
    "Apply settings": "Aplicar configuração",
    "Export": "Exportação",
    "Export Animation": "Exportar Animação",
    "Video Dependencies": "Dependências de Vídeo",
    "Settings applied.": "Configuração aplicada.",
    "{n} scene(s) — {total:.2f}s — ~{frames} frames": "{n} cena(s) — {total:.2f}s — ~{frames} frames",
    "available": "disponível",
    "missing": "ausente",
    # Dependências de vídeo
    "MP4 export uses <b>FFmpeg</b>.\nCheck the status below and download it if it is missing.": "A exportação para MP4 usa o <b>FFmpeg</b>.\nVerifique o estado abaixo e baixe-o se estiver ausente.",
    "Download FFmpeg": "Baixar FFmpeg",
    "Downloads and extracts FFmpeg (~90 MB) to the plugin's local folder.": "Baixa e extrai o FFmpeg (~90 MB) para a pasta local do plugin.",
    "Browse...": "Procurar...",
    "Select an already installed ffmpeg(.exe).": "Selecionar um ffmpeg(.exe) já instalado.",
    "Refresh status": "Atualizar status",
    "Open folder": "Abrir pasta",
    "MISSING": "AUSENTE",
    "absent": "ausente",
    "Downloading FFmpeg... (may take a while / ~90 MB)": "Baixando FFmpeg... (pode demorar / ~90 MB)",
    "FFmpeg ready at: {path}": "FFmpeg pronto em: {path}",
    "FFmpeg failure: {msg}": "Falha no FFmpeg: {msg}",
    "Select the ffmpeg executable": "Selecione o executável ffmpeg",
    "All files (*.*)": "Todos os arquivos (*.*)",
    "FFmpeg set: {path}": "FFmpeg configurado: {path}",
    "Dependencies folder: {path}": "Pasta de dependências: {path}",
    # Downloader (FFmpeg)
    "canceled by user": "cancelado pelo usuário",
    "Downloading FFmpeg...": "Baixando FFmpeg...",
    "Canceled.": "Cancelado.",
    "Downloading from {host}...": "Baixando de {host}...",
    "Extracting...": "Extraindo...",
    "{url}: ffmpeg.exe not found in the package": "{url}: ffmpeg.exe não encontrado no pacote",
    "Download failed.": "Falha no download.",
    # Barra de ferramentas
    "Add Current Scene": "Adicionar Cena Atual",
    "Captures the current camera's eye, target and fov as a new scene.": "Captura eye, target e fov da câmera atual como uma nova cena.",
    "Remove Selected Scene": "Remover Cena Selecionada",
    "Removes the currently selected scene from the list.": "Remove a cena atualmente selecionada da lista.",
    "Clear Scenes": "Limpar Cenas",
    "Removes ALL scenes from the list.": "Remove TODAS as cenas da lista.",
    "Play Scene Animation": "Tocar Animação de Cenas",
    "Smoothly plays through the scenes stored in the viewport.": "Percorre suavemente as cenas armazenadas na viewport.",
    "Stop Animation": "Parar Animação",
    "Stops the running scene animation.": "Interrompe a animação de cenas em execução.",
    "Configure Timings and Frames": "Configurar Tempos e Quadros",
    "Configures FPS, interpolation, loop and per-scene timings.": "Configura FPS, interpolação, loop e os tempos por cena.",
    "Exports the animation as a PNG sequence or MP4 video.": "Exporta a animação como sequência PNG ou vídeo MP4.",
    "Configure/download FFmpeg to export MP4.": "Configurar/baixar o FFmpeg para exportar MP4.",
    "Scenes Panel": "Painel de Cenas",
    "Show/hide the scenes panel.": "Mostrar/ocultar o painel de cenas.",
    "Go to the scenes tab.": "Ir para a aba de cenas.",
})


_TEXTS["es"].update({
    # Títulos de ventanas / diálogos
    "Scenes - Timings and Frames": "Scenes - Tiempos y Fotogramas",
    "Scenes - Export Animation": "Scenes - Exportar Animación",
    "Scenes - Video Dependencies": "Scenes - Dependencias de Vídeo",
    # Diálogo de tiempos y fotogramas
    "Frames per second (FPS):": "Fotogramas por segundo (FPS):",
    "Camera interpolation:": "Interpolación de la cámara:",
    "Loop?": "¿Repetir en bucle?",
    "Default transition:": "Transición predeterminada:",
    "Default hold:": "Permanencia predeterminada:",
    "Scene timings (edit columns 2 and 3):": "Tiempos por escena (edite las columnas 2 y 3):",
    "Hold (s)": "Permanencia (s)",
    "Transition (s)": "Transición (s)",
    # Suavizado / Sí-No
    "Smooth": "Suave",
    "Linear": "Lineal",
    "Yes": "Sí",
    "No": "No",
    # Diálogo de exportación
    "PNG image sequence": "Secuencia de imágenes PNG",
    "MP4 video": "Vídeo MP4",
    "Output format:": "Formato de salida:",
    "W": "A",
    "x  H": "x  H",
    "Size (W × H):": "Tamaño (A × H):",
    "Keep screen aspect ratio": "Mantener relación de aspecto de la pantalla",
    "Current screen size": "Tamaño de pantalla actual",
    "Summary:": "Resumen:",
    "{n} scene(s) - {total:.2f}s - ~{frames} frames - {w}x{h} px": "{n} escena(s) - {total:.2f}s - ~{frames} fotogramas - {w}x{h} px",
    # Exportación
    "There are no scenes to export.": "No hay escenas para exportar.",
    "Viewport not found.": "No se encontró el viewport.",
    "Folder to save the PNG images": "Carpeta para guardar las imágenes PNG",
    "Save MP4 video": "Guardar vídeo MP4",
    "animation.mp4": "animacion.mp4",
    "MP4 video (*.mp4)": "Vídeo MP4 (*.mp4)",
    "FFmpeg was not found.": "No se encontró FFmpeg.",
    "Do you want to configure/download FFmpeg now?\nOtherwise, the animation will be exported as a PNG image sequence.": "¿Desea configurar/descargar FFmpeg ahora?\nSi lo prefiere, la animación se exportará como una secuencia de imágenes PNG.",
    "Configure / Download...": "Configurar / Descargar...",
    "Export PNG": "Exportar PNG",
    "Cancel": "Cancelar",
    "Could not generate the MP4 video.\nThe PNG frames were kept in:\n": "No se pudo generar el vídeo MP4.\nLos fotogramas PNG se guardaron en:\n",
    "Export finished: {n} frames.": "Exportación finalizada: {n} fotogramas.",
    "Failed to run FFmpeg. The PNG frames were kept in:\n": "Error al ejecutar FFmpeg. Los fotogramas PNG se guardaron en:\n",
    # Controlador
    "There are no scenes to remove.": "No hay escenas para eliminar.",
    "Choose the scene to remove:": "Elija la escena a eliminar:",
    "{name} removed.": "{name} eliminada.",
    "Remove ALL {n} scenes?": "¿Eliminar TODAS las {n} escenas?",
    "All scenes were removed.": "Se eliminaron todas las escenas.",
    "Add at least one scene (2 or more recommended).": "Añada al menos una escena (recomendado: 2 o más).",
    "Playing scene animation...": "Reproduciendo la animación de escenas...",
    "Timing and frame settings updated.": "Configuración de tiempos y fotogramas actualizada.",
    "Scene": "Escena",
    "Scene {n}": "Escena {n}",
    "{name} added (eye=({ex:.2f}, {ey:.2f}, {ez:.2f}), fov={fov:.1f}).": "{name} añadida (eye=({ex:.2f}, {ey:.2f}, {ez:.2f}), fov={fov:.1f}).",
})


_TEXTS["es"].update({
    # Panel lateral
    "Scenes": "Escenas",
    "Scenes are saved inside the project's .igz file.": "Las escenas se guardan dentro del archivo .igz del proyecto.",
    "Add": "Añadir",
    "Remove": "Eliminar",
    "Clear": "Limpiar",
    "Playback": "Reproducción",
    "Play": "Reproducir",
    "Stop": "Detener",
    "Loop": "Repetir en bucle",
    "Timings and Frames": "Tiempos y Fotogramas",
    "Interpolation:": "Interpolación:",
    "Apply settings": "Aplicar configuración",
    "Export": "Exportación",
    "Export Animation": "Exportar Animación",
    "Video Dependencies": "Dependencias de vídeo",
    "Settings applied.": "Configuración aplicada.",
    "{n} scene(s) — {total:.2f}s — ~{frames} frames": "{n} escena(s) — {total:.2f}s — ~{frames} fotogramas",
    "available": "disponible",
    "missing": "ausente",
    # Dependencias de vídeo
    "MP4 export uses <b>FFmpeg</b>.\nCheck the status below and download it if it is missing.": "La exportación a MP4 usa <b>FFmpeg</b>.\nCompruebe el estado a continuación y descárguelo si falta.",
    "Download FFmpeg": "Descargar FFmpeg",
    "Downloads and extracts FFmpeg (~90 MB) to the plugin's local folder.": "Descarga y extrae FFmpeg (~90 MB) en la carpeta local del plugin.",
    "Browse...": "Examinar...",
    "Select an already installed ffmpeg(.exe).": "Seleccionar un ffmpeg(.exe) ya instalado.",
    "Refresh status": "Actualizar estado",
    "Open folder": "Abrir carpeta",
    "MISSING": "AUSENTE",
    "absent": "ausente",
    "Downloading FFmpeg... (may take a while / ~90 MB)": "Descargando FFmpeg... (puede tardar / ~90 MB)",
    "FFmpeg ready at: {path}": "FFmpeg listo en: {path}",
    "FFmpeg failure: {msg}": "Error de FFmpeg: {msg}",
    "Select the ffmpeg executable": "Seleccione el ejecutable ffmpeg",
    "All files (*.*)": "Todos los archivos (*.*)",
    "FFmpeg set: {path}": "FFmpeg configurado: {path}",
    "Dependencies folder: {path}": "Carpeta de dependencias: {path}",
    # Descargador (FFmpeg)
    "canceled by user": "cancelado por el usuario",
    "Downloading FFmpeg...": "Descargando FFmpeg...",
    "Canceled.": "Cancelado.",
    "Downloading from {host}...": "Descargando desde {host}...",
    "Extracting...": "Extrayendo...",
    "{url}: ffmpeg.exe not found in the package": "{url}: no se encontró ffmpeg.exe en el paquete",
    "Download failed.": "Error en la descarga.",
    # Barra de herramientas
    "Add Current Scene": "Añadir escena actual",
    "Captures the current camera's eye, target and fov as a new scene.": "Captura el eye, target y fov de la cámara actual como una nueva escena.",
    "Remove Selected Scene": "Eliminar escena seleccionada",
    "Removes the currently selected scene from the list.": "Elimina de la lista la escena seleccionada actualmente.",
    "Clear Scenes": "Limpiar escenas",
    "Removes ALL scenes from the list.": "Elimina TODAS las escenas de la lista.",
    "Play Scene Animation": "Reproducir animación de escenas",
    "Smoothly plays through the scenes stored in the viewport.": "Recorre suavemente las escenas almacenadas en el viewport.",
    "Stop Animation": "Detener animación",
    "Stops the running scene animation.": "Detiene la animación de escenas en ejecución.",
    "Configure Timings and Frames": "Configurar tiempos y fotogramas",
    "Configures FPS, interpolation, loop and per-scene timings.": "Configura FPS, interpolación, bucle y los tiempos por escena.",
    "Exports the animation as a PNG sequence or MP4 video.": "Exporta la animación como secuencia PNG o vídeo MP4.",
    "Configure/download FFmpeg to export MP4.": "Configurar/descargar FFmpeg para exportar MP4.",
    "Scenes Panel": "Panel de escenas",
    "Show/hide the scenes panel.": "Mostrar/ocultar el panel de escenas.",
    "Go to the scenes tab.": "Ir a la pestaña de escenas.",
})


_TEXTS["it"].update({
    # Titoli finestre / dialoghi
    "Scenes - Timings and Frames": "Scenes - Tempi e Fotogrammi",
    "Scenes - Export Animation": "Scenes - Esporta Animazione",
    "Scenes - Video Dependencies": "Scenes - Dipendenze Video",
    # Dialogo tempi e fotogrammi
    "Frames per second (FPS):": "Fotogrammi al secondo (FPS):",
    "Camera interpolation:": "Interpolazione della camera:",
    "Loop?": "Ripetere in loop?",
    "Default transition:": "Transizione predefinita:",
    "Default hold:": "Permanenza predefinita:",
    "Scene timings (edit columns 2 and 3):": "Tempi per scena (modifica le colonne 2 e 3):",
    "Hold (s)": "Permanenza (s)",
    "Transition (s)": "Transizione (s)",
    # Levigatezza / Sì-No
    "Smooth": "Fluido",
    "Linear": "Lineare",
    "Yes": "Sì",
    "No": "No",
    # Dialogo esportazione
    "PNG image sequence": "Sequenza di immagini PNG",
    "MP4 video": "Video MP4",
    "Output format:": "Formato di output:",
    "W": "L",
    "x  H": "x  H",
    "Size (W × H):": "Dimensione (L × H):",
    "Keep screen aspect ratio": "Mantieni le proporzioni dello schermo",
    "Current screen size": "Dimensioni schermo attuali",
    "Summary:": "Riepilogo:",
    "{n} scene(s) - {total:.2f}s - ~{frames} frames - {w}x{h} px": "{n} scena/e - {total:.2f}s - ~{frames} fotogrammi - {w}x{h} px",
    # Esportazione
    "There are no scenes to export.": "Non ci sono scene da esportare.",
    "Viewport not found.": "Viewport non trovato.",
    "Folder to save the PNG images": "Cartella dove salvare le immagini PNG",
    "Save MP4 video": "Salva video MP4",
    "animation.mp4": "animazione.mp4",
    "MP4 video (*.mp4)": "Video MP4 (*.mp4)",
    "FFmpeg was not found.": "FFmpeg non è stato trovato.",
    "Do you want to configure/download FFmpeg now?\nOtherwise, the animation will be exported as a PNG image sequence.": "Vuoi configurare/scaricare FFmpeg adesso?\nIn alternativa, l'animazione verrà esportata come sequenza di immagini PNG.",
    "Configure / Download...": "Configura / Scarica...",
    "Export PNG": "Esporta PNG",
    "Cancel": "Annulla",
    "Could not generate the MP4 video.\nThe PNG frames were kept in:\n": "Impossibile generare il video MP4.\nI fotogrammi PNG sono stati salvati in:\n",
    "Export finished: {n} frames.": "Esportazione completata: {n} fotogrammi.",
    "Failed to run FFmpeg. The PNG frames were kept in:\n": "Impossibile eseguire FFmpeg. I fotogrammi PNG sono stati salvati in:\n",
    # Controller
    "There are no scenes to remove.": "Non ci sono scene da rimuovere.",
    "Choose the scene to remove:": "Scegli la scena da rimuovere:",
    "{name} removed.": "{name} rimossa.",
    "Remove ALL {n} scenes?": "Rimuovere TUTTE le {n} scene?",
    "All scenes were removed.": "Tutte le scene sono state rimosse.",
    "Add at least one scene (2 or more recommended).": "Aggiungi almeno una scena (consigliato: 2 o più).",
    "Playing scene animation...": "Riproduzione dell'animazione delle scene...",
    "Timing and frame settings updated.": "Impostazioni di tempi e fotogrammi aggiornate.",
    "Scene": "Scena",
    "Scene {n}": "Scena {n}",
    "{name} added (eye=({ex:.2f}, {ey:.2f}, {ez:.2f}), fov={fov:.1f}).": "{name} aggiunta (eye=({ex:.2f}, {ey:.2f}, {ez:.2f}), fov={fov:.1f}).",
})


_TEXTS["it"].update({
    # Pannello laterale
    "Scenes": "Scene",
    "Scenes are saved inside the project's .igz file.": "Le scene sono salvate all'interno del file .igz del progetto.",
    "Add": "Aggiungi",
    "Remove": "Rimuovi",
    "Clear": "Svuota",
    "Playback": "Riproduzione",
    "Play": "Riproduci",
    "Stop": "Interrompi",
    "Loop": "Ripeti in loop",
    "Timings and Frames": "Tempi e Fotogrammi",
    "Interpolation:": "Interpolazione:",
    "Apply settings": "Applica impostazioni",
    "Export": "Esportazione",
    "Export Animation": "Esporta Animazione",
    "Video Dependencies": "Dipendenze video",
    "Settings applied.": "Impostazioni applicate.",
    "{n} scene(s) — {total:.2f}s — ~{frames} frames": "{n} scena/e — {total:.2f}s — ~{frames} fotogrammi",
    "available": "disponibile",
    "missing": "assente",
    # Dipendenze video
    "MP4 export uses <b>FFmpeg</b>.\nCheck the status below and download it if it is missing.": "L'esportazione in MP4 usa <b>FFmpeg</b>.\nControlla lo stato qui sotto e scaricalo se manca.",
    "Download FFmpeg": "Scarica FFmpeg",
    "Downloads and extracts FFmpeg (~90 MB) to the plugin's local folder.": "Scarica ed estrae FFmpeg (~90 MB) nella cartella locale del plugin.",
    "Browse...": "Sfoglia...",
    "Select an already installed ffmpeg(.exe).": "Seleziona un ffmpeg(.exe) già installato.",
    "Refresh status": "Aggiorna stato",
    "Open folder": "Apri cartella",
    "MISSING": "ASSENTE",
    "absent": "assente",
    "Downloading FFmpeg... (may take a while / ~90 MB)": "Scaricamento di FFmpeg... (può richiedere tempo / ~90 MB)",
    "FFmpeg ready at: {path}": "FFmpeg pronto in: {path}",
    "FFmpeg failure: {msg}": "Errore FFmpeg: {msg}",
    "Select the ffmpeg executable": "Seleziona l'eseguibile ffmpeg",
    "All files (*.*)": "Tutti i file (*.*)",
    "FFmpeg set: {path}": "FFmpeg configurato: {path}",
    "Dependencies folder: {path}": "Cartella delle dipendenze: {path}",
    # Downloader (FFmpeg)
    "canceled by user": "annullato dall'utente",
    "Downloading FFmpeg...": "Scaricamento di FFmpeg...",
    "Canceled.": "Annullato.",
    "Downloading from {host}...": "Scaricamento da {host}...",
    "Extracting...": "Estrazione...",
    "{url}: ffmpeg.exe not found in the package": "{url}: ffmpeg.exe non trovato nel pacchetto",
    "Download failed.": "Download non riuscito.",
    # Barra degli strumenti
    "Add Current Scene": "Aggiungi scena corrente",
    "Captures the current camera's eye, target and fov as a new scene.": "Cattura eye, target e fov della camera corrente come nuova scena.",
    "Remove Selected Scene": "Rimuovi scena selezionata",
    "Removes the currently selected scene from the list.": "Rimuove dalla lista la scena attualmente selezionata.",
    "Clear Scenes": "Svuota scene",
    "Removes ALL scenes from the list.": "Rimuove TUTTE le scene dalla lista.",
    "Play Scene Animation": "Riproduci animazione delle scene",
    "Smoothly plays through the scenes stored in the viewport.": "Percorre fluidamente le scene memorizzate nel viewport.",
    "Stop Animation": "Interrompi animazione",
    "Stops the running scene animation.": "Interrompe l'animazione delle scene in esecuzione.",
    "Configure Timings and Frames": "Configura tempi e fotogrammi",
    "Configures FPS, interpolation, loop and per-scene timings.": "Configura FPS, interpolazione, loop e i tempi per scena.",
    "Exports the animation as a PNG sequence or MP4 video.": "Esporta l'animazione come sequenza PNG o video MP4.",
    "Configure/download FFmpeg to export MP4.": "Configura/scarica FFmpeg per esportare in MP4.",
    "Scenes Panel": "Pannello scene",
    "Show/hide the scenes panel.": "Mostra/nascondi il pannello delle scene.",
    "Go to the scenes tab.": "Vai alla scheda delle scene.",
})


_TEXTS["de"].update({
    # Fenstertitel / Dialoge
    "Scenes - Timings and Frames": "Scenes - Zeiten und Bilder",
    "Scenes - Export Animation": "Scenes - Animation exportieren",
    "Scenes - Video Dependencies": "Scenes - Video-Abhängigkeiten",
    # Dialog Zeiten und Bilder
    "Frames per second (FPS):": "Bilder pro Sekunde (FPS):",
    "Camera interpolation:": "Kamera-Interpolation:",
    "Loop?": "In Schleife wiederholen?",
    "Default transition:": "Standardübergang:",
    "Default hold:": "Standardverweildauer:",
    "Scene timings (edit columns 2 and 3):": "Zeiten pro Szene (Spalten 2 und 3 bearbeiten):",
    "Hold (s)": "Verweildauer (s)",
    "Transition (s)": "Übergang (s)",
    # Glättung / Ja-Nein
    "Smooth": "Weich",
    "Linear": "Linear",
    "Yes": "Ja",
    "No": "Nein",
    # Dialog Export
    "PNG image sequence": "PNG-Bildsequenz",
    "MP4 video": "MP4-Video",
    "Output format:": "Ausgabeformat:",
    "W": "B",
    "x  H": "x  H",
    "Size (W × H):": "Größe (B × H):",
    "Keep screen aspect ratio": "Seitenverhältnis des Bildschirms beibehalten",
    "Current screen size": "Aktuelle Bildschirmgröße",
    "Summary:": "Zusammenfassung:",
    "{n} scene(s) - {total:.2f}s - ~{frames} frames - {w}x{h} px": "{n} Szene(n) - {total:.2f}s - ~{frames} Bilder - {w}x{h} px",
    # Export
    "There are no scenes to export.": "Es gibt keine Szenen zum Exportieren.",
    "Viewport not found.": "Viewport nicht gefunden.",
    "Folder to save the PNG images": "Ordner zum Speichern der PNG-Bilder",
    "Save MP4 video": "MP4-Video speichern",
    "animation.mp4": "animation.mp4",
    "MP4 video (*.mp4)": "MP4-Video (*.mp4)",
    "FFmpeg was not found.": "FFmpeg wurde nicht gefunden.",
    "Do you want to configure/download FFmpeg now?\nOtherwise, the animation will be exported as a PNG image sequence.": "Möchten Sie FFmpeg jetzt konfigurieren/herunterladen?\nAndernfalls wird die Animation als PNG-Bildsequenz exportiert.",
    "Configure / Download...": "Konfigurieren / Herunterladen...",
    "Export PNG": "PNG exportieren",
    "Cancel": "Abbrechen",
    "Could not generate the MP4 video.\nThe PNG frames were kept in:\n": "Das MP4-Video konnte nicht erstellt werden.\nDie PNG-Bilder wurden gespeichert in:\n",
    "Export finished: {n} frames.": "Export abgeschlossen: {n} Bilder.",
    "Failed to run FFmpeg. The PNG frames were kept in:\n": "FFmpeg konnte nicht ausgeführt werden. Die PNG-Bilder wurden gespeichert in:\n",
    # Controller
    "There are no scenes to remove.": "Es gibt keine Szenen zum Entfernen.",
    "Choose the scene to remove:": "Wählen Sie die zu entfernende Szene:",
    "{name} removed.": "{name} entfernt.",
    "Remove ALL {n} scenes?": "ALLE {n} Szenen entfernen?",
    "All scenes were removed.": "Alle Szenen wurden entfernt.",
    "Add at least one scene (2 or more recommended).": "Fügen Sie mindestens eine Szene hinzu (empfohlen: 2 oder mehr).",
    "Playing scene animation...": "Szenen-Animation wird abgespielt...",
    "Timing and frame settings updated.": "Zeit- und Bild-Einstellungen aktualisiert.",
    "Scene": "Szene",
    "Scene {n}": "Szene {n}",
    "{name} added (eye=({ex:.2f}, {ey:.2f}, {ez:.2f}), fov={fov:.1f}).": "{name} hinzugefügt (eye=({ex:.2f}, {ey:.2f}, {ez:.2f}), fov={fov:.1f}).",
})


_TEXTS["de"].update({
    # Seitenpanel
    "Scenes": "Szenen",
    "Scenes are saved inside the project's .igz file.": "Die Szenen werden in der .igz-Datei des Projekts gespeichert.",
    "Add": "Hinzufügen",
    "Remove": "Entfernen",
    "Clear": "Leeren",
    "Playback": "Wiedergabe",
    "Play": "Abspielen",
    "Stop": "Stopp",
    "Loop": "Schleife",
    "Timings and Frames": "Zeiten und Bilder",
    "Interpolation:": "Interpolation:",
    "Apply settings": "Einstellungen anwenden",
    "Export": "Export",
    "Export Animation": "Animation exportieren",
    "Video Dependencies": "Video-Abhängigkeiten",
    "Settings applied.": "Einstellungen angewendet.",
    "{n} scene(s) — {total:.2f}s — ~{frames} frames": "{n} Szene(n) — {total:.2f}s — ~{frames} Bilder",
    "available": "verfügbar",
    "missing": "fehlt",
    # Video-Abhängigkeiten
    "MP4 export uses <b>FFmpeg</b>.\nCheck the status below and download it if it is missing.": "Der MP4-Export verwendet <b>FFmpeg</b>.\nPrüfen Sie den Status unten und laden Sie es herunter, falls es fehlt.",
    "Download FFmpeg": "FFmpeg herunterladen",
    "Downloads and extracts FFmpeg (~90 MB) to the plugin's local folder.": "Lädt FFmpeg (~90 MB) herunter und entpackt es in den lokalen Plugin-Ordner.",
    "Browse...": "Durchsuchen...",
    "Select an already installed ffmpeg(.exe).": "Eine bereits installierte ffmpeg(.exe) auswählen.",
    "Refresh status": "Status aktualisieren",
    "Open folder": "Ordner öffnen",
    "MISSING": "FEHLT",
    "absent": "fehlt",
    "Downloading FFmpeg... (may take a while / ~90 MB)": "FFmpeg wird heruntergeladen... (kann dauern / ~90 MB)",
    "FFmpeg ready at: {path}": "FFmpeg bereit unter: {path}",
    "FFmpeg failure: {msg}": "FFmpeg-Fehler: {msg}",
    "Select the ffmpeg executable": "Wählen Sie die ffmpeg-Anwendung",
    "All files (*.*)": "Alle Dateien (*.*)",
    "FFmpeg set: {path}": "FFmpeg konfiguriert: {path}",
    "Dependencies folder: {path}": "Abhängigkeitsordner: {path}",
    # Downloader (FFmpeg)
    "canceled by user": "vom Benutzer abgebrochen",
    "Downloading FFmpeg...": "FFmpeg wird heruntergeladen...",
    "Canceled.": "Abgebrochen.",
    "Downloading from {host}...": "Herunterladen von {host}...",
    "Extracting...": "Wird entpackt...",
    "{url}: ffmpeg.exe not found in the package": "{url}: ffmpeg.exe im Paket nicht gefunden",
    "Download failed.": "Download fehlgeschlagen.",
    # Symbolleiste
    "Add Current Scene": "Aktuelle Szene hinzufügen",
    "Captures the current camera's eye, target and fov as a new scene.": "Erfasst Eye, Target und FOV der aktuellen Kamera als neue Szene.",
    "Remove Selected Scene": "Ausgewählte Szene entfernen",
    "Removes the currently selected scene from the list.": "Entfernt die aktuell ausgewählte Szene aus der Liste.",
    "Clear Scenes": "Szenen leeren",
    "Removes ALL scenes from the list.": "Entfernt ALLE Szenen aus der Liste.",
    "Play Scene Animation": "Szenen-Animation abspielen",
    "Smoothly plays through the scenes stored in the viewport.": "Spielt die im Viewport gespeicherten Szenen weich ab.",
    "Stop Animation": "Animation stoppen",
    "Stops the running scene animation.": "Stoppt die laufende Szenen-Animation.",
    "Configure Timings and Frames": "Zeiten und Bilder konfigurieren",
    "Configures FPS, interpolation, loop and per-scene timings.": "Konfiguriert FPS, Interpolation, Schleife und Zeiten pro Szene.",
    "Exports the animation as a PNG sequence or MP4 video.": "Exportiert die Animation als PNG-Sequenz oder MP4-Video.",
    "Configure/download FFmpeg to export MP4.": "FFmpeg konfigurieren/herunterladen, um MP4 zu exportieren.",
    "Scenes Panel": "Szenen-Panel",
    "Show/hide the scenes panel.": "Das Szenen-Panel ein-/ausblenden.",
    "Go to the scenes tab.": "Zum Szenen-Tab wechseln.",
})


# IGZ_L10N_ANCHOR


# =========================================================================
# ÍCONES (mesmo esquema da igz_tb_camera)
# =========================================================================
_HERE = os.path.dirname(os.path.abspath(__file__))
_ICONS_DIR = (
    os.path.join(_HERE, "icons")
    if os.path.isdir(os.path.join(_HERE, "icons"))
    else None
)


def _load_themed_icon(base_name: str, main_window) -> QIcon:
    if not _ICONS_DIR:
        return QIcon()

    if base_name.endswith(".svg"):
        base_name = base_name[:-4]

    is_dark = True
    try:
        if main_window is not None:
            palette = main_window.palette()
            bg_color = palette.color(QPalette.Window)
            is_dark = bg_color.lightness() < 128
    except Exception:
        pass

    if not is_dark:
        light_path = os.path.join(_ICONS_DIR, f"{base_name}_light.svg")
        if os.path.isfile(light_path):
            return QIcon(light_path)

    default_path = os.path.join(_ICONS_DIR, f"{base_name}.svg")
    if os.path.isfile(default_path):
        return QIcon(default_path)

    return QIcon()


# =========================================================================
# MATEMÁTICA DE INTERPOLAÇÃO SUAVE
# =========================================================================

def _smoothstep(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return u * u * (3.0 - 2.0 * u)


def _catmull_rom(p0, p1, p2, p3, t):
    """Catmull-Rom componente a componente (p0..p3 são QVector3D)."""
    t2 = t * t
    t3 = t2 * t

    def comp(a, b, c, d):
        return 0.5 * (
            (2.0 * b)
            + (-a + c) * t
            + (2.0 * a - 5.0 * b + 4.0 * c - d) * t2
            + (-a + 3.0 * b - 3.0 * c + d) * t3
        )

    return QVector3D(
        comp(p0.x(), p1.x(), p2.x(), p3.x()),
        comp(p0.y(), p1.y(), p2.y(), p3.y()),
        comp(p0.z(), p1.z(), p2.z(), p3.z()),
    )


# =========================================================================
# ESTRUTURAS DE DADOS
# =========================================================================

class Scene:
    """Um keyframe de câmera (eye, target, fov) + tempos de exibição."""

    def __init__(self, nome, eye, target, fov, hold_s=1.0, transicao_s=2.0):
        self.nome = str(nome)
        self.eye = [float(eye[0]), float(eye[1]), float(eye[2])]
        self.target = [float(target[0]), float(target[1]), float(target[2])]
        self.fov = float(fov)
        self.hold_s = float(hold_s)
        self.transicao_s = float(transicao_s)

    def to_dict(self):
        return {
            "nome": self.nome,
            "eye": list(self.eye),
            "target": list(self.target),
            "fov": self.fov,
            "hold_s": self.hold_s,
            "transicao_s": self.transicao_s,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            d.get("nome", _t("Scene")),
            d.get("eye", [0.0, -10.0, 5.0]),
            d.get("target", [0.0, 0.0, 0.0]),
            d.get("fov", 30.0),
            d.get("hold_s", 1.0),
            d.get("transicao_s", 2.0),
        )


# =========================================================================
# BACKEND DE VÍDEO (FFmpeg) E EXPORTAÇÃO DE IMAGENS
# =========================================================================

def _find_ffmpeg():
    # 1) Caminho configurado manualmente / baixado pelo plugin
    cfg = load_config()
    p = cfg.get("ffmpeg_path")
    if p and os.path.isfile(p):
        return p
    # 2) No PATH do sistema
    p = shutil.which("ffmpeg")
    if p:
        return p
    # 3) Pasta local do plugin (resultado de download automático)
    local = _ffmpeg_local_dir()
    if os.path.isdir(local):
        for root, _, files in os.walk(local):
            for fn in files:
                if fn.lower() in ("ffmpeg.exe", "ffmpeg"):
                    return os.path.join(root, fn)
    # 4) Locais comuns
    candidates = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        os.path.join(
            os.environ.get("ProgramFiles", ""), "ffmpeg", "bin", "ffmpeg.exe"
        ),
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None


# =========================================================================
# CONFIGURAÇÃO PERSISTENTE E STATUS DE DEPENDÊNCIAS (FFmpeg)
# =========================================================================

_CONFIG_CACHE = {"dir": None, "file": None}


def _config_dir() -> str:
    if _CONFIG_CACHE["dir"]:
        return _CONFIG_CACHE["dir"]
    base = ""
    try:
        base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    except Exception:
        base = ""
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


def _ffmpeg_local_dir() -> str:
    return os.path.join(_config_dir(), "ffmpeg")


def _ffmpeg_status():
    p = _find_ffmpeg()
    return (bool(p), p or "")


def _dependencies_report() -> str:
    ok_ff, p_ff = _ffmpeg_status()
    return (
        f"FFmpeg: {'OK' if ok_ff else _t('MISSING')}"
        f"{' - ' + p_ff if p_ff else ''}"
    )


class FfmpegDownloadWorker(QThread):
    progresso = Signal(int, str)
    concluido = Signal(bool, str)

    URLS = [
        "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
        "https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/"
        "ffmpeg-master-latest-win64-gpl.zip",
    ]

    def __init__(self, dest_dir, parent=None):
        super().__init__(parent)
        self.dest_dir = dest_dir
        self._cancel = False

    def cancelar(self):
        self._cancel = True

    def _baixar(self, url, zip_path):
        req = urllib.request.Request(
            url, headers={"User-Agent": "igz_tb_scenes/1.0"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp, open(
            zip_path, "wb"
        ) as out:
            total = int(resp.headers.get("Content-Length", 0) or 0)
            lido = 0
            while True:
                if self._cancel:
                    raise RuntimeError("cancelado pelo usuário")
                chunk = resp.read(65536)
                if not chunk:
                    break
                out.write(chunk)
                lido += len(chunk)
                if total:
                    self.progresso.emit(
                        int(lido * 100 / total), _t("Downloading FFmpeg...")
                    )
                else:
                    self.progresso.emit(-1, _t("Downloading FFmpeg..."))

    def _extrair(self, zip_path):
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(self.dest_dir)
        for root, _, files in os.walk(self.dest_dir):
            for fn in files:
                if fn.lower() == "ffmpeg.exe":
                    return os.path.join(root, fn)
        return ""

    def run(self):
        os.makedirs(self.dest_dir, exist_ok=True)
        zip_path = os.path.join(self.dest_dir, "ffmpeg_download.zip")
        erros = []
        for url in self.URLS:
            if self._cancel:
                self.concluido.emit(False, _t("Canceled."))
                return
            try:
                self.progresso.emit(
                    0, _t("Downloading from {host}...", host=url.split("/")[2])
                )
                self._baixar(url, zip_path)
                self.progresso.emit(-1, _t("Extracting..."))
                exe = self._extrair(zip_path)
                if exe:
                    set_config_value("ffmpeg_path", exe)
                    try:
                        os.remove(zip_path)
                    except Exception:
                        pass
                    self.concluido.emit(True, exe)
                    return
                erros.append(_t(
                    "{url}: ffmpeg.exe not found in the package", url=url
                ))
            except Exception as exc:
                erros.append(f"{url}: {exc}")
        self.concluido.emit(
            False, "\n".join(erros) or _t("Download failed.")
        )


# =========================================================================
# DIÁLOGO: CONFIGURAR / BAIXAR DEPENDÊNCIAS DE VÍDEO
# =========================================================================

class DependencyDialog(QDialog):
    """Configura/baixa o FFmpeg para exportação de vídeo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_t("Scenes - Video Dependencies"))
        self.resize(580, 440)
        self._dl_thread = None

        root = QVBoxLayout(self)
        intro = QLabel(
            _t(
                "MP4 export uses <b>FFmpeg</b>.\n"
                "Check the status below and download it if it is missing."
            )
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        grid = QGridLayout()
        root.addLayout(grid)

        grid.addWidget(QLabel("<b>FFmpeg</b>"), 0, 0)
        self.lbl_ff = QLabel("")
        self.lbl_ff.setWordWrap(True)
        grid.addWidget(self.lbl_ff, 0, 1)
        caixa_ff = QHBoxLayout()
        self.btn_dl = QPushButton(_t("Download FFmpeg"))
        self.btn_dl.setToolTip(
            _t(
                "Downloads and extracts FFmpeg (~90 MB) to the plugin's "
                "local folder."
            )
        )
        self.btn_dl.clicked.connect(self._baixar_ffmpeg)
        caixa_ff.addWidget(self.btn_dl)
        self.btn_local = QPushButton(_t("Browse..."))
        self.btn_local.setToolTip(
            _t("Select an already installed ffmpeg(.exe).")
        )
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
        self.btn_refresh = btns.addButton(
            _t("Refresh status"), QDialogButtonBox.ActionRole
        )
        self.btn_refresh.clicked.connect(self._atualizar_status)
        self.btn_pasta = btns.addButton(
            _t("Open folder"), QDialogButtonBox.ActionRole
        )
        self.btn_pasta.clicked.connect(self._abrir_pasta)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

        self._atualizar_status()


    def _append_log(self, text):
        if text:
            self.log.appendPlainText(str(text))

    def _atualizar_status(self):
        ok_ff, p_ff = _ffmpeg_status()
        self.lbl_ff.setText(
            (_t("available") if ok_ff else _t("MISSING"))
            + (f"\n{p_ff}" if p_ff else "")
        )
        self.btn_dl.setEnabled(not ok_ff)
        self._append_log(
            f"Status -> FFmpeg: {'OK' if ok_ff else _t('absent')}"
        )

    def _baixar_ffmpeg(self):
        self._append_log(
            _t("Downloading FFmpeg... (may take a while / ~90 MB)")
        )
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.btn_dl.setEnabled(False)
        self._dl_thread = FfmpegDownloadWorker(_ffmpeg_local_dir(), self)
        self._dl_thread.progresso.connect(self._dl_progresso)
        self._dl_thread.concluido.connect(self._dl_fim)
        self._dl_thread.start()

    def _dl_progresso(self, pct, msg):
        if pct < 0:
            self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(pct)
        if msg:
            self._append_log(msg)

    def _dl_fim(self, ok, msg):
        self.progress.setRange(0, 100)
        self.progress.setValue(100 if ok else 0)
        if ok:
            self._append_log(_t("FFmpeg ready at: {path}", path=msg))
        else:
            self._append_log(_t("FFmpeg failure: {msg}", msg=(msg or "")))
        self._atualizar_status()

    def _procurar_ffmpeg(self):
        path, _ = QFileDialog.getOpenFileName(
            self, _t("Select the ffmpeg executable"), "",
            "FFmpeg (ffmpeg.exe ffmpeg);;" + _t("All files (*.*)"),
        )
        if path:
            set_config_value("ffmpeg_path", path)
            self._append_log(_t("FFmpeg set: {path}", path=path))
            self._atualizar_status()

    def _abrir_pasta(self):
        d = _ffmpeg_local_dir()
        try:
            os.makedirs(d, exist_ok=True)
            if sys.platform.startswith("win"):
                os.startfile(d)  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", d])
            else:
                subprocess.Popen(["xdg-open", d])
        except Exception:
            self._append_log(_t("Dependencies folder: {path}", path=d))

    def reject(self):
        if self._dl_thread is not None and self._dl_thread.isRunning():
            self._dl_thread.cancelar()
            self._dl_thread.wait(2000)
        super().reject()


def _fps_str(fps):
    """Formata o FPS para o FFmpeg ('24' em vez de '24.0')."""
    try:
        f = float(fps)
    except Exception:
        return "24"
    if abs(f - round(f)) < 1e-9:
        return str(int(round(f)))
    return ("%.6f" % f).rstrip("0").rstrip(".")


# =========================================================================
# TIMELINE E AMOSTRAGEM DA SEQUÊNCIA (usada por preview E exportação)
# =========================================================================

def sequence_duration(cenas) -> float:
    n = len(cenas)
    if n == 0:
        return 0.0
    if n == 1:
        return max(float(cenas[0].hold_s), 0.0)
    total = 0.0
    for i in range(n):
        total += max(float(cenas[i].hold_s), 0.0)
        if i < n - 1:
            total += max(float(cenas[i].transicao_s), 0.0)
    return total


def sample_sequence(cenas, t, suavizacao="Smooth"):
    """Amostra (eye, target, fov) da sequência no tempo t (segundos)."""
    n = len(cenas)
    if n == 0:
        return [0.0, -10.0, 5.0], [0.0, 0.0, 0.0], 30.0

    if n == 1 or t <= 0.0:
        s = cenas[0]
        return list(s.eye), list(s.target), s.fov

    acc = 0.0
    for i in range(n):
        s = cenas[i]
        # Permanência (dwell) sobre a cena i
        if t < acc + s.hold_s:
            return list(s.eye), list(s.target), s.fov
        acc += s.hold_s

        if i >= n - 1:
            break

        # Transição i -> i+1
        trans = s.transicao_s if s.transicao_s > _EPS else _EPS
        if t < acc + trans:
            u = (t - acc) / trans
            return _interpolar(cenas, i, u, suavizacao)
        acc += trans

    s = cenas[-1]
    return list(s.eye), list(s.target), s.fov


def _interpolar(cenas, i, u, suavizacao):
    n = len(cenas)
    a = cenas[i]
    b = cenas[min(i + 1, n - 1)]
    u = max(0.0, min(1.0, u))
    e = u if suavizacao == "Linear" else _smoothstep(u)

    if suavizacao == "Catmull-Rom" and n >= 3:
        p_prev = cenas[i - 1] if i > 0 else a
        p_next = cenas[i + 2] if (i + 2) <= n - 1 else b
        ev = _catmull_rom(
            QVector3D(*p_prev.eye), QVector3D(*a.eye),
            QVector3D(*b.eye), QVector3D(*p_next.eye), e,
        )
        tv = _catmull_rom(
            QVector3D(*p_prev.target), QVector3D(*a.target),
            QVector3D(*b.target), QVector3D(*p_next.target), e,
        )
        eye = [ev.x(), ev.y(), ev.z()]
        tgt = [tv.x(), tv.y(), tv.z()]
    else:
        eye = [a.eye[k] + (b.eye[k] - a.eye[k]) * e for k in range(3)]
        tgt = [a.target[k] + (b.target[k] - a.target[k]) * e for k in range(3)]

    fov = a.fov + (b.fov - a.fov) * e
    return eye, tgt, fov


# =========================================================================
# MOTOR DE ANIMAÇÃO (preview em tela) — derivado da OrbitAnimation
# =========================================================================

class SceneSequenceAnimation:
    """Percorre suavemente a sequência de cenas na viewport (preview)."""

    def __init__(self, controller, cenas, fps=30.0, suavizacao="Smooth",
                 loop=False):
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
        if self.total <= 0.0:
            self.total = 1.0  # salvaguarda (cena única sem permanência)
        self.timer.start()

    def parar(self):
        if self.timer.isActive():
            self.timer.stop()
        self.controller.animacao_ativa = None

    def sinalizar_interrupcao(self):
        self.interrompido = True
        if self.timer.isActive():
            self.timer.stop()

    def _next_frame(self):
        if self.interrompido:
            self.parar()
            return
        if not self.cenas:
            self.parar()
            return

        eye, tgt, fov = sample_sequence(self.cenas, self.tempo, self.suavizacao)
        self.controller.aplicar_camera(eye, tgt, fov)
        self.frame_count += 1

        self.tempo += 1.0 / self.fps
        if self.tempo > self.total:
            if self.loop:
                self.tempo = 0.0
            else:
                self.timer.stop()
                self.controller.animacao_ativa = None


# =========================================================================
# DIÁLOGO: CONFIGURAR TEMPOS E QUADROS
# =========================================================================

class ScenesConfigDialog(QDialog):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_t("Scenes - Timings and Frames"))
        self.controller = controller

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.sb_fps = QSpinBox()
        self.sb_fps.setRange(1, 240)
        self.sb_fps.setValue(int(round(controller.fps)))
        form.addRow(_t("Frames per second (FPS):"), self.sb_fps)

        self.cb_suav = QComboBox()
        _fill_smooth_combo(self.cb_suav, controller.suavizacao)
        form.addRow(_t("Camera interpolation:"), self.cb_suav)

        self.cb_loop = QComboBox()
        self.cb_loop.addItems([_t("No"), _t("Yes")])
        self.cb_loop.setCurrentText(_t("Yes") if controller.loop else _t("No"))
        form.addRow(_t("Loop?"), self.cb_loop)

        self.sb_trans = QDoubleSpinBox()
        self.sb_trans.setRange(0.0, 3600.0)
        self.sb_trans.setDecimals(2)
        self.sb_trans.setValue(controller.transicao_padrao_s)
        self.sb_trans.setSuffix(" s")
        form.addRow(_t("Default transition:"), self.sb_trans)

        self.sb_hold = QDoubleSpinBox()
        self.sb_hold.setRange(0.0, 3600.0)
        self.sb_hold.setDecimals(2)
        self.sb_hold.setValue(controller.hold_padrao_s)
        self.sb_hold.setSuffix(" s")
        form.addRow(_t("Default hold:"), self.sb_hold)

        layout.addLayout(form)

        layout.addWidget(QLabel(_t("Scene timings (edit columns 2 and 3):")))
        self.tabela = QTableWidget(0, 3)
        self.tabela.setHorizontalHeaderLabels(
            [_t("Scene"), _t("Hold (s)"), _t("Transition (s)")]
        )
        self.tabela.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked
        )
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

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def aplicar(self):
        c = self.controller
        c.fps = float(self.sb_fps.value())
        c.suavizacao = _current_smooth(self.cb_suav)
        c.loop = self.cb_loop.currentText() == _t("Yes")
        c.transicao_padrao_s = self.sb_trans.value()
        c.hold_padrao_s = self.sb_hold.value()

        for r in range(self.tabela.rowCount()):
            if r >= len(c.cenas):
                break
            sc = c.cenas[r]
            try:
                sc.hold_s = float(self.tabela.item(r, 1).text())
            except Exception:
                pass
            try:
                sc.transicao_s = float(self.tabela.item(r, 2).text())
            except Exception:
                pass


# =========================================================================
# DIÁLOGO: EXPORTAR ANIMAÇÃO (PNG ou MP4)
# =========================================================================

class ScenesExportDialog(QDialog):
    def __init__(self, controller, parent=None, modo_inicial=None):
        super().__init__(parent)
        self.setWindowTitle(_t("Scenes - Export Animation"))
        self.controller = controller

        layout = QFormLayout(self)

        self.cb_formato = QComboBox()
        self.cb_formato.addItems([_t("PNG image sequence"), _t("MP4 video")])
        if str(modo_inicial).upper() == "MP4":
            self.cb_formato.setCurrentIndex(1)
        layout.addRow(_t("Output format:"), self.cb_formato)

        self.sb_fps = QSpinBox()
        self.sb_fps.setRange(1, 240)
        self.sb_fps.setValue(int(round(controller.fps)))
        layout.addRow("FPS:", self.sb_fps)

        # Tamanho de saída (largura x altura). Sem este controle a captura
        # usava o tamanho ATUAL da viewport - que, com o painel aberto, fica
        # estreita e alta (vertical) e/ou em resolução inesperada.
        vp = controller.viewport
        self._vp_w = vp.width() if vp is not None else 0
        self._vp_h = vp.height() if vp is not None else 0
        if self._vp_w <= 0:
            self._vp_w = 1920
        if self._vp_h <= 0:
            self._vp_h = 1080

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
        linha_tam.addWidget(QLabel(_t("W")))
        linha_tam.addWidget(self.sb_w)
        linha_tam.addWidget(QLabel(_t("x  H")))
        linha_tam.addWidget(self.sb_h)
        holder = QWidget()
        holder.setLayout(linha_tam)
        layout.addRow(_t("Size (W × H):"), holder)

        self.chk_lock = QCheckBox(_t("Keep screen aspect ratio"))
        self.chk_lock.setChecked(True)
        layout.addRow("", self.chk_lock)

        self.btn_reset = QPushButton(_t("Current screen size"))
        self.btn_reset.clicked.connect(self._usar_viewport)
        layout.addRow("", self.btn_reset)

        self.lbl_info = QLabel("")
        layout.addRow(_t("Summary:"), self.lbl_info)
        self._atualizar()

        self.cb_formato.currentIndexChanged.connect(self._atualizar)
        self.sb_fps.valueChanged.connect(self._atualizar)
        self.sb_w.valueChanged.connect(self._w_mudou)
        self.sb_h.valueChanged.connect(self._h_mudou)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _usar_viewport(self):
        self.sb_w.blockSignals(True)
        self.sb_h.blockSignals(True)
        self.sb_w.setValue(int(self._vp_w))
        self.sb_h.setValue(int(self._vp_h))
        self.sb_w.blockSignals(False)
        self.sb_h.blockSignals(False)
        self.chk_lock.setChecked(True)
        self._atualizar()

    def _w_mudou(self, val):
        if self.chk_lock.isChecked() and self._vp_w > 0:
            self.sb_h.blockSignals(True)
            self.sb_h.setValue(
                max(16, int(round(val * self._vp_h / self._vp_w)))
            )
            self.sb_h.blockSignals(False)
        self._atualizar()

    def _h_mudou(self, val):
        if self.chk_lock.isChecked() and self._vp_h > 0:
            self.sb_w.blockSignals(True)
            self.sb_w.setValue(
                max(16, int(round(val * self._vp_w / self._vp_h)))
            )
            self.sb_w.blockSignals(False)
        self._atualizar()

    def _atualizar(self):
        total = sequence_duration(self.controller.cenas)
        fps = self.sb_fps.value()
        w, h = self.tamanho()
        self.lbl_info.setText(
            _t(
                "{n} scene(s) - {total:.2f}s - ~{frames} frames - {w}x{h} px",
                n=len(self.controller.cenas), total=total,
                frames=max(1, int(round(total * fps))), w=w, h=h,
            )
        )

    def modo_saida(self) -> str:
        return "MP4" if self.cb_formato.currentIndex() == 1 else "PNG"

    def fps(self) -> float:
        return float(self.sb_fps.value())

    def tamanho(self):
        """Retorna (largura, altura) alvo para a exportação."""
        return int(self.sb_w.value()), int(self.sb_h.value())


# =========================================================================
# CONTROLADOR PRINCIPAL (guarda a lista de cenas internamente)
# =========================================================================

class ScenesController:
    def __init__(self, viewport, main_window, app=None):
        self.viewport = viewport
        self.main_window = main_window
        self.app = app

        # Estrutura interna da lista de cenas (equivalente ao ArkZCameras).
        self.cenas = []
        self.indice_selecionado = -1

        # Referências de UI (preenchidas pela toolbar/painel lateral)
        self.panel = None
        self.dock = None

        # Padrões de configuração (tempos e quadros). São os VALORES-PADRÃO
        # para projetos novos; as cenas em si ficam salvas dentro do .igz.
        cfg = load_config()
        self.fps = float(cfg.get("fps", 30.0))
        self.suavizacao = _norm_smooth(cfg.get("suavizacao", "Smooth"))
        self.loop = bool(cfg.get("loop", False))
        self.transicao_padrao_s = float(cfg.get("transicao_padrao_s", 2.0))
        self.hold_padrao_s = float(cfg.get("hold_padrao_s", 1.0))
        self.export_w = int(cfg.get("export_w", 0) or 0)
        self.export_h = int(cfg.get("export_h", 0) or 0)

        self.animacao_ativa = None
        self._carregando_doc = False

        # As cenas pertencem ao PROJETO: se o .igz já tiver cenas gravadas,
        # carrega-as; caso contrário, começa com a lista vazia.
        self.carregar_do_documento()
        self._ligar_eventos_documento()

    # ---- Câmera (mesmo padrão do ArkZCameras, sem depender dele) --------
    def get_camera_eye(self) -> list:
        vp = self.viewport
        if vp and hasattr(vp, "camera"):
            cam = vp.camera
            if hasattr(cam, "eye") and callable(cam.eye):
                try:
                    e = cam.eye()
                    return [e.x(), e.y(), e.z()]
                except Exception:
                    pass
        return [0.0, -10.0, 5.0]

    def get_camera_target(self) -> list:
        vp = self.viewport
        if vp and hasattr(vp, "camera"):
            cam = vp.camera
            if hasattr(cam, "target"):
                t = cam.target
                if hasattr(t, "x"):
                    return [t.x(), t.y(), t.z()]
        return [0.0, 0.0, 0.0]

    def get_camera_fov(self) -> float:
        vp = self.viewport
        if vp and hasattr(vp, "camera"):
            cam = vp.camera
            for attr in ("fov_deg", "fov", "field_of_view"):
                if hasattr(cam, attr):
                    try:
                        v = getattr(cam, attr)
                        if callable(v):
                            v = v()
                        return float(v)
                    except Exception:
                        pass
        return 30.0

    def set_camera(self, eye, target):
        vp = self.viewport
        if not vp or not hasattr(vp, "camera"):
            return
        cam = vp.camera
        eye_vec = QVector3D(eye[0], eye[1], eye[2])
        target_vec = QVector3D(target[0], target[1], target[2])
        dir_vec = target_vec - eye_vec
        if hasattr(cam, "look_from"):
            try:
                cam.look_from(eye_vec, dir_vec)
            except Exception:
                pass
        else:
            try:
                cam.target = target_vec
            except Exception:
                pass
        try:
            vp.update()
        except Exception:
            pass

    def aplicar_camera(self, eye, target, fov=None):
        self.set_camera(eye, target)
        if fov is not None and self.viewport and hasattr(self.viewport, "camera"):
            cam = self.viewport.camera
            for attr in ("fov_deg", "fov", "field_of_view"):
                if hasattr(cam, attr):
                    try:
                        setattr(cam, attr, float(fov))
                        break
                    except Exception:
                        pass
        try:
            self.viewport.update()
        except Exception:
            pass

    # ---- Gestão de cenas ------------------------------------------------
    def adicionar_cena_atual(self):
        eye = self.get_camera_eye()
        target = self.get_camera_target()
        fov = self.get_camera_fov()
        nome = _t("Scene {n}", n=len(self.cenas) + 1)
        sc = Scene(nome, eye, target, fov,
                   hold_s=self.hold_padrao_s,
                   transicao_s=self.transicao_padrao_s)
        self.cenas.append(sc)
        self.indice_selecionado = len(self.cenas) - 1
        self.refresh_panel()
        self.salvar_no_documento()
        self._flash(
            _t(
                "{name} added (eye=({ex:.2f}, {ey:.2f}, {ez:.2f}), "
                "fov={fov:.1f}).",
                name=nome, ex=eye[0], ey=eye[1], ez=eye[2], fov=fov,
            )
        )

    def remover_cena_selecionada(self):
        if not self.cenas:
            QMessageBox.information(
                self.main_window, "Scenes",
                _t("There are no scenes to remove.")
            )
            return
        idx = self.indice_selecionado
        if not (0 <= idx < len(self.cenas)):
            if len(self.cenas) == 1:
                idx = 0
            else:
                idx = self._escolher_cena(_t("Choose the scene to remove:"))
                if idx < 0:
                    return
        nome = self.cenas[idx].nome
        del self.cenas[idx]
        self.indice_selecionado = min(idx, len(self.cenas) - 1)
        self.refresh_panel()
        self.salvar_no_documento()
        self._flash(_t("{name} removed.", name=nome))

    def limpar_cenas(self):
        if not self.cenas:
            return
        resp = QMessageBox.question(
            self.main_window, "Scenes",
            _t("Remove ALL {n} scenes?", n=len(self.cenas)),
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return
        self.cenas = []
        self.indice_selecionado = -1
        self.refresh_panel()
        self.salvar_no_documento()
        self._flash(_t("All scenes were removed."))

    def _escolher_cena(self, titulo):
        dlg = QDialog(self.main_window)
        dlg.setWindowTitle("Scenes")
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel(titulo))
        lista = QListWidget(dlg)
        for i, sc in enumerate(self.cenas):
            QListWidgetItem(f"{i + 1}. {sc.nome}", lista)
        if 0 <= self.indice_selecionado < len(self.cenas):
            lista.setCurrentRow(self.indice_selecionado)
        else:
            lista.setCurrentRow(0)
        lay.addWidget(lista)
        btns = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dlg
        )
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)
        if dlg.exec() == QDialog.Accepted and lista.currentRow() >= 0:
            return lista.currentRow()
        return -1

    def _flash(self, msg, ms=6000):
        try:
            if self.viewport is not None and hasattr(self.viewport, "flash_status"):
                self.viewport.flash_status(msg, ms)
        except Exception:
            pass

    # ---- Persistência no projeto (.igz) ---------------------------------
    def _obter_document_data(self):
        """Lê o valor JSON que este plugin guarda dentro do .igz."""
        app = getattr(self, "app", None)
        if app is None:
            return None
        fn = getattr(app, "document_data", None)
        if not callable(fn):
            return None
        try:
            return fn({})
        except TypeError:
            try:
                return fn(default={})
            except Exception:
                traceback.print_exc()
                return None
        except Exception:
            traceback.print_exc()
            return None

    def _gravar_document_data(self, data):
        """Grava o valor JSON deste plugin dentro do .igz (1 passo de undo)."""
        app = getattr(self, "app", None)
        if app is None:
            return
        fn = getattr(app, "set_document_data", None)
        if not callable(fn):
            return
        try:
            fn(data)
        except Exception:
            traceback.print_exc()

    def _snapshot(self) -> dict:
        """Estado atual (cenas + preferências) pronto para o JSON do .igz."""
        return {
            "cenas": [sc.to_dict() for sc in self.cenas],
            "fps": self.fps,
            "suavizacao": self.suavizacao,
            "loop": self.loop,
            "transicao_padrao_s": self.transicao_padrao_s,
            "hold_padrao_s": self.hold_padrao_s,
            "export_w": self.export_w,
            "export_h": self.export_h,
        }

    def carregar_do_documento(self):
        """Repõe cenas/preferências a partir dos dados salvos no .igz."""
        data = self._obter_document_data()
        if not isinstance(data, dict) or not data:
            return
        self._carregando_doc = True
        try:
            cenas = data.get("cenas")
            if isinstance(cenas, list):
                novas = [
                    Scene.from_dict(d) for d in cenas if isinstance(d, dict)
                ]
                self.cenas = novas
                if not novas:
                    self.indice_selecionado = -1
                elif not (0 <= self.indice_selecionado < len(novas)):
                    self.indice_selecionado = len(novas) - 1
            try:
                if "fps" in data:
                    self.fps = float(data["fps"])
                if "suavizacao" in data:
                    self.suavizacao = str(data["suavizacao"])
                if "loop" in data:
                    self.loop = bool(data["loop"])
                if "transicao_padrao_s" in data:
                    self.transicao_padrao_s = float(
                        data["transicao_padrao_s"]
                    )
                if "hold_padrao_s" in data:
                    self.hold_padrao_s = float(data["hold_padrao_s"])
                if "export_w" in data:
                    self.export_w = int(data["export_w"] or 0)
                if "export_h" in data:
                    self.export_h = int(data["export_h"] or 0)
            except Exception:
                traceback.print_exc()
        finally:
            self._carregando_doc = False

    def salvar_no_documento(self):
        """Grava as cenas DENTRO do arquivo .igz do projeto."""
        if self._carregando_doc:
            return
        self._gravar_document_data(self._snapshot())

    def _ligar_eventos_documento(self):
        app = getattr(self, "app", None)
        if app is None:
            return
        fn = getattr(app, "on_document_changed", None)
        if not callable(fn):
            return
        try:
            fn(self._ao_mudar_documento)
        except Exception:
            traceback.print_exc()

    def _ao_mudar_documento(self, *args, **kwargs):
        # Edições, undo, "Novo" e "Abrir": recarrega as cenas do projeto.
        self.carregar_do_documento()
        self.refresh_panel()

    # ---- Persistência e sincronização com o painel ----------------------
    def save_prefs(self):
        try:
            cfg = load_config()
            cfg.update({
                "fps": self.fps,
                "suavizacao": self.suavizacao,
                "loop": self.loop,
                "transicao_padrao_s": self.transicao_padrao_s,
                "hold_padrao_s": self.hold_padrao_s,
                "export_w": self.export_w,
                "export_h": self.export_h,
            })
            save_config(cfg)
        except Exception:
            traceback.print_exc()
        # As cenas/preferências também ficam gravadas DENTRO do .igz.
        self.salvar_no_documento()

    def refresh_panel(self):
        try:
            if self.panel is not None:
                self.panel.atualizar()
        except Exception:
            traceback.print_exc()

    # ---- Reprodução -----------------------------------------------------
    def tocar_animacao(self):
        if len(self.cenas) < 1:
            QMessageBox.information(
                self.main_window, "Scenes",
                _t("Add at least one scene (2 or more recommended)."),
            )
            return
        if self.viewport is None:
            QMessageBox.warning(
                self.main_window, "Scenes",
                _t("Viewport not found.")
            )
            return
        if self.animacao_ativa:
            self.animacao_ativa.sinalizar_interrupcao()
        self.animacao_ativa = SceneSequenceAnimation(
            self, self.cenas, self.fps, self.suavizacao, self.loop
        )
        self.animacao_ativa.iniciar()
        self._flash(_t("Playing scene animation..."))

    def parar_animacao(self):
        if self.animacao_ativa:
            self.animacao_ativa.sinalizar_interrupcao()
            self.animacao_ativa = None
        self._flash("")

    def configurar_tempos(self):
        dlg = ScenesConfigDialog(self, self.main_window)
        if dlg.exec() == QDialog.Accepted:
            dlg.aplicar()
            self.save_prefs()
            self.refresh_panel()
            self._flash(_t("Timing and frame settings updated."))

    # ---- Exportação -----------------------------------------------------
    def _escolher_backend_mp4(self):
        """Retorna 'ffmpeg', 'png' ou None (cancelar)."""
        while True:
            if _find_ffmpeg() is not None:
                return "ffmpeg"

            box = QMessageBox(self.main_window)
            box.setWindowTitle("Scenes")
            box.setIcon(QMessageBox.Information)
            box.setText(_t("FFmpeg was not found."))
            box.setInformativeText(
                _t(
                    "Do you want to configure/download FFmpeg now?\n"
                    "Otherwise, the animation will be exported as a PNG "
                    "image sequence."
                )
            )
            b_cfg = box.addButton(
                _t("Configure / Download..."), QMessageBox.AcceptRole
            )
            b_png = box.addButton(_t("Export PNG"), QMessageBox.ActionRole)
            b_cancel = box.addButton(_t("Cancel"), QMessageBox.RejectRole)
            box.setDefaultButton(b_cfg)
            box.exec()

            clicado = box.clickedButton()
            if clicado is b_cfg:
                DependencyDialog(self.main_window).exec()
                continue
            if clicado is b_png:
                return "png"
            return None

    def exportar_animacao(self, modo=None):
        if not self.cenas:
            QMessageBox.information(
                self.main_window, "Scenes",
                _t("There are no scenes to export."),
            )
            return
        if self.viewport is None:
            QMessageBox.warning(
                self.main_window, "Scenes",
                _t("Viewport not found.")
            )
            return

        # Sempre abre o diálogo: é onde o usuário escolhe o FORMATO e o
        # TAMANHO (largura x altura) da imagem/vídeo. 'modo' pré-seleciona.
        dlg = ScenesExportDialog(self, self.main_window, modo_inicial=modo)
        if dlg.exec() != QDialog.Accepted:
            return
        modo = dlg.modo_saida()
        fps = dlg.fps()
        size = dlg.tamanho()
        try:
            self.export_w, self.export_h = int(size[0]), int(size[1])
            self.save_prefs()
        except Exception:
            pass

        if modo == "PNG":
            out_dir = QFileDialog.getExistingDirectory(
                self.main_window, _t("Folder to save the PNG images")
            )
            if not out_dir:
                return
            self._render("png", fps, out_dir, None, size)
            return

        out_file, _ = QFileDialog.getSaveFileName(
            self.main_window, _t("Save MP4 video"), _t("animation.mp4"),
            _t("MP4 video (*.mp4)"),
        )
        if not out_file:
            return
        if not out_file.lower().endswith(".mp4"):
            out_file += ".mp4"

        backend = self._escolher_backend_mp4()
        if backend is None:
            return
        if backend == "png":
            out_dir = QFileDialog.getExistingDirectory(
                self.main_window, _t("Folder to save the PNG images")
            )
            if not out_dir:
                return
            self._render("png", fps, out_dir, None, size)
            return
        self._render(backend, fps, None, out_file, size)


    def _render(self, backend, fps, out_dir, out_file, out_size=None):
        vp = self.viewport
        cenas = self.cenas
        suav = self.suavizacao
        try:
            fps = float(fps)
        except Exception:
            fps = float(self.fps)
        total = sequence_duration(cenas)
        n_frames = max(1, int(round(total * fps)))

        ffmpeg = None
        tmp_frames = None

        if backend != "png":
            ffmpeg = _find_ffmpeg()
            if not ffmpeg:
                backend = "png"

        # Para vídeo, guardamos TODOS os frames como PNG temporários e o
        # FFmpeg monta o MP4 no final.
        if backend == "ffmpeg":
            tmp_frames = tempfile.mkdtemp(prefix="igz_scenes_frames_")

        if backend == "png" and not out_dir:
            out_dir = QFileDialog.getExistingDirectory(
                self.main_window, _t("Folder to save the PNG images")
            )
            if not out_dir:
                return

        gravados = 0
        try:
            for idx in range(n_frames):
                t = idx / fps
                eye, tgt, fov = sample_sequence(cenas, t, suav)
                self.aplicar_camera(eye, tgt, fov)
                QApplication.processEvents()

                pix = (
                    vp.grabFramebuffer()
                    if hasattr(vp, "grabFramebuffer") else None
                )
                if pix is None:
                    continue

                # Escala para o tamanho escolhido (se diferente da captura).
                if out_size:
                    try:
                        tw = int(out_size[0])
                        th = int(out_size[1])
                        if tw > 0 and th > 0 and (
                            tw != pix.width() or th != pix.height()
                        ):
                            pix = pix.scaled(
                                tw, th, Qt.IgnoreAspectRatio,
                                Qt.SmoothTransformation,
                            )
                    except Exception:
                        traceback.print_exc()
                gravados += 1

                if tmp_frames is not None:
                    pix.save(
                        os.path.join(tmp_frames, f"f_{gravados:05d}.png"),
                        "PNG",
                    )
                else:
                    pix.save(
                        os.path.join(out_dir, f"scene_{gravados:05d}.png"),
                        "PNG",
                    )
        except Exception:
            traceback.print_exc()

        resultado = ""
        if backend == "ffmpeg":
            if tmp_frames and self._run_ffmpeg(
                ffmpeg, tmp_frames, out_file, fps
            ):
                resultado = out_file
        else:
            resultado = out_dir

        if backend == "ffmpeg":
            if resultado and tmp_frames:
                shutil.rmtree(tmp_frames, ignore_errors=True)
            elif not resultado and tmp_frames:
                QMessageBox.warning(
                    self.main_window, "Scenes",
                    _t("Could not generate the MP4 video.\n"
                       "The PNG frames were kept in:\n") + tmp_frames,
                )

        dest = resultado or (out_file if backend == "ffmpeg" else out_dir)
        QMessageBox.information(
            self.main_window, "Scenes",
            _t("Export finished: {n} frames.", n=gravados)
            + (f"\n{dest}" if dest else ""),
        )

    def _run_ffmpeg(self, ffmpeg, png_dir, out_file, fps):
        if not ffmpeg or not png_dir or not os.path.isdir(png_dir):
            return False
        pattern = os.path.join(png_dir, "f_%05d.png")
        cmd = [
            ffmpeg, "-y", "-framerate", _fps_str(fps), "-i", pattern,
            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", out_file or "",
        ]
        try:
            proc = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True,
            )
        except Exception:
            traceback.print_exc()
            proc = None
        if (proc is not None and proc.returncode == 0 and out_file
                and os.path.isfile(out_file)
                and os.path.getsize(out_file) > 0):
            return True
        if proc is not None:
            _log("FFmpeg falhou (rc=%s): %s" % (
                proc.returncode, (proc.stdout or "")[-800:]))
        QMessageBox.warning(
            self.main_window, "Scenes",
            "Falha ao executar o FFmpeg. Os frames PNG foram mantidos "
            "em:\n" + png_dir,
        )
        return False


# =========================================================================
# PAINEL LATERAL (Dock) COM TODAS AS FERRAMENTAS DE CENAS
# =========================================================================

class ScenesPanel(QWidget):
    """Painel lateral: gestor de cenas, tempos, exportação e dependências."""

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self._build()
        self.atualizar()

    def _build(self):
        c = self.controller

        # Área de rolagem: garante acesso a TODOS os controles mesmo quando o
        # dock/aba fica baixo - antes o painel esticava e cortava o que estava
        # abaixo (ex.: "Dependências de Vídeo"), sem barra de rolagem.
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

        root.addWidget(QLabel("<b>Scenes</b>"))
        nota = QLabel(
            "<i>" + _t("Scenes are saved inside the project's .igz file.")
            + "</i>"
        )
        nota.setWordWrap(True)
        root.addWidget(nota)

        gb = QGroupBox(_t("Scenes"))
        v = QVBoxLayout(gb)
        self.lista = QListWidget()
        self.lista.currentRowChanged.connect(self._selecionar)
        # Altura fixa para exibir exatamente 5 linhas de cena.
        _fm_lista = self.lista.fontMetrics()
        self.lista.setFixedHeight(
            5 * (_fm_lista.height() + 4)
            + 2 * self.lista.frameWidth()
            + 2
        )
        v.addWidget(self.lista)
        h = QHBoxLayout()
        self.btn_add = QPushButton(_t("Add"))
        self.btn_add.clicked.connect(self._add)
        self.btn_rem = QPushButton(_t("Remove"))
        self.btn_rem.clicked.connect(self._rem)
        self.btn_clr = QPushButton(_t("Clear"))
        self.btn_clr.clicked.connect(self._clr)
        for b in (self.btn_add, self.btn_rem, self.btn_clr):
            h.addWidget(b)
        v.addLayout(h)

        gb2 = QGroupBox(_t("Playback"))
        v2 = QVBoxLayout(gb2)
        h2 = QHBoxLayout()
        self.btn_play = QPushButton(_t("Play"))
        self.btn_play.clicked.connect(self._play)
        self.btn_stop = QPushButton(_t("Stop"))
        self.btn_stop.clicked.connect(self._stop)
        h2.addWidget(self.btn_play)
        h2.addWidget(self.btn_stop)
        v2.addLayout(h2)
        self.chk_loop = QCheckBox(_t("Loop"))
        self.chk_loop.setChecked(bool(c.loop))
        self.chk_loop.toggled.connect(self._loop)
        v2.addWidget(self.chk_loop)
        self.lbl_dur = QLabel("")
        v2.addWidget(self.lbl_dur)

        gb3 = QGroupBox(_t("Timings and Frames"))
        v3 = QVBoxLayout(gb3)
        form = QFormLayout()
        self.sb_fps = QSpinBox()
        self.sb_fps.setRange(1, 240)
        self.sb_fps.setValue(int(round(c.fps)))
        form.addRow("FPS:", self.sb_fps)
        self.cb_suav = QComboBox()
        _fill_smooth_combo(self.cb_suav, c.suavizacao)
        form.addRow(_t("Interpolation:"), self.cb_suav)
        self.sb_trans = QDoubleSpinBox()
        self.sb_trans.setRange(0.0, 3600.0)
        self.sb_trans.setDecimals(2)
        self.sb_trans.setSuffix(" s")
        self.sb_trans.setValue(c.transicao_padrao_s)
        form.addRow(_t("Default transition:"), self.sb_trans)
        self.sb_hold = QDoubleSpinBox()
        self.sb_hold.setRange(0.0, 3600.0)
        self.sb_hold.setDecimals(2)
        self.sb_hold.setSuffix(" s")
        self.sb_hold.setValue(c.hold_padrao_s)
        form.addRow(_t("Default hold:"), self.sb_hold)
        v3.addLayout(form)
        self.tabela = QTableWidget(0, 3)
        self.tabela.setHorizontalHeaderLabels(
            [_t("Scene"), _t("Hold (s)"), _t("Transition (s)")]
        )
        self.tabela.setEditTriggers(
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.SelectedClicked
        )
        # Altura fixa para exibir exatamente 4 linhas (+ cabeçalho).
        _cab_tab = self.tabela.horizontalHeader().sizeHint().height() or 26
        _lin_tab = self.tabela.verticalHeader().defaultSectionSize() or 30
        self.tabela.setFixedHeight(
            _cab_tab + 4 * _lin_tab + 2 * self.tabela.frameWidth() + 2
        )
        v3.addWidget(self.tabela)
        self.btn_apply = QPushButton(_t("Apply settings"))
        self.btn_apply.clicked.connect(self._apply)
        v3.addWidget(self.btn_apply)

        gb4 = QGroupBox(_t("Export"))
        v4 = QVBoxLayout(gb4)
        self.cb_formato = QComboBox()
        self.cb_formato.addItems(
            [_t("PNG image sequence"), _t("MP4 video")]
        )
        v4.addWidget(self.cb_formato)
        self.btn_export = QPushButton(_t("Export Animation"))
        self.btn_export.clicked.connect(self._export)
        v4.addWidget(self.btn_export)

        gb5 = QGroupBox(_t("Video Dependencies"))
        v5 = QVBoxLayout(gb5)
        self.lbl_dep = QLabel("")
        self.lbl_dep.setWordWrap(True)
        v5.addWidget(self.lbl_dep)
        self.btn_dep = QPushButton(_t("Configure / Download..."))
        self.btn_dep.clicked.connect(self._deps)
        v5.addWidget(self.btn_dep)

        # Base (reprodução + exportação + dependências) empilhada.
        base = QWidget()
        vb = QVBoxLayout(base)
        vb.setContentsMargins(0, 0, 0, 0)
        vb.addWidget(gb2)
        vb.addWidget(gb4)
        vb.addWidget(gb5)

        # Divisores arrastáveis: Cenas | Tempos e Quadros | Base.
        # Arraste os separadores para exibir mais linhas nas listas.
        self.split = QSplitter(Qt.Vertical)
        self.split.setChildrenCollapsible(False)
        self.split.addWidget(gb)
        self.split.addWidget(gb3)
        self.split.addWidget(base)
        # As seções "Cenas" (5 linhas) e "Tempos e Quadros" (4 linhas) têm
        # altura fixa; o espaço extra do painel fica na seção de baixo (Base).
        self.split.setStretchFactor(0, 0)
        self.split.setStretchFactor(1, 0)
        self.split.setStretchFactor(2, 1)
        self.split.setSizes([180, 340, 260])
        root.addWidget(self.split)


    def _selecionar(self, row):
        self.controller.indice_selecionado = row

    def _add(self):
        self.controller.adicionar_cena_atual()

    def _rem(self):
        self.controller.remover_cena_selecionada()

    def _clr(self):
        self.controller.limpar_cenas()

    def _play(self):
        self.controller.tocar_animacao()

    def _stop(self):
        self.controller.parar_animacao()

    def _loop(self, checked):
        self.controller.loop = bool(checked)

    def _apply(self):
        c = self.controller
        c.fps = float(self.sb_fps.value())
        c.suavizacao = _current_smooth(self.cb_suav)
        c.transicao_padrao_s = self.sb_trans.value()
        c.hold_padrao_s = self.sb_hold.value()
        for r in range(self.tabela.rowCount()):
            if r >= len(c.cenas):
                break
            try:
                c.cenas[r].hold_s = float(self.tabela.item(r, 1).text())
            except Exception:
                pass
            try:
                c.cenas[r].transicao_s = float(self.tabela.item(r, 2).text())
            except Exception:
                pass
        c.save_prefs()
        self.atualizar()
        c._flash(_t("Settings applied."))

    def _export(self):
        modo = "MP4" if self.cb_formato.currentIndex() == 1 else "PNG"
        self.controller.exportar_animacao(modo)

    def _deps(self):
        DependencyDialog(self.window()).exec()
        self.atualizar()

    def atualizar(self):
        c = self.controller
        self.lista.blockSignals(True)
        self.lista.clear()
        for i, sc in enumerate(c.cenas):
            self.lista.addItem(f"{i + 1}. {sc.nome}")
        if 0 <= c.indice_selecionado < len(c.cenas):
            self.lista.setCurrentRow(c.indice_selecionado)
        self.lista.blockSignals(False)

        self.tabela.setRowCount(0)
        for sc in c.cenas:
            r = self.tabela.rowCount()
            self.tabela.insertRow(r)
            item = QTableWidgetItem(sc.nome)
            item.setFlags(Qt.ItemIsEnabled)
            self.tabela.setItem(r, 0, item)
            self.tabela.setItem(r, 1, QTableWidgetItem(f"{sc.hold_s:.2f}"))
            self.tabela.setItem(
                r, 2, QTableWidgetItem(f"{sc.transicao_s:.2f}")
            )
        self.tabela.resizeColumnsToContents()

        total = sequence_duration(c.cenas)
        self.lbl_dur.setText(
            _t(
                "{n} scene(s) — {total:.2f}s — ~{frames} frames",
                n=len(c.cenas), total=total,
                frames=max(1, int(round(total * c.fps))),
            )
        )
        self.sb_fps.setValue(int(round(c.fps)))
        _fill_smooth_combo(self.cb_suav, c.suavizacao)
        self.sb_trans.setValue(c.transicao_padrao_s)
        self.sb_hold.setValue(c.hold_padrao_s)
        self.chk_loop.setChecked(bool(c.loop))

        ok_ff, _ = _ffmpeg_status()
        self.lbl_dep.setText(
            f"FFmpeg: {_t('available') if ok_ff else _t('missing')}"
        )







# =========================================================================
# TOOLBAR E INTEGRAÇÃO
# =========================================================================

_TOOLBAR_CREATED = False


def find_viewport(main_window):
    if not main_window:
        return None

    if hasattr(main_window, "viewport"):
        return main_window.viewport

    for child in main_window.findChildren(QWidget):
        name = child.__class__.__name__.lower()
        if (
            "viewport" in name
            or "gl" in name
            or "canvas" in name
            or "scene" in name
        ):
            return child

    return None


# Títulos (minúsculos) que identificam o grupo de painéis já existente no
# IngeTrazo: Propriedades, BIM, Terreno, IA, Renderizar. Usados para escolher
# a aba/grupo correto onde encaixar o painel "Cenas".
_PANEL_GROUP_TITLES = ("propriedades", "bim", "terreno", "renderiz")


def _titulo_do_grupo(title) -> bool:
    t = (title or "").strip().lower()
    if not t:
        return False
    if t in ("ia", "i.a", "i.a."):
        return True
    return any(k in t for k in _PANEL_GROUP_TITLES)


def _dump_panel_hosts(mw):
    """Loga docks/abas encontrados (diagnóstico do encaixe do painel)."""
    try:
        for d in mw.findChildren(QDockWidget):
            try:
                area = mw.dockWidgetArea(d)
            except Exception:
                area = "?"
            _log(
                "diag dock: title=%r obj=%r area=%s vis=%s"
                % (d.windowTitle(), d.objectName(), area, d.isVisible())
            )
    except Exception:
        pass
    try:
        for tw in mw.findChildren(QTabWidget):
            try:
                labels = [tw.tabText(i) for i in range(tw.count())]
            except Exception:
                labels = []
            _log(
                "diag tabwidget: obj=%r labels=%s cur=%s vis=%s"
                % (tw.objectName(), labels, tw.currentIndex(), tw.isVisible())
            )
    except Exception:
        pass


def _attach_scenes_panel(mw, panel):
    """Anexa o painel "Cenas" ao grupo de painéis existente.

    Retorna (dock, tab_widget):
      * (QDockWidget, None) -> virou uma ABA de docks;
      * (None, QTabWidget)  -> inserido como aba de um QTabWidget;
      * (QDockWidget, None) -> fallback (dock próprio) se nada foi achado;
      * (None, None)        -> host não suporta painéis.
    """
    if mw is None:
        return None, None

    _dump_panel_hosts(mw)

    # 1) QTabWidget que contém as abas conhecidas -> adiciona "Cenas" como
    #    mais uma aba. Feito ANTES de mexer em docks porque era isso que
    #    estava errado: um dock novo era criado e "empurrava" o grupo.
    try:
        tabs = list(mw.findChildren(QTabWidget))
    except Exception:
        tabs = []
    melhor = None
    melhor_score = 0
    for tw in tabs:
        try:
            labels = [tw.tabText(i) for i in range(tw.count())]
        except Exception:
            labels = []
        score = sum(1 for lbl in labels if _titulo_do_grupo(lbl))
        if score > melhor_score:
            melhor, melhor_score = tw, score
    if melhor is not None:
        try:
            melhor.addTab(panel, _t("Scenes"))
            melhor.setCurrentWidget(panel)
            _log(
                "Painel 'Cenas' adicionado como aba em QTabWidget "
                "(abas=%s)."
                % [melhor.tabText(i) for i in range(melhor.count())]
            )
            return None, melhor
        except Exception:
            traceback.print_exc()

    # 2) Grupo de QDockWidgets (tabificados) -> vira aba "Cenas".
    try:
        docks = [d for d in mw.findChildren(QDockWidget) if d is not panel]
    except Exception:
        docks = []

    if docks and hasattr(mw, "tabifyDockWidget"):
        anchor = None
        for d in docks:
            if _titulo_do_grupo(d.windowTitle()):
                anchor = d
                break
        if anchor is None:
            visiveis = [d for d in docks if d.isVisible()]
            anchor = (visiveis or docks)[0]

        area = Qt.RightDockWidgetArea
        try:
            a = mw.dockWidgetArea(anchor)
            if a in (
                Qt.LeftDockWidgetArea, Qt.RightDockWidgetArea,
                Qt.TopDockWidgetArea, Qt.BottomDockWidgetArea,
            ):
                area = a
        except Exception:
            pass

        dock = QDockWidget(_t("Scenes"), mw)
        dock.setObjectName("igz_tb_scenes_dock")
        dock.setWidget(panel)
        dock.setAllowedAreas(
            Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
        )
        mw.addDockWidget(area, dock)
        try:
            mw.tabifyDockWidget(anchor, dock)
            dock.show()
            dock.raise_()
        except Exception:
            traceback.print_exc()
        _log(
            "Painel 'Cenas' tabificado junto ao dock %r."
            % (anchor.windowTitle(),)
        )
        return dock, None

    # 3) Fallback: dock próprio na área direita.
    if hasattr(mw, "addDockWidget"):
        dock = QDockWidget(_t("Scenes"), mw)
        dock.setObjectName("igz_tb_scenes_dock")
        dock.setWidget(panel)
        dock.setAllowedAreas(
            Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
        )
        mw.addDockWidget(Qt.RightDockWidgetArea, dock)
        _log("Painel 'Cenas' criado como dock próprio (fallback).")
        return dock, None

    _log("main_window sem addDockWidget/QTabWidget (painel ignorado).")
    return None, None


def create_toolbar(main_window, viewport=None, app=None):
    if viewport is None:
        viewport = find_viewport(main_window)

    controller = ScenesController(viewport, main_window, app=app)

    toolbar = QToolBar("Scenes", main_window)
    toolbar.setObjectName("igz_tb_scenes")
    toolbar.setWindowTitle(_t("Scenes"))

    def make_action(nome, icone_base, tooltip, callback):
        icon = _load_themed_icon(icone_base, main_window)
        action = QAction(icon, nome, main_window)
        action.setToolTip(tooltip)
        action.setStatusTip(tooltip)
        action.triggered.connect(lambda checked=False: callback())
        return action

    toolbar.addAction(
        make_action(
            _t("Add Current Scene"), "scene_add",
            _t("Captures the current camera's eye, target and fov as a "
               "new scene."),
            controller.adicionar_cena_atual,
        )
    )

    toolbar.addAction(
        make_action(
            _t("Remove Selected Scene"), "scene_remove",
            _t("Removes the currently selected scene from the list."),
            controller.remover_cena_selecionada,
        )
    )

    toolbar.addAction(
        make_action(
            _t("Clear Scenes"), "scene_remove_all",
            _t("Removes ALL scenes from the list."),
            controller.limpar_cenas,
        )
    )

    toolbar.addSeparator()

    toolbar.addAction(
        make_action(
            _t("Play Scene Animation"), "scene_play",
            _t("Smoothly plays through the scenes stored in the viewport."),
            controller.tocar_animacao,
        )
    )

    toolbar.addAction(
        make_action(
            _t("Stop Animation"), "scene_stop",
            _t("Stops the running scene animation."),
            controller.parar_animacao,
        )
    )

    toolbar.addSeparator()

    toolbar.addAction(
        make_action(
            _t("Configure Timings and Frames"), "scene_configure",
            _t("Configures FPS, interpolation, loop and per-scene timings."),
            controller.configurar_tempos,
        )
    )

    toolbar.addAction(
        make_action(
            _t("Export Animation"), "scene_export",
            _t("Exports the animation as a PNG sequence or MP4 video."),
            controller.exportar_animacao,
        )
    )

    # O botão de configurar/baixar o FFmpeg só aparece quando ele não foi
    # localizado; com o FFmpeg disponível a exportação MP4 já funciona.
    if _find_ffmpeg() is None:
        toolbar.addAction(
            make_action(
                _t("Video Dependencies"), "scene_ffmpeg",
                _t("Configure/download FFmpeg to export MP4."),
                lambda: DependencyDialog(main_window).exec(),
            )
        )

    # ---- Painel "Cenas" no grupo de painéis existente ----
    panel = ScenesPanel(controller, main_window)
    controller.panel = panel

    dock, tab_widget = _attach_scenes_panel(main_window, panel)
    controller.dock = dock

    toolbar.addSeparator()
    if dock is not None and hasattr(dock, "toggleViewAction"):
        toggle = dock.toggleViewAction()
        toggle.setText(_t("Scenes Panel"))
        toggle.setToolTip(_t("Show/hide the scenes panel."))
        toggle.setIcon(_load_themed_icon("scene_panel", main_window))
        toolbar.addAction(toggle)
    elif tab_widget is not None:
        toolbar.addAction(
            make_action(
                _t("Scenes Panel"), "scene_panel",
                _t("Go to the scenes tab."),
                lambda: tab_widget.setCurrentWidget(panel),
            )
        )
    else:
        _log("create_toolbar: painel 'Cenas' não anexado a nenhum host.")

    toolbar.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
    return toolbar


# =========================================================================
# PONTO DE ENTRADA DO PLUGIN
# =========================================================================

def setup(app) -> None:
    global _TOOLBAR_CREATED
    if _TOOLBAR_CREATED:
        return

    try:
        mw = None

        qapp = QApplication.instance()
        if qapp is not None:
            for w in qapp.topLevelWidgets():
                if hasattr(w, "addToolBar"):
                    mw = w
                    break

        if mw is None:
            mw = (
                getattr(app, "main_window", None)
                or getattr(app, "window", None)
                or (app if hasattr(app, "addToolBar") else None)
            )

        if mw is None or not hasattr(mw, "addToolBar"):
            _log("setup: main window não encontrada; abortando.")
            return

        vp = find_viewport(mw) or getattr(app, "viewport", None)
        if vp is None:
            _log("setup: viewport não encontrada.")
        else:
            _log(f"setup: viewport = {vp.__class__.__name__}")

        tb = create_toolbar(mw, vp, app=app)
        mw.addToolBar(Qt.TopToolBarArea, tb)
        _TOOLBAR_CREATED = True
        _log("setup: toolbar 'igz_tb_scenes' adicionada com sucesso.")

    except Exception:
        traceback.print_exc()


__all__ = [
    "Scene",
    "SceneSequenceAnimation",
    "ScenesConfigDialog",
    "ScenesExportDialog",
    "ScenesController",
    "create_toolbar",
    "setup",
]
