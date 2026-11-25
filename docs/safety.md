# What the safety checks guarantee

The included commands reject traversal/symlink paths, corrupted source revisions, missing or changed approvals, stale target writes and invalid links. External-mode queries filter source permissions before reading passages and inherit restrictions into approved topic excerpts. They do not identify the model behind a shell or sandbox an agent.

| Control | What it does | What still needs a host or human |
|---|---|---|
| Git ignore | Excludes generated/private files from ordinary Git adds | Check history and avoid force-adds; agents may still read ignored files |
| Processor policy | Filters output through the supported commands | Restrict model/provider, filesystem mounts, connectors and network access |
| Approval record | Binds an attributed decision to exact proposed content | Establish who may approve and protect that authority |
| Terminal confirmation | Reduces accidental acceptance | Agents can allocate terminals; it does not prove a human typed it |
| OS lock and journal | Serializes commands and supports interrupted-write recovery | Keep one trusted workspace authority; avoid manual edits during apply |

## Two separate workspaces

Use one external-safe workspace for a cloud agent and another confidential workspace only with an approved local model/host. Create each with `--workspace PATH init`, then select its processor through `settings`. Import only owner-approved extracts into the cloud workspace with `--processor external-ok`. Keep identifying client notes and full confidential transcripts in the restricted workspace.

Put confidential directories outside the cloud agent's accessible project roots. Configure the host to deny filesystem reads/writes there and deny unauthorized network or connector access. A directory name or JSON flag alone cannot enforce this. Use synthetic sentinels to verify that an agent session actually cannot read the restricted location. If your host cannot provide the necessary restrictions, do not give it confidential files.

## Owner-controlled approval

For personal use, show the full proposal, obtain the owner's decision and record it. This is a workflow agreement with the agent. The default template does not authenticate an approver or cryptographically authorize changes.

For stronger separation:

1. Keep the authoritative workspace outside the proposing agent's filesystem authority. Only the owner or a separately controlled apply process may write it or its decision records.
2. Give the agent reviewed, processor-permitted source extracts through a separate read-only input folder and a writable draft/output folder. Do not give it the authoritative workspace, approval credentials or the trusted apply runner.
3. In an owner-controlled terminal/process, import the permitted evidence and run `propose` using the draft, summary and source pointers. Inspect `show PACKET-ID`, including every changed page and metadata field.
4. Have the owner record approval and run apply from that trusted environment. Export only the reviewed, permitted result back to the agent's input folder.
5. Verify with fictional files that the agent cannot alter the authoritative wiki, decision, journal or trusted runner. Log the host configuration and outcome privately. Recheck after changing host permissions.

The exact filesystem identities and host sandbox configuration depend on your environment and are not provisioned by this kit. Running the owner terminal under the same unrestricted agent-accessible account/path does not create this separation. Organizations needing authenticated approvals should use their existing protected review/apply service rather than treating local JSON as authentication.

Recordings and client evidence need a clear purpose, participant permission, permitted processors and retention owner. Restrict derived summaries and indexes too. Read [privacy](privacy.md) and [connections](connections.md) before bringing in real accounts.
