# Command reference

Use Python 3.9+. Replace `python3` with `py -3` on Windows. `--workspace PATH` goes **before** the command. Success exits 0; invalid input or denied operations exit 1. All commands run offline.

| Command | Result |
|---|---|
| `python3 brain.py doctor` | Reports the interpreter and offline core |
| `python3 brain.py init` | Initializes an empty private workspace |
| `python3 brain.py settings` | Shows configuration without reading evidence |
| `python3 brain.py settings --allow-cloud --confirm-data-policy` | Records the owner's external-processing choice |
| `python3 brain.py settings --processor local --confirm-data-policy` | Records local mode; does not configure a model or sandbox |
| `python3 brain.py settings --topic-review-days 30` | Sets the default review cadence for new proposals; 0 disables time-based reminders |
| `python3 brain.py import notes.txt --id interview --processor local-only` | Preserves immutable evidence and journals registry/log changes |
| `python3 brain.py import metrics.csv --id metrics --processor external-ok --refresh-days 7` | Imports approved evidence with a refresh reminder; 0 is the default for immutable references |
| `python3 brain.py query "activation definition" --budget-bytes 3000` | Returns up to three permitted excerpts within the UTF-8 byte budget |
| `python3 brain.py catalog` | Returns permitted topic summaries; use this instead of directly reading a mixed private index |
| `python3 brain.py propose activation --file workspace/draft.md --summary "Activation definition and exclusions" --source raw-local/interview/HASH.txt` | Saves a pending packet and prints its ID |
| `python3 brain.py show PACKET-ID` | Displays the exact topic/metadata changes |
| `python3 brain.py approve PACKET-ID --by "Workspace owner"` | Displays the diff and asks for the exact packet ID |
| `python3 brain.py approve PACKET-ID --by "Workspace owner" --confirm PACKET-ID` | Records an already explicit human decision through an agent or noninteractive shell |
| `python3 brain.py apply PACKET-ID` | Verifies approval and applies the saved transaction |
| `python3 brain.py retire activation --reason "Project ended"` | Proposes retirement while preserving the page/evidence/history |
| `python3 brain.py rename activation --into onboarding` | Proposes a new topic, old-name redirect and inbound-link repairs |
| `python3 brain.py merge activation --into onboarding --file workspace/merged.md --summary "Combined onboarding evidence"` | Proposes the supplied merged body, union of sources, redirect and inbound-link repairs |
| `python3 brain.py review 2026-w48` | Prepares weekly coverage and role instructions; does not run agents |
| `python3 brain.py health` | Reports review/refresh due dates, dependency drift, broken/retired links, unlinked topics and pending decisions |
| `python3 brain.py brief --save` | Saves a deterministic daily status scaffold; the agent supplies actual priorities |
| `python3 brain.py recover` | Resumes an interrupted import/apply transaction |
| `python3 brain.py rebuild --to ../rebuilt-workspace` | Reconstructs recorded state into a separate empty directory after validating receipts |

The default query processor comes from the owner's configured workspace. A conflicting query `--processor` flag is refused. Cloud workspaces import only explicitly external-approved sources. Settings are policy records, not model identity or access-control enforcement.

Topic names use lowercase letters, digits and single hyphens. Bodies contain 1–400 words and cite every supplied source path. Repeat `--source` for multiple sources. `--summary` is one reviewed line up to 240 characters; if omitted, the first body line becomes the summary. `--review-days` overrides the default on a proposal. Actual conversation dates and reporting windows belong in the evidence/claim; import time does not establish event time.

Proposals include full generated metadata in before/after previews. Approval binds the proposal hash. A changed target, proposal, source or lifecycle wiki snapshot requires a new review. Rename/merge inspect the whole wiki to update inbound links, so they require a fully permitted workspace. Merged bodies must cite the union of both topics' sources; local-only restrictions are retained. Retired/redirect pages stay in the catalog and are excluded from normal wiki answer excerpts; original raw evidence remains available under its original policy.

All workspace commands serialize through a process-scoped OS lock. A crash releases the lock automatically. Reads refuse incomplete transactions until recovery, preventing a partially applied wiki/dependency/catalog state. Repeated import is idempotent; repeating the same apply is safe while its recorded outputs still match. Later changes conflict rather than rolling knowledge backward.

`health` exit 0 means the check ran, not that every finding is resolved. A singleton topic is allowed; an unlinked-topic finding is a navigation suggestion, not a reason to invent a connection. Source refresh and topic review have independent cadences. Superseded source revisions do not produce refresh noise.

Rebuild checks completed journal/decision history and the current recorded state before writing a new workspace. Keep raw evidence, proposals, decisions, journals and receipts together. Unrecorded edits, missing/corrupt receipts and nonempty destinations cause refusal. Daily notes, arbitrary drafts and credentials need a separate encrypted backup. Rebuild is not a substitute for a verified restore test. See [safety](safety.md) for approval authority and [troubleshooting](troubleshooting.md) for migration/recovery.
