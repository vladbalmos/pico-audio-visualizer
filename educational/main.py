import argparse
import sys
import math
import threading
import queue
import time
from src import screen
from src import fft
from src import animation_utils
from src import audio_source
from collections import deque

MAX_AMPLITUDE = 100
ANIMATION_FRAMERATE = 60
FFT_SAMPLING_RATE = 60

fft_queue = queue.Queue()
stop_event = threading.Event()
pixels_queue = deque()
args = None

last_fft = 0
threshold = math.floor(1000 / FFT_SAMPLING_RATE) - 1


def next_divisible_by_32(n):
    remainder = n % 32
    if remainder == 0:
        return int(n + 32)
    else:
        return int(n + (32 - remainder))


def audio_worker():
    fft.init(fft_queue)

    source = None
    source_type = None
    
    if args.file:
        source = args.file
        source_type = 'wav'
    elif args.input_id:
        source = args.input_id
        source_type = 'stream'
        
    if source is None:
        print("No audio source provided")
        raise RuntimeError("No audio source provided")

    # Open the audio source
    samples_count, framerate, sample_width, channels, wav_generator = audio_source.open_audio(source, source_type, FFT_SAMPLING_RATE)
    print("Samples count", samples_count)
    print("Audio framerate", framerate)
    print("Sample width", sample_width)
    print("Channels", channels)
    
    # Read data
    for data in wav_generator:
        fft.analyze(data, samples_count, framerate, sample_width, channels)
        if stop_event.is_set():
            wav_generator.close()
            break
    
    

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
    
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Audio visualizer demo. Provide either --file or --input-id')
    parser.add_argument('--file', type=str, help='Path to the audio wav file')
    parser.add_argument('--input-id', type=str, help='The id of the input device to capture. Use --list-inputs to list all available input devices')
    parser.add_argument('--list-inputs', action='store_true', help='List all available input devices')
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
        
    args = parser.parse_args()
    
    if args.list_inputs:
        audio_source.list_audio_input_devices()
        exit(0)
    
    print('Animation framerate (fps)', ANIMATION_FRAMERATE)
    screen.init(ANIMATION_FRAMERATE)

    thread = threading.Thread(target=audio_worker)
    thread.start()

    try:
        screen.mainloop(rasterize)
    finally:
        stop_event.set()
