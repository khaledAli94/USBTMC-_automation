import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def main():
    # 1. Check if the user provided a CSV file in the command line
    if len(sys.argv) < 2:
        print("Usage: python bode.py <path_to_csv>")
        print("Example: python bode.py scope.csv")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"Error: File '{csv_path}' not found.")
        sys.exit(1)

    print(f"Loading data from {csv_path}...")

    # 2. Read the CSV using pandas
    # Your CSV headers are: time_s, ch1_v, ch2_v
    df = pd.read_csv(csv_path)
    
    t = df['time_s'].to_numpy()
    u = df['ch1_v'].to_numpy()  # Input
    y = df['ch2_v'].to_numpy()  # Output

    # 3. Pre-processing
    # Remove DC offset (crucial for valid Bode plots)
    u = u - np.mean(u)
    y = y - np.mean(y)

    # Optional: Apply a Hanning window to reduce spectral leakage
    # (Uncomment the next 2 lines if your data has sharp discontinuities)
    # window = np.hanning(len(u))
    # u = u * window; y = y * window

    # 4. Calculate Sampling Frequency (Fs)
    Ts = np.mean(np.diff(t))
    Fs = 1.0 / Ts
    N = len(t)

    # 5. Compute Fast Fourier Transform (FFT)
    U = np.fft.fft(u)
    Y = np.fft.fft(y)

    # 6. Calculate Transfer Function Estimate H(f) = Y(f) / U(f)
    # Add a tiny epsilon to denominator to avoid divide-by-zero warnings
    H = Y / (U + 1e-12)

    # 7. Create Frequency Vector (Hz)
    f = np.fft.fftfreq(N, Ts)
    
    # We only care about the positive half of the frequencies (up to Nyquist)
    half_N = N // 2
    f_half = f[:half_N]
    H_half = H[:half_N]

    # 8. Calculate Magnitude (dB) and Phase (degrees)
    mag_dB = 20 * np.log10(np.abs(H_half))
    phase_deg = np.angle(H_half) * (180 / np.pi)

    # 9. Plotting
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(10, 6))

    # Magnitude Plot
    ax1.semilogx(f_half, mag_dB, 'b-')
    ax1.set_title('Bode Plot Estimate')
    ax1.set_ylabel('Magnitude (dB)')
    ax1.grid(True, which="both", ls="--")

    # Phase Plot
    ax2.semilogx(f_half, phase_deg, 'r-')
    ax2.set_xlabel('Frequency (Hz)')
    ax2.set_ylabel('Phase (deg)')
    ax2.grid(True, which="both", ls="--")

    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    main()