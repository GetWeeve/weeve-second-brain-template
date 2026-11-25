#!/usr/bin/env python3
"""Offline company memory tools. Standard library only, Python 3.9+."""
import argparse
from contextlib import contextmanager
from datetime import date, datetime, timezone
import hashlib
import difflib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
ROLES = ('research', 'marketing', 'sales', 'product', 'delivery', 'strategy', 'coordinator')


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def safe(root, relative):
    """Reject traversal, symlinks and Windows path tricks on every platform."""
    if not isinstance(relative, str) or not relative or '\\' in relative or ':' in relative:
        raise ValueError('Use a relative path inside the workspace')
    path = Path(relative)
    if path.is_absolute() or any(part in ('..', '.') for part in path.parts):
        raise ValueError('Path escapes workspace')
    target = root / path
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('Symlink paths are unsupported')
    if root.resolve() not in target.resolve().parents:
        raise ValueError('Path escapes workspace')
    return target


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=str(path.parent), prefix='.write-')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def slug(value):
    reserved = {'con', 'prn', 'aux', 'nul'} | {'com' + str(i) for i in range(1, 10)} | {'lpt' + str(i) for i in range(1, 10)}
    if not isinstance(value, str) or value in reserved or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', value):
        raise ValueError('Names use lowercase letters, digits and single hyphens')
    return value


def workspace(value):
    path = Path(value).expanduser().absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        # /tmp is a system symlink on macOS. Resolve the base before using it.
        path = path.resolve()
    if not (path / 'settings.json').is_file():
        raise ValueError('Initialize this workspace first')
    if safe(path, '.brain/rebuild-in-progress').exists():
        raise ValueError('Reconstruction is incomplete. Use the original workspace or a verified backup')
    if read_json(safe(path, 'settings.json')).get('version') != 1:
        raise ValueError('Unsupported workspace version')
    return path


@contextmanager
def locked(root):
    """A process-scoped exclusive OS lock, retained for consistent multi-file reads."""
    if safe(root, '.lock').exists():
        raise ValueError('Legacy .lock found. Verify no old process remains; see docs/troubleshooting.md')
    lock = safe(root, '.brain/workspace.lock')
    flags = os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(str(lock), flags, 0o600)
    acquired = False
    try:
        if os.fstat(fd).st_size == 0:
            os.write(fd, b'0')
        os.lseek(fd, 0, os.SEEK_SET)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except OSError:
            raise ValueError('Workspace is busy. Retry when the other command finishes') from None
        yield
    finally:
        if acquired:
            if os.name == 'nt':
                import msvcrt
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def init(path):
    path = Path(path).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    if any(path.iterdir()):
        raise ValueError('Choose an empty workspace directory')
    # Strong default for users who later initialize Git in this directory.
    atomic(path / '.gitignore', b'*\n')
    atomic(path / 'settings.json', encode({'version': 1, 'name': 'My second brain',
        'timezone': 'UTC', 'source_max_age_days': 0, 'topic_review_days': 30,
        'processor_mode': 'unset', 'external_processors_enabled': False}))
    for name in ('raw-local', 'wiki', 'reviews', 'daily', '.brain'):
        (path / name).mkdir()
    atomic(path / '.brain/sources.json', encode([]))
    atomic(path / '.brain/page-deps.json', encode({}))
    atomic(path / 'index.md', b'# Knowledge index\n\nAdd reviewed topics through a proposal.\n')
    atomic(path / 'log.md', b'# Change log\n')
    print('Initialized private local workspace:', path)


def import_source(root, file, label, processor, refresh_days=0):
    slug(label)
    if processor not in ('local-only', 'external-ok') or not 0 <= refresh_days <= 36500:
        raise ValueError('Choose local-only or external-ok and a nonnegative refresh cadence')
    source = Path(file).expanduser()
    if source.is_symlink() or not source.is_file():
        raise ValueError('Import an ordinary UTF-8 text file')
    if source.suffix.lower() not in ('.md', '.txt', '.json', '.csv'):
        raise ValueError('Export as Markdown, text, JSON or CSV first')
    data = source.read_bytes()
    if len(data) > 5_000_000:
        raise ValueError('Source exceeds 5 MB. Export a smaller scoped source')
    data.decode('utf-8')
    revision = digest(data)
    relative = 'raw-local/' + label + '/' + revision + source.suffix.lower()
    folder = safe(root, '.brain/imports/' + label + '-' + revision)
    journal_path, receipt_path = folder / 'journal.json', folder / 'receipt.json'
    no_pending(root, except_journal=journal_path)
    if journal_path.exists() and not receipt_path.exists():
        run_transaction(root, journal_path, receipt_path)
    registry = load_registry(root)
    prior = next((r for r in registry if r['id'] == label and r['sha256'] == revision), None)
    if prior:
        if prior['processor'] != processor:
            raise ValueError('Existing source permission differs. Review the source policy explicitly')
        if safe(root, prior['path']).read_bytes() != data:
            raise ValueError('Immutable source integrity failed')
        print('Already imported:', prior['path'])
        return
    dest = safe(root, relative)
    if dest.exists() and dest.read_bytes() != data:
        raise ValueError('Immutable source collision')
    atomic(dest, data)
    observed = stamp()
    registry.append({'id': label, 'sha256': revision, 'path': relative, 'processor': processor,
                     'observed_at': observed, 'classification': 'private', 'refresh_days': refresh_days})
    log = safe(root, 'log.md').read_text(encoding='utf-8')
    log += '\n## [' + observed[:10] + '] ingest | ' + relative + ' | ' + processor + ' | ' + observed + '\n'
    prepare_transaction(root, journal_path, {'kind': 'import', 'source': relative},
                        {'.brain/sources.json': encode(registry).decode(), 'log.md': log})
    run_transaction(root, journal_path, receipt_path)
    print('Imported:', relative)


