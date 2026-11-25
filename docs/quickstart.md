# Your first ten minutes

## Get a private copy

On GitHub choose **Use this template → Create a new repository → Private**, or **Code → Download ZIP** and extract it locally. Git is optional. To clone your own private copy, copy its HTTPS URL from GitHub and run `git clone YOUR-PRIVATE-COPY-URL weeve-second-brain-template`, then open that folder.

Install Python 3.9+ from [python.org](https://www.python.org/downloads/). On Mac/Linux use `python3`; on Windows use `py -3` throughout. No Python packages or service accounts are needed for the offline core.

```sh
python3 brain.py doctor
python3 demo.py
python3 brain.py init
python3 brain.py settings
```

The demo uses fictional coaching, freelance and team evidence in temporary directories. `init` creates an ignored `workspace/`; it refuses a nonempty directory. For a different location, put `--workspace PATH` before every command, including init. Keep confidential work outside shared or synced folders.

## Choose where data may go

Before an agent reads real files, decide which model/provider is permitted. For a cloud-backed coding agent, use a workspace containing only external-approved material. The fictional example below is safe to use for learning.

```sh
python3 brain.py settings --allow-cloud --confirm-data-policy
python3 brain.py import examples/coach.txt --id coaching-demo --processor external-ok
python3 brain.py query "session completion"
```

For an approved local model, configure a **separate** workspace using `settings --processor local --confirm-data-policy`; imports default to local-only. This command does not switch your coding agent to a local model. Configure and verify its filesystem/network restrictions separately. A cloud agent must not use a local flag to retrieve restricted passages. [Data boundaries](privacy.md) · [Owner-controlled approval](safety.md).

Settings commands do not connect services or authorize every future source. Real imports still need an owner-approved purpose, audience and processor. `settings --disable-cloud --confirm-data-policy` selects local mode and disables cloud query output.

## Make the first useful page

Tell your agent your role, goal, authoritative sources, metric definitions and who decides changes. Ask:

> Read AGENTS.md and skills/answer-with-citations/SKILL.md. Use the fictional coaching source to answer one question with citations. Draft a short topic and meaningful one-line summary. Prepare a proposal and show its exact diff. Wait for my decision.

The source path printed by import/query contains a full revision hash. The topic must cite that exact path. Use [the topic template](../templates/topic.md) as a guide and save the body as `workspace/draft.md`, then use the actual source path:

```sh
python3 brain.py propose session-completion --file workspace/draft.md --summary "Session completion evidence and open questions" --source raw-local/coaching-demo/HASH.txt
python3 brain.py show PACKET-ID
```

Replace HASH and PACKET-ID with the actual values. After reviewing, the owner can run `python3 brain.py approve PACKET-ID --by "Workspace owner"` and type the packet ID. Alternatively, after an explicit human decision, an agent may record it with `--confirm PACKET-ID`. The command prints the full diff; this records attribution, not identity authentication.

```sh
python3 brain.py apply PACKET-ID
python3 brain.py catalog
python3 brain.py health
python3 brain.py brief --save
```

## Confirm what Git excludes

Before real data, run:

```sh
git check-ignore workspace/settings.json workspace/raw-local/probe.txt workspace/wiki/probe.md .mcp.json .env
```

Every path should be printed. ZIP users can inspect the included `.gitignore` and stay entirely local. The generated workspace also has its own `*` ignore rule. Git ignore does not limit agent reads. Never force-add private paths. Ignoring a previously committed file does not remove its history; revoke exposed credentials and follow [GitHub's removal guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).

For deliberate private wiki sync, use a separate private repository rooted at the workspace and replace its ignore rule with this narrow allowlist:

```gitignore
*
!/.gitignore
!/wiki/
/wiki/*
!/wiki/*.md
!/index.md
```

Review every page and the catalog for their intended audience first. Titles, summaries and source paths can be sensitive. This creates a read-only knowledge mirror; ingestion/review needs a configured workspace and authorized source evidence. Keep settings, raw sources, decisions, logs, keys and derived indexes excluded.

## Your first week

Start with one source and one reviewed page. Use [daily/weekly reviews](reviews.md), then add [connections](connections.md) only when the local loop works. [Writing guidance](writing.md) helps you develop a private voice guide. [Commands](commands.md) covers maintenance and recovery. [Compatibility](compatibility.md) states what has actually been tested.
