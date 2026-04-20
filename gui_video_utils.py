import os
import sys
import subprocess
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from tkinter import ttk
import tkinter.font as tkfont
from urllib.parse import urlparse, parse_qs, urlunparse # URL 파싱


VIDEO_TYPES = [
    ("Video files", "*.mp4 *.mkv *.mov *.avi *.webm *.m4v"),
    ("All files", "*.*"),
]

AUDIO_TYPES = [
    ("Audio files", "*.mp3 *.wav *.flac *.m4a *.ogg *.wma"),
    ("All files", "*.*"),
]

# Combined list for the Audio Extractor tab
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
ytdlp_bin = resource_path("yt-dlp.exe") # Added yt-dlp binary reference

if not os.path.exists(ffmpeg_bin): ffmpeg_bin = "ffmpeg"
if not os.path.exists(ytdlp_bin): ytdlp_bin = "yt-dlp"


def quote_cmd(cmd):
    # Pretty command for display (no shell execution)
    out = []
    for part in cmd:
        part = str(part)
        if " " in part or "\t" in part:
            out.append(f'"{part}"')
        else:
            out.append(part)
    return " ".join(out)


def run_logged(cmd, log_write, cwd=None):
    """Run a command and stream stdout/stderr to the provided logger."""
    log_write(f"> {quote_cmd(cmd)}\n")
    
    # Windows에서 한글 깨짐 방지를 위한 환경 변수 설정
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",    # FFmpeg/yt-dlp의 UTF-8 출력을 받음1
        errors="replace",    # 알 수 없는 문자는 대체 문자로 처리
        env=env,
        # Windows에서 실행 시 검은색 CMD 창이 튀어나오는 것을 방지
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0 
    )
    
    if proc.stdout:
        for line in proc.stdout:
            log_write(line)
            
    rc = proc.wait()
    return rc


class AudioExtractorTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)

        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.start_time = tk.StringVar(value="00:01:00")
        self.end_time = tk.StringVar(value="00:01:30")

        self._build()

    def _build(self):
        pad = {"padx": 10, "pady": 6}

        # Input Path
        ttk.Label(self, text="원본 파일 경로 (영상 또는 오디오):").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.input_path, width=70).grid(row=0, column=1, sticky="we", **pad)
        ttk.Button(self, text="파일 탐색", command=self.browse_input).grid(row=0, column=2, **pad)

        # Output Path
        ttk.Label(self, text="MP3 저장 경로:").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.output_path, width=70).grid(row=1, column=1, sticky="we", **pad)
        ttk.Button(self, text="저장 경로", command=self.browse_output).grid(row=1, column=2, **pad)

        # Time Controls
        ttk.Label(self, text="시작 시간 (HH:MM:SS):").grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.start_time, width=20).grid(row=2, column=1, sticky="w", **pad)

        ttk.Label(self, text="종료 시간 (HH:MM:SS):").grid(row=3, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.end_time, width=20).grid(row=3, column=1, sticky="w", **pad)

        # Action Button
        ttk.Button(self, text="MP3 변환/추출 시작", command=self.run).grid(row=4, column=1, sticky="w", padx=10, pady=10)

        # Log console
        ttk.Label(self, text="Console:").grid(row=5, column=0, sticky="w", **pad)
        self.log = ScrolledText(self, width=120, height=17, state="disabled", font=("Malgun Gothic", 10))
        self.log.grid(row=6, column=0, columnspan=3, sticky="nsew", padx=10, pady=(0, 10))

        self.log.tag_configure("success", foreground="green")
        self.log.tag_configure("error", foreground="red")
        self.log.tag_configure("warning", foreground="#CC9900") # 약간 어두운 노랑 (가독성용)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(6, weight=1)

    def log_write(self, text: str):
        # 때때로 들어오는 데이터가 인코딩이 꼬였을 경우를 대비
        try:
            # 이미 str 타입이지만, 혹시 모를 내부 깨짐 방지
            safe_text = text.encode('utf-8', errors='ignore').decode('utf-8')
        except:
            safe_text = text

        self.log.configure(state="normal")
        
        # 현재 마지막 위치 저장
        start_index = self.log.index("end-1c")
        self.log.insert("end", text)
        end_index = self.log.index("end-1c")

        # 키워드에 따라 색상 적용
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
        # Uses MEDIA_TYPES to allow video or audio selection
        path = filedialog.askopenfilename(title="원본 파일 선택", filetypes=MEDIA_TYPES)
        if path:
            self.input_path.set(path)
            # Auto-suggest .mp3 output name
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

        # FFmpeg Command Breakdown:
        # -ss / -to : Trim the time
        # -vn       : Disable video (crucial if input is a video file)
        # -acodec libmp3lame : Use the standard MP3 encoder
        # -q:a 2    : High quality Variable Bitrate (VBR)
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
        self.log_write(f"[AUDIO EXTRACTION/TRIM]\n")
        self.log_write(f"Source: {inp}\n")
        self.log_write(f"Command: {quote_cmd(cmd)}\n\n")

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