def source_records(root):
    records = load_registry(root)
    for record in records:
        if record['processor'] not in ('local-only', 'external-ok'):
            raise ValueError('Invalid source processor policy')
        if not record['path'].startswith('raw-local/'):
            raise ValueError('Source registry path is outside evidence storage')
        path = safe(root, record['path'])
        if digest(path.read_bytes()) != record['sha256']:
            raise ValueError('Immutable source integrity failed: ' + record['id'])
    return records


def sections(text):
    heading, lines = 'Document', []
    for line in text.splitlines():
        if line.startswith('#'):
            if lines:
                yield heading, '\n'.join(lines)
            heading, lines = line.lstrip('#').strip(), []
        else:
            lines.append(line)
    if lines:
        yield heading, '\n'.join(lines)


def retrieve(root, query, processor, budget):
    if processor not in ('local', 'external'):
        raise ValueError('Choose a local or external processor')
    if budget < 256 or budget > 100000:
        raise ValueError('Context budget must be 256 to 100000 UTF-8 bytes')
    settings = read_json(safe(root, 'settings.json'))
    if processor == 'external' and not settings['external_processors_enabled']:
        raise ValueError('External processing is disabled. After owner permission, run: settings --allow-cloud --confirm-data-policy')
    no_pending(root)
    terms = set(re.findall(r'\w+', query.lower()))
    candidates = []
    # Permissions are filtered before source text is read or emitted.
    records = load_registry(root)
    latest = {r['id']: r['sha256'] for r in records}
    cache = {}
    for record in records:
        if not record['path'].startswith('raw-local/'):
            raise ValueError('Source registry path is outside evidence storage')
        if latest[record['id']] != record['sha256']:
            continue
        if processor == 'external' and record['processor'] != 'external-ok':
            continue
        data = safe(root, record['path']).read_bytes()
        if digest(data) != record['sha256']:
            raise ValueError('Immutable source integrity failed')
        cache[record['path']] = data
        for number, (heading, body) in enumerate(sections(data.decode('utf-8')), 1):
            score = len(terms & set(re.findall(r'\w+', heading.lower() + ' ' + body.lower())))
            if score:
                candidates.append((score, record, number, heading, body))
    by_path = {r['path']: r for r in records}
    deps = read_json(safe(root, '.brain/page-deps.json'))
    for relative, source_paths in deps.items():
        if not re.fullmatch(r'wiki/[a-z0-9]+(?:-[a-z0-9]+)*\.md', relative):
            raise ValueError('Invalid topic path in dependency map')
        # A topic inherits every source's processor restriction. Never expose a
        # summary if a source dependency is missing, restricted or superseded.
        allowed = bool(source_paths) and all(s in by_path for s in source_paths)
        allowed = allowed and all(latest[by_path[s]['id']] == by_path[s]['sha256'] for s in source_paths)
        if processor == 'external':
            allowed = allowed and all(by_path[s]['processor'] == 'external-ok' for s in source_paths)
        if not allowed:
            continue
        for source in source_paths:
            data = cache.get(source)
            if data is None:
                data = safe(root, source).read_bytes()
                if digest(data) != by_path[source]['sha256']:
                    raise ValueError('Topic source integrity failed')
                cache[source] = data
        text = safe(root, relative).read_text(encoding='utf-8')
        if page_info(text).get('status', 'active') != 'active':
            continue
        text = re.sub(r'\A---\n.*?\n---\n', '', text, count=1, flags=re.S)
        for number, (heading, body) in enumerate(sections(text), 1):
            score = len(terms & set(re.findall(r'\w+', heading.lower() + ' ' + body.lower())))
            if score:
                candidates.append((score + 1, {'path': relative}, number, heading, body))
    candidates.sort(key=lambda row: (-row[0], row[1]['path'], row[2]))
    output = []
    used = 0
    for _, record, number, heading, body in candidates:
        prefix = '\n[source:' + record['path'] + '#section-' + str(number) + '] ' + heading + '\n'
        room = budget - used - len(prefix.encode('utf-8'))
        if room < 40:
            continue
        excerpt = body.encode('utf-8')[:room].decode('utf-8', errors='ignore')
        chunk = prefix + excerpt
        output.append(chunk)
        used += len(chunk.encode('utf-8'))
        if len(output) == 3:
            break
    return ''.join(output) if output else 'No permitted matching evidence. Report this gap.\n'


def proposal(root, topic, file, sources, summary=None, review_days=None):
    slug(topic)
    body = Path(file).read_text(encoding='utf-8')
    target = 'wiki/' + topic + '.md'
    change = new_change(root, target, body, sources, summary, review_days=review_days)
    return make_packet(root, change, 'synthesize')


def packet_path(root, packet_id):
    slug(packet_id)
    packet = safe(root, 'reviews/' + packet_id)
    for name in ('proposal.json', 'decision.json', 'before.md', 'after.md', 'before-files.json', 'apply-journal.json', 'receipt.json'):
        safe(root, 'reviews/' + packet_id + '/' + name)
    return packet


def approve(root, packet_id, by):
    """Record an already explicit human decision; this function is not authentication."""
    packet = packet_path(root, packet_id)
    proposal_data = (packet / 'proposal.json').read_bytes()
    payload = json.loads(proposal_data)
    validate_proposal(root, payload)
    before, after = packet_previews(root, payload, check_current=False)
    if (packet / 'after.md').read_text(encoding='utf-8') != after:
        raise ValueError('Preview differs from the proposal. Prepare a new proposal')
    # Stored before previews are checked against every target hash, not today's file.
    if payload.get('version') == 1:
        preview = (packet / 'before.md').read_bytes()
        if (digest(preview) if payload['before_sha256'] is not None else None) != payload['before_sha256']:
            raise ValueError('Before preview differs from the proposal')
    else:
        saved = read_json(packet / 'before-files.json')
        if set(saved) != {c['target'] for c in changes_in(payload)}:
            raise ValueError('Before preview paths differ from the proposal')
        for change in changes_in(payload):
            old = saved[change['target']]
            if (digest(old.encode()) if old is not None else None) != change['before_sha256']:
                raise ValueError('Before preview differs from the proposal')
        expected = preview_files(saved)
        if (packet / 'before.md').read_text(encoding='utf-8') != expected:
            raise ValueError('Before preview differs from the proposal')
    if not by.strip():
        raise ValueError('Record the human decision maker')
    atomic(packet / 'decision.json', encode({'status': 'approved', 'by': by,
            'recorded_at': stamp(), 'proposal_sha256': digest(proposal_data)}))
    print('Recorded approval attribution for', packet_id)


