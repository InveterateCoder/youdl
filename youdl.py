import os
import shlex
import subprocess
import threading
import re
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext
from tkinter import ttk
from tkinter import filedialog

READONLY = "readonly"

YT_DLP_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "yt-dlp.exe")
)
FFMPEG_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe")
)


class YouDl(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.root = parent

        self.url_entry_val = tk.StringVar(self)
        self.url_entry_val.trace_add("write", self.url_val_changed)
        self.url_frame = tk.Frame(self)
        self.url_label = tk.Label(self.url_frame, text="Cсылка:")
        self.url_entry = tk.Entry(self.url_frame, textvariable=self.url_entry_val)

        self.url_label.pack(side="left")
        self.url_entry.pack(side="right", fill="x", expand=True, padx=(30, 0))
        self.url_frame.pack(side="top", fill="x", pady=30, padx=30)

        self.download_frame = tk.Frame(self)
        self.download_label = tk.Label(self.download_frame, text="Качество видео:")
        self.download_a_label = tk.Label(self.download_frame, text="Качество аудио:")
        self.q_video_entry = ttk.Combobox(
            self.download_frame,
            width=15,
            state=tk.DISABLED,
        )
        self.q_audio_entry = ttk.Combobox(
            self.download_frame,
            width=15,
            state=tk.DISABLED,
        )
        self.download_btn = tk.Button(
            self.download_frame,
            text="Скачать",
            width=15,
            state=tk.DISABLED,
            command=self.download_video,
        )

        self.download_label.pack(side="left", padx=(0, 10))
        self.q_video_entry.pack(side="left")
        self.download_a_label.pack(side="left", padx=(30, 10))
        self.q_audio_entry.pack(side="left")
        self.download_btn.pack(side="right")
        self.download_frame.pack(side="bottom", fill="x", pady=30, padx=30)

        self.console_widget = scrolledtext.ScrolledText(self)
        self.console_widget.config(wrap=tk.WORD, state=tk.DISABLED, bg=self.cget("bg"))
        self.console_widget.pack(
            side="bottom", padx=30, pady=30, expand=True, fill="both"
        )
        self.url_is_parsed = False
        self.video_list = []
        self.audio_list = []

    def is_url_valid(self, url):
        return (
            re.match(r"^https\:\/\/youtu\.be\/.+$", url) is not None
            or re.match(r"^https\:\/\/www\.youtube\.com\/watch\?v=.+$", url) is not None
        )

    def dep_available(self):
        yt_dlp_exist = Path(YT_DLP_PATH).is_file()
        if not yt_dlp_exist:
            self.print_to_console(f"{YT_DLP_PATH} не найден{os.linesep}")
        ffmpeg_exist = Path(FFMPEG_PATH).is_file()
        if not ffmpeg_exist:
            self.print_to_console(f"{FFMPEG_PATH} не найден{os.linesep}")
        return yt_dlp_exist and ffmpeg_exist

    def print_to_console(self, text):
        self.console_widget.config(state=tk.NORMAL)
        self.console_widget.insert(tk.END, text)
        self.console_widget.see(tk.END)
        self.console_widget.config(state=tk.DISABLED)

    def get_quality_code(self, line):
        match = re.match(r"^(\d+\S*)", line)
        if match:
            return match.group(1)
        return None

    def run_and_capture_output(self, command, collect_q_code):
        self.print_to_console(
            "Command: " + " ".join(shlex.quote(arg) for arg in command) + os.linesep
        )
        try:
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            v_list, a_list = [], []

            for line in process.stdout:
                self.print_to_console(line)
                if collect_q_code:
                    code = self.get_quality_code(line)
                    if code:
                        if "audio only" in line:
                            a_list.append(code)
                        elif "video only" in line:
                            v_list.append(code)
                        else:
                            a_list.append(code)
                            v_list.append(code)

            process.stdout.close()
            process.wait()

            if len(v_list) > 0:
                self.video_list = v_list
            if len(a_list) > 0:
                self.audio_list = a_list

            if process.returncode == 0:
                self.print_to_console("Done!" + os.linesep)
                self.url_parsed()
            else:
                error_output = process.stderr.read()
                self.print_to_console(f"\nError:\n{error_output}")
        except Exception as e:
            self.print_to_console(f"\nException occurred:\n{str(e)}")
        finally:
            self.enable_url()

    def url_val_changed(self, *args):
        url = self.url_entry_val.get().strip()
        if not self.is_url_valid(url) or not self.dep_available():
            self.url_not_parsed()
            return
        self.disable_url()
        command = [YT_DLP_PATH, "-F", "--no-playlist", url]
        threading.Thread(
            target=self.run_and_capture_output, args=(command, True), daemon=True
        ).start()

    def disable_url(self):
        self.url_entry.config(state=READONLY)

    def enable_url(self):
        self.url_entry.config(state=tk.NORMAL)

    def disable_downloader(self):
        self.download_btn.config(state=tk.DISABLED)
        self.q_video_entry.config(state=tk.DISABLED)
        self.q_audio_entry.config(state=tk.DISABLED)

    def enable_downloader(self):
        self.download_btn.config(state=tk.NORMAL)
        self.q_video_entry.config(state=READONLY)
        self.q_audio_entry.config(state=READONLY)

    def reset_downloader(self):
        self.video_list = []
        self.audio_list = []
        self.q_video_entry.config(values=[])
        self.q_audio_entry.config(values=[])
        self.q_video_entry.set("")
        self.q_audio_entry.set("")

    def url_parsed(self):
        if not self.url_is_parsed:
            bestvideo = "bestvideo"
            bestaudio = "bestaudio"
            self.q_video_entry.config(values=[bestvideo, *self.video_list])
            self.q_audio_entry.config(values=[bestaudio, *self.audio_list])
            self.q_video_entry.set(bestvideo)
            self.q_audio_entry.set(bestaudio)
            self.enable_downloader()
            self.url_is_parsed = True

    def url_not_parsed(self):
        if self.url_is_parsed:
            self.reset_downloader()
            self.disable_downloader()
            self.url_is_parsed = False

    def download_video(self):
        self.disable_url()
        self.disable_downloader()
        url = self.url_entry_val.get().strip()
        q_vid = self.q_video_entry.get()
        q_aud = self.q_audio_entry.get()
        if not (q_vid and q_aud) or not self.dep_available():
            return
        dest = filedialog.askdirectory()
        command = [
            YT_DLP_PATH,
            "--ffmpeg-location",
            FFMPEG_PATH,
            "-f",
            f"{q_vid}+{q_aud}/best",
            "-o",
            f'{os.path.normpath(os.path.join(dest, "%(title)s.%(ext)s"))}',
            "--merge-output-format",
            "mp4",
            "--postprocessor-args",
            "ffmpeg:-c:v libx264 -c:a aac -b:a 192k",
            "--no-playlist",
            url,
        ]
        threading.Thread(
            target=self.run_and_capture_output, args=(command, False), daemon=True
        ).start()


if __name__ == "__main__":
    w, h = 800, 500
    root = tk.Tk()
    root.geometry(f"{w}x{h}")
    root.minsize(w, h)
    root.resizable(True, True)
    root.title("Youdl")
    YouDl(root).pack(fill="both", expand=True)
    root.mainloop()
