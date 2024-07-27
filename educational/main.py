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
from src import tcp_server
from collections import deque

MAX_AMPLITUDE = 100
ANIMATION_FRAMERATE = 60
FFT_SAMPLING_RATE = 20

fft_queue = queue.Queue()
stop_event = threading.Event()
pixels_queue = deque()
args = None

last_fft = 0
last_levels = None
threshold = math.floor(1000 / FFT_SAMPLING_RATE) - 1


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
    last = time.time()
    for data in wav_generator:
        # now = time.time()
        # print((now - last) * 1000)
        # last = now

        fft.analyze(data, samples_count, framerate, sample_width, channels)
        if stop_event.is_set():
            wav_generator.close()
            break
        
def interpolate(a, b, t):
    return (1 - t) * a + t * b
        
def main(frames_queue):
    global last_fft, last_levels

    values = None
    
    try:
        values = fft_queue.get_nowait()
        # tcp_server.data_queue.put(values)
    except queue.Empty:
        return
    except:
        print("No more audio. Exiting!")
        sys.exit(0)
        
    if last_levels is None:
        last_levels = [-1] * len(values)
    
    current_levels = []
    for max_amp in values:
        current_levels.append(animation_utils.get_level(max_amp))
        
    num_frames = ANIMATION_FRAMERATE // FFT_SAMPLING_RATE
    frames = []
    for i in range(num_frames):
        t = i / (num_frames - 1)
        interpolated_frame = [interpolate(last_levels[i], current_levels[i], t) for i in range(len(last_levels))] 
        frames.append(interpolated_frame)
        
    last_levels = current_levels
        
    for frame in frames:
        pixels = []
        for level in frame:
            pixels.append(animation_utils.level_to_pixels(round(level)))
            
        frames_queue.appendleft(pixels)
        
        
    # pixels = []
    # for max_amp in values:
    #     level = animation_utils.get_level(max_amp)
    #     frame = animation_utils.level_to_pixels(level)
    #     pixels.append(frame)
        
    # frames_queue.appendleft(pixels)
    
    
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
    
    # tcp_server.start(ANIMATION_FRAMERATE, len(fft.frequency_bands))

    try:
        screen.mainloop(main)
    except KeyboardInterrupt:
        exit(0)
    finally:
        stop_event.set()
        # tcp_server.stop()
