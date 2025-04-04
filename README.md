A simple Python RF frequency scanner.
pyfrscan v0.8
DetailTech

How to Use This Script

Prerequisites:

Install the required Python libraries:
pip install numpy scipy rtlsdr

Ensure you have an RTL-SDR device connected to your computer and the necessary drivers installed (e.g., via Zadig on Windows).

Customize the Bands:
In the bands list, set the scan flag to 1 for the frequency bands you want to scan, and leave it as 0 for those you want to skip. For example:
i.e.
{'start': 450e6, 'end': 470e6, 'scan': 1, 'service': 'Land Mobile'},
This will scan the 450–470 MHz range (e.g., for GMRS/FRS signals).

Run the Script:
Save the code to a file (e.g., rtl_sdr_scanner.py) and run it:
python rtl_sdr_scanner.py

The script will continuously scan the selected bands and display active signals in the terminal.

Stop the Script:
Press Ctrl+C to stop scanning.


What the Script Does

Band Selection: You control which frequency bands to scan by setting the scan flag in the bands list.
Signal Detection: The RTL-SDR captures samples, computes the power spectrum, and detects signals above a squelch threshold.
Service Identification: Detected frequencies are matched to specific services (e.g., GMRS, FRS) or general band allocations.
Output: The terminal updates with a list of active signals, showing frequency (in MHz), power level (in dB), timestamp, and service type.


Configuration Options

You can tweak these parameters in the script to adjust performance:
sample_rate: Sampling rate (default: 2.048 MHz).
fft_size: FFT points for frequency resolution (default: 4096).
squelch_offset_dB: Sensitivity threshold above the noise floor (default: 20 dB).
sdr.gain: Receiver gain (default: 20 dB; adjust based on your environment).


Tested on Raspberry Pi 4 running Ubuntu 22 LTS.
