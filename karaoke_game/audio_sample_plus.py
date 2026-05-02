import sounddevice as sd
import numpy as np
import pyqtgraph as pg

# Set up audio stream constants
CHUNK_SIZE = 1024 
RATE = 44100      
CHANNELS = 1      

# Shared data buffer
audio_buffer = np.zeros(CHUNK_SIZE)

# Print info about audio devices
print("Available input devices:\n")
devices = sd.query_devices()
for i, dev in enumerate(devices):
    if dev['max_input_channels'] > 0:
        print(f"{i}: {dev['name']}")

# Let user select audio device
input_device = int(input("\nSelect input device: "))

# Set up interactive plot
app = pg.mkQApp("Audio Visualizer")
win = pg.GraphicsLayoutWidget(title="Live Audio Analysis")
win.resize(800, 700)

# --- Info Label ---
peak_label = win.addLabel("Peak Frequency: 0 Hz", color='y', size='20pt')
win.nextRow()

# --- Time Domain Plot ---
time_plot = win.addPlot(title="Time Domain (Waveform)")
time_plot.setYRange(-1, 1)
time_curve = time_plot.plot(pen='c')

win.nextRow() 

# --- Frequency Domain Plot ---
spec_plot = win.addPlot(title="Frequency Domain (0 - 1000 Hz)")
spec_plot.setXRange(0, 1000, padding=0) 
spec_plot.setYRange(0, 0.5)           
spec_plot.setLabel('bottom', 'Frequency', units='Hz')
spec_curve = spec_plot.plot(pen='m')

win.show()

# Pre-calculate frequency bins and window
freq_bins = np.fft.rfftfreq(CHUNK_SIZE, 1/RATE)
window = np.hanning(CHUNK_SIZE)

# The callback ONLY updates the data buffer
def audio_callback(indata, frames, time, status):
    global audio_buffer
    if status:
        print(status)
    # Use .copy() to ensure the main thread has its own snapshot of the data
    audio_buffer = indata[:, 0].copy()

# This function runs in the MAIN THREAD (safe for GUI updates)
def update_gui():
    global audio_buffer
    
    # 1. Update Time Domain Plot
    time_curve.setData(audio_buffer)

    # 2. Calculate FFT
    fft_raw = np.abs(np.fft.rfft(audio_buffer * window)) / CHUNK_SIZE
    
    # 3. Find Peak Frequency
    max_idx = np.argmax(fft_raw)
    peak_freq = freq_bins[max_idx]
    
    # 4. Update Frequency Domain Plot and Label
    spec_curve.setData(freq_bins, fft_raw)
    peak_label.setText(f"Peak Frequency: {peak_freq:.1f} Hz")

# Set up a timer to update the GUI every 30 milliseconds (~33 FPS)
timer = pg.QtCore.QTimer()
timer.timeout.connect(update_gui)
timer.start(30)

# Open audio input stream
stream = sd.InputStream(
    device=input_device,
    channels=CHANNELS,
    samplerate=RATE,
    blocksize=CHUNK_SIZE,
    callback=audio_callback,
    latency='low'
)

with stream:
    print("\nStreaming... (Ctrl+C to stop)")
    pg.exec()