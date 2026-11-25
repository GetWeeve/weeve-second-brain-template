# Working with coding agents

The shared entrypoint is [AGENTS.md](../AGENTS.md). Follow its numbered first-run sequence and choose the permitted processor before source access. Use a file-capable agent and the Python commands to operate on saved evidence and proposals. The agent supplies reasoning and writing. The offline CLI supplies file integrity, retrieval and workflow records.

| Host | Entry instructions | Setup check |
|---|---|---|
| Codex | [AGENTS.md](../AGENTS.md) | Ask which instruction files it loaded and run doctor |
| Claude Code | [CLAUDE.md](../CLAUDE.md) imports AGENTS.md | Confirm the import in the session's memory/context display |
| Gemini CLI | [GEMINI.md](../GEMINI.md) imports AGENTS.md | Confirm loaded project context and run doctor |
| OpenCode | [AGENTS.md](../AGENTS.md) | Confirm rules and tool permissions, then run doctor |
| Other coding agent | Explicitly ask it to read [AGENTS.md](../AGENTS.md) | Check file/shell permissions and verify a cited demo answer |

An instruction format alone does not ensure a host enforces filesystem restrictions or runs subagents identically. Set model, context capacity, external source permissions, working directory and allowed operations in the host. Check [compatibility](compatibility.md) for executed tests.

Start with this task

> Read AGENTS.md and docs/quickstart.md. Run the fictional demo and explain the evidence-to-review loop. Confirm processor permissions before using my files. Help me draft one topic with citations and prepare its proposal. Show me the before/after before asking for a decision.

For a single reviewer

> Read agents/product.md. Use the specified weekly delta and research digest. Retrieve only permitted relevant evidence. Write the product report in that weekly directory with findings, source/version references, uncertainty and proposed changes. Give each result an owner and next check where evidence supports them.

The same procedure works for each named role. On hosts with subagents, give each a narrow role, common research digest, reporting window and its own output file. On a single-agent host, use fresh sequential sessions over the saved artifacts. Research precedes domain work, and the coordinator follows it. Avoid copying the whole parent chat into every reviewer.

Store a compact private checkpoint with task, current phase, actual source coverage, artifact paths, decisions and next action. On resumption read authoritative instructions and the checkpoint, then recheck source revisions and pending packets. Load at most a few relevant topics and one skill per task. The byte cap bounds tool output only. Budget the full model context, including tools, history, instructions and reserved answer space, using the host's token display or tokenizer.

Try the [worked generic skills](../skills/README.md), then create private task skills from [the blank template](../templates/task-skill.md). Put business facts and writing samples in the wiki and retrieve them. Add only the steps and checks that the task needs. Use synthetic examples when contributing a generic extension. A third-party skill can execute code or change instructions, so review its source, license and permissions before installing it.
