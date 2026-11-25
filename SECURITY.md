# Security

Report a vulnerability privately through this repository's GitHub Security tab → Report a vulnerability. If that option is unavailable, use the contact route on https://getweeve.io/ and ask for a private security channel before sharing exploit details or company data.

The offline commands enforce path, source integrity and approval checks within their supported interface. They do not sandbox an agent with arbitrary shell access. Configure host permissions, permitted processors and connector scopes. Local approval files record a human decision and do not authenticate identity. The supported interface serializes local commands through a process-scoped OS lock and refuses incomplete transaction reads until recovery. Stronger approval separation and its host requirements are described in docs/safety.md.

Keep source bodies, credentials and user identifiers out of public issues. Use a synthetic reproduction. See docs/privacy.md and docs/connections.md. Run `python3 audit.py` before contributing or releasing. Review all candidate files and their Git history as well as the scanner output.