def validate_proposal(root, payload):
    checked_records = source_records(root)
    records = {r['path']: r for r in checked_records}
    latest = {r['id']: r['path'] for r in checked_records}
    changes = changes_in(payload)
    targets = {c['target'] for c in changes}
    if len(targets) != len(changes):
        raise ValueError('Duplicate proposal targets')
    for change in changes:
        target = change['target']
        topic_path(target)
        if not change['body'].strip() or len(change['body'].split()) > 400:
            raise ValueError('Topic body must contain 1 to 400 words')
        if change.get('status', 'active') == 'active' and any(s in records and latest[records[s]['id']] != s for s in change['sources']):
            raise ValueError('Proposal cites superseded evidence. Reconcile before approval or apply')
        if not change['sources'] or any(s not in records or s not in change['body'] for s in change['sources']):
            raise ValueError('Proposal lacks valid evidence citations')
        if change.get('status', 'active') not in ('active', 'retired', 'redirect'):
            raise ValueError('Invalid topic status')
        summary_text(change.get('summary') or auto_summary(change['body']))
        cadence = change.get('review_days', 30)
        if not isinstance(cadence, int) or not 0 <= cadence <= 36500:
            raise ValueError('Review cadence must be 0 to 36500 days')
        for link in re.findall(r'\[\[([^\]]+)\]\]', change['body']):
            linked = 'wiki/' + slug(link) + '.md'
            if linked not in targets and not safe(root, linked).is_file():
                raise ValueError('Broken wiki link: ' + link)
        redirect = change.get('redirect')
        if change.get('status') == 'redirect' and not redirect:
            raise ValueError('Redirect requires a destination')
        if redirect:
            linked = 'wiki/' + slug(redirect) + '.md'
            if linked == target or (linked not in targets and not safe(root, linked).is_file()):
                raise ValueError('Invalid redirect destination')
            target_change = next((c for c in changes if c['target'] == linked), None)
            destination = target_change or page_info(safe(root, linked).read_text(encoding='utf-8'))
            if destination.get('status', 'active') != 'active':
                raise ValueError('Redirect must point directly to an active topic')
    return records


def apply(root, packet_id):
    packet = packet_path(root, packet_id)
    raw = (packet / 'proposal.json').read_bytes()
    payload = json.loads(raw)
    decision = read_json(packet / 'decision.json')
    if decision.get('status') != 'approved' or decision.get('proposal_sha256') != digest(raw):
        raise ValueError('Approval is missing or proposal changed')
    records = validate_proposal(root, payload)
    journal_path, receipt_path = packet / 'apply-journal.json', packet / 'receipt.json'
    no_pending(root, except_journal=journal_path)
    if not journal_path.exists():
        if payload.get('wiki_snapshot') is not None and wiki_snapshot(root) != payload['wiki_snapshot']:
            raise ValueError('Wiki changed since lifecycle proposal. Prepare a new proposal')
        values = {}
        for change in changes_in(payload):
            target = safe(root, change['target'])
            current = target.read_bytes() if target.exists() else None
            if (digest(current) if current is not None else None) != change['before_sha256']:
                raise ValueError('Target changed since proposal. Prepare a new proposal')
            values[change['target']] = render_page(change, payload['created_at'][:10], records, payload.get('version') == 1)
        pages = read_pages(root)
        pages.update(values)
        values['index.md'] = catalog_text(pages)
        deps = read_json(safe(root, '.brain/page-deps.json'))
        for change in changes_in(payload):
            deps[change['target']] = change['sources']
        values['.brain/page-deps.json'] = encode(deps).decode()
        action = payload.get('action', 'synthesize')
        values['log.md'] = safe(root, 'log.md').read_text(encoding='utf-8') + '\n## [' + payload['created_at'][:10] + '] ' + action + ' | ' + payload['target'] + ' | ' + packet_id + '\n'
        prepare_transaction(root, journal_path, {'kind': 'apply', 'proposal_sha256': digest(raw)}, values)
    journal = read_json(journal_path)
    expected_paths = {c['target'] for c in changes_in(payload)} | {'index.md', '.brain/page-deps.json', 'log.md'}
    if journal.get('proposal_sha256') != digest(raw) or {c['path'] for c in journal['changes']} != expected_paths:
        raise ValueError('Apply journal refers to a different proposal or paths')
    for change in changes_in(payload):
        saved = next(c['after'] for c in journal['changes'] if c['path'] == change['target'])
        reconciled = page_info(saved).get('last_reconciled', payload['created_at'][:10]) if payload.get('version') == 1 else payload['created_at'][:10]
        date.fromisoformat(reconciled)
        if saved != render_page(change, reconciled, records, payload.get('version') == 1):
            raise ValueError('Journal topic differs from the approved proposal')
    run_transaction(root, journal_path, receipt_path)
    print('Applied:', payload['target'])


