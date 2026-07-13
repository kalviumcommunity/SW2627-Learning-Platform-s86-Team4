import sys
from pathlib import Path
p = Path(__file__).resolve().parents[0] / '..' / 'requirements.txt'
# normalize path
p = p.resolve()
raw = p.read_bytes()
encodings = ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1']
for enc in encodings:
    try:
        text = raw.decode(enc)
        p.write_text(text, encoding='utf-8', newline='\n')
        print(f"converted_from:{enc}")
        break
    except Exception:
        continue
else:
    print('failed to decode requirements.txt')
    sys.exit(1)
print('done')
