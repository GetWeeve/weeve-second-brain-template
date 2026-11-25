"""Inspect release files, local links and all reachable Git-history text blobs."""
import hashlib
import json
from pathlib import Path
import re
import struct
import zlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
# Match actual key-like values, not generic variable names or policy documentation.
PATTERNS = [re.compile(p) for p in (
    r'gh[pousr]_[A-Za-z0-9]{30,}',
    r'github_pat_[A-Za-z0-9_]{40,}',
    r'phx_[A-Za-z0-9]{20,}',
    r'sk-(?:proj-)?[A-Za-z0-9_-]{20,}',
    r'AKIA[0-9A-Z]{16}',
    r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    r'(?i)Bearer\s+[A-Za-z0-9_.-]{25,}',
)]
ALLOWED_ROOTS = {'brain.py', 'demo.py', 'audit.py', 'manifest.py', 'benchmark.py', 'AGENTS.md', 'CLAUDE.md', 'GEMINI.md',
                 'README.md', '.gitignore', '.gitattributes', 'LICENSE', 'SECURITY.md', 'CONTRIBUTING.md', 'release-manifest.json'}
ALLOWED_DIRS = {'agents', 'docs', 'templates', 'examples', 'tests', '.github', 'assets', 'skills'}
APPROVED_IMAGES = {'assets/weeve-notes-demo.png'}
SUFFIXES = {'.md', '.py', '.json', '.txt', '.yml'}


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def violations(data):
    text = data.decode('utf-8', errors='replace')
    return any(pattern.search(text) for pattern in PATTERNS)


def candidates():
    result = []
    for path in sorted(ROOT.rglob('*')):
        relative = path.relative_to(ROOT)
        if relative.parts[0] == '.git' or '__pycache__' in relative.parts:
            continue
        if relative.parts[0] in ('workspace', 'workspaces'):
            continue
        if path.is_symlink():
            raise ValueError('Symlink in release tree: ' + str(relative))
        if path.is_file():
            if relative.parts[0] not in ALLOWED_DIRS and str(relative) not in ALLOWED_ROOTS:
                raise ValueError('Unexpected release path: ' + str(relative))
            if relative.parts[0] == 'assets' and relative.as_posix() not in APPROVED_IMAGES | {'assets/README.md'}:
                raise ValueError('Unreviewed image asset: ' + relative.as_posix())
            if len(relative.parts) > 1 and path.suffix not in SUFFIXES and relative.as_posix() not in APPROVED_IMAGES | {'assets/README.md'}:
                raise ValueError('Unexpected file type: ' + str(relative))
            result.append(path)
    return result


def validate_png(data):
    """Accept the reviewed PNG format and reject ancillary metadata or trailers."""
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Invalid PNG asset')
    position = 8
    chunks = []
    while position < len(data):
        if position + 12 > len(data):
            raise ValueError('Truncated PNG asset')
        length = struct.unpack('>I', data[position:position + 4])[0]
        end = position + 12 + length
        if end > len(data):
            raise ValueError('Truncated PNG chunk')
        kind = data[position + 4:position + 8]
        if kind not in (b'IHDR', b'IDAT', b'IEND'):
            raise ValueError('PNG contains unreviewed metadata')
        body = data[position + 8:end - 4]
        checksum = struct.unpack('>I', data[end - 4:end])[0]
        if zlib.crc32(kind + body) & 0xffffffff != checksum:
            raise ValueError('PNG checksum mismatch')
        chunks.append(kind)
        position = end
        if kind == b'IEND':
            break
    if not chunks or chunks[0] != b'IHDR' or chunks[-1] != b'IEND' or b'IDAT' not in chunks or position != len(data):
        raise ValueError('Invalid PNG structure or trailing metadata')


def audit():
    paths = candidates()
    manifest = json.loads((ROOT / 'release-manifest.json').read_text(encoding='utf-8'))
    actual = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in paths if p.name != 'release-manifest.json'}
    if manifest['files'] != actual:
        raise ValueError('Release manifest differs. Review changed files and refresh hashes')
    for path in paths:
        data = path.read_bytes()
        if path.relative_to(ROOT).as_posix() in APPROVED_IMAGES:
            validate_png(data)
        else:
            data.decode('utf-8')
        if violations(data):
            raise ValueError('Possible credential in ' + str(path.relative_to(ROOT)))
        if path.suffix == '.json':
            json.loads(data)
        if path.suffix == '.md':
            text = data.decode('utf-8')
            if text.count('```') % 2:
                raise ValueError('Unbalanced code fence: ' + str(path))
            for target in re.findall(r'\]\(([^)]+)\)', text):
                if target.startswith(('https://', 'http://', '#')):
                    continue
                if not (path.parent / target.split('#')[0]).is_file():
                    raise ValueError('Broken file link: ' + str(path.relative_to(ROOT)))
    try:
        tracked = git('ls-files', '-z').decode().strip('\0').split('\0')
    except (FileNotFoundError, subprocess.CalledProcessError):
        raise ValueError('Initialize Git before the release audit')
    for name in filter(None, tracked):
        if name not in actual and name != 'release-manifest.json':
            raise ValueError('Unexpected tracked file: ' + name)
    commits = git('rev-list', '--all').decode().splitlines()
    blobs = set()
    for commit in commits:
        for row in git('ls-tree', '-r', commit).decode().splitlines():
            info, name = row.split('\t', 1)
            mode, kind, oid = info.split()
            if mode == '120000' or (name not in actual and name != 'release-manifest.json'):
                raise ValueError('Unexpected path in Git history')
            if kind == 'blob':
                blobs.add(oid)
    for oid in blobs:
        data = git('cat-file', 'blob', oid)
        if data.startswith(b'\x89PNG\r\n\x1a\n'):
            validate_png(data)
        else:
            data.decode('utf-8')
        if violations(data):
            raise ValueError('Possible credential in Git history')
    print('Reviewed manifest matches', len(paths), 'release files;', len(commits), 'commits scanned.')
    print('Automated checks complement the recorded manual data/IP review.')


if __name__ == '__main__':
    try:
        audit()
    except (ValueError, OSError, UnicodeDecodeError) as error:
        print('Audit failed:', str(error), file=sys.stderr)
        sys.exit(1)