def review(root, period, processor='local'):
    no_pending(root)
    slug(period)
    folder = safe(root, 'reviews/' + period)
    if folder.exists():
        raise ValueError('Review already exists. Resume its saved files')
    folder.mkdir()
    registry = permitted_records(root, processor)
    delta = '# Evidence coverage\n\nRecord reporting window, baseline, changed results, owners and missing sources.\n\n'
    delta += ''.join('- ' + r['path'] + ' | ' + r['observed_at'] + ' | ' + r['processor'] + '\n' for r in registry)
    atomic(folder / 'delta.md', delta.encode())
    for role in ROLES:
        prompt = (ROOT / 'agents' / (role + '.md')).read_text(encoding='utf-8')
        atomic(folder / (role + '.md'), ('# Pending ' + role + ' review\n\n' + prompt).encode())
    atomic(folder / 'run-state.json', encode({'phase': 'research', 'started_at': stamp(), 'completed_roles': [],
        'next': 'Run research first, domain roles next, coordinator last. See docs/reviews.md'}))
    print('Prepared review:', folder)


def health(root, processor='local'):
    findings = health_findings(root, processor)
    print(json.dumps({'findings': findings, 'observed_at': stamp()}, indent=2))
    return findings


def load_registry(root):
    records = read_json(safe(root, '.brain/sources.json'))
    if not isinstance(records, list):
        raise ValueError('Invalid source registry')
    for record in records:
        slug(record['id'])
        revision = record['sha256']
        if not isinstance(revision, str) or not re.fullmatch(r'[0-9a-f]{64}', revision):
            raise ValueError('Invalid source revision')
        prefix = 'raw-local/' + record['id'] + '/' + revision
        if record['path'] not in {prefix + suffix for suffix in ('.md', '.txt', '.csv', '.json')}:
            raise ValueError('Invalid source storage path')
        if record['processor'] not in ('local-only', 'external-ok'):
            raise ValueError('Invalid source processor policy')
        datetime.fromisoformat(record['observed_at'])
    return records


def pending_transactions(root):
    journals = list(safe(root, 'reviews').glob('*/apply-journal.json'))
    journals += list(safe(root, '.brain').glob('imports/*/journal.json'))
    return [p for p in journals if not safe(root, p.relative_to(root).as_posix()).with_name('receipt.json').exists()]


def no_pending(root, except_journal=None):
    if any(p != except_journal for p in pending_transactions(root)):
        raise ValueError('Interrupted transaction found. Run recover before reading or changing knowledge')


def prepare_transaction(root, journal_path, metadata, values):
    changes = []
    for relative, after in values.items():
        dest = safe(root, relative)
        before = dest.read_bytes() if dest.exists() else None
        changes.append({'path': relative, 'before_sha256': digest(before) if before is not None else None,
                        'after': after})
    journal = dict(metadata, journal_version=2, changes=changes)
    journal['checksum'] = digest(encode(journal))
    atomic(journal_path, encode(journal))


def verify_journal(journal):
    if journal.get('journal_version') == 2:
        core = {key: value for key, value in journal.items() if key != 'checksum'}
        if journal.get('checksum') != digest(encode(core)):
            raise ValueError('Transaction journal integrity failed')


def run_transaction(root, journal_path, receipt_path):
    raw = journal_path.read_bytes()
    journal = json.loads(raw)
    verify_journal(journal)
    paths = [c['path'] for c in journal['changes']]
    if len(set(paths)) != len(paths):
        raise ValueError('Duplicate transaction paths')
    if journal.get('kind') == 'import' and set(paths) != {'.brain/sources.json', 'log.md'}:
        raise ValueError('Unexpected import transaction paths')
    if receipt_path.exists():
        receipt = read_json(receipt_path)
        if receipt.get('journal_sha256', digest(raw)) != digest(raw):
            raise ValueError('Completed transaction journal changed')
        if receipt.get('files') != {c['path']: digest(c['after'].encode()) for c in journal['changes']}:
            raise ValueError('Receipt differs from transaction')
        if any(not safe(root, name).is_file() or digest(safe(root, name).read_bytes()) != sha
               for name, sha in receipt['files'].items()):
            raise ValueError('Later changes conflict with this completed transaction')
        return
    for change in journal['changes']:
        path = safe(root, change['path'])
        current = digest(path.read_bytes()) if path.exists() else None
        if current not in (change['before_sha256'], digest(change['after'].encode())):
            raise ValueError('Concurrent edit conflicts with transaction: ' + change['path'])
    for change in journal['changes']:
        atomic(safe(root, change['path']), change['after'].encode())
    atomic(receipt_path, encode({'completed_at': stamp(), 'proposal_sha256': journal.get('proposal_sha256'),
        'journal_sha256': digest(raw), 'files': {c['path']: digest(c['after'].encode()) for c in journal['changes']}}))


def settings(root, mode=None, confirm=False, topic_days=None):
    value = read_json(safe(root, 'settings.json'))
    if mode is not None:
        if not confirm:
            raise ValueError('Confirm the owner-selected data policy with --confirm-data-policy')
        value.update(processor_mode=mode, external_processors_enabled=(mode == 'external'))
    if topic_days is not None:
        if not 0 <= topic_days <= 36500:
            raise ValueError('Review cadence must be 0 to 36500 days')
        value['topic_review_days'] = topic_days
    if mode is not None or topic_days is not None:
        no_pending(root)
        atomic(safe(root, 'settings.json'), encode(value))
    print(json.dumps(value, indent=2))
    return value


def selected_processor(root, requested=None):
    value = read_json(safe(root, 'settings.json'))
    mode = value.get('processor_mode', 'unset')
    if mode not in ('local', 'external'):
        raise ValueError('Choose the permitted processor first: settings --processor local --confirm-data-policy, or settings --allow-cloud --confirm-data-policy for an owner-approved cloud workspace')
    if requested and requested != mode:
        raise ValueError('Processor flag differs from this workspace policy. Use a separately configured workspace')
    if mode == 'external' and not value.get('external_processors_enabled'):
        raise ValueError('External processing is disabled. After owner permission, run settings --allow-cloud --confirm-data-policy')
    return mode


