import numpy as np

_DEFAULT_ALPHA = 0.5
_DEFAULT_MAX_AMPLITUDE = 500
_MAX_AMPLITUDE_BIN_SIZE = 250
_EPSILON = 1e-10
_STARTING_EMMA = -60

_fft_queue = None

frequency_bands = [
    (1, 32, [], [_STARTING_EMMA], _DEFAULT_ALPHA + 0.10),
    (32, 62, [], [_STARTING_EMMA], _DEFAULT_ALPHA + 0.10),
    (63, 125, [], [_STARTING_EMMA], _DEFAULT_ALPHA + 0.15),
    (126, 250, [], [_STARTING_EMMA], _DEFAULT_ALPHA + 0.15),
    (251, 500, [], [_STARTING_EMMA], _DEFAULT_ALPHA + 0.15),
    (501, 1000, [], [_STARTING_EMMA], _DEFAULT_ALPHA + 0.15),
    (1001, 2000, [], [_STARTING_EMMA], _DEFAULT_ALPHA + 0.1),
    (2001, 4000, [], [_STARTING_EMMA], _DEFAULT_ALPHA + 0.1),
    (4001, 8000, [], [_STARTING_EMMA], _DEFAULT_ALPHA + 0.1),
    (8001, 16000, [], [_STARTING_EMMA], _DEFAULT_ALPHA + 0.1)
]

# frequency_bands = [
#     (1, 32, [], [_STARTING_EMMA], _DEFAULT_ALPHA),
#     (32, 62, [], [_STARTING_EMMA], _DEFAULT_ALPHA),
#     (63, 125, [], [_STARTING_EMMA], _DEFAULT_ALPHA),
#     (126, 250, [], [_STARTING_EMMA], _DEFAULT_ALPHA),
#     (251, 500, [], [_STARTING_EMMA], _DEFAULT_ALPHA),
#     (501, 1000, [], [_STARTING_EMMA], _DEFAULT_ALPHA),
#     (1001, 2000, [], [_STARTING_EMMA], _DEFAULT_ALPHA),
#     (2001, 4000, [], [_STARTING_EMMA], _DEFAULT_ALPHA),
#     (4001, 8000, [], [_STARTING_EMMA], _DEFAULT_ALPHA),
#     (8001, 16000, [], [_STARTING_EMMA], _DEFAULT_ALPHA)
# ]


def analyze(audio_frames, slice_size, audio_framerate, sample_width, channels):
    global global_max
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
        hann_window = np.hamming(len(frames))
        frames = frames * hann_window

        if len(frames) == 0:
            break

        fft_real = np.fft.fft(np_data)
        fft_result = np.abs(fft_real)
        fft_freqs = np.fft.fftfreq(len(fft_result), 1.0 / audio_framerate)
        
        bin_maxima = np.zeros(len(frequency_bands))

        for i, (low, high, max_amplitudes, ema, alpha) in enumerate(frequency_bands):
            bin_indices = np.where((fft_freqs >= low) & (fft_freqs < high))[0]
            
            if bin_indices.size == 0:
                bin_maxima[i] = -np.inf
                continue

            amplitudes = np.abs(fft_result[bin_indices])
            
            max_band_amplitude = max(np.max(amplitudes), _EPSILON)
            
            max_amplitudes.append(max_band_amplitude)
            if len(max_amplitudes) > _MAX_AMPLITUDE_BIN_SIZE:
                max_amplitudes.pop(0)
                
            max_amplitude = max(np.max(max_amplitudes), _DEFAULT_MAX_AMPLITUDE)

            loudness_db = 20 * np.log10((amplitudes + _EPSILON) / (max_amplitude + _EPSILON))
            max_loudness = np.max(loudness_db)
            # bin_maxima[i] = max_loudness
            ema[0] = (max_loudness * alpha) + (ema[0] * (1 - alpha))
            bin_maxima[i] = ema[0]
            
        # print(bin_maxima)
        _fft_queue.put(bin_maxima)
        start = end
        end += slice_size

def init(fft_queue):
    global _fft_queue
    _fft_queue = fft_queue