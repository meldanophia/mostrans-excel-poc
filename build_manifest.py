#!/usr/bin/env python3
"""Build manifest.xml from manifest.template.xml using a HTTPS hosting root URL."""
from pathlib import Path
from urllib.parse import urlparse
import sys

if len(sys.argv) != 2:
    raise SystemExit('Usage: python build_manifest.py https://USERNAME.github.io/REPOSITORY/web')
url = sys.argv[1].rstrip('/')
p = urlparse(url)
if p.scheme != 'https' or not p.netloc or p.username or p.password or p.query or p.fragment:
    raise SystemExit('URL must be an HTTPS base URL (without query/fragment).')
base = Path(__file__).resolve().parent
text = (base/'manifest.template.xml').read_text(encoding='utf-8')
text = text.replace('__BASE_URL__', url)
text = text.replace('__APP_DOMAIN__', f'{p.scheme}://{p.netloc}')
(base/'manifest.xml').write_text(text, encoding='utf-8')
print(f'Manifest dibuat: {base / "manifest.xml"}')
print(f'Pastikan URL berikut bisa diakses: {url}/taskpane.html')
