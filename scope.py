import libusb_package
import numpy as np
import pyvisa
import pyvisa_py.usb
import matplotlib.pyplot as plt
import csv
from pathlib import Path


def read_channel(scope, channel):
    """Read waveform data from a channel without changing scope settings."""
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


def export_csv(path, headers, columns):
    """Write columns (equal-length arrays) to a CSV file."""
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(zip(*columns))


def main():
    pyvisa_py.usb.libusb1 = libusb_package.get_libusb1_backend()
    rm = pyvisa.ResourceManager('@py')

    resource_str = f'USB0::{int(0x1AB1)}::{int(0x0517)}::DS1ZE280400648::0::INSTR'
    scope = rm.open_resource(resource_str, read_termination='\n')
    scope.timeout = 10000

    t1, v1 = read_channel(scope, 1)  # Input voltage
    t2, v2 = read_channel(scope, 2)  # Output voltage

    scope.close()
    rm.close()

    # Single CSV named after this script: scope.csv
    out_path = Path(__file__).with_suffix('.csv')
    export_csv(out_path, ['time_s', 'ch1_v', 'ch2_v'], [t1, v1, v2])
    print(f'Wrote {out_path.resolve()}')

    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(10, 6))

    ax1.plot(t1 * 1000, v1, 'b-')
    ax1.set_title('CH1 - Input Voltage')
    ax1.set_ylabel('Voltage (V)')
    ax1.grid(True)

    ax2.plot(t2 * 1000, v2, 'r-')
    ax2.set_title('CH2 - Output Voltage')
    ax2.set_xlabel('Time (ms)')
    ax2.set_ylabel('Voltage (V)')
    ax2.grid(True)

    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    main()