class ExtractorTab(ttk.Frame):
    def __init__(self, master, log_font_size=9):
        super().__init__(master)

        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.start_time = tk.StringVar(value="00:10:00")
        self.end_time = tk.StringVar(value="01:15:30")

        self._build()

    def _build(self):
        pad = {"padx": 10, "pady": 6}

        ttk.Label(self, text="원본 영상 경로:").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.input_path, width=70).grid(row=0, column=1, sticky="we", **pad)
        ttk.Button(self, text="파일 탐색", command=self.browse_input).grid(row=0, column=2, **pad)

        ttk.Label(self, text="추출 영상 경로:").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.output_path, width=70).grid(row=1, column=1, sticky="we", **pad)
        ttk.Button(self, text="저장 경로", command=self.browse_output).grid(row=1, column=2, **pad)

        ttk.Label(self, text="시작 시간 (HH:MM:SS):").grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.start_time, width=20).grid(row=2, column=1, sticky="w", **pad)

        ttk.Label(self, text="종료 시간 (HH:MM:SS):").grid(row=3, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.end_time, width=20).grid(row=3, column=1, sticky="w", **pad)

        ttk.Button(self, text="추출", command=self.run).grid(row=4, column=1, sticky="w", padx=10, pady=10)

        # Log console
        ttk.Label(self, text="Console:").grid(row=5, column=0, sticky="w", **pad)
        self.log = ScrolledText(self, width=120, height=17, state="disabled", font=("Malgun Gothic", 10))
        self.log.grid(row=6, column=0, columnspan=3, sticky="nsew", padx=10, pady=(0, 10))

        self.log.tag_configure("success", foreground="green")
        self.log.tag_configure("error", foreground="red")
        self.log.tag_configure("warning", foreground="#CC9900") # 약간 어두운 노랑 (가독성용)

        # Layout weights
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(6, weight=1)

    def log_write(self, text: str):
        # 때때로 들어오는 데이터가 인코딩이 꼬였을 경우를 대비
        try:
            # 이미 str 타입이지만, 혹시 모를 내부 깨짐 방지
            safe_text = text.encode('utf-8', errors='ignore').decode('utf-8')
        except:
            safe_text = text

        self.log.configure(state="normal")
        
        # 현재 마지막 위치 저장
        start_index = self.log.index("end-1c")
        self.log.insert("end", text)
        end_index = self.log.index("end-1c")

        # 키워드에 따라 색상 적용
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
        if path:
            self.output_path.set(path)

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

        out_dir = os.path.dirname(out)
        if out_dir and not os.path.exists(out_dir):
            messagebox.showerror("Error", f"저장 경로가 올바르지 않습니다:\n{out_dir}")
            return

        cmd = [
            ffmpeg_bin,
            "-y",
            "-ss", str(ss),
            "-to", str(to),
            "-i", inp,
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            out,
        ]

        self.log_write("\n==============================\n")
        self.log_write(f"ffmpeg: {ffmpeg_bin}\n")
        self.log_write(f"cmd: {quote_cmd(cmd)}\n\n")

        try:
            rc = run_logged(cmd, self.log_write)

            produced = os.path.exists(out) and os.path.getsize(out) > 1024

            if rc == 0:
                self.log_write("\n[OK] Extraction finished.\n")
                messagebox.showinfo("Done", f"Saved:\n{out}")
                return

            if produced:
                self.log_write(f"\n[WARN] ffmpeg returned exit code {rc}, 영상 추출 성공.\n")
                messagebox.showwarning(
                    "Extracted (with warnings)",
                    f"추출된 영상이 저장된 경로:\n{out}\n\nffmpeg returned exit code {rc}.\n콘솔의 에러를 확인하시오."
                )
                return

            self.log_write(f"\n[ERROR] ffmpeg returned exit code {rc}. 영상 추출 실패.\n")
            messagebox.showerror(
                "영상 추출 실패",
                f"ffmpeg returned exit code {rc}.\n콘솔의 에러를 확인하시오."
            )

        except FileNotFoundError:
            self.log_write("\n[ERROR] 올바른 ffmpeg 패키지가 없습니다.\n")
            messagebox.showerror(
                "ffmpeg not found",
                "ffmpeg.exe was not found (bundled) and ffmpeg is not on PATH.\n"
                "Rebuild with --add-data \"ffmpeg.exe;.\" and ensure ffmpeg.exe exists."
            )
        except Exception as e:
            self.log_write(f"\n[ERROR] {e}\n")
            messagebox.showerror("알 수 없는 오류로 영상 추출에 실패하였습니다", str(e))


class MergerTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)

        self.output_path = tk.StringVar(value=os.path.abspath("merged.mp4"))

        self._drag_from_index = None
        self._build()
        self._init_external_drop_support()

    def _build(self):
        pad = {"padx": 10, "pady": 6}

        # Row: output path
        ttk.Label(self, text="병합 저장 경로:").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.output_path, width=70).grid(row=0, column=1, sticky="we", **pad)
        ttk.Button(self, text="저장 경로", command=self.browse_output).grid(row=0, column=2, **pad)

        # Row: buttons
        btns = ttk.Frame(self)
        btns.grid(row=1, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 6))

        ttk.Button(btns, text="비디오 추가", command=self.add_videos).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="선택 제거", command=self.remove_selected).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(btns, text="모두 지우기", command=self.clear_list).grid(row=0, column=2, padx=(0, 8))
        ttk.Button(btns, text="▲ 위로", command=lambda: self.move_selected(-1)).grid(row=0, column=3, padx=(0, 8))
        ttk.Button(btns, text="▼ 아래로", command=lambda: self.move_selected(1)).grid(row=0, column=4, padx=(0, 8))
        ttk.Button(btns, text="병합", command=self.merge).grid(row=0, column=5, padx=(12, 0))

        # Listbox + scrollbar
        ttk.Label(self, text="병합 순서 (드래그로 순서 변경 가능):").grid(row=2, column=0, sticky="w", **pad)

        list_frame = ttk.Frame(self)
        list_frame.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=10, pady=(0, 10))

        self.listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=10)
        self.listbox.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        sb.pack(side="right", fill="y")
        self.listbox.configure(yscrollcommand=sb.set)

        # Internal drag reorder bindings
        self.listbox.bind("<Button-1>", self._on_list_click)
        self.listbox.bind("<B1-Motion>", self._on_list_drag)
        self.listbox.bind("<ButtonRelease-1>", self._on_list_release)

        # Log console
        ttk.Label(self, text="Console:").grid(row=4, column=0, sticky="w", **pad)
        self.log = ScrolledText(self, width=120, height=15, state="disabled", font=("Malgun Gothic", 10))
        self.log.grid(row=5, column=0, columnspan=3, sticky="nsew", padx=10, pady=(0, 10))

        self.log.tag_configure("success", foreground="green")
        self.log.tag_configure("error", foreground="red")
        self.log.tag_configure("warning", foreground="#CC9900") # 약간 어두운 노랑 (가독성용)

        # Layout weights
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self.grid_rowconfigure(5, weight=1)

    def log_write(self, text: str):
        # 때때로 들어오는 데이터가 인코딩이 꼬였을 경우를 대비
        try:
            # 이미 str 타입이지만, 혹시 모를 내부 깨짐 방지
            safe_text = text.encode('utf-8', errors='ignore').decode('utf-8')
        except:
            safe_text = text

        self.log.configure(state="normal")
        
        # 현재 마지막 위치 저장
        start_index = self.log.index("end-1c")
        self.log.insert("end", text)
        end_index = self.log.index("end-1c")

        # 키워드에 따라 색상 적용
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
        if path:
            self.output_path.set(path)

    def add_videos(self):
        paths = filedialog.askopenfilenames(title="병합할 비디오 선택", filetypes=VIDEO_TYPES)
        if not paths:
            return
        self._add_files(paths)

    def _add_files(self, paths):
        added = 0
        for p in paths:
            p = p.strip()
            if not p:
                continue
            if not os.path.exists(p):
                continue
            # avoid duplicates
            existing = set(self.listbox.get(0, "end"))
            if p in existing:
                continue
            self.listbox.insert("end", p)
            added += 1
        if added:
            self.log_write(f"[INFO] Added {added} file(s).\n")

    def remove_selected(self):
        sel = list(self.listbox.curselection())
        if not sel:
            return
        for i in reversed(sel):
            self.listbox.delete(i)

    def clear_list(self):
        self.listbox.delete(0, "end")

    def move_selected(self, delta):
        sel = list(self.listbox.curselection())
        if len(sel) != 1:
            messagebox.showinfo("Info", "한 개만 선택 후 이동하세요.")
            return
        i = sel[0]
        j = i + delta
        if j < 0 or j >= self.listbox.size():
            return
        item = self.listbox.get(i)
        self.listbox.delete(i)
        self.listbox.insert(j, item)
        self.listbox.selection_set(j)

    # --- Internal drag reorder ---
    def _on_list_click(self, event):
        self._drag_from_index = self.listbox.nearest(event.y)

    def _on_list_drag(self, event):
        if self._drag_from_index is None:
            return
        to_index = self.listbox.nearest(event.y)
        if to_index == self._drag_from_index:
            return
        item = self.listbox.get(self._drag_from_index)
        self.listbox.delete(self._drag_from_index)
        self.listbox.insert(to_index, item)
        self._drag_from_index = to_index
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(to_index)

    def _on_list_release(self, event):
        self._drag_from_index = None

    # --- External file drop support (best-effort on Windows) ---
    def _init_external_drop_support(self):
        """
        Best-effort Windows drag&drop into Listbox using tkdnd if available.
        If not available, app still works via file dialog.
        """
        self._dnd_enabled = False
        try:
            # tkdnd is not part of stdlib. Many machines won't have it.
            # If user installs tkinterdnd2, this can be enabled.
            import tkinterdnd2  # type: ignore

            # Re-parent root: tkinterdnd2 requires using TkinterDnD.Tk()
            # We can't safely change the root class here, so only enable if root already supports it.
            # (Most likely not in your current app.)
            self.log_write("[INFO] tkinterdnd2 detected, but root is not TkinterDnD.Tk(). External drop disabled.\n")
        except Exception:
            # No external DnD support; internal reorder still works.
            pass

    # --- ffmpeg merging logic (v2-inspired) ---
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

        out_dir = os.path.dirname(out)
        if out_dir and not os.path.exists(out_dir):
            messagebox.showerror("Error", f"저장 경로가 올바르지 않습니다:\n{out_dir}")
            return

        self.log_write("\n==============================\n")
        self.log_write(f"ffmpeg: {ffmpeg_bin}\n")
        self.log_write(f"[INFO] Output: {out}\n")

        try:
            # First try: fast (lossless) concat demuxer after regenerating PTS
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
        """
        v2 fast path:
        - regenerate PTS (copy streams)
        - concat demuxer with -c copy (lossless when compatible)
        """
        workdir = tempfile.mkdtemp(prefix="video_merge_")
        fixed = []
        try:
            for f in files:
                fixed_name = os.path.join(workdir, f"fixed_{os.path.basename(f)}")
                cmd = [ffmpeg_bin, "-y", "-fflags", "+genpts", "-i", f, "-c", "copy", fixed_name]
                rc = run_logged(cmd, self.log_write)
                if rc != 0:
                    raise RuntimeError(f"ffmpeg genpts failed for: {f} (exit {rc})")
                fixed.append(fixed_name)

            file_list = os.path.join(workdir, "input.txt")
            with open(file_list, "w", encoding="utf-8") as fh:
                for ff in fixed:
                    ff_norm = ff.replace("\\", "/")
                    fh.write(f"file '{ff_norm}'\n")

            cmd_merge = [ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", file_list, "-c", "copy", out]
            rc = run_logged(cmd_merge, self.log_write)
            if rc != 0:
                raise RuntimeError(f"ffmpeg concat copy failed (exit {rc})")

            return out
        finally:
            # Cleanup (best effort)
            try:
                for p in fixed:
                    if os.path.exists(p):
                        os.remove(p)
                file_list = os.path.join(workdir, "input.txt")
                if os.path.exists(file_list):
                    os.remove(file_list)
                if os.path.exists(workdir):
                    os.rmdir(workdir)
            except Exception:
                pass

    def reencode_and_concat_demuxer(self, files, out, crf=14):
        """
        Re-encode each input ONCE to a uniform format, then concat demuxer with -c copy.

        Your requested changes:
        - remove '-r 30' (we do NOT force FPS)
        - use CRF=14 (higher quality, bigger file)
        """
        workdir = tempfile.mkdtemp(prefix="video_reenc_")
        reenc = []
        try:
            for f in files:
                name = os.path.join(workdir, f"reenc_{os.path.basename(f)}")
                cmd = [
                    ffmpeg_bin, "-y", "-fflags", "+genpts", "-i", f,
                    # video
                    "-c:v", "libx264", "-preset", "fast", "-crf", str(crf), "-pix_fmt", "yuv420p",
                    # audio (normalize for concat)
                    "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
                    name,
                ]
                rc = run_logged(cmd, self.log_write)
                if rc != 0:
                    raise RuntimeError(f"ffmpeg re-encode failed for: {f} (exit {rc})")
                reenc.append(name)

            file_list = os.path.join(workdir, "input.txt")
            with open(file_list, "w", encoding="utf-8") as fh:
                for rr in reenc:
                    rr_norm = rr.replace("\\", "/")
                    fh.write(f"file '{rr_norm}'\n")

            # Now safe to stream-copy merge (no 2nd generation loss)
            cmd_merge = [ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", file_list, "-c", "copy", out]
            rc = run_logged(cmd_merge, self.log_write)
            if rc != 0:
                raise RuntimeError(f"ffmpeg concat (copy) failed after re-encode (exit {rc})")

            return out
        finally:
            # Cleanup (best effort)
            try:
                for p in reenc:
                    if os.path.exists(p):
                        os.remove(p)
                file_list = os.path.join(workdir, "input.txt")
                if os.path.exists(file_list):
                    os.remove(file_list)
                if os.path.exists(workdir):
                    os.rmdir(workdir)
            except Exception:
                pass


class YoutubeDownloaderTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.url = tk.StringVar()
        self.output_path = tk.StringVar()
        # 다운로드 타입 기본값 mp4
        self.download_type = tk.StringVar(value="mp4") 
        # 타입 변경 시 확장자 자동 업데이트를 위한 추적(trace) 설정
        self.download_type.trace_add("write", self._update_extension)

        self._build()

    def _build(self):
        pad = {"padx": 10, "pady": 6}

        # URL Input
        ttk.Label(self, text="YouTube URL:").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.url, width=70).grid(row=0, column=1, sticky="we", **pad)

        # Output Path
        ttk.Label(self, text="저장 경로:").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.output_path, width=70).grid(row=1, column=1, sticky="we", **pad)
        ttk.Button(self, text="경로 선택", command=self.browse_output).grid(row=1, column=2, **pad)

        # Download Options (Type)
        opts_frame = ttk.LabelFrame(self, text="다운로드 옵션")
        opts_frame.grid(row=2, column=1, sticky="w", **pad)
        ttk.Radiobutton(opts_frame, text="Video (MP4 1080p)", variable=self.download_type, value="mp4").pack(side="left", padx=5)
        ttk.Radiobutton(opts_frame, text="Audio (MP3)", variable=self.download_type, value="mp3").pack(side="left", padx=5)

        # Action Button
        ttk.Button(self, text="다운로드 시작", command=self.run).grid(row=3, column=1, sticky="w", padx=10, pady=10)

        # Log console
        ttk.Label(self, text="Console:").grid(row=4, column=0, sticky="w", **pad)
        self.log = ScrolledText(self, width=120, height=20, state="disabled", font=("Malgun Gothic", 10))
        self.log.grid(row=5, column=0, columnspan=3, sticky="nsew", padx=10, pady=(0, 10))

        self.log.tag_configure("success", foreground="green")
        self.log.tag_configure("error", foreground="red")
        self.log.tag_configure("warning", foreground="#CC9900") # 약간 어두운 노랑 (가독성용)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(5, weight=1)

    def _update_extension(self, *args):
        """다운로드 옵션이 바뀔 때 기존 경로의 확장자를 교체함"""
        current_path = self.output_path.get().strip()
        if not current_path:
            return

        new_ext = ".mp4" if self.download_type.get() == "mp4" else ".mp3"
        base, _ = os.path.splitext(current_path)
        
        # .mp4.mp3 중복 방지를 위해 확장자를 새로 붙임
        self.output_path.set(base + new_ext)

    def browse_output(self):
        ext = ".mp4" if self.download_type.get() == "mp4" else ".mp3"
        ftypes = [("Video", "*.mp4")] if self.download_type.get() == "mp4" else [("Audio", "*.mp3")]
        
        path = filedialog.asksaveasfilename(
            title="저장 경로 선택", 
            defaultextension=ext,
            filetypes=ftypes + [("All files", "*.*")]
        )
        if path: 
            self.output_path.set(path)

    def log_write(self, text: str):
        # 때때로 들어오는 데이터가 인코딩이 꼬였을 경우를 대비
        try:
            # 이미 str 타입이지만, 혹시 모를 내부 깨짐 방지
            safe_text = text.encode('utf-8', errors='ignore').decode('utf-8')
        except:
            safe_text = text

        self.log.configure(state="normal")
        
        # 현재 마지막 위치 저장
        start_index = self.log.index("end-1c")
        self.log.insert("end", text)
        end_index = self.log.index("end-1c")

        # 키워드에 따라 색상 적용
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
        
        # --- URL 정제 로직 추가 ---
        try:
            parsed_url = urlparse(raw_url)
            if 'youtube.com' in parsed_url.netloc:
                query = parse_qs(parsed_url.query)
                # 'v' 파라미터(영상 ID)만 추출
                video_id = query.get('v', [None])[0]
                if video_id:
                    # &list= 등 부가 정보를 제외한 깨끗한 URL 재조합
                    url = f"https://www.youtube.com/watch?v={video_id}"
                else:
                    url = raw_url
            elif 'youtu.be' in parsed_url.netloc:
                # 단축 URL(youtu.be/ID)의 경우 경로 부분만 유지
                url = f"https://youtu.be{parsed_url.path}"
            else:
                url = raw_url
        except Exception:
            url = raw_url
        # -------------------------
        
        if not out:
            messagebox.showerror("Error", "저장 경로를 선택하세요.")
            return

        # yt-dlp 명령어 구성
        cmd = [ytdlp_bin, "--ffmpeg-location", ffmpeg_bin]
        
        if self.download_type.get() == "mp3":
            cmd += ["-x", "--audio-format", "mp3", "--audio-quality", "0"]
        else:
            # H.264/AAC MP4 우선순위 설정
            cmd += [
                "-f", "bestvideo[height<=1080][vcodec^=avc1]+bestaudio[acodec^=mp4a]/best[height<=1080][ext=mp4]/best",
                "--merge-output-format", "mp4",
                "--format-sort", "vcodec:h264,res:1080,acodec:m4a"
            ]

        # 구간 설정 코드 삭제됨 (전체 다운로드)
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


