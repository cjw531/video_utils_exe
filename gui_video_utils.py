import os
import sys
import subprocess
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox
from urllib.parse import urlparse, parse_qs

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


class AudioExtractorTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        self.input_path = ctk.StringVar()
        self.output_path = ctk.StringVar()
        self.start_time = ctk.StringVar(value="00:01:00")
        self.end_time = ctk.StringVar(value="00:01:30")

        self._build()

    def _build(self):
        pad = {"padx": 10, "pady": 8}

        ctk.CTkLabel(self, text="원본 파일 경로 (영상/오디오):").grid(row=0, column=0, sticky="w", **pad)
        ctk.CTkEntry(self, textvariable=self.input_path).grid(row=0, column=1, sticky="we", **pad)
        ctk.CTkButton(self, text="파일 탐색", command=self.browse_input, width=100).grid(row=0, column=2, **pad)

        ctk.CTkLabel(self, text="MP3 저장 경로:").grid(row=1, column=0, sticky="w", **pad)
        ctk.CTkEntry(self, textvariable=self.output_path).grid(row=1, column=1, sticky="we", **pad)
        ctk.CTkButton(self, text="저장 경로", command=self.browse_output, width=100).grid(row=1, column=2, **pad)

        ctk.CTkLabel(self, text="시작 시간 (HH:MM:SS):").grid(row=2, column=0, sticky="w", **pad)
        ctk.CTkEntry(self, textvariable=self.start_time, width=150).grid(row=2, column=1, sticky="w", **pad)

        ctk.CTkLabel(self, text="종료 시간 (HH:MM:SS):").grid(row=3, column=0, sticky="w", **pad)
        ctk.CTkEntry(self, textvariable=self.end_time, width=150).grid(row=3, column=1, sticky="w", **pad)

        ctk.CTkButton(self, text="MP3 변환/추출 시작", command=self.run, fg_color="#2b7b50", hover_color="#1f5a3a").grid(row=4, column=1, sticky="w", padx=10, pady=15)

        ctk.CTkLabel(self, text="Console:").grid(row=5, column=0, sticky="w", **pad)
        self.log = ctk.CTkTextbox(self, state="disabled", font=("Malgun Gothic", 12))
        self.log.grid(row=6, column=0, columnspan=3, sticky="nsew", padx=10, pady=(0, 10))

        # Textbox tags support
        self.log.tag_config("success", foreground="#00FF00")
        self.log.tag_config("error", foreground="#FF4444")
        self.log.tag_config("warning", foreground="#FFD700")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(6, weight=1)

    def log_write(self, text: str):
        try:
            safe_text = text.encode('utf-8', errors='ignore').decode('utf-8')
        except:
            safe_text = text

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
        path = filedialog.askopenfilename(title="원본 파일 선택", filetypes=MEDIA_TYPES)
        if path:
            self.input_path.set(path)
            if not self.output_path.get().strip():
                base, _ = os.path.splitext(path)
                self.output_path.set(f"{base}_extracted.mp3")

    def browse_output(self):
        path = filedialog.asksaveasfilename(
            title="MP3 저장 경로",
            defaultextension=".mp3",
            filetypes=[("MP4 Audio", "*.mp3"), ("All files", "*.*")],
        )
        if path:
            self.output_path.set(path)

    def run(self):
        inp = self.input_path.get().strip()
        out = self.output_path.get().strip()
        ss = self.start_time.get().strip()
        to = self.end_time.get().strip()

        if not inp or not os.path.exists(inp):
            messagebox.showerror("Error", "올바른 원본 파일 경로를 지정하세요.")
            return
        if not out:
            messagebox.showerror("Error", "저장될 MP3 경로를 지정하세요.")
            return

        cmd = [
            ffmpeg_bin, "-y",
            "-ss", ss,
            "-to", to,
            "-i", inp,
            "-vn",
            "-acodec", "libmp3lame",
            "-q:a", "2",
            out
        ]

        self.log_write("\n==============================\n")
        self.log_write(f"[AUDIO EXTRACTION/TRIM]\nSource: {inp}\nCommand: {quote_cmd(cmd)}\n\n")

        try:
            rc = run_logged(cmd, self.log_write)
            if rc == 0:
                self.log_write("\n[OK] MP3 작업 완료.\n")
                messagebox.showinfo("Done", f"MP3 파일이 생성되었습니다:\n{out}")
            else:
                self.log_write(f"\n[ERROR] ffmpeg exit code: {rc}\n")
                messagebox.showerror("Error", "추출 작업 중 오류가 발생했습니다. 콘솔을 확인하세요.")
        except Exception as e:
            self.log_write(f"\n[FATAL ERROR] {str(e)}\n")
            messagebox.showerror("Error", str(e))


