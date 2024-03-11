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
    (1, 32, [], [-60]),
    (32, 62, [], [-60]),
    (62, 125, [], [-60]),
    (125, 250, [], [-60]),
    (250, 500, [], [-60]),
    (500, 1000, [], [-60]),
    (1000, 2000, [], [-60]),
    (2000, 4000, [], [-60]),
    (4000, 8000, [], [-60]),
    (8000, 16000, [], [-60])
]
def next_divisible_by_32(n):
    remainder = n % 32
    if remainder == 0:
        return int(n + 32)
    else:
        return int(n + (32 - remainder))

    
last_frames = []
alpha = 0.4

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
    epsilon = 1e-10

    while True:
        frames = np_data[start:end]
        # TODO: analyze window of current - 100ms in time
        
        # frames = np_data[0:end]
        # if len(frames) == 0 or end >= len(np_data):
        if len(frames) == 0:
            break

        fft_result = np.fft.fft(np_data)
        fft_freqs = np.fft.fftfreq(len(fft_result), 1.0 / audio_framerate)
    
        bin_maxima = np.zeros(len(frequency_bands))

        for i, (low, high, max_amplitudes, ema) in enumerate(frequency_bands):
            bin_indices = np.where((fft_freqs >= low) & (fft_freqs < high))[0]
            
            if bin_indices.size == 0:
                bin_maxima[i] = -np.inf
                continue

            # print(low, high, bin_indices)
            amplitudes = np.abs(fft_result[bin_indices])

            max_band_amplitude = max(np.max(amplitudes), epsilon)
            max_amplitudes.append(max_band_amplitude)
            if len(max_amplitudes) > 500:
                max_amplitudes.pop(0)
                
            max_amplitude = np.max(max_amplitudes)

            loudness_db = 20 * np.log10((amplitudes + epsilon) / (max_amplitude + epsilon))
            max_loudness = np.max(loudness_db)
            ema1 = ema[0]
            ema[0] = (max_loudness * alpha) + (ema[0] * (1 - alpha))
            
            # diff = abs(ema[0] - ema1)
            # if diff < 3:
            #     ema[0] = math.ceil(ema[0] + ema1) / 2
            bin_maxima[i] = ema[0]
            
        # print(bin_maxima)
        fft_queue.put(bin_maxima)
        start = end
        end += slice_size

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
    if max_amp >= -1.5:
        return 7
    
    if max_amp >= -3:
        return 6
    
    if max_amp >= -6:
        return 5
    
    if max_amp >= -9:
        return 4
    
    if max_amp >= -12:
        return 3
    
    if max_amp >= -15:
        return 2
    
    if max_amp >= -18:
        return 1
    
    if max_amp >= -30:
        return 0
    
    return -1

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
