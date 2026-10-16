# USBTMC-_automation
lab test equipment automation scripts 

```md
```python
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
```
```