class ExtractorTab(ctk.CTkFrame):
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


class MergerTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.output_path = ctk.StringVar(value=os.path.abspath("merged.mp4"))
        self._drag_from_index = None
        self._build()

    def _build(self):
        pad = {"padx": 10, "pady": 8}

        ctk.CTkLabel(self, text="병합 저장 경로:").grid(row=0, column=0, sticky="w", **pad)
        ctk.CTkEntry(self, textvariable=self.output_path).grid(row=0, column=1, sticky="we", **pad)
        ctk.CTkButton(self, text="저장 경로", command=self.browse_output, width=100).grid(row=0, column=2, **pad)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=1, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 6))

        ctk.CTkButton(btns, text="비디오 추가", command=self.add_videos, width=100).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btns, text="선택 제거", command=self.remove_selected, width=100).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btns, text="모두 지우기", command=self.clear_list, width=100).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btns, text="▲ 위로", command=lambda: self.move_selected(-1), width=80).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btns, text="▼ 아래로", command=lambda: self.move_selected(1), width=80).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btns, text="병합 시작", command=self.merge, width=100, fg_color="#2b7b50", hover_color="#1f5a3a").pack(side="left", padx=(15, 0))

        ctk.CTkLabel(self, text="병합 순서 (드래그로 순서 변경 가능):").grid(row=2, column=0, sticky="w", **pad)

        # Style standard Listbox for Dark Mode
        list_frame = ctk.CTkFrame(self)
        list_frame.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=10, pady=(0, 10))
        
        self.listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, bg="#2b2b2b", fg="white", 
                                  selectbackground="#1f538d", highlightthickness=0, borderwidth=0, font=("Malgun Gothic", 11))
        self.listbox.pack(side="left", fill="both", expand=True, padx=2, pady=2)

        sb = ctk.CTkScrollbar(list_frame, command=self.listbox.yview)
        sb.pack(side="right", fill="y")
        self.listbox.configure(yscrollcommand=sb.set)

        self.listbox.bind("<Button-1>", self._on_list_click)
        self.listbox.bind("<B1-Motion>", self._on_list_drag)
        self.listbox.bind("<ButtonRelease-1>", self._on_list_release)

        ctk.CTkLabel(self, text="Console:").grid(row=4, column=0, sticky="w", **pad)
        self.log = ctk.CTkTextbox(self, state="disabled", font=("Malgun Gothic", 12))
        self.log.grid(row=5, column=0, columnspan=3, sticky="nsew", padx=10, pady=(0, 10))

        self.log.tag_config("success", foreground="#00FF00")
        self.log.tag_config("error", foreground="#FF4444")
        self.log.tag_config("warning", foreground="#FFD700")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self.grid_rowconfigure(5, weight=1)

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

    def browse_output(self):
        path = filedialog.asksaveasfilename(
            title="병합 영상 저장 경로",
            defaultextension=".mp4",
            filetypes=[("MP4", "*.mp4"), ("MKV", "*.mkv"), ("MOV", "*.mov"), ("All files", "*.*")],
        )
        if path: self.output_path.set(path)

    def add_videos(self):
        paths = filedialog.askopenfilenames(title="병합할 비디오 선택", filetypes=VIDEO_TYPES)
        if paths: self._add_files(paths)

    def _add_files(self, paths):
        added = 0
        existing = set(self.listbox.get(0, "end"))
        for p in paths:
            p = p.strip()
            if not p or not os.path.exists(p) or p in existing:
                continue
            self.listbox.insert("end", p)
            added += 1
        if added:
            self.log_write(f"[INFO] Added {added} file(s).\n")

    def remove_selected(self):
        sel = list(self.listbox.curselection())
        for i in reversed(sel): self.listbox.delete(i)

    def clear_list(self):
        self.listbox.delete(0, "end")

    def move_selected(self, delta):
        sel = list(self.listbox.curselection())
        if len(sel) != 1:
            messagebox.showinfo("Info", "한 개만 선택 후 이동하세요.")
            return
        i = sel[0]
        j = i + delta
        if j < 0 or j >= self.listbox.size(): return
        item = self.listbox.get(i)
        self.listbox.delete(i)
        self.listbox.insert(j, item)
        self.listbox.selection_set(j)

    def _on_list_click(self, event):
        self._drag_from_index = self.listbox.nearest(event.y)

    def _on_list_drag(self, event):
        if self._drag_from_index is None: return
        to_index = self.listbox.nearest(event.y)
        if to_index == self._drag_from_index: return
        item = self.listbox.get(self._drag_from_index)
        self.listbox.delete(self._drag_from_index)
        self.listbox.insert(to_index, item)
        self._drag_from_index = to_index
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(to_index)

    def _on_list_release(self, event):
        self._drag_from_index = None

    def merge(self):
        files = list(self.listbox.get(0, "end"))
        out = self.output_path.get().strip()

        if len(files) < 2:
            messagebox.showerror("Error", "병합할 비디오를 2개 이상 추가하세요.")
            return
        for f in files:
            if not os.path.exists(f):
                messagebox.showerror("Error", f"파일이 존재하지 않습니다:\n{f}")
                return
        if not out:
            messagebox.showerror("Error", "저장 경로를 지정하세요.")
            return

        self.log_write("\n==============================\n")
        self.log_write(f"ffmpeg: {ffmpeg_bin}\n[INFO] Output: {out}\n")

        try:
            merged = self.try_fast_fix(files, out)
            self.log_write(f"\n[OK] Fast merge done:\n{merged}\n")
            messagebox.showinfo("Done", f"Fast merge completed:\n{merged}")
            return
        except Exception as e:
            self.log_write(f"\n[WARN] Fast merge failed. Falling back to re-encode.\nReason: {e}\n")

        try:
            merged = self.reencode_and_concat_demuxer(files, out, crf=14)
            self.log_write(f"\n[OK] Re-encode merge done:\n{merged}\n")
            messagebox.showinfo("Done", f"Re-encode merge completed:\n{merged}")
        except Exception as e:
            self.log_write(f"\n[ERROR] Merge failed: {e}\n")
            messagebox.showerror("Merge failed", str(e))

    def try_fast_fix(self, files, out):
        workdir = tempfile.mkdtemp(prefix="video_merge_")
        fixed = []
        try:
            for f in files:
                fixed_name = os.path.join(workdir, f"fixed_{os.path.basename(f)}")
                cmd = [ffmpeg_bin, "-y", "-fflags", "+genpts", "-i", f, "-c", "copy", fixed_name]
                rc = run_logged(cmd, self.log_write)
                if rc != 0: raise RuntimeError(f"ffmpeg genpts failed for: {f} (exit {rc})")
                fixed.append(fixed_name)

            file_list = os.path.join(workdir, "input.txt")
            with open(file_list, "w", encoding="utf-8") as fh:
                for ff in fixed:
                    fh.write(f"file '{ff.replace(os.sep, '/')}'\n")

            cmd_merge = [ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", file_list, "-c", "copy", out]
            rc = run_logged(cmd_merge, self.log_write)
            if rc != 0: raise RuntimeError(f"ffmpeg concat copy failed (exit {rc})")
            return out
        finally:
            try:
                for p in fixed:
                    if os.path.exists(p): os.remove(p)
                file_list = os.path.join(workdir, "input.txt")
                if os.path.exists(file_list): os.remove(file_list)
                if os.path.exists(workdir): os.rmdir(workdir)
            except Exception: pass

    def reencode_and_concat_demuxer(self, files, out, crf=14):
        workdir = tempfile.mkdtemp(prefix="video_reenc_")
        reenc = []
        try:
            for f in files:
                name = os.path.join(workdir, f"reenc_{os.path.basename(f)}")
                cmd = [
                    ffmpeg_bin, "-y", "-fflags", "+genpts", "-i", f,
                    "-c:v", "libx264", "-preset", "fast", "-crf", str(crf), "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", name,
                ]
                rc = run_logged(cmd, self.log_write)
                if rc != 0: raise RuntimeError(f"ffmpeg re-encode failed for: {f} (exit {rc})")
                reenc.append(name)

            file_list = os.path.join(workdir, "input.txt")
            with open(file_list, "w", encoding="utf-8") as fh:
                for rr in reenc:
                    fh.write(f"file '{rr.replace(os.sep, '/')}'\n")

            cmd_merge = [ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", file_list, "-c", "copy", out]
            rc = run_logged(cmd_merge, self.log_write)
            if rc != 0: raise RuntimeError(f"ffmpeg concat failed after re-encode (exit {rc})")
            return out
        finally:
            try:
                for p in reenc:
                    if os.path.exists(p): os.remove(p)
                file_list = os.path.join(workdir, "input.txt")
                if os.path.exists(file_list): os.remove(file_list)
                if os.path.exists(workdir): os.rmdir(workdir)
            except Exception: pass


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

    def run(self):
        raw_url = self.url.get().strip()
        out = self.output_path.get().strip()
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
        
        try:
            rc = run_logged(cmd, self.log_write)
            if rc == 0:
                self.log_write("\n[OK] Download completed.\n")
                messagebox.showinfo("Done", "다운로드가 완료되었습니다.")
            else:
                self.log_write(f"\n[ERROR] yt-dlp exit code: {rc}\n")
                messagebox.showerror("Error", f"다운로드 중 오류 발생 (Exit Code: {rc})\n콘솔을 확인하세요.")
        except Exception as e:
            self.log_write(f"\n[FATAL ERROR] {str(e)}\n")
            messagebox.showerror("Error", str(e))


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- CustomTkinter Theme Setup ---
        ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
        ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

        self.title("Audio & Video Utility")
        self.geometry("1000x750")

        # --- CTkTabview replacing ttk.Notebook ---
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        # Add tabs to tabview
        self.tab_audio = self.tabview.add("MP3 추출")
        self.tab_extract = self.tabview.add("영상 추출")
        self.tab_merge = self.tabview.add("영상 병합")
        self.tab_yt = self.tabview.add("YouTube 다운로드")

        # Instantiate tab classes by passing the created tab frames
        self.audio_tab = AudioExtractorTab(self.tab_audio)
        self.audio_tab.pack(fill="both", expand=True)

        self.extract_tab = ExtractorTab(self.tab_extract)
        self.extract_tab.pack(fill="both", expand=True)

        self.merge_tab = MergerTab(self.tab_merge)
        self.merge_tab.pack(fill="both", expand=True)

        self.yt_tab = YoutubeDownloaderTab(self.tab_yt)
        self.yt_tab.pack(fill="both", expand=True)

        # Footer
        footer = ctk.CTkLabel(self, text="\N{COPYRIGHT SIGN} 2026 리턴1. All rights reserved.", text_color="gray")
        footer.pack(anchor="w", padx=20, pady=(0, 10))


if __name__ == "__main__":
    App().mainloop()


# Build:
# py -m PyInstaller --noconsole --onefile --name "AudioVideoUtils" --add-data "ffmpeg.exe;." gui_video_utils.py
# py -m PyInstaller --noconsole --onefile --name "AudioVideoUtils_v3.0.0" --add-data "ffmpeg.exe;." --add-data "yt-dlp.exe;." gui_video_utils.py
