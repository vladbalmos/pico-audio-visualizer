import numpy as np
import wave
import matplotlib.pyplot as plt

# Open the WAV file
file_path = 'sample.wav'
wav_file = wave.open(file_path, 'r')

# Extract Raw Audio from Wav File
signal = wav_file.readframes(-1)
signal = np.frombuffer(signal, dtype=np.int16)

# Get the frame rate
framerate = wav_file.getframerate()
print(framerate)

# Time vector spaced linearly with the size of the audio file
t = np.linspace(0, len(signal) / framerate, num=len(signal))

# Perform the FFT on the signal
fft_signal = np.fft.fft(signal)
print(len(fft_signal))

# Calculate the frequencies for the FFT result
frequencies = np.fft.fftfreq(len(fft_signal), d=1/framerate)
print(len(frequencies))

# Plot the FFT
plt.figure(figsize=(12, 6))
plt.plot(frequencies, np.abs(fft_signal))  # Plot in frequency domain
plt.xlabel('Frequency (Hz)')
plt.ylabel('Amplitude')
plt.title('FFT of Audio File')
plt.xlim(0, frequencies.max())  # Limit x-axis to positive frequencies only
plt.show()