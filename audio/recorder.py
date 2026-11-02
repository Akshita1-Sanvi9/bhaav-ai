import os
import sys
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def record_audio(duration: int = 5, output_filename: str = "temp_input.wav") -> str:
    """
    Records microphone audio for a specified duration (in seconds)
    and saves it as a clean WAV file with automatic input device detection.
    """
    sample_rate = getattr(config, "SAMPLE_RATE", 16000)
    channels = getattr(config, "CHANNELS", 1)

    print(f"[*] Initializing microphone recording for {duration}s at {sample_rate}Hz...")
    try:
        # Automatically find a valid input device index from the system
        device_in = None
        devices = sd.query_devices()
        for idx, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                device_in = idx
                break  # Pick the first available working microphone

        if device_in is None:
            raise RuntimeError("No active microphone input device detected on this system.")

        # Capture raw audio frames using the detected device
        audio_data = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=channels,
            dtype='int16',
            device=device_in
        )
        sd.wait()  # Wait until recording finishes
        
        write(output_filename, sample_rate, audio_data)
        print(f"[+] Recording successfully saved to: {output_filename}")
        return output_filename

    except Exception as e:
        print(f"[!] Recording Error: {e}")
        return ""