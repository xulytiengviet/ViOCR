"""Score a real OCR run against a UTF-8 reference (one form-feed between pages)."""
import argparse
import json
import math
import platform
import statistics
import tempfile
import time
import unicodedata
from pathlib import Path
from run import MODEL, convert


def normalize(s):
    return ' '.join(unicodedata.normalize('NFC', s).split())


def score(path, reference, repeats, dpi):
    expected = [normalize(s) for s in reference.read_text(encoding='utf-8-sig').split('\f')]
    inference, wall, exact = [], [], []
    with tempfile.TemporaryDirectory() as folder:
        for _ in range(repeats):
            output = Path(folder) / 'result.jsonl'
            start = time.perf_counter()
            convert(path, output, 'unicode', dpi)
            rows = [json.loads(s) for s in output.read_text(encoding='utf8').splitlines()]
            wall.append((time.perf_counter() - start) / max(1, len(rows)))
            exact.append(bool(rows) and all(expected) and expected == [normalize(row['text']) for row in rows])
            inference.extend(row['inference_s'] for row in rows)
    p95 = sorted(inference)[math.ceil(.95 * len(inference))-1] if inference else None
    return dict(system=platform.platform(), machine=platform.machine(), file=path.name, dpi=dpi, runs=repeats,
                measured_pages=len(inference), model_bytes=MODEL.stat().st_size, inference_p95_s=p95,
                mean_wall_s_per_page=statistics.mean(wall), exact_text=all(exact),
                passed=bool(p95 is not None and p95 < .5 and MODEL.stat().st_size < 30_000_000 and all(exact)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('document', type=Path)
    parser.add_argument('reference', type=Path)
    parser.add_argument('--runs', type=int, default=10)
    parser.add_argument('--dpi', type=int, default=150)
    args = parser.parse_args()
    if args.runs < 1 or not 72 <= args.dpi <= 600:
        parser.error('runs >= 1, DPI 72..600')
    result = score(args.document, args.reference, args.runs, args.dpi)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
