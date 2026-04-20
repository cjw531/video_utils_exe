from utils import *
from tabs.audio_extract import AudioExtractTab
from tabs.video_extract import VideoExtractTab
from tabs.video_merge import VideoMergeTab
from tabs.youtube_download import YoutubeDownloaderTab


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- CustomTkinter Theme Setup ---
        ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
        ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

        self.title("Audio & Video Utility")
        self.geometry("800x600")

        # --- CTkTabview replacing ttk.Notebook ---
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        # Add tabs to tabview
        self.tab_audio = self.tabview.add("MP3 추출")
        self.tab_extract = self.tabview.add("영상 추출")
        self.tab_merge = self.tabview.add("영상 병합")
        self.tab_yt = self.tabview.add("YouTube 다운로드")

        # Instantiate tab classes by passing the created tab frames
        self.audio_tab = AudioExtractTab(self.tab_audio)
        self.audio_tab.pack(fill="both", expand=True)

        self.extract_tab = VideoExtractTab(self.tab_extract)
        self.extract_tab.pack(fill="both", expand=True)

        self.merge_tab = VideoMergeTab(self.tab_merge)
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
# py -m PyInstaller --noconsole --onefile --name "AudioVideoUtils_v4.1.0" --add-data "ffmpeg.exe;." --add-data "yt-dlp.exe;." main.py


# TODO:
# aria2c download YouTube faster, but make sure to make sub-directory and when user prompted to stop in the middle of the process, remove this folder

# TODO 2:
# 4K enhancement feature
