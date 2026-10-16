import time
import numpy as np
import matplotlib.pyplot as plt
import libusb_package
import pyvisa
import pyvisa_py.usb


def read_channel(scope, channel):
    scope.write(f':WAV:SOUR CHAN{channel}')
    scope.write(':WAV:MODE NORM')
    scope.write(':WAV:FORM BYTE')

    x_inc = float(scope.query(':WAV:XINC?'))
    x_orig = float(scope.query(':WAV:XOR?'))
    y_inc = float(scope.query(':WAV:YINC?'))
    y_orig = float(scope.query(':WAV:YOR?'))
    y_ref = float(scope.query(':WAV:YREF?'))

    raw = scope.query_binary_values(
        ':WAV:DATA?', datatype='B', container=np.array, delay=0.1
    )
    voltage = (raw - y_ref) * y_inc + y_orig
    time_axis = x_orig + np.arange(len(voltage)) * x_inc
    return time_axis, voltage


def lockin_measure(t, v, f0):
    """Coherent detection: amplitude & phase of v at frequency f0."""
    w = 2 * np.pi * f0
    I = np.mean(v * np.cos(w * t)) * 2
    Q = np.mean(v * np.sin(w * t)) * 2
    amplitude = np.hypot(I, Q)
    phase = np.arctan2(Q, I)
    return amplitude, phase


def set_timebase_for_freq(scope, freq, cycles=5, divisions=12):
    """Adjust horizontal scale to show `cycles` periods across the screen."""
    period = 1.0 / freq
    total_time = cycles * period
    scale = total_time / divisions
    scope.write(f':TIM:SCAL {scale:.6e}')
    return scale


def main():
    pyvisa_py.usb.libusb1 = libusb_package.get_libusb1_backend()
    rm = pyvisa.ResourceManager('@py')

    scope = rm.open_resource(
        f'USB0::{int(0x1AB1)}::{int(0x0517)}::DS1ZE280400648::0::INSTR',
        read_termination='\n',
    )
    scope.timeout = 10000

    # Optional: connect to your function generator here, e.g.
    # gen = rm.open_resource('USB0::...::INSTR')
    # gen.write(':SOUR1:FREQ {freq}')

    # Log-spaced frequency points (adjust density as needed)
    freqs = np.logspace(np.log10(1e-3), np.log10(5e5), num=60)

    mag_db = []
    phase_deg = []
    measured_freqs = []

    for f in freqs:
        # gen.write(f':SOUR1:FREQ {f}')  # set generator frequency
        set_timebase_for_freq(scope, f, cycles=5)

        # Settling time: longer for low frequencies
        settle = max(3.0 / f, 0.05)
        settle = min(settle, 30)  # cap to avoid absurd waits at 1 mHz
        time.sleep(settle)

        t1, v1 = read_channel(scope, 1)  # input
        t2, v2 = read_channel(scope, 2)  # output

        a_in, ph_in = lockin_measure(t1, v1, f)
        a_out, ph_out = lockin_measure(t2, v2, f)

        if a_in < 1e-6:
            continue  # skip bad/noisy points

        gain = 20 * np.log10(a_out / a_in)
        phase_diff = np.degrees(ph_out - ph_in)
        phase_diff = (phase_diff + 180) % 360 - 180  # wrap to [-180, 180]

        mag_db.append(gain)
        phase_deg.append(phase_diff)
        measured_freqs.append(f)

        print(f'f={f:.4g} Hz  Gain={gain:.2f} dB  Phase={phase_diff:.1f} deg')

    scope.close()
    rm.close()

    measured_freqs = np.array(measured_freqs)
    mag_db = np.array(mag_db)
    phase_deg = np.array(phase_deg)

    # Unwrap phase for a cleaner plot
    phase_unwrapped = np.degrees(np.unwrap(np.radians(phase_deg)))

    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(9, 7))

    ax1.semilogx(measured_freqs, mag_db, 'b.-')
    ax1.set_ylabel('Magnitude (dB)')
    ax1.set_title('Bode Plot')
    ax1.grid(True, which='both')

    ax2.semilogx(measured_freqs, phase_unwrapped, 'r.-')
    ax2.set_ylabel('Phase (deg)')
    ax2.set_xlabel('Frequency (Hz)')
    ax2.grid(True, which='both')

    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    main()