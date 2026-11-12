"""Offline Vietnamese document OCR. Pixel coordinates use a top-left origin."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from PIL import Image, ImageOps, ImageSequence
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / 'models' / 'vie.traineddata'
DIGEST = '79df64caf7bcfb2a27df5042ecb6121e196eada34da774956995747636d5bfa1'


def pages(path, dpi):
    if path.suffix.lower() == '.pdf':
        with pdfium.PdfDocument(path) as document:
            for page in document:
                try:
                    bitmap = page.render(scale=dpi / 72)
                    try:
                        yield bitmap.to_pil().convert('L')
                    finally:
                        bitmap.close()
                finally:
                    page.close()
    else:
        with Image.open(path) as image:
            for frame in ImageSequence.Iterator(image):
                yield ImageOps.exif_transpose(frame).convert('L')


def recognize(image, mode):
    binary = shutil.which('tesseract') or str(Path(os.getenv('ProgramFiles', 'C:/Program Files')) / 'Tesseract-OCR/tesseract.exe')
    buf = io.BytesIO()
    image.save(buf, format='PPM')
    cmd = [binary, 'stdin', 'stdout', '--tessdata-dir', str(MODEL.parent), '-l', 'vie', '--oem', '1', '--psm', '3']
    if mode == 'base27':
        cmd += ['-c', 'tessedit_char_whitelist=0123456789 ']
    # Request TSV via variable so the standalone model directory needs no configs/tsv.
    cmd += ['-c', 'tessedit_create_tsv=1']
    start = time.perf_counter()
    proc = subprocess.run(cmd, input=buf.getvalue(), capture_output=True, check=True,
                          env={**os.environ, 'OMP_THREAD_LIMIT': '1'})
    elapsed = time.perf_counter() - start
    groups = {}
    for word in csv.DictReader(io.StringIO(proc.stdout.decode('utf8')), delimiter='\t', quoting=csv.QUOTE_NONE):
        if word['level'] != '5' or not word['text'].strip():
            continue
        key = tuple(word[k] for k in ('block_num', 'par_num', 'line_num'))
        groups.setdefault(key, []).append(dict(text=word['text'], confidence=float(word['conf']),
            box=[int(word[k]) for k in ('left', 'top', 'width', 'height')]))
    lines = list(groups.values())
    encoded = subprocess.run(['node', str(ROOT / 'codec.js'), mode],
        input=json.dumps([' '.join(w['text'] for w in line) for line in lines]).encode(),
        capture_output=True, check=True)
    decoded = json.loads(encoded.stdout)
    for words, line in zip(lines, decoded, strict=True):
        line['words'] = words
    return decoded, elapsed


def convert(path, output, mode, dpi):
    if hashlib.sha256(MODEL.read_bytes()).hexdigest() != DIGEST:
        raise ValueError('Sai SHA-256 của mô hình vie.traineddata')
    if path.resolve() == output.resolve():
        raise ValueError('Tệp đầu vào và đầu ra phải khác nhau')
    tmp = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf8', dir=output.parent, delete=False) as dst:
            tmp = Path(dst.name)
            tick = time.perf_counter()
            for number, image in enumerate(pages(path, dpi), 1):
                lines, inference = recognize(image, mode)
                result = dict(schemaVersion=1, file=path.name, page=number, width=image.width, height=image.height,
                    mode=mode, inference_s=inference, lines=lines, text='\n'.join(line['unicode'] for line in lines))
                result['page_s'] = time.perf_counter() - tick
                dst.write(json.dumps(result, ensure_ascii=False) + '\n')
                tick = time.perf_counter()
        tmp.replace(output)
    finally:
        if tmp:
            tmp.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('-o', '--output', required=True, type=Path)
    parser.add_argument('--mode', choices=['unicode', 'cvss', 'base27'], default='unicode')
    parser.add_argument('--dpi', type=int, default=150, choices=range(72, 601), metavar='72..600')
    args = parser.parse_args()
    try:
        convert(args.input, args.output, args.mode, args.dpi)
    except subprocess.CalledProcessError as exc:
        parser.exit(1, exc.stderr.decode('utf8', errors='replace') + '\n')
    except (OSError, ValueError, pdfium.PdfiumError) as exc:
        parser.exit(1, str(exc) + '\n')
