#!/usr/bin/env python3
"""A bounded synthetic retrieval benchmark, with no models or network access."""
from contextlib import redirect_stdout
import argparse
import io
import json
from pathlib import Path
import statistics
import tempfile
import time
import brain


def run(size, repeats):
    with tempfile.TemporaryDirectory(prefix='weeve-benchmark-') as temp:
        base = Path(temp).resolve()
        root = base / 'workspace'
        with redirect_stdout(io.StringIO()):
            brain.init(root)
            for i in range(size):
                source = base / 'sample.txt'
                source.write_text('# Case ' + str(i) + '\nrecord' + str(i) + ' clients renewed after scope review.\n', encoding='utf-8')
                brain.import_source(root, source, 'case-' + str(i), 'external-ok')
        timings, hits, maximum = [], 0, 0
        questions = ['record0', 'record' + str(size // 2), 'record' + str(size - 1)]
        for _ in range(repeats):
            for question in questions:
                start = time.perf_counter()
                result = brain.retrieve(root, question, 'local', 1200)
                timings.append((time.perf_counter() - start) * 1000)
                hits += int(question in result)
                maximum = max(maximum, len(result.encode('utf-8')))
        synonym_result = brain.retrieve(root, 'renewal', 'local', 1200)
        return {'sources': size, 'queries': len(timings), 'exact_locator_hits': hits,
                'exact_locator_recall': hits / len(timings), 'median_ms': round(statistics.median(timings), 3),
                'max_ms': round(max(timings), 3), 'max_output_bytes': maximum,
                'synonym_query_missed': 'No permitted matching evidence' in synonym_result}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sizes', type=int, nargs='+', default=[20, 100, 300])
    parser.add_argument('--repeats', type=int, default=3)
    args = parser.parse_args(argv)
    if not 1 <= args.repeats <= 10 or len(args.sizes) > 5 or any(not 1 <= n <= 1000 for n in args.sizes):
        parser.error('Use 1–5 corpus sizes of 1–1000 and 1–10 repeats')
    print(json.dumps({'scope': 'Synthetic exact-locator recall and local latency; not semantic or model answer quality',
                      'results': [run(n, args.repeats) for n in args.sizes]}, indent=2))


if __name__ == '__main__':
    main()
