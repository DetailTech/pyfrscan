import numpy as np
from rtlsdr import RtlSdr
from scipy.signal import find_peaks
import os
import time

# Configuration Parameters
start_freq = 450e6       # Start frequency in Hz (450 MHz)
end_freq = 470e6         # End frequency in Hz (470 MHz)
sample_rate = 2.048e6    # Sample rate in Hz (2.048 MHz)
fft_size = 4096          # Number of FFT points for frequency resolution
num_ffts = 10            # Number of FFTs to average for noise reduction
squelch_offset_dB = 20   # Squelch level offset above noise floor in dB
signal_bandwidth = 12.5e3  # Expected signal bandwidth in Hz (e.g., 12.5 kHz)
bin_width = sample_rate / fft_size  # Frequency resolution per bin
min_distance = int(signal_bandwidth / bin_width)  # Minimum distance between peaks

# Initialize RTL-SDR
sdr = RtlSdr()

try:
    # Configure the device
    sdr.sample_rate = sample_rate
    sdr.gain = 2  # Set gain to 2
    
    # Calculate center frequencies to cover the range
    bandwidth = end_freq - start_freq
    num_steps = int(np.ceil(bandwidth / sample_rate))
    center_freqs = [start_freq + (i + 0.5) * sample_rate for i in range(num_steps)]
    
    while True:
        # Clear the console before each scan
#        os.system('cls' if os.name == 'nt' else 'clear')
        active_signals = []
        
        # Perform the scan across all center frequencies
        for center_freq in center_freqs:
            sdr.center_freq = center_freq
            
            # Capture samples
            samples = sdr.read_samples(fft_size * num_ffts)
            samples = samples.reshape((num_ffts, fft_size))
            
            # Compute averaged power spectrum
            fft = np.fft.fft(samples, axis=1)
            power = np.mean(np.abs(fft)**2, axis=0)
            
            # Calculate frequencies and shift power spectrum
            freqs = np.fft.fftshift(np.fft.fftfreq(fft_size, d=1/sample_rate)) + center_freq
            power = np.fft.fftshift(power)
            power_dB = 10 * np.log10(power + 1e-10)
            
            # Estimate noise floor
            noise_floor_dB = np.percentile(power_dB, 5)
            
            # Set squelch level
            squelch_level_dB = noise_floor_dB + squelch_offset_dB
            
            # Detect peaks
            peaks, _ = find_peaks(power_dB, height=squelch_level_dB, distance=min_distance)
            
            # Collect active signals with timestamp
            for peak in peaks:
                freq = freqs[peak]
                if start_freq <= freq <= end_freq and abs(freq - center_freq) > 10e3:
                    power_level = power_dB[peak]
                    # Add timestamp when the signal is detected
                    timestamp = time.strftime('%H:%M:%S')
                    active_signals.append((freq, power_level, timestamp))
        
        # Sort signals by frequency
        active_signals.sort(key=lambda x: x[0])
        os.system('cls' if os.name == 'nt' else 'clear')        
        # Print the latest scan results with timestamps
        print("Active signals found:", flush=True)
        if active_signals:
            for freq, power, timestamp in active_signals:
                print(f"[{timestamp}] Frequency: {freq / 1e6:.3f} MHz, Power: {power:.2f} dB", flush=True)
        else:
            print("No active signals detected.", flush=True)

except KeyboardInterrupt:
    print("\nScan interrupted by user.")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    sdr.close()
