import os
import sys
import sounddevice as sd
from scipy.io.wavfile import read

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def play_audio(file_path: str):
    """
    Plays a WAV audio file through the default speaker with error protection.
    """
    if not os.path.exists(file_path):
        print(f"[!] Audio file not found: {file_path}")
        return

    try:
        sample_rate, data = read(file_path)
        print(f"[*] Playing audio output: {file_path}")
        sd.play(data, sample_rate)
        sd.wait()
        print("[+] Playback completed.")

    except Exception as e:
        print(f"[!] Audio Playback Error: {e}")