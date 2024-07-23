import numpy as np

_fft_queue = None
_frequency_bands = [
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

_alpha = 0.45

def analyze(audio_frames, slice_size, audio_framerate, sample_width, channels):
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
        hann_window = np.hamming(len(frames))
        frames = frames * hann_window
        # TODO: analyze window of current - 100ms in time
        
        # frames = np_data[0:end]
        # if len(frames) == 0 or end >= len(np_data):
        if len(frames) == 0:
            break

        fft_result = np.fft.fft(np_data)
        fft_freqs = np.fft.fftfreq(len(fft_result), 1.0 / audio_framerate)
    
        bin_maxima = np.zeros(len(_frequency_bands))

        for i, (low, high, max_amplitudes, ema) in enumerate(_frequency_bands):
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
            ema[0] = (max_loudness * _alpha) + (ema[0] * (1 - _alpha))
            
            # diff = abs(ema[0] - ema1)
            # if diff < 3:
            #     ema[0] = math.ceil(ema[0] + ema1) / 2
            bin_maxima[i] = ema[0]
            
        # print(bin_maxima)
        _fft_queue.put(bin_maxima)
        start = end
        end += slice_size

def init(fft_queue):
    global _fft_queue
    _fft_queue = fft_queue