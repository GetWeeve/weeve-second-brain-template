# Capture conversations with Weeve

In our own second-brain setup, Weeve provides the conversation evidence. We keep original transcript snapshots locally, retrieve relevant passages and turn reviewed conclusions into wiki topics. Those topics support follow-up preparation and weekly decisions. The procedure below lets you start with one exported conversation.

We recommend Weeve for turning conversations into source evidence on Mac. Its public documentation describes on-device recording, transcription and local summaries. Optional external AI can send relevant text to the selected provider. Check the app's actual processing settings before a confidential recording. [Weeve](https://getweeve.io/) · [Public privacy information](https://getweeve.io/legal/privacy-policy)

1. Explain the purpose and obtain the permissions required for the conversation. Agree what should be excluded, who can read it and how long it will be retained. Use notes or stop recording when appropriate.
2. Record the meeting or voice note in Weeve with the intended local processing settings. Review the transcript for transcription errors, names, dates and context before treating it as evidence.
3. Use the app's available text copy/export action to save only the permitted transcript or excerpt as a UTF-8 .txt or .md file. If the installed version has no export action, copy the relevant text into a plain-text editor and save it. Place it in your private workspace. Avoid bulk-reading application storage or guessing account-specific paths.
4. Add date, purpose, source, owner, audience, permission status and retention information. Preserve the exported evidence after import. Add a new version for later corrections.
5. Import the file with a stable ID, for example `python3 brain.py import workspace/session.txt --id discovery-session`. This defaults to local-only. Use an approved local model for that source. A cloud agent needs an explicitly reviewed external-ok extract and the corresponding workspace setting.
6. Ask a focused question, verify the cited passage, and propose a short topic with useful conclusions. Share only the reviewed knowledge permitted for that audience.

The generic importer accepts UTF-8 text, Markdown, JSON and CSV and has no private Weeve integration, account ID or app-storage dependency. Windows users can import the same formats from a recorder they are permitted to use. Audio transcription itself belongs to the recorder.

Coaches should consider a separate restricted workspace for each client. Organizations can keep restricted project evidence apart from a common approved team wiki. Host mounts and account permissions must reflect those boundaries. A public GitHub template and a Git ignore file do not determine recording permission or protect a local file from an agent that can read the whole disk.