def topic_path(relative):
    if not re.fullmatch(r'wiki/[a-z0-9]+(?:-[a-z0-9]+)*\.md', relative):
        raise ValueError('Invalid topic path')
    return relative


def summary_text(value):
    if not isinstance(value, str) or not value.strip() or '\n' in value or len(value) > 240:
        raise ValueError('Summary must be one nonempty line of at most 240 characters')
    return value.strip()


def auto_summary(body):
    for line in body.splitlines():
        if line.strip():
            return line.lstrip('# ').strip()[:240]
    return 'Reviewed topic'


def page_info(text):
    result = {'body': text, 'sources': [], 'status': 'active'}
    match = re.match(r'\A---\n(.*?)\n---\n', text, re.S)
    if not match:
        return result
    result['body'] = text[match.end():]
    in_sources = False
    for line in match.group(1).splitlines():
        if line.startswith('  - ') and in_sources:
            result['sources'].append(line[4:])
        elif ':' in line:
            key, value = line.split(':', 1)
            in_sources = key == 'sources'
            if in_sources:
                continue
            value = value.strip()
            if value.startswith('"'):
                value = json.loads(value)
            if key == 'review_days':
                value = int(value)
            result[key] = value
    return result


def read_pages(root):
    pages = {}
    for path in safe(root, 'wiki').glob('*.md'):
        relative = path.relative_to(root).as_posix()
        topic_path(relative)
        pages[relative] = safe(root, relative).read_text(encoding='utf-8')
    return pages


def wiki_snapshot(root):
    return {name: digest(text.encode()) for name, text in sorted(read_pages(root).items())}


def catalog_text(pages):
    lines = ['# Knowledge index', '', 'Private catalog: use the catalog command for processor-filtered output.', '']
    for name, text in sorted(pages.items()):
        info = page_info(text)
        summary = summary_text(info.get('summary') or auto_summary(info['body']))
        status = info.get('status', 'active')
        suffix = '' if status == 'active' else ' (' + status + ')'
        lines.append('- [[' + Path(name).stem + ']] — ' + summary + suffix)
    return '\n'.join(lines) + '\n'


def permitted_records(root, processor):
    if processor == 'external' and not read_json(safe(root, 'settings.json')).get('external_processors_enabled'):
        raise ValueError('External processing is disabled. Use settings after owner permission')
    records = load_registry(root)
    latest = {r['id']: r['path'] for r in records}
    return [r for r in records if latest[r['id']] == r['path'] and
            (processor == 'local' or r['processor'] == 'external-ok')]


def permitted_pages(root, processor):
    available = load_registry(root) if processor == 'local' else permitted_records(root, processor)
    records = {r['path']: r for r in available}
    pages = {}
    for relative, sources in read_json(safe(root, '.brain/page-deps.json')).items():
        topic_path(relative)
        if not sources or any(s not in records for s in sources):
            continue
        path = safe(root, relative)
        if path.is_file():
            pages[relative] = path.read_text(encoding='utf-8')
    return pages


def catalog(root, processor):
    no_pending(root)
    return catalog_text(permitted_pages(root, processor))


def changes_in(payload):
    return [payload] + payload.get('additional', [])


def new_change(root, target, body, sources, summary=None, status='active', redirect=None, review_days=None):
    topic_path(target)
    path = safe(root, target)
    cadence = read_json(safe(root, 'settings.json')).get('topic_review_days', 30) if review_days is None else review_days
    return {'target': target, 'before_sha256': digest(path.read_bytes()) if path.exists() else None,
            'body': body, 'sources': sorted(set(sources)), 'summary': summary_text(summary or auto_summary(body)),
            'status': status, 'redirect': redirect, 'review_days': cadence}


def render_page(change, reconciled, records, legacy=False):
    processor = 'external-ok' if all(records[s]['processor'] == 'external-ok' for s in change['sources']) else 'local-only'
    if legacy:
        return ('---\ntype: topic\nprocessor: ' + processor + '\nlast_reconciled: ' + reconciled +
                '\nsources:\n' + ''.join('  - ' + item + '\n' for item in change['sources']) + '---\n' + change['body'])
    summary = summary_text(change.get('summary') or auto_summary(change['body']))
    page = ('---\ntype: topic\nprocessor: ' + processor + '\nstatus: ' + change.get('status', 'active') +
            '\nsummary: ' + json.dumps(summary, ensure_ascii=False) + '\nlast_reconciled: ' + reconciled +
            '\nreview_days: ' + str(change.get('review_days', 30)) + '\n')
    if change.get('redirect'):
        page += 'redirect: ' + change['redirect'] + '\n'
    return page + 'sources:\n' + ''.join('  - ' + s + '\n' for s in change['sources']) + '---\n' + change['body']


def preview_files(values):
    return '\n'.join('## ' + name + '\n\n' + (text if text is not None else '(new file)\n')
                     for name, text in sorted(values.items()))


def packet_previews(root, payload, check_current=True):
    if payload.get('version') == 1:
        path = safe(root, payload['target'])
        return path.read_text(encoding='utf-8') if path.exists() else '', payload['body']
    records = {r['path']: r for r in load_registry(root)}
    before, after = {}, {}
    for change in changes_in(payload):
        path = safe(root, change['target'])
        if check_current:
            before[change['target']] = path.read_text(encoding='utf-8') if path.exists() else None
        after[change['target']] = render_page(change, payload['created_at'][:10], records)
    return preview_files(before), preview_files(after)


