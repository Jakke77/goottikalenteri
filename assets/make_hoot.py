"""Generate our original, synthetic eagle-owl-style double hoot (MIT)."""
import math
from pathlib import Path
import struct
import wave


def generate(path):
    rate = 22050
    samples = []
    phase = 0.0
    for i in range(int(3.2 * rate)):
        t = i / rate
        value = 0.0
        for start, length, base in ((0.18, 0.70, 166), (1.26, 1.20, 144)):
            u = (t - start) / length
            if 0 <= u < 1:
                envelope = math.sin(math.pi * u) ** 0.85
                frequency = base + 11 * math.sin(math.pi * u) - 17 * u
                phase += 2 * math.pi * frequency / rate
                value = envelope * (math.sin(phase) + .18 * math.sin(2 * phase) + .04 * math.sin(3 * phase))
        samples.append(struct.pack('<h', int(max(-1, min(1, value * .56)) * 32767)))
    with wave.open(str(path), 'wb') as target:
        target.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        target.writeframes(b''.join(samples))

if __name__ == '__main__':
    generate(Path(__file__).with_name('huuhkaja.wav'))
