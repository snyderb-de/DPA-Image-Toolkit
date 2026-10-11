# Domain Docs

## Layout

This is a single-context repository. Domain vocabulary lives in root `CONTEXT.md`; architecture decisions live in `docs/adr/`.

## Before Exploring

Read `CONTEXT.md` and ADRs relevant to the area being changed. If `CONTEXT-MAP.md` exists later, follow its pointers to relevant contexts.
If these documents do not exist, proceed silently. Do not create empty domain documents or flag their absence; domain-modeling work creates them when terms or decisions are resolved.

## Vocabulary

Use domain terms defined in `CONTEXT.md` in issue titles, tests, hypotheses, and proposals. Avoid synonyms the glossary explicitly excludes.
Reconsider invented terminology; record real vocabulary gaps during domain modeling.

## Decisions

Read relevant ADRs before proposing changes. Explicitly identify any conflict with an existing ADR and explain why reopening the decision is warranted.