def make_packet(root, change, action, additional=None, snapshot=None):
    no_pending(root)
    payload = dict(change, version=2, action=action, created_at=stamp(), additional=additional or [])
    if snapshot is not None:
        payload['wiki_snapshot'] = snapshot
    validate_proposal(root, payload)
    packet_id = Path(change['target']).stem + '-' + digest(encode(payload))[:12]
    packet = safe(root, 'reviews/' + packet_id)
    packet.mkdir()
    before, after = packet_previews(root, payload)
    before_files = {}
    for item in changes_in(payload):
        path = safe(root, item['target'])
        before_files[item['target']] = path.read_text(encoding='utf-8') if path.exists() else None
    atomic(packet / 'proposal.json', encode(payload))
    atomic(packet / 'decision.json', encode({'status': 'pending', 'proposal_sha256': digest(encode(payload))}))
    atomic(packet / 'before-files.json', encode(before_files))
    atomic(packet / 'before.md', before.encode())
    atomic(packet / 'after.md', after.encode())
    print(packet_id)
    return packet_id


def lifecycle(root, action, topic, destination=None, file=None, summary=None, reason=None):
    slug(topic)
    pages = read_pages(root)
    target = 'wiki/' + topic + '.md'
    if target not in pages or page_info(pages[target]).get('status', 'active') != 'active':
        raise ValueError('Choose an existing active topic')
    original = page_info(pages[target])
    additional = []
    if action in ('rename', 'merge'):
        slug(destination)
        dest = 'wiki/' + destination + '.md'
        if target == dest:
            raise ValueError('Choose a different destination')
        if action == 'rename':
            if dest in pages:
                raise ValueError('Rename destination already exists')
            dest_info = original
        else:
            if dest not in pages or page_info(pages[dest]).get('status', 'active') != 'active':
                raise ValueError('Merge destination must be an active topic')
            dest_info = page_info(pages[dest])
        sources = sorted(set(original['sources'] + dest_info['sources']))
        body = Path(file).read_text(encoding='utf-8') if action == 'merge' else original['body']
        body = body.replace('[[' + topic + ']]', '[[' + destination + ']]')
        additional.append(new_change(root, dest, body, sources, summary or dest_info.get('summary'),
                                     review_days=dest_info.get('review_days', 30)))
        # Redirects retain old evidence and never erase the original decision history.
        redirect_body = '# Moved topic\n\nSee [[' + destination + ']].\n\n' + '\n'.join('Source: ' + s for s in sources) + '\n'
        first = new_change(root, target, redirect_body, sources, 'Moved to ' + destination, 'redirect', destination, 0)
        for name, text in pages.items():
            if name in (target, dest):
                continue
            info = page_info(text)
            if '[[' + topic + ']]' in info['body'] or info.get('redirect') == topic:
                updated = info['body'].replace('[[' + topic + ']]', '[[' + destination + ']]')
                additional.append(new_change(root, name, updated, info['sources'], info.get('summary'),
                    info.get('status', 'active'), destination if info.get('redirect') == topic else info.get('redirect'), info.get('review_days', 30)))
    elif action == 'retire':
        if not reason or not reason.strip():
            raise ValueError('Retirement needs an explicit --reason')
        body = original['body'] + '\n\nRetired: ' + reason.strip() + '\n'
        first = new_change(root, target, body, original['sources'], original.get('summary'), 'retired', review_days=0)
    else:
        raise ValueError('Unsupported lifecycle action')
    return make_packet(root, first, action, additional, wiki_snapshot(root))


def guard_packet(root, packet_id, processor):
    payload = read_json(packet_path(root, packet_id) / 'proposal.json')
    allowed_records = load_registry(root) if processor == 'local' else permitted_records(root, processor)
    allowed = {r['path'] for r in allowed_records}
    if any(source not in allowed for change in changes_in(payload) for source in change['sources']):
        raise ValueError('Packet depends on unavailable or restricted evidence. Use its permitted workspace and processor')
    return payload


def show_packet(root, packet_id):
    packet = packet_path(root, packet_id)
    return ''.join(difflib.unified_diff((packet / 'before.md').read_text(encoding='utf-8').splitlines(True),
        (packet / 'after.md').read_text(encoding='utf-8').splitlines(True), fromfile='before', tofile='after'))


def health_findings(root, processor='local'):
    no_pending(root)
    findings = []
    records = permitted_records(root, processor)
    current_paths = {r['path'] for r in records}
    for record in records:
        if digest(safe(root, record['path']).read_bytes()) != record['sha256']:
            findings.append('Source integrity failed: ' + record['id'])
        cadence = record.get('refresh_days', 0)
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(record['observed_at'])).days
        if cadence and age > cadence:
            findings.append('Source refresh due: ' + record['id'] + ' imported ' + record['observed_at'])
    pages = read_pages(root) if processor == 'local' else permitted_pages(root, processor)
    deps = read_json(safe(root, '.brain/page-deps.json'))
    active = {name for name, text in pages.items() if page_info(text).get('status', 'active') == 'active'}
    incoming = {name: set() for name in active}
    for name, text in pages.items():
        info = page_info(text)
        paths = deps.get(name)
        if not paths:
            findings.append('Topic missing dependencies: ' + name)
        elif info.get('status', 'active') == 'active' and any(path not in current_paths for path in paths):
            findings.append('Topic needs source reconciliation: ' + name)
        if paths is not None and sorted(paths) != sorted(info['sources']):
            findings.append('Topic dependency metadata differs: ' + name)
        if name in active:
            cadence = int(info.get('review_days', read_json(safe(root, 'settings.json')).get('topic_review_days', 30)))
            reconciled = info.get('last_reconciled')
            if not reconciled:
                findings.append('Topic missing reconciliation date: ' + name)
            elif cadence and (date.today() - date.fromisoformat(reconciled)).days > cadence:
                findings.append('Topic review due: ' + name + ' last reconciled ' + reconciled)
        for link in re.findall(r'\[\[([^\]]+)\]\]', info['body']):
            linked = 'wiki/' + slug(link) + '.md'
            if not safe(root, linked).is_file():
                findings.append('Broken link: ' + link)
            elif linked in incoming and name != linked:
                incoming[linked].add(name)
            if linked in pages and page_info(pages[linked]).get('status') == 'retired':
                findings.append('Link points to retired topic: ' + name + ' -> ' + link)
    if len(active) > 1:
        findings += ['Unlinked topic: ' + name for name in sorted(active) if not incoming[name]]
    if processor == 'local':
        if safe(root, 'index.md').read_text(encoding='utf-8') != catalog_text(pages) and pages:
            findings.append('Catalog differs from topic files; propose reviewed repairs')
        findings += ['Dependency points to missing topic: ' + name for name in deps if name not in pages]
    for path in safe(root, 'reviews').glob('*/decision.json'):
        safe(root, path.relative_to(root).as_posix())
        if read_json(path).get('status') == 'pending':
            try:
                guard_packet(root, path.parent.name, processor)
            except ValueError:
                continue
            findings.append('Awaiting human decision: ' + path.parent.name)
    return findings


