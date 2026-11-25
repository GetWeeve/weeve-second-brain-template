# Compatibility and validation scope

The core requires Python 3.9+ and uses the standard library. Commands use pathlib and Python subprocess APIs so shell-specific setup scripts are unnecessary. Python tests and the demo run on macOS in the release environment. GitHub Actions exercises Ubuntu, Windows and macOS on Python 3.13, plus the minimum Python 3.9 on Ubuntu 24.04. The local macOS checks also use Python 3.9.6. Check the candidate PR for the actual four-job result. Check the Actions tab for the actual run status and tested versions.

The generic workflow works through files and commands. Codex and Claude Code instruction adapters are included, with thin Gemini and documented OpenCode entrypoints. A language model's ability to follow the procedure still depends on its capabilities, permissions and available context. The core tests verify deterministic behavior, including approvals, source permissions, integrity, revision selection and resumption. They do not measure every model's answer quality.

The demo covers fictional coaching notes, a freelance project and a team experiment. It validates the file workflow. Human reasoning, source interpretation, live PostHog/Analytics access, recorder UI behavior and real organizational adoption need evaluation in the user's authorized environment. Offline commands do not require a paid model or provider account.

The search is a small lexical/heading retriever with bounded excerpts. It can miss synonyms and sources that require multiple linked passages. Report retrieval gaps. Long PDF parsing, embeddings, audio transcription, live connector clients and scheduled agent hosting belong to optional external tools. Text exports can be imported into this release.

Public documentation links and Weeve's public product/privacy claims were checked on 24 November 2026. Service authentication and app controls may change. Follow the linked official guide and verify a scoped read in your own account.

## Release smoke checks

On 24 November 2026, Codex CLI 0.167.0-alpha.4.1 and Claude Code 2.1.331 each read the shared setup instructions and ran doctor and the fictional demo successfully on macOS with Python 3.9.6. The Codex test used a workspace-write sandbox because the demo creates temporary files. Both tests used isolated synthetic-only copies. Gemini and OpenCode instructions are documented and awaiting runtime smoke tests. The earlier published baseline ran 17 deterministic tests. The release candidate expands coverage for settings, confirmation, filtered catalogs/status, import logging, OS lock crash release, multi-page maintenance, reconstruction and release tooling. Run the suite for the current count.

Repository text uses LF line endings on every platform so release checksums remain stable. CI caught and corrected a native Windows path separator in the health check. The demo and regression test for superseded topics exercise this path.

The owner-controlled approval procedure describes an independent host trust boundary; this kit does not provision or certify a sandbox for every host. Optional PageIndex/Graphify adapters are not installed. See [safety](safety.md) and [retrieval scope](performance.md).

The minimum-version CI job uses Ubuntu 24.04 because the latest Ubuntu runner has no Python 3.9 artifact. Supported platform builds are listed in [GitHub's Python versions manifest](https://github.com/actions/python-versions/blob/main/versions-manifest.json). This changes CI provisioning, not the core Python requirement.
