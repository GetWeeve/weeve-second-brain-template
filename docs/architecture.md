# Architecture, framework references and credits

The system keeps immutable source revisions, a short reviewed wiki, and procedures that use that wiki. A catalog routes agents to topics. A chronological import/apply log and source dependency map help trace changes. Reviewed summaries route agents through the processor-filtered catalog. The rebuild command reconstructs recorded state from sources, approved decisions and completed journals/receipts into a separate empty directory. Reviewed interpretations require their decision history; raw sources alone cannot recreate the exact judgment.

Each private workspace contains

```text
settings.json          processor permissions, freshness and workspace preferences
raw-local/             content-addressed imported evidence
wiki/                  approved topic pages
index.md               topic catalog
log.md                 append-only import and applied-change history
.brain/sources.json    source revision, observation and processor registry
.brain/page-deps.json  topic-to-source dependencies
reviews/               proposals, decisions, role reports and apply receipts
daily/                 brief outputs and private session checkpoints
```

The importer hashes originals and treats reimporting identical evidence as idempotent. Changed content receives a new hash. The query tool searches latest source revisions and approved topics through headings and words, retrieves a few relevant passages, and includes source locators. The UTF-8 byte limit bounds emitted excerpts, with room still needed for the rest of the model context. Queries return evidence excerpts. The user's selected agent reasons over them and writes cited answers.

A proposal records the target's previous hash, body, sources and proposed time. Approval binds to its content hash. Apply checks that the decision and source evidence still match. A process-scoped OS lock and journals protect consistent reads/writes and interrupted import/application. Pending transactions block reads until recovery. Reviewed retirement, rename and merge preserve evidence and decision history. Files must be inside the workspace, and traversal/symlink paths are rejected. Multi-user deployments still need authentication and OS or service access control appropriate to the team.

## Frameworks and sources

| Source | Contribution | How this kit uses it |
|---|---|---|
| Karpathy's LLM Wiki | Compiled Markdown knowledge, catalog, log and ingest/query/lint | Source-backed synthesis plus explicit human review |
| Tim Scheuer's OXYGEN walkthrough | Company context and task skills over shared knowledge | Generic private roles that retrieve company knowledge |
| Tom Blomfield's YC talk | Recording domain knowledge and reviewing improvement loops | Daily/weekly evidence checks with an accountable human decision |
| Garry Tan's company-brain talk and GBrain | Persistent context and task routing | Shared knowledge, narrow role context and explicit source references |
| Matt Paige's walkthrough | A practical first-source onboarding flow | Fictional source → cited question → proposed update → health check |
| Forte's CODE | Capture, organize, distill and express | A simple way to teach the lifecycle |
| Lean Startup | Build, measure and learn | Experiment baselines, comparable windows and outcome checks |
| Anthropic context engineering | Selective context and durable working notes | Focused retrieval, scoped role reports and checkpoints |
| Agent Skills / AGENTS.md | Portable instruction formats and progressive loading | Shared entrypoint, thin host adapters and blank private skills |

This project combines established ideas with a small local implementation. Its initial design was informed by Weeve's internal operating experience. Public files were newly authored for this template. The generic kit excludes internal business evidence and purchased playbook libraries.

Read the original sources

- [Karpathy, LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- [Tim Scheuer, OXYGEN company brain](https://www.linkedin.com/posts/tim-scheuer-91b005237_we-built-a-company-wide-second-brain-for-activity-7476288218125021184-nj4V)
- [Matt Paige, practical walkthrough](https://mattpaige68.substack.com/p/andrej-karpathy-just-showed-us-how)
- [Tom Blomfield, How to Build a Self-Improving Company with AI](https://www.youtube.com/watch?v=X_JsIHUfUjc)
- [Garry Tan, Every company should have a Brain](https://www.youtube.com/watch?v=eBUyTS7SzV4) and [GBrain](https://github.com/garrytan/gbrain)
- [Forte, CODE](https://fortelabs.com/blog/basboverview/)
- [Lean Startup principles](https://theleanstartup.com/principles)
- [Context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Agent Skills](https://agentskills.io/specification) and [AGENTS.md](https://agents.md/)

PageIndex and Graphify informed possible retrieval improvements. This release uses deterministic text/heading lookup. A future PageIndex adapter should demonstrate better source recall and citations on long public/synthetic documents within its token, latency and privacy budget. Explicit links and model-inferred relationships should carry different labels. [PageIndex](https://github.com/VectifyAI/PageIndex) · [Graphify](https://github.com/Graphify-Labs/graphify)

See [retrieval measurements](performance.md), [approval/data boundaries](safety.md) and [command details](commands.md).
