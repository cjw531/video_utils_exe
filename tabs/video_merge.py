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


class VideoMergeTab(ctk.CTkFrame):
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

        ctk.CTkLabel(self, text="병합 순서 (드래그로 순서 변경 가능):").grid(row=2, column=0, columnspan=3, sticky="w", **pad)

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

        ctk.CTkLabel(self, text="Console:").grid(row=4, column=0, columnspan=3, sticky="w", **pad)
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