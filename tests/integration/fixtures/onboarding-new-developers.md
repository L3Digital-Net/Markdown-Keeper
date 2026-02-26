---
title: Onboarding New Developers
tags: onboarding,team,process
category: process
concepts: onboarding,setup,environment,getting-started,mentorship
---

# Onboarding New Developers

The first two weeks on a new team shape a developer's productivity for months. A structured onboarding process reduces time-to-first-commit from weeks to days and signals that the team values its people enough to invest in their ramp-up.

## Environment Setup and Tool Access

Before the new hire's start date, their manager should ensure the following accounts and permissions are provisioned: GitHub organization membership, CI/CD dashboard access, cloud provider IAM role, internal wiki read/write, and chat workspace membership. Waiting until day one to file access requests wastes the most energetic hours of someone's tenure on password resets and approval queues.

On day one, the developer should clone the primary repository and run the bootstrap script. Most of our projects use a single `./scripts/setup.sh` that installs dependencies, creates a local database, and runs the test suite. If the script fails, that is a bug in the script, not a problem with the new hire's machine. File an issue immediately and pair with them to fix it; this also serves as a gentle introduction to the contribution workflow.

The local development stack requires Python 3.10+, Docker, and a running PostgreSQL instance (or the Docker Compose file handles it). Editor choice is personal, but we maintain shared configuration for VS Code in the repository's `.vscode/` directory, including recommended extensions and debug launch configs. See the [project documentation guide](./project-documentation-guide.md) for details on where configuration lives.

## Codebase Orientation

Schedule three 30-minute walkthroughs during the first week. The first covers high-level architecture: service boundaries, data flow, and deployment topology. The second focuses on the area of the codebase where the new developer will make their first changes. The third walks through the CI/CD pipeline from commit to production, including how feature flags, canary deployments, and rollback procedures work.

Resist the temptation to do these as monologues. Ask the new developer to share their screen, navigate the code, and narrate what they think each component does. Misconceptions caught in week one prevent bugs in week four.

Assign a "starter task" that is genuinely useful, scoped to a single file or module, and has a clear definition of done. Good examples: fix a known minor bug, add a missing unit test, or update an out-of-date docstring. Avoid contrived exercises or tasks that will be thrown away. Nothing deflates motivation like learning your first PR was busy work.

## Mentorship and Feedback Loops

Pair the new developer with a mentor who is not their manager. The mentor's role is to answer the questions that feel too small to bring to a team meeting, review early pull requests with extra context, and check in informally twice a week.

At the end of week one, the manager should hold a brief retro: what went well, what was confusing, what is still blocked. Document the answers and feed them back into the onboarding checklist for the next hire. Onboarding materials that are not updated after each cohort become stale fast.

At the 30-day mark, schedule a more formal check-in. By this point the developer should have merged several PRs, attended a sprint planning session, and participated in at least one [incident response](./incident-response-playbook.md) drill or review. If any of those have not happened, adjust the plan rather than assuming the developer will figure it out on their own.
