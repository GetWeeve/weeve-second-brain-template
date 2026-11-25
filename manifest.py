#!/usr/bin/env python3
"""Preview or refresh the public payload manifest after reviewing changed files."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import audit


def payload():
    files = {}
    for path in audit.candidates():
        name = path.relative_to(audit.ROOT).as_posix()
        if name == 'release-manifest.json':
            continue
        data = path.read_bytes()
        if name in audit.APPROVED_IMAGES:
            audit.validate_png(data)
        else:
            data.decode('utf-8')
        if audit.violations(data):
            raise ValueError('Possible credential in ' + name)
        files[name] = hashlib.sha256(data).hexdigest()
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true', help='Write reviewed payload hashes; does not approve a release')
    args = parser.parse_args(argv)
    path = audit.ROOT / 'release-manifest.json'
    try:
        manifest = json.loads(path.read_text(encoding='utf-8'))
        previous = manifest['files']
        current = payload()
        for name in sorted(set(previous) | set(current)):
            if previous.get(name) != current.get(name):
                action = 'added' if name not in previous else 'removed' if name not in current else 'changed'
                print(action + ': ' + name)
        if args.refresh:
            manifest.update(files=current, reviewed_on=datetime.now(timezone.utc).date().isoformat(), status='release candidate; founder review pending')
            with path.open('w', encoding='utf-8', newline='\n') as stream:
                stream.write(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
            print('Manifest refreshed. Review changed files and run audit.py; hashes do not certify safety.')
            return 0
        if previous != current:
            print('Review the changes, then run python3 manifest.py --refresh')
            return 1
        print('Manifest matches the reviewed candidate.')
        return 0
    except (ValueError, OSError, UnicodeDecodeError) as error:
        print('Manifest check failed:', str(error))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
