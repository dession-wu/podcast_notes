"""Draw small native navigation icons; run with a Python containing Pillow."""
from pathlib import Path
from PIL import Image, ImageDraw

output = Path(__file__).resolve().parents[1] / 'miniprogram' / 'assets'
output.mkdir(parents=True, exist_ok=True)
for name in ('search', 'book'):
    for selected, color in ((False, '#6b6d64'), (True, '#a4412d')):
        image = Image.new('RGBA', (384, 384))
        draw = ImageDraw.Draw(image)
        if name == 'search':
            draw.ellipse((68, 52, 260, 244), outline=color, width=14)
            draw.line((236, 220, 320, 304), fill=color, width=16)
        else:
            draw.line([(192, 96), (136, 68), (56, 68), (56, 292), (136, 292), (192, 320), (248, 292), (328, 292), (328, 68), (248, 68), (192, 96), (192, 320)], fill=color, width=12, joint='curve')
            for y in (132, 180, 228):
                draw.line((88, y, 144, y+8), fill=color, width=9)
                draw.line((240, y+8, 296, y), fill=color, width=9)
        image.resize((96, 96), Image.Resampling.LANCZOS).save(output / f'{name}{"-selected" if selected else ""}.png')
