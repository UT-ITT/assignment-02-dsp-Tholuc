import numpy as np
import pyaudio
import pyglet
import time
import sounddevice as sd

# -------------------
# CONFIG
# -------------------
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 2048

MIN_FREQ = 50
MAX_FREQ = 1000

# Note frequencies/names in order of play. it keeps looping when its done
SONG_NOTES = [261, 261, 392, 392, 440, 440, 392,
               349, 349, 329, 329, 293, 293, 261, 440, 392]
NOTE_NAMES = ["C", "C", "G", "G", "A", "A", "G",
               "F", "F", "E", "E", "D", "D", "C", "A", "G"]


# ---------------------
# HANDLE INPUT DEVICE
# ---------------------

print("Available input devices:\n")
devices = sd.query_devices()

input_devices = []
for i, dev in enumerate(devices):
    if dev['max_input_channels'] > 0:
        print(f"{i}: {dev['name']}")
        input_devices.append(i)

# let user select audio device
input_device = int(input("\nSelect input device: "))

# -----------------------
# GAME
# -----------------------
class KaraokeGame(pyglet.window.Window):
    def __init__(self):
        super().__init__(800, 400, "Python Pitch Hero")

        # -------------------
        # AUDIO
        # -------------------
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            input_device_index=input_device,
            frames_per_buffer=CHUNK
        )

        # -------------------
        # GAME STATE
        # -------------------
        # State playing vs game over
        self.state = "playing"

        # score and target score to get to game over screen
        self.score = 0
        self.target_score = 100

        # current position in song + target pitch
        self.note_index = 0
        self.active_note = SONG_NOTES[0]

        # times to calculate finishing time later
        self.start_time = time.time()
        self.end_time = None

        # -------------------
        # PITCH
        # -------------------
        # raw pitch
        self.current_freq = 0.0

        # smoothed pitch
        self.smoothed_freq = 0.0

        # alpha is how much we take from the new input. 0.2 -> 20% 
        self.alpha = 0.2

        # tolerance is close u need to get to perfect pitch 
        self.pitch_tolerance_semitones = 1.5

        # -------------------
        # UI
        # -------------------
        self.label_freq = pyglet.text.Label('', x=10, y=370)
        self.label_score = pyglet.text.Label('', x=700, y=370)
        self.label_target = pyglet.text.Label(
            '', x=400, y=200, anchor_x='center', font_size=30
        )

        # GAME OVER UI
        self.gameover_title = pyglet.text.Label(
            "GAME OVER",
            x=400,
            y=280,
            anchor_x="center",
            font_size=32
        )

        self.gameover_score = pyglet.text.Label(
            "",
            x=400,
            y=230,
            anchor_x="center",
            font_size=20
        )

        self.gameover_time = pyglet.text.Label(
            "",
            x=400,
            y=200,
            anchor_x="center",
            font_size=20
        )

        self.gameover_hint = pyglet.text.Label(
            "Press R to restart | ESC to quit",
            x=400,
            y=140,
            anchor_x="center",
            font_size=16
        )

        pyglet.clock.schedule_interval(self.update_pitch, 1 / 30.0)
        pyglet.clock.schedule_interval(self.next_note, 2.0)

    # -------------------
    # RESET GAME
    # -------------------
    def reset_game(self):
        self.state = "playing"

        self.score = 0
        self.note_index = 0
        self.active_note = SONG_NOTES[0]

        self.current_freq = 0
        self.smoothed_freq = 0

        self.start_time = time.time()
        self.end_time = None

    # -------------------
    # VOICE DETECTION
    # -------------------
    
    def voice_detected(self, samples):
        rms = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
        # if to quiet -> ignore the input 
        return rms > 800

    # -------------------
    # PITCH DETECTION
    # -------------------
    def get_pitch_autocorr(self, samples):
        
        # get raw samples and remove shiftbias to center sound wave
        samples = samples - np.mean(samples)

        # we soften the edges of the signal as mentioned in the lecture
        samples = samples * np.hanning(len(samples))

        # autocorrelation instead of fft since this worked way better for me 
        # we basically shift our wave with our samples and look how much it differs so dot product between signal and shifted version of itself
        corr = np.correlate(samples, samples, mode='full')

        # we cut off negative shifts as data would be redundant
        corr = corr[len(corr)//2:]

        # only use data within human voice range
        min_lag = int(RATE / MAX_FREQ)
        max_lag = int(RATE / MIN_FREQ)

        # cut off the stuff that got shifted by insignificant amount
        corr[:min_lag] = 0

        # dont trust stuff where there is not a huge peak in similiarity
        if np.max(corr) < 1e7:
            return 0

        # peak is the index with the biggest similarity so its basically one wave cycle
        peak = np.argmax(corr[:max_lag])
        if peak == 0:
            return 0

        # RATE = samples per second
        # peak = samples per cycle   
        # 1 / peak / RATE which would be seconds per cycle but we want freq in Hz
        freq = RATE / peak

        # safety check to filter non-human-voice frequencies by noise etc.
        if freq < MIN_FREQ or freq > MAX_FREQ:
            return 0

        return freq

    # -------------------
    # AUDIO LOOP
    # -------------------
    def update_pitch(self, dt):
        if self.state != "playing":
            return

        try:
            data = self.stream.read(CHUNK, exception_on_overflow=False)
            samples = np.frombuffer(data, dtype=np.int16)

            # ignore if to quiet
            if not self.voice_detected(samples):
                return

            raw_freq = self.get_pitch_autocorr(samples)

            # smooth freq
            self.smoothed_freq = (
                self.alpha * raw_freq +
                (1 - self.alpha) * self.smoothed_freq
            )

            self.current_freq = self.smoothed_freq

            self.check_score()

            if self.score >= self.target_score:
                self.end_game()

        except Exception as e:
            print("Audio error:", e)

    # -------------------
    # MUSICAL MAPPING
    # -------------------
    def freq_to_midi(self, f):
        return 69 + 12 * np.log2(f / 440.0)

    # -------------------
    # SCORING
    # -------------------
    def check_score(self):
        if self.current_freq < MIN_FREQ:
            return

        target = self.freq_to_midi(self.active_note)
        input_pitch = self.freq_to_midi(self.current_freq)

        diff = abs(target - input_pitch)

        if diff < self.pitch_tolerance_semitones:
            self.score += 1
            self.label_target.color = (0, 255, 0, 255)
        elif diff < self.pitch_tolerance_semitones * 2:
            self.label_target.color = (255, 255, 0, 255)
        else:
            self.label_target.color = (255, 255, 255, 255)

    # -------------------
    # SONG FLOW
    # -------------------
    def next_note(self, dt):
        if self.state != "playing":
            return

        self.note_index = (self.note_index + 1) % len(SONG_NOTES)
        self.active_note = SONG_NOTES[self.note_index]

    # -------------------
    # GAME OVER
    # -------------------
    def end_game(self):
        self.state = "gameover"
        self.end_time = time.time()

    # -------------------
    # VISUAL MAPPING
    # -------------------
    def freq_to_x(self, freq, min_freq=MIN_FREQ, max_freq=MAX_FREQ, width=600):
        freq = max(min_freq, min(max_freq, freq))

        min_midi = self.freq_to_midi(min_freq)
        max_midi = self.freq_to_midi(max_freq)
        f_midi = self.freq_to_midi(freq)

        return 100 + (f_midi - min_midi) / (max_midi - min_midi) * width

    # -------------------
    # DRAW
    # -------------------
    def on_draw(self):
        self.clear()

        # -------------------
        # GAME OVER SCREEN
        # -------------------
        if self.state == "gameover":
            total_time = self.end_time - self.start_time

            self.gameover_score.text = f"Score: {self.score} / {self.target_score}"
            self.gameover_time.text = f"Time: {total_time:.2f} seconds"

            self.gameover_title.draw()
            self.gameover_score.draw()
            self.gameover_time.draw()
            self.gameover_hint.draw()
            return

        # -------------------
        # HUD
        # -------------------
        self.label_freq.text = f"Input: {int(self.current_freq)} Hz"
        self.label_score.text = f"Score: {self.score}"
        self.label_target.text = f"SING: {NOTE_NAMES[self.note_index]} ({self.active_note} Hz)"
        self.label_freq.draw()
        self.label_score.draw()
        self.label_target.draw()

        # -------------------
        # PITCH LANE
        # -------------------
        pyglet.shapes.Rectangle(100, 100, 600, 20, color=(40, 40, 40)).draw()

        min_midi = self.freq_to_midi(MIN_FREQ)
        max_midi = self.freq_to_midi(MAX_FREQ)
        target_midi = self.freq_to_midi(self.active_note)

        def midi_to_x(midi):
            return 100 + (midi - min_midi) / (max_midi - min_midi) * 600

        # GREEN ZONE
        left = target_midi - self.pitch_tolerance_semitones
        right = target_midi + self.pitch_tolerance_semitones

        left_x = midi_to_x(left)
        right_x = midi_to_x(right)

        pyglet.shapes.Rectangle(
            int(left_x),
            95,
            int(right_x - left_x),
            30,
            color=(80, 255, 80)
        ).draw()

        # TARGET LINE
        target_x = midi_to_x(target_midi)

        pyglet.shapes.Rectangle(
            int(target_x),
            90,
            3,
            40,
            color=(255, 80, 80)
        ).draw()

        # USER PITCH
        user_x = self.freq_to_x(self.current_freq)
        bar_width = max(0, user_x - 100)

        pyglet.shapes.Rectangle(
            100,
            100,
            bar_width,
            20,
            color=(100, 100, 255)
        ).draw()

    # -------------------
    # INPUT HANDLING
    # -------------------
    def on_key_press(self, symbol, modifiers):
        if symbol == pyglet.window.key.ESCAPE:
            self.on_close()

        if self.state == "gameover" and symbol == pyglet.window.key.R:
            self.reset_game()

    # -------------------
    # CLEAN EXIT
    # -------------------
    def on_close(self):
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()
        super().on_close()


if __name__ == "__main__":
    game = KaraokeGame()
    pyglet.app.run()