# Issue Tracker: GitHub

Issues and specs live in GitHub Issues for `snyderb-de/DPA-Image-Toolkit`.
Use the `gh` CLI from this repository, or supply `--repo snyderb-de/DPA-Image-Toolkit` explicitly.

## Conventions

- Create: `gh issue create --title "..." --body-file <file>`.
- Read: `gh issue view <number> --comments`; inspect the body and labels with `gh issue view <number> --json number,title,body,labels,state`.
- List: `gh issue list --state open --json number,title,body,labels,comments`, using label filters when appropriate.
- Comment: `gh issue comment <number> --body-file <file>`.
- Label: `gh issue edit <number> --add-label "..."` or `--remove-label "..."`.
- Close: `gh issue close <number> --comment "..."`.

Use a body file for multiline text. Check existing issues before creating a duplicate.
Use the mappings in `docs/agents/triage-labels.md` for triage states.
Review findings become individual bug issues with reproduction steps, expected behavior, affected code, acceptance criteria, and a link to the originating PR/review.
Keep P1/P2 severity in the issue title; severity is separate from triage state.

## Pull Requests as a Triage Surface

**PRs as a request surface: no.**

Pull requests are reviewed as proposed changes. Confirmed review findings may become linked issues when requested, but PRs are not automatically included in the triage queue.
GitHub shares issue and PR numbers: use `gh pr view <number>` and fall back to `gh issue view <number>` when resolving an unknown reference.

## Skill Operations

When a skill says "publish to the issue tracker", create a GitHub issue.
When a skill says "fetch the relevant ticket", run `gh issue view <number> --comments` and inspect its labels.

## Wayfinding Operations

- Map: one issue labelled `wayfinder:map`, holding Notes, Decisions-so-far, and Fog. Create the label only when that workflow is used.
- Children: link tickets as native GitHub sub-issues. If unavailable, use a task list in the map and a `Part of #<map>` line in each child. Use `wayfinder:<type>` labels (research, prototype, grilling, task) when needed.
- Blocking: use native GitHub issue dependencies with `gh api --method POST repos/snyderb-de/DPA-Image-Toolkit/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-database-id>`. Obtain the database ID using `gh api repos/snyderb-de/DPA-Image-Toolkit/issues/<number> --jq .id`. If unavailable, use a `Blocked by: #<number>` line.
- Frontier: select the first open child in map order with no open blockers and no assignee.
- Claim: assign the ticket to the driving developer using `gh issue edit <number> --add-assignee @me`.
- Resolve: comment with the answer, close the ticket, and add an evidence/context link to the map's Decisions-so-far.
