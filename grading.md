# Tholuc (13.5/15P)

## 1 - Karaoke Game (7/7P)
* frequency detection works correctly and robustly
    * yep (3P)
* the game is playable, does not crash, and is (kind of) fun to play
    * yep (2P)
* the game tracks some kind of score for correctly sung notes
    * yep (1P)
* low latency between input and detection
    * yep (1P)
* buuuuuut: please don't use pyaudio, since it doesn't work with newer python versions


## 2 - Whistle Input (6/7P)
* upwards and downwards whistling is detected correctly and robustly
    * yep (3P)
*  detection is robust against background noise
    * speaking triggers input (1P)
* low latency between input and detection
    * yep (1P)
* triggered key events work
    * yep (1P)


## Code-Quality and .venv used (0.5/1P)
* requirements.txt way overloaded with unneeded packages
* no Readme (this will be point deduction in following assignments)