import os
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import tkinter.font as tkfont


VIDEO_TYPES = [
    ("Video files", "*.mp4 *.mkv *.mov *.avi *.webm *.m4v"),
    ("All files", "*.*"),
]

# --- PyInstaller resource resolution (your requested version) ---
def resource_path(rel):
    return os.path.join(getattr(sys, "_MEIPASS", os.path.abspath(".")), rel)

ffmpeg_bin = resource_path("ffmpeg.exe")
if not os.path.exists(ffmpeg_bin):
    ffmpeg_bin = "ffmpeg"  # fallback to PATH
# ---------------------------------------------------------------


def quote_cmd(cmd):
    # Pretty command for display (no shell execution)
    out = []
    for part in cmd:
        if " " in part or "\t" in part:
            out.append(f'"{part}"')
        else:
            out.append(part)
    return " ".join(out)


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        # ----- Increase font size globally (recommended) -----
        # Adjust these to taste
        base_size = 10          # default is often ~9-10 on Windows
        mono_size = 9          # for console / fixed width

        default_font = tkfont.nametofont("TkDefaultFont")
        text_font = tkfont.nametofont("TkTextFont")
        fixed_font = tkfont.nametofont("TkFixedFont")
        menu_font = tkfont.nametofont("TkMenuFont")
        heading_font = tkfont.nametofont("TkHeadingFont")
        caption_font = tkfont.nametofont("TkCaptionFont")
        small_caption_font = tkfont.nametofont("TkSmallCaptionFont")
        icon_font = tkfont.nametofont("TkIconFont")
        tooltip_font = tkfont.nametofont("TkTooltipFont")

        for f in (default_font, text_font, menu_font, heading_font,
                  caption_font, small_caption_font, icon_font, tooltip_font):
            f.configure(size=base_size)

        fixed_font.configure(size=mono_size)
        # -----------------------------------------------------

        self.title("Video Extractor")
        self.geometry("780x500")
        self.resizable(True, True)

        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.start_time = tk.StringVar(value="00:10:00")
        self.end_time = tk.StringVar(value="01:15:30")

        self._build()

    def _build(self):
        pad = {"padx": 10, "pady": 6}

        tk.Label(self, text="원본 영상 경로:").grid(row=0, column=0, sticky="w", **pad)
        tk.Entry(self, textvariable=self.input_path, width=70).grid(row=0, column=1, sticky="w", **pad)
        tk.Button(self, text="파일 탐색", command=self.browse_input).grid(row=0, column=2, **pad)

        tk.Label(self, text="추출 영상 경로:").grid(row=1, column=0, sticky="w", **pad)
        tk.Entry(self, textvariable=self.output_path, width=70).grid(row=1, column=1, sticky="w", **pad)
        tk.Button(self, text="저장 경로", command=self.browse_output).grid(row=1, column=2, **pad)

        tk.Label(self, text="시작 시간 (HH:MM:SS):").grid(row=2, column=0, sticky="w", **pad)
        tk.Entry(self, textvariable=self.start_time, width=20).grid(row=2, column=1, sticky="w", **pad)

        tk.Label(self, text="종료 시간 (HH:MM:SS):").grid(row=3, column=0, sticky="w", **pad)
        tk.Entry(self, textvariable=self.end_time, width=20).grid(row=3, column=1, sticky="w", **pad)

        tk.Button(self, text="추출", height=2, width=18, command=self.run).grid(
            row=4, column=1, sticky="w", padx=10, pady=10
        )

        # Log console
        tk.Label(self, text="Console:").grid(row=5, column=0, sticky="w", **pad)
        self.log = ScrolledText(self, width=120, height=17, state="disabled")
        self.log.grid(row=6, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 10))

        # Small note
        tk.Label(
            self,
            text="\N{COPYRIGHT SIGN} 2026 리턴1. All rights reserved.",
            fg="#444",
        ).grid(row=7, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 10))

    def log_write(self, text: str):
        self.log.configure(state="normal")
        self.log.insert("end", text)
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
            # Stream ffmpeg output into the GUI console
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # ffmpeg logs mainly to stderr
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            assert proc.stdout is not None
            for line in proc.stdout:
                self.log_write(line)

            rc = proc.wait()

            # If it produced a file, we treat as success but may show warning
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


if __name__ == "__main__":
    App().mainloop()


# Build:
# py -m PyInstaller --noconsole --onefile --name "VideoUtil" --add-data "ffmpeg.exe;." gui_video_extract.py
