# Data and processor boundaries

| Material | Default handling |
|---|---|
| Generic template and fictional examples | May be public |
| Company wiki, decisions, titles and source metadata | Private local workspace |
| Recordings, transcripts, legal, HR, customer notes and derived indexes | Restricted evidence with an explicit owner, audience and retention policy |
| API keys, OAuth files, client secrets and MCP authorization | Host secret store or files outside Git |

A common team document can still be confidential. A summary, source title, hash, graph or embedding can reveal information about its original source. Review derived materials under the same data policy.

The Python commands read local files and make no network calls. A coding agent that receives those files can send them to its model provider. Local storage and local model processing require separate checks. Use an approved local model and host filesystem/network restrictions for local-only evidence. Opening the template directory in a broadly authorized cloud agent may give it access to ignored subdirectories. A .gitignore rule affects Git, not agent reads or network traffic.

`query` uses the owner-selected workspace processor and refuses an unconfigured policy. New workspaces start unconfigured with external processing disabled. It filters source processor permissions before reading passages, excludes superseded source revisions, and checks that cited dependencies allow an approved wiki page to be used. Use a separate external-safe workspace for cloud agents and mount confidential evidence only for permitted local tasks. The policy checks cover the included commands. A general shell or connector can bypass them, so configure host restrictions too.

Import only the source scope you need. Record permission to capture conversations, participant notice where required, purpose, source window, owner and permitted processors in your private records. For coaches, keep identifying client data outside broadly shared workspaces and use de-identified extracts only after review.

The normal importer preserves original evidence. An authorized retention or erasure process may remove evidence when required. Remove affected wiki claims and private indexes too, and record a minimal deletion receipt outside public Git. Coordinate backup expiry and any legal hold with the responsible owner. Back up private evidence using encryption, a separate key and a verified restore test.

Source files can contain hostile instructions. Agents must treat those as quoted material and keep tool permissions unchanged. The importer never executes text. Query output can still contain hostile text, so an agent must evaluate it as evidence. Host-level controls and human review remain important.

Use the filtered `catalog`, `health` and `brief` commands in a cloud workspace. Directly reading a mixed private index can expose local-only titles and summaries. The CLI rejects a processor flag that conflicts with its configured mode; this reduces mistakes but cannot prevent arbitrary shell access. See [safety and owner-controlled approval](safety.md).
