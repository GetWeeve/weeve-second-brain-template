"""Run fictional end-to-end scenarios in temporary workspaces without network access."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import brain


def demo():
    for persona, question in [('coach', 'session completion'), ('freelancer', 'scope'), ('organization', 'activation')]:
        with tempfile.TemporaryDirectory(prefix='brain-demo-') as temp:
            root = Path(temp).resolve() / 'workspace'
            with redirect_stdout(io.StringIO()):
                brain.init(root)
                brain.import_source(root, brain.ROOT / 'examples' / (persona + '.txt'), persona, 'external-ok')
            with redirect_stdout(io.StringIO()):
                brain.settings(root, 'external', True)
            evidence = brain.retrieve(root, question, 'external', 3000)
            source = brain.source_records(root)[0]['path']
            assert source in evidence
            draft = Path(temp) / 'draft.md'
            draft.write_text('# Reviewed demo\n\nFictional evidence for ' + persona + '.\n\nSource: ' + source + '\n', encoding='utf-8')
            with redirect_stdout(io.StringIO()):
                packet = brain.proposal(root, persona, draft, [source])
            try:
                brain.apply(root, packet)
            except ValueError:
                pass
            else:
                raise AssertionError('Unapproved application was allowed')
            with brain.locked(root), redirect_stdout(io.StringIO()):
                brain.approve(root, packet, 'Fictional demo owner')
                brain.apply(root, packet)
                brain.apply(root, packet)
                brain.review(root, 'demo-week')
                findings = brain.health(root)
            assert not findings
            assert (root / 'wiki' / (persona + '.md')).exists()
            assert json.loads((root / '.brain/page-deps.json').read_text(encoding='utf-8'))
            assert 'Reviewed demo' in brain.catalog(root, 'external')
            assert 'Generated status scaffold' in brain.brief(root, 'external')
            with redirect_stdout(io.StringIO()):
                moved = brain.lifecycle(root, 'rename', persona, persona + '-reviewed')
                brain.approve(root, moved, 'Fictional demo owner')
                brain.apply(root, moved)
                brain.rebuild(root, Path(temp) / 'reconstructed')
            print(persona + ': import, cited retrieval, approval gate, weekly preparation, rename and reconstruction passed')
    print('Demo complete. All data was fictional and temporary.')


if __name__ == '__main__':
    demo()
