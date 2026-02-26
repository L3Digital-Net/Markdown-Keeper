---
title: Git Branching Strategies for Teams
tags: git,version-control,workflow
category: development
concepts: git,branch,merge,rebase,trunk-based
---

## Trunk-Based Development vs GitFlow

The choice between trunk-based development and GitFlow depends on team size, release cadence, and deployment automation maturity. Trunk-based development keeps everyone committing to a single `main` branch (or very short-lived feature branches), relying on feature flags and CI gates to keep the trunk releasable at all times. Teams shipping continuously, with strong test coverage, tend to prefer this model because it minimizes merge conflicts and keeps the feedback loop tight.

GitFlow introduces long-lived `develop`, `release/*`, and `hotfix/*` branches alongside `main`. It was designed for projects with scheduled releases and multiple supported versions. The extra ceremony costs coordination effort; merge conflicts between `develop` and release branches are common when fixes must be cherry-picked in both directions. For most web applications deployed from a single version, GitFlow adds overhead without proportional benefit.

A middle ground works well for many teams: short-lived feature branches (1-3 days) off `main`, with CI running on every push and a merge queue enforcing linear history. This gives code review a natural home without the drift that long-lived branches invite.

For how branching interacts with CI pipelines, see [ci-pipeline-best-practices](./ci-pipeline-best-practices.md).

## Feature Branches, Merge, and Rebase

Feature branches should be small and focused. A branch that touches 15 files across 4 subsystems is harder to review and more likely to conflict than three separate branches each addressing one concern. The [GitHub flow guide](https://docs.github.com/en/get-started/using-github/github-flow) recommends keeping branches short-lived for this reason.

The merge vs rebase question is partly aesthetic and partly practical. `git merge --no-ff` preserves the branch topology in the commit graph, making it easy to see where a feature started and ended. `git rebase` produces a linear history that reads cleanly in `git log --oneline` but rewrites commit hashes, which complicates collaboration if the branch is shared.

A reasonable default: rebase locally before pushing (to clean up WIP commits), then merge to `main` with a merge commit. This gives you linear local history and visible merge points on the mainline. Avoid rebasing branches that others have pulled; force-pushing a shared branch is a reliable way to generate confusion and lost work.

Interactive rebase (`git rebase -i`) is valuable for squashing "fix typo" and "WIP" commits before opening a pull request. The goal is a commit history where each commit represents a coherent, reviewable unit of change, not a diary of the developer's keystrokes.

## Release Branches and Hotfixes

Release branches are useful when you need to stabilize a version while development continues on `main`. Cut a `release/1.2` branch, apply only bug fixes to it, and tag the final commit as `v1.2.0`. Backporting fixes from `main` to a release branch is straightforward with `git cherry-pick`, though conflicts arise when the codebases diverge.

Hotfix workflow: branch from the release tag (not from `main`), fix the issue, tag a patch release, then forward-port the fix to `main`. Skipping the forward-port is a common source of regression; the fix exists in production but the next release reintroduces the bug because `main` never received the change.

Tagging conventions matter. Use annotated tags (`git tag -a v1.2.0 -m "Release 1.2.0"`) rather than lightweight tags so the tagger identity and date are recorded. Semantic versioning gives downstream consumers a machine-readable signal about compatibility expectations. See [code-review-checklist](./code-review-checklist.md) for how branching strategy connects to the review workflow.