def brief(root, processor, save=False):
    findings = health_findings(root, processor)
    text = '# Daily review — ' + date.today().isoformat() + '\n\n'
    text += 'Generated status scaffold; the agent and human supply evidence-based priorities.\n\n'
    text += '## Needs attention\n\n' + ('\n'.join('- ' + f for f in findings) if findings else 'No automated findings in the permitted evidence.') + '\n\n'
    text += '## Up to three priorities\n\nFor each: evidence/date, owner, next action, completion evidence and next review.\n'
    if save:
        atomic(safe(root, 'daily/' + date.today().isoformat() + '-status.md'), text.encode())
    return text


def recover(root):
    for journal in pending_transactions(root):
        if journal.name == 'apply-journal.json':
            apply(root, journal.parent.name)
        else:
            run_transaction(root, journal, journal.with_name('receipt.json'))
    print('No interrupted transactions remain')


def rebuild(root, destination):
    """Reconstruct approved state from completed journals, without altering the source."""
    no_pending(root)
    records = source_records(root)
    events = []
    journals = list(safe(root, 'reviews').glob('*/apply-journal.json')) + list(safe(root, '.brain').glob('imports/*/journal.json'))
    for journal in journals:
        safe(root, journal.relative_to(root).as_posix())
        receipt_path = safe(root, journal.with_name('receipt.json').relative_to(root).as_posix())
        receipt = read_json(receipt_path)
        raw = journal.read_bytes()
        data = json.loads(raw)
        verify_journal(data)
        if receipt.get('journal_sha256', digest(raw)) != digest(raw):
            raise ValueError('Rebuild journal integrity failed')
        if receipt['files'] != {c['path']: digest(c['after'].encode()) for c in data['changes']}:
            raise ValueError('Rebuild receipt differs from journal')
        if journal.name == 'apply-journal.json':
            packet = journal.parent
            payload_raw = (packet / 'proposal.json').read_bytes()
            decision = read_json(packet / 'decision.json')
            if decision.get('status') != 'approved' or decision.get('proposal_sha256') != digest(payload_raw):
                raise ValueError('Rebuild requires retained matching approval decisions')
            payload = json.loads(payload_raw)
            expected = {c['target'] for c in changes_in(payload)} | {'index.md', '.brain/page-deps.json', 'log.md'}
            if data.get('proposal_sha256') != digest(payload_raw) or {c['path'] for c in data['changes']} != expected:
                raise ValueError('Rebuild apply paths differ from approved proposal')
        elif {c['path'] for c in data['changes']} != {'.brain/sources.json', 'log.md'}:
            raise ValueError('Unexpected rebuild import paths')
        events.append((receipt.get('completed_at', receipt.get('applied_at', '')), journal.as_posix(), data))
    imported = {event[2].get('source') for event in events if event[2].get('kind') == 'import'}
    legacy = [r for r in records if r['path'] not in imported]
    state = {'index.md': '# Knowledge index\n\nAdd reviewed topics through a proposal.\n',
             'log.md': '# Change log\n', '.brain/page-deps.json': encode({}).decode(), '.brain/sources.json': encode(legacy).decode()}
    for _, _, event in sorted(events):
        for change in event['changes']:
            path = change['path']
            safe(root, path)
            before = state.get(path)
            if (digest(before.encode()) if before is not None else None) != change['before_sha256']:
                raise ValueError('Rebuild history is incomplete or out of order: ' + path)
            state[path] = change['after']
    # Refuse to silently bless manual edits or silently drop uncaptured topic files.
    if set(read_pages(root)) != {name for name in state if name.startswith('wiki/')}:
        raise ValueError('Rebuild found topic files without retained apply history')
    for path, content in state.items():
        if safe(root, path).read_bytes() != content.encode():
            raise ValueError('Rebuild differs from current state; retain backups and review: ' + path)
    target = Path(destination).expanduser().resolve()
    if target == root or root in target.parents or target in root.parents:
        raise ValueError('Rebuild destination must be outside the source workspace')
    if target.exists() and any(target.iterdir()):
        raise ValueError('Rebuild destination must be empty')
    init(target)
    marker = target / '.brain/rebuild-in-progress'
    atomic(marker, b'Incomplete reconstruction\n')
    for record in records:
        atomic(safe(target, record['path']), safe(root, record['path']).read_bytes())
    for path, content in state.items():
        atomic(safe(target, path), content.encode())
    for prefix in ('reviews', '.brain/imports'):
        origin = safe(root, prefix)
        if origin.exists():
            for path in origin.rglob('*'):
                relative = path.relative_to(root).as_posix()
                safe(root, relative)
                if path.is_file():
                    atomic(safe(target, relative), path.read_bytes())
    atomic(target / 'settings.json', safe(root, 'settings.json').read_bytes())
    marker.unlink()
    print('Rebuilt approved state. Daily notes and other untracked working drafts require your backup:', target)
    return target


