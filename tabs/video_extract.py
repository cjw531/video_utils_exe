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

from utils import *


class VideoExtractTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.input_path = ctk.StringVar()
        self.output_path = ctk.StringVar()
        self.start_time = ctk.StringVar(value="00:10:00")
        self.end_time = ctk.StringVar(value="01:15:30")
        self._build()

    def _build(self):
        pad = {"padx": 10, "pady": 8}

        ctk.CTkLabel(self, text="원본 영상 경로:").grid(row=0, column=0, sticky="w", **pad)
        ctk.CTkEntry(self, textvariable=self.input_path).grid(row=0, column=1, sticky="we", **pad)
        ctk.CTkButton(self, text="파일 탐색", command=self.browse_input, width=100).grid(row=0, column=2, **pad)

        ctk.CTkLabel(self, text="추출 영상 경로:").grid(row=1, column=0, sticky="w", **pad)
        ctk.CTkEntry(self, textvariable=self.output_path).grid(row=1, column=1, sticky="we", **pad)
        ctk.CTkButton(self, text="저장 경로", command=self.browse_output, width=100).grid(row=1, column=2, **pad)

        ctk.CTkLabel(self, text="시작 시간 (HH:MM:SS):").grid(row=2, column=0, sticky="w", **pad)
        ctk.CTkEntry(self, textvariable=self.start_time, width=150).grid(row=2, column=1, sticky="w", **pad)

        ctk.CTkLabel(self, text="종료 시간 (HH:MM:SS):").grid(row=3, column=0, sticky="w", **pad)
        ctk.CTkEntry(self, textvariable=self.end_time, width=150).grid(row=3, column=1, sticky="w", **pad)

        ctk.CTkButton(self, text="추출 시작", command=self.run, fg_color="#2b7b50", hover_color="#1f5a3a").grid(row=4, column=1, sticky="w", padx=10, pady=15)

        ctk.CTkLabel(self, text="Console:").grid(row=5, column=0, sticky="w", **pad)
        self.log = ctk.CTkTextbox(self, state="disabled", font=("Malgun Gothic", 12))
        self.log.grid(row=6, column=0, columnspan=3, sticky="nsew", padx=10, pady=(0, 10))

        self.log.tag_config("success", foreground="#00FF00")
        self.log.tag_config("error", foreground="#FF4444")
        self.log.tag_config("warning", foreground="#FFD700")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(6, weight=1)

    def log_write(self, text: str):
        try: safe_text = text.encode('utf-8', errors='ignore').decode('utf-8')
        except: safe_text = text
        self.log.configure(state="normal")
        start_index = self.log.index("end-1c")
        self.log.insert("end", text)
        end_index = self.log.index("end-1c")

        lower_text = text.lower()
        if "[ok]" in lower_text or "완료" in lower_text or "success" in lower_text:
            self.log.tag_add("success", start_index, end_index)
        elif "[error]" in lower_text or "fail" in lower_text or "오류" in lower_text:
            self.log.tag_add("error", start_index, end_index)
        elif "[warn]" in lower_text or "warning" in lower_text:
            self.log.tag_add("warning", start_index, end_index)
        
        self.log.see("end")
        self.log.configure(state="disabled")
        self.update_idletasks()

    def browse_input(self):
        path = filedialog.askopenfilename(title="원본 영상 경로", filetypes=VIDEO_TYPES)
        if path:
            self.input_path.set(path)
            if not self.output_path.get().strip():
                base, ext = os.path.splitext(path)
                self.output_path.set(f"{base}_extracted{ext}")

    def browse_output(self):
        path = filedialog.asksaveasfilename(
            title="추출 영상 저장 경로",
            defaultextension=".mp4",
            filetypes=[("MP4", "*.mp4"), ("MKV", "*.mkv"), ("MOV", "*.mov"), ("All files", "*.*")],
        )
        if path: self.output_path.set(path)

    def run(self):
        inp = self.input_path.get().strip()
        out = self.output_path.get().strip()
        ss = self.start_time.get().strip()
        to = self.end_time.get().strip()

        if not inp or not os.path.exists(inp):
            messagebox.showerror("Error", "올바른 영상인지 파일의 확장자를 확인하세요.")
            return
        if not out:
            messagebox.showerror("Error", "추출된 영상이 저장 될 경로를 지정하세요.")
            return
        if not ss or not to:
            messagebox.showerror("Error", "시작 시간과 종료 시간을 지정하세요.")
            return

        cmd = [
            ffmpeg_bin, "-y",
            "-ss", str(ss),
            "-to", str(to),
            "-i", inp,
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            out,
        ]

        self.log_write("\n==============================\n")
        self.log_write(f"ffmpeg: {ffmpeg_bin}\ncmd: {quote_cmd(cmd)}\n\n")

        try:
            rc = run_logged(cmd, self.log_write)
            produced = os.path.exists(out) and os.path.getsize(out) > 1024
            if rc == 0:
                self.log_write("\n[OK] Extraction finished.\n")
                messagebox.showinfo("Done", f"Saved:\n{out}")
            elif produced:
                self.log_write(f"\n[WARN] ffmpeg returned exit code {rc}, 영상 추출 성공.\n")
                messagebox.showwarning("Extracted", f"저장된 경로:\n{out}\n\nffmpeg exit {rc}")
            else:
                self.log_write(f"\n[ERROR] ffmpeg exit code {rc}. 영상 추출 실패.\n")
                messagebox.showerror("실패", f"ffmpeg exit {rc}")
        except Exception as e:
            self.log_write(f"\n[ERROR] {e}\n")
            messagebox.showerror("오류", str(e))
