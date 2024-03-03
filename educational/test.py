import sys
import math
import threading
import queue
import time
import numpy as np
import pyaudio
import wave
import screen

MAX_AMPLITUDE = 100
ANIMATION_FRAMERATE = 60
FFT_SAMPLING_RATE = int(math.floor(ANIMATION_FRAMERATE / 2))

fft_queue = queue.Queue()
stop_event = threading.Event()

# Define new frequency bands
frequency_bands = [
    (20, 60),     # Sub-Bass
    (60, 250),    # Bass
    (250, 500),   # Low Midrange
    (500, 1000),  # Midrange
    (1000, 2000), # Upper Midrange
    (2000, 4000), # Presence
    (4000, 6000), # Brilliance
    (6000, 10000),# Upper Brilliance
    (10000, 16000),# Highs
    (16000, 20000) # Ultra Highs
]

frequency_bands = [
    (20, 60),     # Sub-Bass
    (60, 100),    # Bass
    (100, 200),   # Low Midrange
    (200, 250),  # Midrange
    (250, 500), # Upper Midrange
    (500, 1000), # Presence
    (1000, 1500), # Brilliance
    (1500, 2000),# Upper Brilliance
    (3000, 4000),# Highs
    (4000, 20000) # Ultra Highs
]


def next_divisible_by_32(n):
    remainder = n % 32
    if remainder == 0:
        return int(n + 32)
    else:
        return int(n + (32 - remainder))

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

        
        start = end
        end += slice_size

def audio_worker():
    # Path to the WAV file
    wav_file_path = 'sample.wav'
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

last_called = 0
threshold = 1 / FFT_SAMPLING_RATE
def rasterize(queue):
    global last_called

    now = time.time()
    diff = now - last_called
    
    if diff < threshold:
        return

    last_called = now
    try:
        values = fft_queue.get(block=True, timeout=0.5)
    except:
        print("No more audio. Exiting!")
        sys.exit(0)

    # strs = []
    # for i, max_amp in enumerate(values):
    #     strs.append(f"({frequency_bands[i][0]:.2f}-{frequency_bands[i][1]:.2f} Hz) = {max_amp}")
    # print('; '.join(strs))
    
    pixels = []
    for max_amp in values:
        pixel_rows = []
        for j in range(screen.LED_ROWS):
            level = get_level(max_amp)

            if level == -1 or j > level:
                pixel_rows.append(False)
                continue
            
            pixel_rows.append(True)
            
        pixels.append(pixel_rows)

    queue.append(pixels)

try:
    screen.mainloop(rasterize)
finally:
    stop_event.set()