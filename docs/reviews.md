# Daily and weekly work

## Daily brief

Run `python3 brain.py brief --save` for pending-decision and health status, then read the current permitted wiki and evidence for the active goal. The generated file is a scaffold; it does not invent priorities. Check the canonical experiment, delivery and commercial systems where connected. Read pending decision packets before suggesting new work. Write up to three priorities with evidence date, accountable owner, next action, desired completion evidence and review date. Keep unknown owners and outcomes explicit.

Mention changed or urgent evidence and pending human decisions. Use [the brief template](../templates/brief.md) and save the brief under the private workspace's daily directory. Daily work may create its brief and checkpoint. Knowledge changes go through proposals. A missing source stays visible with its last known date and recovery step.

## Weekly review

Choose a reporting window and relevant sources. Run

```sh
python3 brain.py review 2026-w48
```

For a worked procedure, read [the generic weekly-review skill](../skills/weekly-review/SKILL.md). Use a lowercase ISO-week label or a descriptive period such as `client-project-november`. The folder contains coverage notes and pending role files. It prepares instructions, and the selected coding agent runs those instructions. A folder's existence does not mean the roles completed.

1. Complete delta.md with reporting window, source dates, scope, unavailable data, experiments and current commitments. Aggregate metrics need definitions, baseline and comparable observation windows.
2. Run [research](../agents/research.md) first. Read targeted feedback and record recurring needs, exceptions, sample limitations and evidence pointers in research.md.
3. Run the relevant domain reviewers. [Marketing](../agents/marketing.md), [sales](../agents/sales.md), [product](../agents/product.md), [delivery](../agents/delivery.md) and [strategy](../agents/strategy.md) each own exactly their report. Each consumes delta.md and research.md, then retrieves relevant permitted sources. A coach or freelancer may need only research and delivery. A team may use every role.
4. Run [coordinator](../agents/coordinator.md) last. Reconcile overlapping recommendations and conflicting facts into coordinator.md. Include a numbered decision agenda with proposed change, current wording, replacement wording, sources, implications and missing evidence. Record completed roles and next phase in run-state.json.
5. Draft each approved-direction topic update and call propose for it. The human can approve all presented items or choose exclusions. Record approval for each accepted proposal only after this response. Use show for the full diff, record only the explicit human decision, then apply accepted packets and run health. Approval is attributable local history, not identity authentication. Link the decision and resulting evidence back to the canonical task or experiment during the user's normal process.
6. Review next week whether the approved action was executed and produced its intended outcome. A decision, completed work and measured improvement have separate evidence.

Roles share evidence, dates and definitions. They write reports, and the coordinator creates proposals. Keep reports under 600 words unless specific evidence requires more. Every finding cites a source and version. With no relevant change, report the gap or unchanged state briefly. Do not invent a KPI merely to fill a table.

## Correct and improve

When an answer is wrong, record the correction and evidence in a new proposal. Test the original question again and check neighboring claims. Update the topic after human review and add a synthetic regression case when the failure affects generic tooling. This makes the loop improve beyond one chat.

## Scheduling

Run manually first. A host scheduler can run daily briefs or weekly preparation using these saved procedures after you configure it. Set timezone, owner, budget, source permissions and one producer per job. Scheduled preparation ends with a decision packet. A scheduled process cannot record human approval for its own changes. Save actual start/end, provider/model, coverage, errors and output paths. Notify on meaningful changes or requests for action. Before restarting a job, check existing run folders to prevent duplicate reviews.
