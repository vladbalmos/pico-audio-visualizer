import sys
import pprint
import math
import threading
import queue
import time
import numpy as np
import pyaudio
import wave
import screen
from collections import deque

MAX_AMPLITUDE = 100
ANIMATION_FRAMERATE = 60
FFT_SAMPLING_RATE = 60

fft_queue = queue.Queue()
stop_event = threading.Event()
pixels_queue = deque()

# Define new frequency bands
frequency_bands = [
    (1, 32),
    (32, 62),
    (62, 125),
    (125, 250),
    (250, 500),
    (500, 1000),
    (1000, 2000),
    (2000, 4000),
    (4000, 8000),
    (8000, 16000)
]

def next_divisible_by_32(n):
    remainder = n % 32
    if remainder == 0:
        return int(n + 32)
    else:
        return int(n + (32 - remainder))

    
last_frames = []

def analyze_fft(audio_frames, slice_size, audio_framerate, sample_width, channels):
    if sample_width == 2:
        _dtype = np.int16
    else:
        _dtype = np.int8

    np_data = np.frombuffer(audio_frames, dtype=_dtype)
    
    # If stereo, convert to mono
    if channels == 2:
        np_data = np_data.reshape(-1, 2)
        np_data = np_data.mean(axis=1)

    start = 0
    end = slice_size

    while True:
        frames = np_data[start:end]
        
        # frames = np_data[0:end]
        # if len(frames) == 0 or end >= len(np_data):
        if len(frames) == 0:
            break

        fft_result = np.fft.fft(np_data)
        fft_freqs = np.fft.fftfreq(len(fft_result), 1.0 / audio_framerate)

        # Keep only the positive half of the spectrum
        positive_freqs = fft_freqs[:len(fft_freqs)//2]
        positive_amplitudes = np.abs(fft_result)[:len(fft_result)//2] / len(np_data)

        max_amplitude = np.max(positive_amplitudes)
        scale_factor = MAX_AMPLITUDE / max_amplitude if max_amplitude != 0 else 0
        normalized_amplitudes = positive_amplitudes * scale_factor

        # Initialize bin maxima
        bin_maxima = np.zeros(len(frequency_bands))

        # Assign each FFT result to a bin and find the max amplitude
        for i, (low, high) in enumerate(frequency_bands):
            bin_indices = np.where((positive_freqs >= low) & (positive_freqs < high))[0]
            if bin_indices.size > 0:
                # bin_maxima[i] = np.max(positive_amplitudes[bin_indices])
                bin_maxima[i] = int(math.ceil(np.max(normalized_amplitudes[bin_indices])))

        fft_queue.put(bin_maxima)

        
        # print(start, end, len(np_data))
        start = end
        end += slice_size

def audio_worker():
    # Path to the WAV file
    wav_file_path = 'sample3.wav'
    # wav_file_path = 'snuff.wav'

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
    while audio_frames and not stop_event.is_set():
        stream.write(audio_frames)
        analyze_fft(audio_frames, frames_for_fft, framerate, sample_width, channels)
        audio_frames = wf.readframes(chunk_size)

    # Stop and close the stream
    stream.stop_stream()
    stream.close()

    # Close PyAudio
    p.terminate()
    
print('Animation framerate (fps)', ANIMATION_FRAMERATE)
screen.init(ANIMATION_FRAMERATE)

thread = threading.Thread(target=audio_worker)
thread.start()

def get_level(max_amp):
    if max_amp < 0:
        return -1

    if max_amp < 10:
        return 0
    
    if max_amp >= 10 and max_amp < 20:
        return 1
    
    if max_amp >= 20 and max_amp < 30:
        return 2
    
    if max_amp >= 30 and max_amp < 40:
        return 3
    
    if max_amp >= 40 and max_amp < 50:
        return 4
    
    if max_amp >= 50 and max_amp < 60:
        return 5
    
    if max_amp >= 60 and max_amp < 80:
        return 6
    
    return 7


def new_frame(pixel_value = 0):
    frame = [pixel_value] * screen.LED_ROWS
    return frame
    
def set_pixels(start, end, state, dst = None):
    if dst == None:
        dst = []
    for i in range(start, end + 1):
        dst[i] = state
    
    return dst

def level_to_pixels(level):
    frame = new_frame()
    if level < 0:
        return frame

    set_pixels(0, level, 1, frame)
    return frame
        
last_fft = 0
threshold = math.floor(1000 / FFT_SAMPLING_RATE) - 1

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
            level = get_level(max_amp)
            pixels.append(level_to_pixels(level))
            
        frames_queue.appendleft(pixels)
    
    
try:
    screen.mainloop(rasterize)
finally:
    stop_event.set()