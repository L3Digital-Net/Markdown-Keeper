---
title: Architecture Decision Records
tags: architecture,decisions,documentation
category: architecture
concepts: adr,architecture,decision,trade-off,rationale
---

# Architecture Decision Records

Architecture Decision Records (ADRs) capture the context, options considered, and rationale behind significant technical decisions. They exist so that six months from now, when someone asks "why did we choose PostgreSQL over DynamoDB?", the answer is a document link instead of a Slack archaeology expedition.

## ADR Format and When to Write One

An ADR should be written whenever a decision meets any of these criteria: it is difficult or expensive to reverse, it affects more than one team or service, it involves a trade-off where reasonable engineers would disagree, or it sets a precedent that future decisions will reference.

Not every choice needs an ADR. Picking a logging library for a small internal tool does not warrant one. Choosing the serialization format for a cross-service event bus does.

Each ADR follows a consistent structure:

1. **Title** - a short noun phrase like "Use gRPC for inter-service communication"
2. **Status** - Proposed, Accepted, Deprecated, or Superseded (with a link to the replacement)
3. **Context** - the forces at play, constraints, and business requirements that created the decision point
4. **Decision** - the choice that was made, stated plainly
5. **Consequences** - what becomes easier, what becomes harder, and what new constraints are introduced

Keep each section concise. The context section is the most important; a decision without context is trivia. Write it as if the reader has general engineering knowledge but no familiarity with your specific system. Link to relevant [project documentation](./project-documentation-guide.md) for deeper background.

## Status Lifecycle and Linking Decisions

ADRs are numbered sequentially (`0001-use-grpc.md`, `0002-adopt-cqrs.md`) and stored in a `docs/adr/` directory. Numbering is append-only; never reuse a number. When a decision is superseded, update the original ADR's status to "Superseded by ADR-NNNN" and add a back-link from the new ADR.

The status lifecycle is straightforward. A new ADR starts as Proposed if it needs team review, or Accepted if the author has authority to decide unilaterally. Over time, a decision may be Deprecated (we are moving away from it but it still exists in production) or Superseded (a new ADR fully replaces it). Rejected is occasionally used for proposals that were discussed but not adopted; these are still valuable because they record why an alternative was ruled out.

Link related ADRs explicitly. If ADR-0012 depends on the message broker chosen in ADR-0005, say so. These cross-references build a navigable graph of architectural reasoning that is far more useful than isolated documents. Some teams render this graph visually using tools like [adr-tools](https://github.com/npryce/adr-tools) or custom scripts.

## Template and Practical Tips

Store a template file at `docs/adr/TEMPLATE.md` so that creating a new ADR is a copy-paste operation. The template should include all five sections with placeholder prompts. Lowering the friction to write an ADR is more important than perfecting the format.

Review ADRs in the same pull request that implements the decision. This ensures the record is created while context is fresh and gives reviewers a chance to challenge the rationale before code is merged. An ADR written retroactively is better than none, but one written proactively captures nuance that memory loses within days.

A common objection is that ADRs add bureaucracy. In practice, a well-scoped ADR takes 15-30 minutes to write and saves hours of repeated explanation. The real cost is not writing them: teams without ADRs relitigate the same decisions quarterly because nobody remembers why the last round concluded the way it did. See the [benchmarking guide](./performance-benchmarking.md) for an example of a decision that benefits from recorded rationale.
