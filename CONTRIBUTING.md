# Contributing

Use fictional examples and newly authored generic instructions. Check rights and licenses before reusing material. Keep company data, purchased playbooks, personal samples and credentials out of commits, PRs and issues.

Git commit authors and committers are public metadata. Use your GitHub noreply address for public commits and check author/committer addresses before pushing. For merges through GitHub, enable [email privacy](https://docs.github.com/en/account-and-profile/how-tos/email-preferences/setting-your-commit-email-address) in your account settings.

Make a focused change and run:

```sh
python3 -m unittest discover -s tests -v
python3 demo.py
python3 manifest.py
```

The manifest command previews added/changed/removed payload paths. Review each changed file, then run `python3 manifest.py --refresh` and `python3 audit.py`. Refreshing hashes records the candidate; it is not a security or release approval. Audit checks candidate files, local links, credential patterns, the explicitly reviewed image and reachable Git history. Use an independent credential scanner and manual data/IP review before a release. On Windows use `py -3`.

Add regression tests for integrity, permissions, approvals, citations, lifecycle or recovery changes. Describe the resulting behavior, validation and limits in the PR. Keep UTF-8 text with LF endings for cross-platform checksums. Run `python3 benchmark.py` when changing retrieval and report the dataset/scope, not just a speed claim.

For connector guides, link official setup, describe scopes/data flow, local credential references, revocation and a bounded read check. Mark untested provider configurations explicitly. The blank connection record is not a native host configuration or an enforcement mechanism.

Changes to instructions, roles, schemas and data handling need workflow review, including a first-time user path. Keep one canonical instruction source and thin host adapters. Preserve role-specific ownership and narrow context. Review source/image rights separately from code licensing. See [the asset rights notice](assets/README.md).

A draft PR may be pushed for review while release is held. Merge, repository metadata changes and release promotion need the maintainer's final decision. Do not include private audit receipts or actual user workspaces in the public payload.
