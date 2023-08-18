#!/usr/bin/env python3

import os
import argparse
import platform
import subprocess
from datetime import timedelta

try:
    import whisper
    import yt_dlp
    from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip
    from moviepy.video.tools.subtitles import SubtitlesClip
except ImportError:
    print("trying to install dependencies")

    def install_libraries():
        required_libraries = ['whisper', 'yt_dlp', 'moviepy']  # Add your libraries here
        current_os = platform.system()
        
        if current_os == 'Windows':
            package_manager = 'pip'
        elif current_os == 'Darwin':
            package_manager = 'pip3'
        elif current_os == 'Linux':
            package_manager = 'pip3'
        else:
            print("unsupported operating system, skipping install")
            return
        
        for library in required_libraries:
            try:
                subprocess.check_call([package_manager, 'install', library])
                print(f"{library} installed successfully, run the script again")
            except subprocess.CalledProcessError:
                print(f"failed to install {library}")
                exit()

    install_libraries()

YT_ATTACH = "youtube-a"
YT_GENERATE = "youtube-g"
VALID_MODES = ("attach", "generate", YT_ATTACH, YT_GENERATE)
YT_MODES = (YT_ATTACH, YT_GENERATE)
TEMP_FILE = "temp.mp3"
OUTPUT_SRT = "output.srt"
OUTPUT_VID = "output.mp4"
YT_VID = "yt.mp4"


class VideoManager:
    def __init__(self, path: str, youtube: bool) -> None:
        self.path = path
        self.youtube = youtube
        if not self.youtube:
            self.video = VideoFileClip(path)

        self.extract_audio()

    def download(self) -> None:
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": "yt",
        }
        with yt_dlp.YoutubeDL(ydl_opts) as dl:
            dl.download([self.path])

        self.video = VideoFileClip(YT_VID)

    def extract_audio(self) -> None:
        if self.youtube:
            self.download()

        if self.video.audio is not None:
            self.video.audio.write_audiofile("temp.mp3", codec="mp3")
        else:
            print("video has no audio, quitting")


class Utility:
    def __init__(self, path: str, youtube: bool) -> None:
        self.path = path
        self.youtube = youtube

    def file_exists(self) -> bool:
        if self.youtube:
            return True
        return len(self.path) > 0 and os.path.exists(path=self.path)


class SubtitleGenerator:
    def __init__(self, videomanager: VideoManager) -> None:
        self.videomanager = videomanager

    def generate(self) -> None:
        # Credit goes to
        # https://github.com/openai/whisper/discussions/98#discussioncomment-3725983
        # github.com/lectair

        model = whisper.load_model("base")
        transcribe = model.transcribe(audio=TEMP_FILE, fp16=False)
        segments = transcribe["segments"]

        for seg in segments:
            start = str(0) + str(timedelta(seconds=int(seg["start"]))) + ",000"
            end = str(0) + str(timedelta(seconds=int(seg["end"]))) + ",000"
            text = seg["text"]
            segment_id = seg["id"] + 1
            segment = f"{segment_id}\n{start} --> {end}\n{text[1:] if text[0] == ' ' else text}\n\n"
            with open(OUTPUT_SRT, "a", encoding="utf-8") as f:
                f.write(segment)

        print("subtitles generated")

    def attach(self) -> None:
        self.generate()
        if os.path.exists(OUTPUT_SRT):
            subtitles = SubtitlesClip(
                OUTPUT_SRT,
                lambda txt: TextClip(
                    txt,
                    font="Arial",
                    fontsize=24,
                    color="white",
                    bg_color="black",
                ),
            )

            video_with_subtitles = CompositeVideoClip(
                [
                    self.videomanager.video,
                    subtitles.set_position(("center", 0.95), relative=True),
                ]
            )

            video_with_subtitles.write_videofile(OUTPUT_VID, codec="libx264")
            print(f"saved to {OUTPUT_VID}")

def check_ffmpeg() -> bool:
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        return result.returncode == 0 and 'ffmpeg' in result.stdout
    except FileNotFoundError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="auto caption generator v1.0")
    parser.add_argument(
        "mode", metavar="mode", type=str, help="operation mode (attach|generate)"
    )
    parser.add_argument("path", metavar="path", type=str, help="filepath of the video")
    args = parser.parse_args()
    mode = args.mode
    path = args.path

    if not check_ffmpeg():
        print("ffmpeg must be installed to run this script, quitting")
        exit()

    if len(mode) > 0 and len(path) > 0:
        yt_mode = True if mode in YT_MODES else False
        utility = Utility(path, yt_mode)

        if mode in VALID_MODES and utility.file_exists():
            videomanager = VideoManager(utility.path, yt_mode)
            subtitle_generator = SubtitleGenerator(videomanager)

            if mode == VALID_MODES[0] or mode == VALID_MODES[2]:
                subtitle_generator.attach()
            elif mode == VALID_MODES[1] or mode == VALID_MODES[3]:
                subtitle_generator.generate()
        else:
            print("invalid mode or file path, quitting")


if __name__ == "__main__":
    main()