# =========================
# Main app (tabs)
# =========================
class App(tk.Tk):
    def __init__(self):
        super().__init__()

        # ----- Increase font size globally -----
        base_font_family = "Malgun Gothic"
        base_size = 10
        mono_size = 10

        font_names = (
            "TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont",
            "TkCaptionFont", "TkSmallCaptionFont", "TkIconFont", "TkTooltipFont"
        )

        for name in font_names:
            tkfont.nametofont(name).configure(family=base_font_family, size=base_size)
            
        # 고정폭 폰트(콘솔용) 설정
        tkfont.nametofont("TkFixedFont").configure(family=base_font_family, size=mono_size)
        # --------------------------------------

        self.title("Audio & Video Utility")
        self.geometry("900x650")
        self.resizable(True, True)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        self.audio_tab = AudioExtractorTab(nb)
        self.extract_tab = ExtractorTab(nb)
        self.merge_tab = MergerTab(nb)
        self.yt_tab = YoutubeDownloaderTab(nb)

        nb.add(self.audio_tab, text="MP3 추출")
        nb.add(self.extract_tab, text="영상 추출")
        nb.add(self.merge_tab, text="영상 병합")
        nb.add(self.yt_tab, text="YouTube 다운로드")

        # Footer
        footer = ttk.Label(self, text="\N{COPYRIGHT SIGN} 2026 리턴1. All rights reserved.", foreground="#444")
        footer.pack(anchor="w", padx=10, pady=(0, 10))


if __name__ == "__main__":
    App().mainloop()

# Build:
# py -m PyInstaller --noconsole --onefile --name "AudioVideoUtils" --add-data "ffmpeg.exe;." gui_video_utils.py
# py -m PyInstaller --noconsole --onefile --name "AudioVideoUtils_v3.0.0" --add-data "ffmpeg.exe;." --add-data "yt-dlp.exe;." gui_video_utils.py
