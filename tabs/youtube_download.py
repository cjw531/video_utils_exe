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


class YoutubeDownloaderTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.url = ctk.StringVar()
        self.output_path = ctk.StringVar()
        self.download_type = ctk.StringVar(value="mp4") 
        self.download_type.trace_add("write", self._update_extension)
        self._build()

    def _build(self):
        pad = {"padx": 10, "pady": 8}

        ctk.CTkLabel(self, text="YouTube URL:").grid(row=0, column=0, sticky="w", **pad)
        ctk.CTkEntry(self, textvariable=self.url).grid(row=0, column=1, sticky="we", **pad)

        ctk.CTkLabel(self, text="저장 경로:").grid(row=1, column=0, sticky="w", **pad)
        ctk.CTkEntry(self, textvariable=self.output_path).grid(row=1, column=1, sticky="we", **pad)
        ctk.CTkButton(self, text="경로 선택", command=self.browse_output, width=100).grid(row=1, column=2, **pad)

        ctk.CTkLabel(self, text="다운로드 형식:").grid(row=2, column=0, sticky="w", **pad)
        opts_frame = ctk.CTkFrame(self, fg_color="transparent")
        opts_frame.grid(row=2, column=1, sticky="w", padx=10, pady=8)
        
        ctk.CTkRadioButton(opts_frame, text="Video (MP4 1080p)", variable=self.download_type, value="mp4").pack(side="left", padx=(0, 15))
        ctk.CTkRadioButton(opts_frame, text="Audio (MP3)", variable=self.download_type, value="mp3").pack(side="left", padx=5)

        ctk.CTkButton(self, text="다운로드 시작", command=self.run, fg_color="#2b7b50", hover_color="#1f5a3a").grid(row=3, column=1, sticky="w", padx=10, pady=15)

        ctk.CTkLabel(self, text="Console:").grid(row=4, column=0, sticky="w", **pad)
        self.log = ctk.CTkTextbox(self, state="disabled", font=("Malgun Gothic", 12))
        self.log.grid(row=5, column=0, columnspan=3, sticky="nsew", padx=10, pady=(0, 10))

        self.log.tag_config("success", foreground="#00FF00")
        self.log.tag_config("error", foreground="#FF4444")
        self.log.tag_config("warning", foreground="#FFD700")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(5, weight=1)

    def _update_extension(self, *args):
        current_path = self.output_path.get().strip()
        if not current_path: return
        new_ext = ".mp4" if self.download_type.get() == "mp4" else ".mp3"
        base, _ = os.path.splitext(current_path)
        self.output_path.set(base + new_ext)

    def browse_output(self):
        ext = ".mp4" if self.download_type.get() == "mp4" else ".mp3"
        ftypes = [("Video", "*.mp4")] if self.download_type.get() == "mp4" else [("Audio", "*.mp3")]
        path = filedialog.asksaveasfilename(
            title="저장 경로 선택", 
            defaultextension=ext,
            filetypes=ftypes + [("All files", "*.*")]
        )
        if path: self.output_path.set(path)

    def log_write(self, text: str):
        def update_log():
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
            
        # 메인 스레드에서 안전하게 UI를 업데이트하도록 예약
        self.after(0, update_log)

    def run(self):
        raw_url = self.url.get().strip()
        out = self.output_path.get().strip()
        
        # 1. UI 입력값 검증 (메인 스레드에서 즉시 처리)
        if not raw_url:
            messagebox.showerror("Error", "YouTube URL을 입력하세요.")
            return
        
        try:
            parsed_url = urlparse(raw_url)
            if 'youtube.com' in parsed_url.netloc:
                query = parse_qs(parsed_url.query)
                video_id = query.get('v', [None])[0]
                url = f"https://www.youtube.com/watch?v={video_id}" if video_id else raw_url
            elif 'youtu.be' in parsed_url.netloc:
                url = f"https://youtu.be{parsed_url.path}"
            else:
                url = raw_url
        except Exception:
            url = raw_url
            
        if not out:
            messagebox.showerror("Error", "저장 경로를 선택하세요.")
            return

        cmd = [ytdlp_bin, "--ffmpeg-location", ffmpeg_bin]
        if self.download_type.get() == "mp3":
            cmd += ["-x", "--audio-format", "mp3", "--audio-quality", "0"]
        else:
            cmd += [
                "-f", "bestvideo[height<=1080][vcodec^=avc1]+bestaudio[acodec^=mp4a]/best[height<=1080][ext=mp4]/best",
                "--merge-output-format", "mp4",
                "--format-sort", "vcodec:h264,res:1080,acodec:m4a"
            ]

        cmd += ["-o", out, url]

        self.log_write(f"\n[DOWNLOAD START]\nURL: {url}\nOutput: {out}\n")
        self.log_write(f"Command: {quote_cmd(cmd)}\n\n")
        
        # 2. 백그라운드 스레드에서 실행할 작업 정의
        def download_process():
            try:
                rc = run_logged(cmd, self.log_write)
                if rc == 0:
                    self.log_write("\n[OK] Download completed.\n")
                    # UI 조작(messagebox)은 메인 스레드에서 안전하게 실행되도록 self.after 사용
                    self.after(0, lambda: messagebox.showinfo("Done", "다운로드가 완료되었습니다."))
                else:
                    self.log_write(f"\n[ERROR] yt-dlp exit code: {rc}\n")
                    self.after(0, lambda: messagebox.showerror("Error", f"다운로드 중 오류 발생 (Exit Code: {rc})\n콘솔을 확인하세요."))
            except Exception as e:
                self.log_write(f"\n[FATAL ERROR] {str(e)}\n")
                self.after(0, lambda: messagebox.showerror("Error", str(e)))

        # 3. 스레드 시작 (daemon=True로 설정하면 메인 프로그램 종료 시 스레드도 함께 종료됨)
        threading.Thread(target=download_process, daemon=True).start()
