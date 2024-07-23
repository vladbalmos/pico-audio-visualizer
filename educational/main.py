import sys
import math
import threading
import queue
import time
import pyaudio
import wave
from src import screen
from src import fft
from src import animation_utils
from collections import deque

MAX_AMPLITUDE = 100
ANIMATION_FRAMERATE = 60
FFT_SAMPLING_RATE = 60

fft_queue = queue.Queue()
stop_event = threading.Event()
pixels_queue = deque()

last_fft = 0
threshold = math.floor(1000 / FFT_SAMPLING_RATE) - 1


# Define new frequency bands
def next_divisible_by_32(n):
    remainder = n % 32
    if remainder == 0:
        return int(n + 32)
    else:
        return int(n + (32 - remainder))


def audio_worker():
    # Path to the WAV file
    try:
        wav_file_path = sys.argv[1]
    except:
        wav_file_path = 'sample.wav'
    # wav_file_path = 'snuff.wav'
    print(sys.argv)

    # Open the WAV file
    wf = wave.open(wav_file_path, 'rb')
    framerate = wf.getframerate()
    sample_width = wf.getsampwidth()
    channels = wf.getnchannels()

    # Instantiate PyAudio
    p = pyaudio.PyAudio()

    # Open a stream
    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True)

    # Read data in chunks
    frames_for_fft = (1 / FFT_SAMPLING_RATE) / (1 / framerate)
    frames_for_fft = next_divisible_by_32(frames_for_fft)
    chunk_size = 4 * frames_for_fft

    print('FFT rate (fps)', FFT_SAMPLING_RATE)
    print('FFT frames', frames_for_fft, 'Audio frames', chunk_size)

    audio_frames = wf.readframes(chunk_size)
    fft.init(fft_queue)

    while audio_frames and not stop_event.is_set():
        stream.write(audio_frames)
        fft.analyze(audio_frames, frames_for_fft, framerate, sample_width, channels)
        audio_frames = wf.readframes(chunk_size)

    # Stop and close the stream
    stream.stop_stream()
    stream.close()

    # Close PyAudio
    p.terminate()
    


def rasterize(frames_queue):
    global last_fft, last_values

    now = time.time()
    diff = math.floor((now - last_fft) * 1000)
    values = None
    
    if diff >= threshold:
        last_fft = now
        try:
            values = fft_queue.get(block=True, timeout=0.5)
        except:
            print("No more audio. Exiting!")
            sys.exit(0)

         
        pixels = []
        for i, max_amp in enumerate(values):
            level = animation_utils.get_level(max_amp)
            pixels.append(animation_utils.level_to_pixels(level))
            
        frames_queue.appendleft(pixels)
    
    
print('Animation framerate (fps)', ANIMATION_FRAMERATE)
screen.init(ANIMATION_FRAMERATE)

thread = threading.Thread(target=audio_worker)
thread.start()

try:
    screen.mainloop(rasterize)
finally:
    stop_event.set()
