"""Release regressions for onboarding, crash safety, maintenance and restoration."""
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import brain


class ReleaseWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'instance'
        self.quiet(brain.init, self.root)
        self.source = self.base / 'source.txt'
        self.source.write_text('# Retention\nClients renewed after a scope review.\n', encoding='utf-8')
        self.quiet(brain.import_source, self.root, self.source, 'interview', 'external-ok')
        self.path = brain.source_records(self.root)[0]['path']

    def quiet(self, func, *args, **kwargs):
        with redirect_stdout(io.StringIO()):
            return func(*args, **kwargs)

    def cli(self, *args, ok=True):
        run = subprocess.run([sys.executable, str(brain.ROOT / 'brain.py'), '--workspace', str(self.root), *args],
                             capture_output=True, text=True, encoding='utf-8', stdin=subprocess.DEVNULL)
        self.assertEqual(run.returncode, 0 if ok else 1, run.stdout + run.stderr)
        return run

    def topic(self, name='retention', body=None, sources=None, summary='Renewal evidence and open questions'):
        draft = self.base / (name + '-draft.md')
        draft.write_text(body or '# Retention\nClients renewed. Source: ' + self.path + '\n', encoding='utf-8')
        packet = self.quiet(brain.proposal, self.root, name, draft, sources or [self.path], summary)
        self.quiet(brain.approve, self.root, packet, 'Fictional reviewer')
        self.quiet(brain.apply, self.root, packet)
        return packet

    def apply_packet(self, packet):
        self.quiet(brain.approve, self.root, packet, 'Fictional reviewer')
        self.quiet(brain.apply, self.root, packet)

    def test_first_use_requires_owner_data_policy_with_exact_command(self):
        result = self.cli('query', 'retention', ok=False)
        self.assertIn('--confirm-data-policy', result.stderr)
        self.cli('settings', '--allow-cloud', ok=False)
        self.cli('settings', '--allow-cloud', '--confirm-data-policy')
        self.assertIn('Clients renewed', self.cli('query', 'retention').stdout)
        self.cli('query', 'retention', '--processor', 'local', ok=False)

    def test_cloud_import_denied_before_reading_local_file(self):
        self.cli('settings', '--allow-cloud', '--confirm-data-policy')
        result = self.cli('import', str(self.base / 'missing.txt'), '--id', 'private', ok=False)
        self.assertIn('--processor external-ok', result.stderr)
        self.assertNotIn('ordinary UTF', result.stderr)

    def test_cli_emits_utf8_even_with_an_ansi_pipe_default(self):
        self.cli('settings', '--allow-cloud', '--confirm-data-policy')
        self.source.write_text('# Renewal\n客户 renewed — fictional evidence.\n', encoding='utf-8')
        self.cli('import', str(self.source), '--id', 'unicode', '--processor', 'external-ok')
        env = dict(os.environ, PYTHONIOENCODING='cp1252')
        run = subprocess.run([sys.executable, str(brain.ROOT / 'brain.py'), '--workspace', str(self.root),
                              'query', 'renewed'], capture_output=True, encoding='utf-8', env=env)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('客户 renewed — fictional evidence', run.stdout)

    def test_local_cli_policy_works_without_cloud_opt_in(self):
        self.cli('settings', '--processor', 'local', '--confirm-data-policy')
        self.assertIn('Clients renewed', self.cli('query', 'retention').stdout)
        self.assertFalse(brain.read_json(self.root / 'settings.json')['external_processors_enabled'])

    def test_approval_cli_shows_full_diff_and_requires_confirmation(self):
        self.cli('settings', '--allow-cloud', '--confirm-data-policy')
        draft = self.base / 'draft.md'
        draft.write_text('Clients renewed. Source: ' + self.path, encoding='utf-8')
        packet = self.quiet(brain.proposal, self.root, 'retention', draft, [self.path], 'Renewal summary')
        denied = self.cli('approve', packet, '--by', 'Fictional reviewer', ok=False)
        self.assertIn('summary:', denied.stdout)
        self.assertIn('Renewal summary', denied.stdout)
        self.assertIn('not human authentication', denied.stdout)
        self.cli('approve', packet, '--by', 'Fictional reviewer', '--confirm', 'wrong', ok=False)
        self.cli('apply', packet, ok=False)
        self.cli('approve', packet, '--by', 'Fictional reviewer', '--confirm', packet)
        self.cli('apply', packet)

    def test_summary_change_invalidates_approval(self):
        packet = self.topic()
        proposal_path = self.root / 'reviews' / packet / 'proposal.json'
        value = brain.read_json(proposal_path)
        value['summary'] = 'An unreviewed claim'
        brain.atomic(proposal_path, brain.encode(value))
        with self.assertRaises(ValueError):
            brain.apply(self.root, packet)

    def test_import_logs_once_and_keeps_old_revisions(self):
        before = (self.root / 'log.md').read_text(encoding='utf-8')
        self.quiet(brain.import_source, self.root, self.source, 'interview', 'external-ok')
        self.assertEqual(before, (self.root / 'log.md').read_text(encoding='utf-8'))
        self.source.write_text('Clients renewed; the scope remains uncertain.', encoding='utf-8')
        self.quiet(brain.import_source, self.root, self.source, 'interview', 'external-ok')
        self.assertEqual((self.root / 'log.md').read_text(encoding='utf-8').count('] ingest |'), 2)
        self.assertTrue((self.root / self.path).exists())

    def test_import_recovery_blocks_reads_until_complete(self):
        extra = self.base / 'extra.txt'
        extra.write_text('A new source snapshot', encoding='utf-8')
        real = brain.atomic
        def interrupted(path, data):
            if path == self.root / 'log.md':
                raise OSError('Synthetic interruption')
            real(path, data)
        with patch.object(brain, 'atomic', interrupted), self.assertRaises(OSError):
            brain.import_source(self.root, extra, 'extra', 'external-ok')
        with self.assertRaisesRegex(ValueError, 'recover'):
            brain.retrieve(self.root, 'retention', 'local', 1000)
        self.quiet(brain.recover, self.root)
        self.quiet(brain.import_source, self.root, extra, 'extra', 'external-ok')
        self.assertEqual((self.root / 'log.md').read_text(encoding='utf-8').count('] ingest |'), 2)

    def test_apply_interruption_blocks_another_writer_and_recovers(self):
        draft = self.base / 'draft.md'
        draft.write_text('Clients renewed. Source: ' + self.path, encoding='utf-8')
        packet = self.quiet(brain.proposal, self.root, 'retention', draft, [self.path])
        self.quiet(brain.approve, self.root, packet, 'Fictional reviewer')
        real = brain.atomic
        def interrupted(path, data):
            if path == self.root / 'index.md':
                raise OSError('Synthetic interruption')
            real(path, data)
        with patch.object(brain, 'atomic', interrupted), self.assertRaises(OSError):
            brain.apply(self.root, packet)
        with self.assertRaisesRegex(ValueError, 'recover'):
            brain.review(self.root, 'another-week')
        self.quiet(brain.recover, self.root)
        self.assertIn('retention', brain.catalog(self.root, 'local'))

    def test_process_crash_releases_lock_and_live_writer_blocks_reader(self):
        self.cli('settings', '--processor', 'local', '--confirm-data-policy')
        code = ('import brain,os,sys; from pathlib import Path\n'
                'with brain.locked(Path(sys.argv[1])):\n'
                ' print("locked",flush=True)\n'
                ' sys.stdin.readline()\n'
                ' os._exit(0)\n')
        child = subprocess.Popen([sys.executable, '-c', code, str(self.root)], cwd=brain.ROOT,
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), 'locked')
            self.assertIn('busy', self.cli('query', 'retention', ok=False).stderr)
            child.communicate('\n', timeout=10)
            self.assertEqual(child.returncode, 0)
            self.assertIn('Clients renewed', self.cli('query', 'retention').stdout)
            self.assertTrue((self.root / '.brain/workspace.lock').exists())
        finally:
            if child.poll() is None:
                child.kill()
                child.communicate()

    def test_legacy_lock_is_not_deleted_while_owner_is_uncertain(self):
        (self.root / '.lock').write_text('12345', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Legacy'):
            with brain.locked(self.root):
                pass
        self.assertTrue((self.root / '.lock').exists())

    def test_index_contains_reviewed_summary_and_filters_private_topics(self):
        self.topic()
        self.source.write_text('# Private\nPRIVATE_SYNTHETIC_MARKER\n', encoding='utf-8')
        self.quiet(brain.import_source, self.root, self.source, 'private', 'local-only')
        private = brain.source_records(self.root)[-1]['path']
        self.topic('private-topic', 'Private claim. Source: ' + private, [private], 'PRIVATE_SUMMARY')
        self.quiet(brain.settings, self.root, 'external', True)
        result = brain.catalog(self.root, 'external')
        self.assertIn('Renewal evidence', result)
        self.assertNotIn('PRIVATE_SUMMARY', result)
        self.assertNotIn('private-topic', result)

    def test_health_separates_topic_review_from_source_refresh(self):
        self.topic()
        registry_path = self.root / '.brain/sources.json'
        records = brain.read_json(registry_path)
        records[0]['observed_at'] = '2000-01-01T00:00:00+00:00'
        brain.atomic(registry_path, brain.encode(records))
        findings = brain.health_findings(self.root)
        self.assertFalse(any('refresh due' in f for f in findings))
        page = self.root / 'wiki/retention.md'
        page.write_text(page.read_text(encoding='utf-8').replace('last_reconciled: ' + brain.date.today().isoformat(),
                                                'last_reconciled: 2000-01-01'), encoding='utf-8')
        self.assertTrue(any('Topic review due' in f for f in brain.health_findings(self.root)))
        records[0]['refresh_days'] = 7
        brain.atomic(registry_path, brain.encode(records))
        self.assertTrue(any('Source refresh due' in f for f in brain.health_findings(self.root)))

    def test_superseded_sources_do_not_generate_refresh_noise(self):
        registry_path = self.root / '.brain/sources.json'
        records = brain.read_json(registry_path)
        records[0].update(observed_at='2000-01-01T00:00:00+00:00', refresh_days=1)
        brain.atomic(registry_path, brain.encode(records))
        self.source.write_text('Fresh renewal evidence', encoding='utf-8')
        self.quiet(brain.import_source, self.root, self.source, 'interview', 'external-ok', 7)
        self.assertFalse(any('refresh due' in f for f in brain.health_findings(self.root)))

    def test_health_detects_uncatalogued_pages_orphans_and_missing_dependencies(self):
        self.topic()
        (self.root / 'wiki/orphan.md').write_text('# Orphan\nUnreviewed manual file\n', encoding='utf-8')
        findings = brain.health_findings(self.root)
        self.assertTrue(any('missing dependencies: wiki/orphan.md' in f for f in findings))
        self.assertTrue(any('Unlinked topic: wiki/orphan.md' in f for f in findings))
        self.assertTrue(any('Catalog differs' in f for f in findings))

    def test_external_health_and_review_do_not_emit_private_titles(self):
        self.source.write_text('Private detail', encoding='utf-8')
        self.quiet(brain.import_source, self.root, self.source, 'private-marker', 'local-only')
        self.quiet(brain.settings, self.root, 'external', True)
        self.assertNotIn('private-marker', json.dumps(brain.health_findings(self.root, 'external')))
        self.quiet(brain.review, self.root, 'test-week', 'external')
        self.assertNotIn('private-marker', (self.root / 'reviews/test-week/delta.md').read_text(encoding='utf-8'))

    def test_retirement_is_proposed_and_keeps_raw_and_history(self):
        self.topic()
        before = (self.root / 'wiki/retention.md').read_bytes()
        packet = self.quiet(brain.lifecycle, self.root, 'retire', 'retention', reason='The project ended')
        self.assertEqual(before, (self.root / 'wiki/retention.md').read_bytes())
        with self.assertRaises(ValueError):
            brain.apply(self.root, packet)
        self.apply_packet(packet)
        self.assertEqual(brain.page_info((self.root / 'wiki/retention.md').read_text(encoding='utf-8'))['status'], 'retired')
        result = brain.retrieve(self.root, 'retention', 'local', 3000)
        self.assertNotIn('[source:wiki/retention.md', result)
        self.assertTrue((self.root / self.path).exists())

    def test_rename_updates_inbound_links_redirects_index_and_dependencies(self):
        self.topic()
        self.topic('delivery', '# Delivery\nSee [[retention]]. Source: ' + self.path, summary='Delivery links')
        packet = self.quiet(brain.lifecycle, self.root, 'rename', 'retention', 'renewals')
        self.apply_packet(packet)
        self.assertIn('[[renewals]]', (self.root / 'wiki/delivery.md').read_text(encoding='utf-8'))
        self.assertEqual(brain.page_info((self.root / 'wiki/retention.md').read_text(encoding='utf-8'))['redirect'], 'renewals')
        self.assertIn('wiki/renewals.md', brain.read_json(self.root / '.brain/page-deps.json'))
        self.assertIn('[[renewals]] — Renewal evidence', (self.root / 'index.md').read_text(encoding='utf-8'))
        target = self.base / 'rebuilt'
        self.quiet(brain.rebuild, self.root, target)
        self.assertEqual(brain.wiki_snapshot(self.root), brain.wiki_snapshot(target))

    def test_lifecycle_rejects_new_wiki_changes_after_proposal(self):
        self.topic()
        packet = self.quiet(brain.lifecycle, self.root, 'rename', 'retention', 'renewals')
        self.quiet(brain.approve, self.root, packet, 'Fictional reviewer')
        self.topic('new-topic')
        with self.assertRaisesRegex(ValueError, 'Wiki changed'):
            brain.apply(self.root, packet)

    def test_merge_preserves_union_of_source_permissions_and_updates_links(self):
        self.topic()
        self.source.write_text('Private renewal evidence', encoding='utf-8')
        self.quiet(brain.import_source, self.root, self.source, 'private', 'local-only')
        private = brain.source_records(self.root)[-1]['path']
        self.topic('feedback', 'Private claim. Source: ' + private, [private])
        draft = self.base / 'merged.md'
        draft.write_text('Merged renewal evidence. Sources: ' + self.path + ' ' + private, encoding='utf-8')
        packet = self.quiet(brain.lifecycle, self.root, 'merge', 'feedback', 'retention', draft, 'Combined evidence')
        self.apply_packet(packet)
        info = brain.page_info((self.root / 'wiki/retention.md').read_text(encoding='utf-8'))
        self.assertEqual(set(info['sources']), {private, self.path})
        self.assertEqual(info['processor'], 'local-only')
        self.quiet(brain.settings, self.root, 'external', True)
        self.assertNotIn('Combined evidence', brain.catalog(self.root, 'external'))

    def test_lifecycle_interrupted_apply_resumes_all_files_once(self):
        self.topic()
        packet = self.quiet(brain.lifecycle, self.root, 'rename', 'retention', 'renewals')
        self.quiet(brain.approve, self.root, packet, 'Fictional reviewer')
        real = brain.atomic
        def interrupted(path, data):
            if path == self.root / 'wiki/renewals.md':
                raise OSError('Synthetic interruption')
            real(path, data)
        with patch.object(brain, 'atomic', interrupted), self.assertRaises(OSError):
            brain.apply(self.root, packet)
        self.quiet(brain.recover, self.root)
        self.assertEqual((self.root / 'log.md').read_text(encoding='utf-8').count('] rename |'), 1)
        self.assertTrue((self.root / 'wiki/renewals.md').exists())

    def test_pending_journal_metadata_corruption_is_rejected(self):
        draft = self.base / 'draft.md'
        draft.write_text('Renewal evidence. Source: ' + self.path, encoding='utf-8')
        packet = self.quiet(brain.proposal, self.root, 'retention', draft, [self.path])
        self.quiet(brain.approve, self.root, packet, 'Fictional reviewer')
        real = brain.atomic
        def interrupted(path, data):
            if path == self.root / 'index.md':
                raise OSError('Synthetic interruption')
            real(path, data)
        with patch.object(brain, 'atomic', interrupted), self.assertRaises(OSError):
            brain.apply(self.root, packet)
        journal_path = self.root / 'reviews' / packet / 'apply-journal.json'
        value = brain.read_json(journal_path)
        next(c for c in value['changes'] if c['path'] == 'index.md')['after'] = 'Unexpected catalog'
        brain.atomic(journal_path, brain.encode(value))
        with self.assertRaisesRegex(ValueError, 'integrity'):
            brain.apply(self.root, packet)

    def test_cloud_catalog_health_and_review_do_not_read_restricted_bodies(self):
        self.source.write_text('A private source', encoding='utf-8')
        self.quiet(brain.import_source, self.root, self.source, 'private', 'local-only')
        private = brain.source_records(self.root)[-1]['path']
        self.topic('private-topic', 'Private. Source: ' + private, [private])
        self.quiet(brain.settings, self.root, 'external', True)
        denied = {self.root / private, self.root / 'wiki/private-topic.md'}
        real_bytes, real_text = Path.read_bytes, Path.read_text
        def guarded_bytes(path):
            if path in denied:
                raise AssertionError('Read a restricted body')
            return real_bytes(path)
        def guarded_text(path, *args, **kwargs):
            if path in denied:
                raise AssertionError('Read a restricted body')
            return real_text(path, *args, **kwargs)
        with patch.object(Path, 'read_bytes', guarded_bytes), patch.object(Path, 'read_text', guarded_text):
            brain.catalog(self.root, 'external')
            brain.health_findings(self.root, 'external')
            self.quiet(brain.review, self.root, 'permitted-week', 'external')

    def test_before_preview_tampering_rejected(self):
        self.topic()
        packet = self.quiet(brain.lifecycle, self.root, 'retire', 'retention', reason='Project ended')
        path = self.root / 'reviews' / packet / 'before-files.json'
        saved = brain.read_json(path)
        saved['wiki/retention.md'] = 'Different before'
        brain.atomic(path, brain.encode(saved))
        with self.assertRaises(ValueError):
            brain.approve(self.root, packet, 'Fictional reviewer')

    def test_retiring_superseded_evidence_does_not_require_rewriting_history(self):
        self.topic()
        self.source.write_text('A revised current source', encoding='utf-8')
        self.quiet(brain.import_source, self.root, self.source, 'interview', 'external-ok')
        packet = self.quiet(brain.lifecycle, self.root, 'retire', 'retention', reason='Superseded conclusion')
        self.apply_packet(packet)
        self.assertEqual(brain.page_info((self.root / 'wiki/retention.md').read_text(encoding='utf-8'))['status'], 'retired')
        self.assertIn('retention', brain.catalog(self.root, 'local'))
        self.assertFalse(any('Topic needs source reconciliation' in f for f in brain.health_findings(self.root)))

    def test_cross_platform_reserved_names_are_rejected(self):
        for name in ('con', 'nul', 'com1', 'lpt9'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                brain.slug(name)

    def test_query_verifies_shared_source_only_once(self):
        self.topic()
        self.topic('delivery')
        target = self.root / self.path
        real = Path.read_bytes
        reads = []
        def counted(path):
            if path == target:
                reads.append(path)
            return real(path)
        with patch.object(Path, 'read_bytes', counted):
            brain.retrieve(self.root, 'renewed', 'local', 3000)
        self.assertEqual(len(reads), 1)

    def test_brief_is_a_permitted_status_scaffold_not_an_invented_priority(self):
        self.topic()
        result = brain.brief(self.root, 'local', save=True)
        self.assertIn('Generated status scaffold', result)
        self.assertTrue((self.root / 'daily' / (brain.date.today().isoformat() + '-status.md')).exists())

    def test_rebuild_replays_decisions_and_refuses_unrecorded_changes(self):
        self.topic()
        target = self.base / 'rebuilt'
        self.quiet(brain.rebuild, self.root, target)
        for path in ('index.md', 'log.md', '.brain/sources.json', '.brain/page-deps.json', 'wiki/retention.md'):
            self.assertEqual((self.root / path).read_bytes(), (target / path).read_bytes())
        with self.assertRaises(ValueError):
            brain.rebuild(self.root, target)
        (self.root / 'wiki/retention.md').write_text('Manual edit', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'differs'):
            brain.rebuild(self.root, self.base / 'other')
        self.assertFalse((self.base / 'other').exists())

    def test_version_one_packet_keeps_legacy_preview_and_rebuild_support(self):
        packet = 'legacy-packet'
        folder = self.root / 'reviews' / packet
        folder.mkdir()
        payload = {'version': 1, 'target': 'wiki/legacy.md', 'before_sha256': None,
                   'body': '# Legacy\nFictional evidence. Source: ' + self.path,
                   'sources': [self.path], 'created_at': brain.stamp()}
        brain.atomic(folder / 'proposal.json', brain.encode(payload))
        brain.atomic(folder / 'decision.json', brain.encode({'status': 'pending'}))
        brain.atomic(folder / 'before.md', b'')
        brain.atomic(folder / 'after.md', payload['body'].encode())
        self.apply_packet(packet)
        self.assertEqual(brain.page_info((self.root / 'wiki/legacy.md').read_text(encoding='utf-8'))['body'], payload['body'])
        self.quiet(brain.rebuild, self.root, self.base / 'rebuilt')

    def test_rebuild_rejects_journal_corruption_before_creating_target(self):
        packet = self.topic()
        journal_path = self.root / 'reviews' / packet / 'apply-journal.json'
        value = brain.read_json(journal_path)
        value['changes'][0]['after'] += '\nUnreviewed claim'
        brain.atomic(journal_path, brain.encode(value))
        with self.assertRaisesRegex(ValueError, 'integrity'):
            brain.rebuild(self.root, self.base / 'rebuilt')
        self.assertFalse((self.base / 'rebuilt').exists())

    def test_rebuild_rejects_symlink_receipt(self):
        packet = self.topic()
        receipt = self.root / 'reviews' / packet / 'receipt.json'
        real = self.base / 'real-receipt.json'
        real.write_bytes(receipt.read_bytes())
        receipt.unlink()
        try:
            receipt.symlink_to(real)
        except OSError:
            self.skipTest('Symlink creation unavailable')
        with self.assertRaises(ValueError):
            brain.rebuild(self.root, self.base / 'rebuilt')


if __name__ == '__main__':
    unittest.main()
