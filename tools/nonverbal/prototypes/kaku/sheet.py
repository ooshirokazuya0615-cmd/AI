"""Contact sheet: one small frame every STEP seconds, labelled."""
import subprocess, sys
from pathlib import Path
step = float(sys.argv[1]) if len(sys.argv) > 1 else 0.4
t0 = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
t1 = float(sys.argv[3]) if len(sys.argv) > 3 else 25.6
ts = []
t = t0
while t < t1 - 1e-6:
    ts.append(round(t, 3)); t += step
subprocess.run([sys.executable, 'build.py', '--size', '180x320', '--stills', ','.join(map(str, ts))], check=True, capture_output=True)
from PIL import Image, ImageDraw
ims = [(t, Image.open(f'frames/still-{round(t*60)/60:05.2f}s.png')) for t in ts]
cols = 16
rows = (len(ims) + cols - 1) // cols
W, Hh = 180, 320
sheet = Image.new('RGB', (cols * W, rows * (Hh + 14)), 'white')
d = ImageDraw.Draw(sheet)
for k, (t, im) in enumerate(ims):
    x, y = (k % cols) * W, (k // cols) * (Hh + 14)
    sheet.paste(im, (x, y + 14)); d.text((x + 3, y + 1), f'{t:.1f}s b{t/ (60/112.5):.1f}', fill='black')
sheet.save(sys.argv[4] if len(sys.argv) > 4 else 'sheet.png')
print(len(ims))
