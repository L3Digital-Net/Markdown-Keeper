---
title: CI/CD Pipeline Best Practices
tags: ci,pipeline,automation
category: devops
concepts: ci,pipeline,github-actions,automation,deployment
---

## Pipeline Stages and Parallel Jobs

A well-structured CI pipeline separates concerns into stages that run in dependency order: install, lint, test, build, deploy. Each stage gates the next; if linting fails, tests never run, which saves compute and gives faster feedback on trivial issues.

Within a stage, independent jobs should run in parallel. Linting, type checking, and unit tests have no dependencies on each other; running them concurrently on separate runners cuts wall-clock time significantly. GitHub Actions expresses this with a job matrix or separate jobs under the same workflow:

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install ruff && ruff check src/

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install mypy && mypy src/

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e ".[test]" && pytest tests/
```

Integration tests and end-to-end tests typically run after unit tests pass, in a subsequent stage. They are slower, may require service containers (databases, message brokers), and their failures are more expensive to investigate. Gating them behind the fast checks avoids wasting runner minutes on a build that would fail linting anyway.

For how testing patterns feed into pipeline design, see [python-testing-patterns](./python-testing-patterns.md).

## Caching and Artifact Management

Dependency caching is the single highest-impact optimization for most pipelines. Downloading and installing packages on every run wastes time and bandwidth. GitHub Actions provides `actions/cache` keyed on lockfile hashes:

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: pip-${{ hashFiles('requirements.lock') }}
    restore-keys: pip-
```

Cache hits skip the install step almost entirely. For Node.js projects, cache `node_modules` keyed on `package-lock.json`. For Rust, cache the `target/` directory keyed on `Cargo.lock`. The principle is the same: deterministic inputs produce deterministic outputs, so cache the outputs.

Build artifacts (compiled binaries, container images, test reports) should be uploaded and passed between stages rather than rebuilt. GitHub Actions artifacts persist across jobs within a workflow run. For container images, push to a registry (GHCR, ECR, Docker Hub) with a tag derived from the commit SHA, then reference that exact tag in the deployment stage.

Avoid caching things that change on every run (timestamps, random seeds in test data). A cache that never hits is worse than no cache because it adds the overhead of saving and restoring without the benefit. Refer to the [GitHub Actions caching documentation](https://docs.github.com/en/actions/using-workflows/caching-dependencies-to-speed-up-workflows) for size limits and eviction policies.

## Deployment Strategies and Safety

Deployment is the stage where mistakes are most visible. Progressive delivery strategies reduce blast radius. Blue-green deployment maintains two identical environments; traffic switches from blue to green atomically once the new version passes health checks. Canary deployment routes a small percentage of traffic (1-5%) to the new version, monitors error rates and latency, and gradually increases the percentage if metrics stay healthy.

Rolling deployments update instances one at a time behind a load balancer. They require no extra infrastructure but expose a window where two versions serve traffic simultaneously, which can break if the versions have incompatible API contracts or database schemas.

Feature flags decouple deployment from release. Code ships dark (deployed but disabled), then the flag is toggled when the feature is ready. This separates the question "is the code in production?" from "are users seeing the feature?" and lets you roll back a feature without redeploying.

Every deployment should be reversible within minutes. Automate rollback: if the health check endpoint returns errors within 5 minutes of a deploy, trigger an automatic revert to the previous version. Manual rollback procedures that require SSH access and command-line expertise do not scale and fail under pressure. See [code-review-checklist](./code-review-checklist.md) for pre-merge checks that reduce the likelihood of deploying broken code in the first place.
