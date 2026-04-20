import os
import sys
import subprocess
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox
from urllib.parse import urlparse, parse_qs
import threading

# CustomTkinter import
import customtkinter as ctk


VIDEO_TYPES = [
    ("Video files", "*.mp4 *.mkv *.mov *.avi *.webm *.m4v"),
    ("All files", "*.*"),
]

AUDIO_TYPES = [
    ("Audio files", "*.mp3 *.wav *.flac *.m4a *.ogg *.wma"),
    ("All files", "*.*"),
]

MEDIA_TYPES = [
    ("Media files", "*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.mp3 *.wav *.flac *.m4a *.ogg"),
    ("Video files", "*.mp4 *.mkv *.mov *.avi *.webm *.m4v"),
    ("Audio files", "*.mp3 *.wav *.flac *.m4a *.ogg"),
    ("All files", "*.*"),
]

# --- PyInstaller resource resolution ---
def resource_path(rel):
    return os.path.join(getattr(sys, "_MEIPASS", os.path.abspath(".")), rel)

ffmpeg_bin = resource_path("ffmpeg.exe")
ytdlp_bin = resource_path("yt-dlp.exe")

if not os.path.exists(ffmpeg_bin): ffmpeg_bin = "ffmpeg"
if not os.path.exists(ytdlp_bin): ytdlp_bin = "yt-dlp"

def quote_cmd(cmd):
    out = []
    for part in cmd:
        part = str(part)
        if " " in part or "\t" in part:
            out.append(f'"{part}"')
        else:
            out.append(part)
    return " ".join(out)

def run_logged(cmd, log_write, cwd=None):
    log_write(f"> {quote_cmd(cmd)}\n")
    
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0 
    )
    
    if proc.stdout:
        for line in proc.stdout:
            log_write(line)
            
    rc = proc.wait()
    return rc
