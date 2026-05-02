Dear Tutors,

karaoke game took alot from me. worked on it 10+ hours and it was really rough with my setup.
I have a shitty microphone which made debugging a real pain and i did not have the time nor money to buy a better microphone fast enough. I was kinda in a bad cycle of doing it over and over again.

I use audio_sample_plus to look at my microphone and ftts a bit more and came to the conclusion that i cant fix that.. 
When i was (trying) to sing notes in the fft there were like 3 peaks of different frequenzies that were far apart and very similar in likelyness. like 200 400 and 600 Hz also being close to each other which would result in alot of jitter.

So i used a different method to get a pitch. I hope that is okayy, we used ffts but i couldnt make them work...
I used autocorrelation (https://de.wikipedia.org/wiki/Autokorrelation)
The main idea is to shift ur sample by timesteps and then see how big the similiarity is with the normal data. The peak of your similarity will be when u shift by the time of a cycle. Pretty straight forward :)

Then i didnt do much to it, i only used smoothing so the history of the frequency is taken in consideration.

For the game i wanted to keep it simple but functional. I also gave a bigger tolerance to hitting the note which made it far more enjoyable and also some visual indication where u need to go.
Falling Blocks like from guitar hero or something like singstar isnt far off now but my micro was still to shitty to really payoff from that gameplay. 

So i polished that stuff gave it a score and also a main gameloop. 
You sing until u hit a score. I gave it 100 but can make it larger (target_score) but for testing this was not to short and not to long.

Once u hit ur target score u see how fast u got there. You can then either replay and try to beat it or escape. My Highscore was like 8 Seconds (Humming works better with a deeper voice imo).

Also the notes are always the same loop so you can better compare your score :)
Idk how strict u are with the latency but i had no problems playing it like this. If u want faster put down chunk to 1024 again but it went perfectly fine for me like this.

After all the stress im quite pleased with the simple thing, hope u like it too.