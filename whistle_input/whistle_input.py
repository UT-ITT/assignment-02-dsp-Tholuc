import pyaudio
import numpy as np
from pynput.keyboard import Key, Controller
import time
import sounddevice as sd
from collections import deque

# --- Configuration & Tuning Parameters ---
# Audio settings
RATE = 44100
CHUNK = 1024           
FORMAT = pyaudio.paInt16
CHANNELS = 1

# Whistle detection settings
MIN_FREQ = 700         # Human whistle typically starts around here
MAX_FREQ = 3000        # Human whistle rarely exceeds this
MAG_THRESHOLD = 7000   # Volume threshold. Adjust this based on mic sensitivity
HISTORY_LEN = 15       # How many chunks to remember (~340ms of audio history)
CHIRP_DELTA = 300      # Minimum Hz change required to trigger a chirp 
COOLDOWN_TIME = 0.8    # Seconds to wait after a keypress to prevent spam

# Initialize Keyboard Controller
keyboard = Controller()


# print info about audio devices
print("Available input devices:\n")
devices = sd.query_devices()

input_devices = []
for i, dev in enumerate(devices):
    if dev['max_input_channels'] > 0:
        print(f"{i}: {dev['name']}")
        input_devices.append(i)

# let user select audio device
input_device = int(input("\nSelect input device: "))



def start_listening():
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    input_device_index = input_device,
                    frames_per_buffer=CHUNK)

    print("Listening for whistles... (Press Ctrl+C to stop)")
    print("Whistle UP (ooouuuiii) -> Up Arrow | Whistle DOWN (iiiuuuooo) -> Down Arrow")

    freq_history = deque(maxlen=HISTORY_LEN)
    last_trigger_time = 0

    try:
        while True:
            # 1. Read audio data
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16)

            # 2. Apply a Hanning window to reduce spectral leakage
            window = np.hanning(len(audio_data))
            
            # 3. Perform FFT to get frequency spectrum
            fft_result = np.fft.rfft(audio_data * window)
            magnitudes = np.abs(fft_result)
            frequencies = np.fft.rfftfreq(len(audio_data), 1.0/RATE)

            # 4. Bandpass filter: Only look at human whistle frequencies (Noise Robustness)
            valid_indices = np.where((frequencies >= MIN_FREQ) & (frequencies <= MAX_FREQ))[0]
            
            if len(valid_indices) == 0:
                continue

            # 5. Find the peak frequency and its magnitude
            peak_index = valid_indices[np.argmax(magnitudes[valid_indices])]
            peak_freq = frequencies[peak_index]
            peak_mag = magnitudes[peak_index]

            # 6. Check if it's loud enough to be an intentional whistle
            if peak_mag > MAG_THRESHOLD:
                freq_history.append(peak_freq)
            else:
                # If silent or too quiet, clear history to avoid false connections
                freq_history.clear()

            # 7. Analyze history for chirps
            if len(freq_history) == HISTORY_LEN and (time.time() - last_trigger_time) > COOLDOWN_TIME:
                
                # Calculate the frequency change over the tracked window
                start_freq = np.mean(list(freq_history)[:3])  # Average of first 3 frames
                end_freq = np.mean(list(freq_history)[-3:])   # Average of last 3 frames
                
                delta_freq = end_freq - start_freq

                if delta_freq > CHIRP_DELTA:
                    print(f"Upwards chirp detected!")
                    keyboard.press(Key.up)
                    keyboard.release(Key.up)
                    last_trigger_time = time.time()
                    freq_history.clear()

                elif delta_freq < -CHIRP_DELTA:
                    print(f"Downwards chirp detected!")
                    keyboard.press(Key.down)
                    keyboard.release(Key.down)
                    last_trigger_time = time.time()
                    freq_history.clear()

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

if __name__ == "__main__":
    start_listening()