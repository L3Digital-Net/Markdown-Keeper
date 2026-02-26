---
title: Code Review Best Practices and Checklist
tags: code-review,quality,process
category: development
concepts: code-review,pull-request,quality,linting
---

## The Review Process

Code review serves two purposes: catching defects before they reach production and spreading knowledge across the team. Both matter, but teams that treat review purely as a gatekeeping exercise miss the knowledge-sharing benefit entirely.

Review the pull request description before reading the code. The description should explain *why* the change exists, not just what it does. A PR titled "Update handler.py" with no description forces the reviewer to reverse-engineer intent from a diff, which is slow and error-prone. If the description is missing, send it back and ask for one; this is not nitpicking, it is setting a baseline for communication.

Read the diff top-down: start with tests. Tests reveal the author's intent more clearly than implementation code. If the tests make sense and cover the stated behavior, the implementation review becomes a matter of verifying correctness and style rather than guessing at requirements. Missing tests for new behavior should block the review.

Keep review turnaround under 24 hours. Stale PRs accumulate merge conflicts, block dependent work, and frustrate the author. If you cannot review in time, say so and let someone else pick it up. The [Google engineering practices guide](https://google.github.io/eng-practices/review/reviewer/) recommends same-day turnaround as a default.

## Common Issues and Constructive Feedback

Distinguish between blocking and non-blocking feedback. A security vulnerability or data loss risk blocks the PR. A variable naming preference does not. Prefix non-blocking comments with "nit:" or "optional:" so the author knows which feedback requires action and which is a suggestion.

Common issues worth flagging:

Error handling gaps where exceptions are swallowed silently or error paths return ambiguous values. Race conditions in concurrent code, especially around shared mutable state. SQL injection from string interpolation instead of parameterized queries. Hardcoded secrets, even in test code, because test files often end up in public repositories.

Tone matters. "This is wrong" is less useful than "This will fail when `user_id` is None because the join condition won't match. Consider adding a guard clause." Attach context to criticism. The goal is a conversation between peers, not a verdict from an authority. If you find yourself writing paragraphs of feedback on a single PR, it may indicate the PR is too large rather than too flawed.

Automated checks (linters, formatters, type checkers) should handle style enforcement so that human reviewers focus on logic, design, and correctness. If a comment could be replaced by a linter rule, add the rule instead. See [python-testing-patterns](./python-testing-patterns.md) for patterns that make code more reviewable by keeping test intent clear.

## PR Size Guidelines and Automated Checks

Small PRs get faster, higher-quality reviews. Research consistently shows that review quality drops sharply beyond 400 lines of diff. A 2000-line PR will receive superficial approval because no reviewer can maintain focus across that much code. Split large features into a stack of small PRs that each make incremental progress toward the goal.

Strategies for keeping PRs small: separate refactoring from behavior changes. Extract a "prepare" PR that moves code around without changing functionality, then a "implement" PR that adds the new behavior on the clean foundation. Database migrations should be their own PR, deployed and verified before the application code that depends on the new schema.

Automated checks that should run before human review begins:

- Linting and formatting (ruff, eslint, prettier) to eliminate style discussions
- Type checking (mypy, tsc) to catch type errors mechanically
- Unit tests with coverage thresholds to enforce test discipline
- Dependency vulnerability scanning (dependabot, snyk) to flag known CVEs
- Commit message format validation if the project uses conventional commits

These checks run in CI and their status appears on the PR. Reviewers should not approve a PR with failing checks unless the failure is a known flake, documented and tracked. For CI pipeline structure, see [ci-pipeline-best-practices](./ci-pipeline-best-practices.md). For branching workflows that affect PR flow, see [git-branching-strategy](./git-branching-strategy.md).
