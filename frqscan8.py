import numpy as np
from rtlsdr import RtlSdr
from scipy.signal import find_peaks
import os
import time

# Define the bands with their frequency ranges, scan flags, and services
bands = [
    {'start': 100e6, 'end': 108e6, 'scan': 0, 'service': 'FM Broadcasting'},
    {'start': 108e6, 'end': 137e6, 'scan': 0, 'service': 'Aviation'},
    {'start': 137e6, 'end': 144e6, 'scan': 1, 'service': 'Military'},
    {'start': 144e6, 'end': 148e6, 'scan': 1, 'service': 'Amateur Radio (2m)'},
    {'start': 148e6, 'end': 174e6, 'scan': 1, 'service': 'Land Mobile'},
    {'start': 174e6, 'end': 216e6, 'scan': 0, 'service': 'TV Broadcasting'},
    {'start': 216e6, 'end': 220e6, 'scan': 1, 'service': 'Maritime'},
    {'start': 220e6, 'end': 225e6, 'scan': 1, 'service': 'Amateur Radio (1.25m)'},
    {'start': 225e6, 'end': 400e6, 'scan': 1, 'service': 'Military'},
    {'start': 400e6, 'end': 420e6, 'scan': 1, 'service': 'Government'},
    {'start': 420e6, 'end': 450e6, 'scan': 1, 'service': 'Amateur Radio (70cm)'},
    {'start': 450e6, 'end': 470e6, 'scan': 1, 'service': 'Land Mobile'},
    {'start': 470e6, 'end': 512e6, 'scan': 0, 'service': 'TV Broadcasting'},
    {'start': 512e6, 'end': 698e6, 'scan': 0, 'service': 'TV Broadcasting'},
    {'start': 698e6, 'end': 806e6, 'scan': 0, 'service': 'Wireless Communications'},
    {'start': 806e6, 'end': 896e6, 'scan': 1, 'service': 'Cellular/Public Safety'},
    {'start': 896e6, 'end': 901e6, 'scan': 1, 'service': 'Cellular'},
    {'start': 901e6, 'end': 902e6, 'scan': 1, 'service': 'Paging'},
    {'start': 902e6, 'end': 928e6, 'scan': 1, 'service': 'ISM/Amateur Radio'},
    {'start': 928e6, 'end': 960e6, 'scan': 0, 'service': 'Cellular'},
    {'start': 960e6, 'end': 1000e6, 'scan': 1, 'service': 'Aviation'}
]

# Configuration Parameters
sample_rate = 2.048e6    # Sample rate in Hz (2.048 MHz)
fft_size = 4096          # Number of FFT points for frequency resolution
num_ffts = 10            # Number of FFTs to average for noise reduction
squelch_offset_dB = 20   # Squelch level offset above noise floor in dB
signal_bandwidth = 12.5e3  # Expected signal bandwidth in Hz (e.g., 12.5 kHz)
bin_width = sample_rate / fft_size  # Frequency resolution per bin (~500 Hz)
min_distance = int(signal_bandwidth / bin_width)  # Minimum distance between peaks

# Specific frequency lists for GMRS and FRS in Hz (within 450-470 MHz)
gmrs_primary = [
    462.5500e6, 462.5750e6, 462.6000e6, 462.6250e6,
    462.6500e6, 462.6750e6, 462.7000e6, 462.7250e6
]
gmrs_repeater_in = [
    467.5500e6, 467.5750e6, 467.6000e6, 467.6250e6,
    467.6500e6, 467.6750e6, 467.7000e6, 467.7250e6
]
frs_gmrs_shared = [
    462.5625e6, 462.5875e6, 462.6125e6, 462.6375e6,
    462.6625e6, 462.6875e6, 462.7125e6
]
frs_only = [
    467.5625e6, 467.5875e6, 467.6125e6, 467.6375e6,
    467.6625e6, 467.6875e6, 467.7125e6
]

# Function to identify the service based on frequency
def get_service(freq):
    tolerance = 1000  # 1 kHz tolerance for specific matches
    # Check specific GMRS and FRS frequencies first
    for f in gmrs_primary:
        if abs(freq - f) < tolerance:
            return "GMRS Primary"
    for f in gmrs_repeater_in:
        if abs(freq - f) < tolerance:
            return "GMRS Repeater Input"
    for f in frs_gmrs_shared:
        if abs(freq - f) < tolerance:
            return "FRS/GMRS Shared"
    for f in frs_only:
        if abs(freq - f) < tolerance:
            return "FRS"
    # Fall back to broader allocations
    for band in bands:
        if band['start'] <= freq <= band['end']:
            return band['service']
    return "Unknown"

# Initialize RTL-SDR
sdr = RtlSdr()

try:
    # Configure the device
    sdr.sample_rate = sample_rate
    sdr.gain = 20  # Adjust gain as needed (e.g., 20 dB)

    # Get bands to scan
    scanned_bands = [band for band in bands if band['scan'] == 1]

    # Calculate center frequencies for the scanned bands
    center_freqs = []
    for band in scanned_bands:
        band_start = band['start']
        band_end = band['end']
        band_center_freqs = np.arange(band_start + sample_rate / 2, band_end, sample_rate)
        center_freqs.extend(band_center_freqs)
    center_freqs = sorted(set(center_freqs))  # Remove duplicates and sort

    print(f"Scanning selected bands with {len(center_freqs)} center frequencies...")

    # Continuous scanning loop
    while True:
        active_signals = []

        # Scan across all center frequencies
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
            power_dB = 10 * np.log10(power + 1e-10)  # Add small constant to avoid log(0)

            # Estimate noise floor (5th percentile)
            noise_floor_dB = np.percentile(power_dB, 5)

            # Set squelch level
            squelch_level_dB = noise_floor_dB + squelch_offset_dB

            # Detect peaks above squelch level
            peaks, _ = find_peaks(power_dB, height=squelch_level_dB, distance=min_distance)

            # Collect active signals with timestamp and service
            for peak in peaks:
                freq = freqs[peak]
                # Check if frequency is within a scanned band and avoid DC spike (±10 kHz from center)
                if any(b['start'] <= freq <= b['end'] for b in scanned_bands) and abs(freq - center_freq) > 10e3:
                    power_level = power_dB[peak]
                    timestamp = time.strftime('%H:%M:%S')
                    service = get_service(freq)
                    active_signals.append((freq, power_level, timestamp, service))

        # Sort signals by frequency
        active_signals.sort(key=lambda x: x[0])

        # Clear terminal and display results
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"Active signals found in selected bands:", flush=True)
        if active_signals:
            for freq, power, timestamp, service in active_signals:
                print(f"[{timestamp}] Frequency: {freq / 1e6:.3f} MHz, "
                      f"Power: {power:.2f} dB, Service: {service}", flush=True)
        else:
            print("No active signals detected.", flush=True)

except KeyboardInterrupt:
    print("\nScan interrupted by user.")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    sdr.close()
