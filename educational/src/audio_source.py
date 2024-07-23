import wave
import pyaudio

def next_divisible_by_32(n):
    remainder = n % 32
    if remainder == 0:
        return int(n + 32)
    else:
        return int(n + (32 - remainder))
    
def stream_generator(p, stream, chunk_size):
    try:
        while True:
            data = stream.read(chunk_size)
            yield data
    except GeneratorExit:
        stream.stop_stream()
        stream.close()
        p.terminate()
    
    
def wav_generator(p, wf, output_stream, chunk_size):
    try:
        data = wf.readframes(chunk_size)

        while data:
            output_stream.write(data)
            yield data
            data = wf.readframes(chunk_size)

        output_stream.stop_stream()
        output_stream.close()
        p.terminate()

    except GeneratorExit:
        output_stream.stop_stream()
        output_stream.close()
        p.terminate()

def open_wav(source, chunk_size_factor):
    wf = wave.open(source, 'rb')
    framerate = wf.getframerate()
    sample_width = wf.getsampwidth()
    channels = wf.getnchannels()
    
    p = pyaudio.PyAudio()
    
    output_stream = p.open(format=p.get_format_from_width(sample_width),
                    channels=channels,
                    rate=framerate,
                    output=True)

    samples_count = (1 / chunk_size_factor) / (1 / framerate)
    samples_count = next_divisible_by_32(samples_count)
    chunk_size = 4 * samples_count

    return (samples_count, framerate, sample_width, channels, wav_generator(p, wf, output_stream, chunk_size))

def open_stream(source, chunk_size_factor):
    p = pyaudio.PyAudio()
    
    info = p.get_default_host_api_info()
    input_devices = []
    for i in range(info.get('deviceCount')):
        device = p.get_device_info_by_host_api_device_index(0, i)
        if device.get('maxInputChannels') > 0:
            input_devices.append(device)
            
    if not len(input_devices):
        raise RuntimeError('No input devices found')
        
    audio_input = None
    for d in input_devices:
        if int(d.get('index')) == int(source):
            audio_input = d
            break

    if audio_input is None:
        raise RuntimeError(f"Input device {source} not found")
    
    framerate = int(audio_input.get('defaultSampleRate'))
    sample_width = 2
    channels = audio_input.get('maxInputChannels')

    samples_count = (1 / chunk_size_factor) / (1 / framerate)
    samples_count = next_divisible_by_32(samples_count)
    chunk_size = 4 * samples_count
    
    stream = p.open(
        format = pyaudio.paInt16,
        channels = channels,
        rate = framerate,
        input = True,
        input_device_index = audio_input.get('index'),
        frames_per_buffer = chunk_size
    )
    
    return (samples_count, framerate, sample_width, channels, stream_generator(p, stream, chunk_size))
    

def open_audio(source, source_type, chunk_size_factor):
    if source_type == 'wav':
        return open_wav(source, chunk_size_factor)
    
    if source_type == 'stream':
        return open_stream(source, chunk_size_factor)
    
    raise ValueError(f"Invalid source type {source_type}")
    
def list_audio_input_devices():
    p = pyaudio.PyAudio()
    info = p.get_default_host_api_info()
    input_devices = []
    for i in range(info.get('deviceCount')):
        device = p.get_device_info_by_host_api_device_index(0, i)
        if device.get('maxInputChannels') > 0:
            input_devices.append(device)

    p.terminate()
            
    if not len(input_devices):
        print('No input devices found')
        return
        
    for d in input_devices:
        print(d.get('index'), d.get('name'))