def main(argv=None):
    # Redirected Windows streams may otherwise use an ANSI code page.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', default=str(ROOT / 'workspace'))
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    sub.add_parser('doctor')
    config = sub.add_parser('settings')
    mode = config.add_mutually_exclusive_group()
    mode.add_argument('--processor', choices=['local', 'external'])
    mode.add_argument('--allow-cloud', action='store_true')
    mode.add_argument('--disable-cloud', action='store_true')
    config.add_argument('--confirm-data-policy', action='store_true')
    config.add_argument('--topic-review-days', type=int)
    imp = sub.add_parser('import')
    imp.add_argument('file')
    imp.add_argument('--id', required=True)
    imp.add_argument('--processor', choices=['local-only', 'external-ok'], default='local-only')
    imp.add_argument('--refresh-days', type=int, default=0)
    get = sub.add_parser('query')
    get.add_argument('query')
    get.add_argument('--processor', choices=['local', 'external'])
    get.add_argument('--budget-bytes', type=int, default=6000)
    sub.add_parser('catalog')
    prop = sub.add_parser('propose')
    prop.add_argument('topic')
    prop.add_argument('--file', required=True)
    prop.add_argument('--source', action='append', required=True)
    prop.add_argument('--summary')
    prop.add_argument('--review-days', type=int)
    for command in ('retire', 'rename', 'merge'):
        item = sub.add_parser(command)
        item.add_argument('topic')
        if command == 'retire':
            item.add_argument('--reason', required=True)
        else:
            item.add_argument('--into', required=True)
            item.add_argument('--summary')
        if command == 'merge':
            item.add_argument('--file', required=True)
    show = sub.add_parser('show')
    show.add_argument('packet')
    decision = sub.add_parser('approve')
    decision.add_argument('packet')
    decision.add_argument('--by', required=True)
    decision.add_argument('--confirm', help='Exact packet ID, only after explicit human approval of its shown diff')
    app = sub.add_parser('apply')
    app.add_argument('packet')
    rev = sub.add_parser('review')
    rev.add_argument('period')
    sub.add_parser('health')
    daily = sub.add_parser('brief')
    daily.add_argument('--save', action='store_true')
    sub.add_parser('recover')
    restore = sub.add_parser('rebuild')
    restore.add_argument('--to', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'doctor':
            print('Python', sys.version.split()[0], '| offline core | zero third-party dependencies')
            return 0
        if args.command == 'init':
            init(args.workspace)
            return 0
        root = workspace(args.workspace)
        with locked(root):
            if args.command == 'settings':
                choice = 'external' if args.allow_cloud else 'local' if args.disable_cloud else args.processor
                settings(root, choice, args.confirm_data_policy, args.topic_review_days)
                return 0
            processor = selected_processor(root, args.processor if args.command == 'query' else None)
            if args.command not in ('recover', 'import', 'apply'):
                no_pending(root)
            if args.command == 'query':
                print(retrieve(root, args.query, processor, args.budget_bytes), end='')
            elif args.command == 'catalog':
                print(catalog(root, processor), end='')
            elif args.command == 'health':
                health(root, processor)
            elif args.command == 'brief':
                print(brief(root, processor, args.save), end='')
            elif args.command == 'import':
                if processor == 'external' and args.processor != 'external-ok':
                    raise ValueError('Cloud workspaces import only sources explicitly approved with --processor external-ok')
                import_source(root, args.file, args.id, args.processor, args.refresh_days)
            elif args.command == 'propose':
                allowed = {r['path'] for r in permitted_records(root, processor)}
                if any(source not in allowed for source in args.source):
                    raise ValueError('Proposal sources are unavailable or restricted for this workspace processor')
                proposal(root, args.topic, args.file, args.source, args.summary, args.review_days)
            elif args.command in ('retire', 'rename', 'merge'):
                # Lifecycle operations inspect inbound links across the entire wiki.
                topic_files = {p.relative_to(root).as_posix() for p in safe(root, 'wiki').glob('*.md')}
                if processor == 'external' and set(permitted_pages(root, processor)) != topic_files:
                    raise ValueError('Lifecycle needs a fully permitted wiki; use its approved local workspace')
                lifecycle(root, args.command, args.topic, getattr(args, 'into', None),
                          getattr(args, 'file', None), getattr(args, 'summary', None), getattr(args, 'reason', None))
            elif args.command in ('show', 'approve', 'apply'):
                guard_packet(root, args.packet, processor)
                if args.command == 'show':
                    print(show_packet(root, args.packet), end='')
                elif args.command == 'approve':
                    print(show_packet(root, args.packet), end='')
                    print('This records attribution, not human authentication. Confirm only an explicit human decision.')
                    confirmation = args.confirm
                    if confirmation is None:
                        if not sys.stdin.isatty():
                            raise ValueError('Review with show, then have the human confirm in a terminal or explicitly authorize --confirm PACKET-ID')
                        confirmation = input('Type the exact packet ID to record approval: ')
                    if confirmation != args.packet:
                        raise ValueError('Confirmation did not match the packet ID')
                    approve(root, args.packet, args.by)
                else:
                    apply(root, args.packet)
            elif args.command == 'review':
                review(root, args.period, processor)
            elif args.command == 'recover':
                # Recovery may inspect transaction outputs; all sources must be permitted.
                all_records = load_registry(root)
                if processor == 'external' and any(r['processor'] != 'external-ok' for r in all_records):
                    raise ValueError('Recover this mixed workspace with its approved local processor')
                recover(root)
            elif args.command == 'rebuild':
                records = load_registry(root)
                if processor == 'external' and any(r['processor'] != 'external-ok' for r in records):
                    raise ValueError('Rebuild this mixed workspace with its approved local processor')
                rebuild(root, args.to)
        return 0
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        # Do not echo file contents or credentials in diagnostics.
        print('Error:', type(error).__name__, str(error) if isinstance(error, ValueError) else 'Check workspace files and permissions', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
