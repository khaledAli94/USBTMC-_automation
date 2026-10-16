import time
import numpy as np
import matplotlib.pyplot as plt
import libusb_package
import pyvisa
import pyvisa_py.usb


SCOPE_RESOURCE = 'USB0::6833::1303::DS1ZE280400648::0::INSTR'


def read_channel(scope, channel):
    """Download the saved waveform for one channel."""
    scope.write(f':WAV:SOUR CHAN{channel}')
    scope.write(':WAV:MODE RAW')
    scope.write(':WAV:FORM BYTE')

    x_inc = float(scope.query(':WAV:XINC?'))
    x_orig = float(scope.query(':WAV:XOR?'))

    y_inc = float(scope.query(':WAV:YINC?'))
    y_orig = float(scope.query(':WAV:YOR?'))
    y_ref = float(scope.query(':WAV:YREF?'))

    raw = scope.query_binary_values(
        ':WAV:DATA?',
        datatype='B',
        container=np.array,
    )

    if len(raw) == 0:
        raise RuntimeError(f'CH{channel} returned no waveform data.')

    voltage = (raw.astype(float) - y_ref) * y_inc + y_orig
    time_axis = x_orig + np.arange(len(raw)) * x_inc

    return time_axis, voltage


def main():
    pyvisa_py.usb.libusb1 = libusb_package.get_libusb1_backend()
    rm = pyvisa.ResourceManager('@py')

    scope = rm.open_resource(
        SCOPE_RESOURCE,
        read_termination='\n',
    )
    scope.timeout = 60000

    try:
        print('Connected:', scope.query('*IDN?').strip())

        # Display the current scope configuration.
        # These are queries only; they do not modify scope settings.
        print('Trigger source:', scope.query(':TRIG:EDGE:SOUR?').strip())
        print('Time scale:', scope.query(':TIM:SCAL?').strip(), 's/div')
        print('Memory depth:', scope.query(':ACQ:MDEPTH?').strip())

        # Check whether a previous command caused an instrument error.
        print('Scope error state:', scope.query(':SYST:ERR?').strip())

        print('\nArming scope with its CURRENT front-panel settings...')
        print('Waiting for external trigger edge...')

        # Single capture. Red STOP LED after capture is normal.
        scope.write(':SING')

        timeout_seconds = 5.0
        start = time.time()

        while True:
            state = scope.query(':TRIG:STAT?').strip()
            print(f'\rTrigger status: {state:8}', end='', flush=True)

            if state == 'STOP':
                break

            if time.time() - start > timeout_seconds:
                print()
                raise TimeoutError(
                    'No trigger received within 5 seconds. '
                    'Set EXT edge triggering manually on the scope, '
                    'then verify the EXT square wave reaches the EXT TRIG BNC.'
                )

            time.sleep(0.05)

        print('\nCapture complete. Reading CH1 and CH2...')

        t1, ch1 = read_channel(scope, 1)
        t2, ch2 = read_channel(scope, 2)

    finally:
        scope.close()
        rm.close()

    if len(t1) < 2:
        raise RuntimeError('Not enough CH1 samples to calculate the time axis.')

    duration = t1[-1] - t1[0]
    sample_rate = 1.0 / (t1[1] - t1[0])

    print(f'CH1 points:       {len(ch1):,}')
    print(f'Capture duration: {duration * 1000:.3f} ms')
    print(f'Sample rate:      {sample_rate / 1e6:.3f} MSa/s')

    # Save capture, useful for later response/Bode processing.
    np.savez('sweep_capture.npz', time=t1, ch1=ch1, ch2=ch2)

    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(11, 7))

    ax1.plot(t1 * 1000, ch1, linewidth=0.7, color='tab:blue')
    ax1.set_title('CH1: Input sweep')
    ax1.set_ylabel('Voltage (V)')
    ax1.grid(True)

    ax2.plot(t2 * 1000, ch2, linewidth=0.7, color='tab:red')
    ax2.set_title('CH2: Output response')
    ax2.set_xlabel('Time (ms)')
    ax2.set_ylabel('Voltage (V)')
    ax2.grid(True)

    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    main()