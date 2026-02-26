---
title: Project Documentation Guide
tags: documentation,writing,process
category: process
concepts: documentation,markdown,readme,changelog
---

# Project Documentation Guide

Good documentation is the difference between a project that others can adopt and one that dies in obscurity. This guide covers the key artifacts every project should maintain, along with practical advice for keeping them accurate over time.

## README Structure

The README is the front door of your project. A reader who lands on your repository should understand what the project does, how to install it, and how to run a basic example within 60 seconds.

Start with a one-paragraph summary that avoids jargon. Follow it with installation instructions that include the exact shell commands, not just prose descriptions. A quick-start section with a minimal working example goes a long way; people copy-paste before they read.

Include a section on prerequisites (runtime versions, system libraries, OS constraints) and another on configuration. If the project exposes environment variables or config files, list them in a table with defaults and descriptions. Link out to the full [API documentation](./architecture-decision-records.md) rather than duplicating it inline.

Badge rows at the top (build status, coverage, latest version) are useful but keep them to five or fewer. A wall of badges signals insecurity more than quality.

## API Docs and Architecture Diagrams

Treat documentation as code. Store it in the repository alongside the source, write it in Markdown or reStructuredText, and render it through a static site generator like MkDocs or Sphinx. This keeps docs version-locked to the code they describe, which eliminates the "docs say v2 but the code is v3" problem.

For API references, generate them from docstrings or OpenAPI specs whenever possible. Hand-written API docs drift within weeks. Automated generation from source is not a silver bullet, but it sets a floor that manual prose cannot.

Architecture diagrams should live in a `docs/` directory as both source (Mermaid, PlantUML, or draw.io XML) and rendered images. Never commit only a PNG with no editable source; the next person who needs to update the diagram will redraw it from scratch, poorly. Diagrams should show component boundaries, data flow direction, and external dependencies. Internal implementation details belong in code comments, not architecture diagrams.

## Changelog Maintenance

A changelog is a curated, human-readable history of notable changes. It is not a git log dump. Follow the [Keep a Changelog](https://keepachangelog.com/) format: group entries under Added, Changed, Deprecated, Removed, Fixed, and Security. Date each release. Link each version heading to the corresponding diff on your hosting platform.

Update the changelog in the same pull request that introduces the change. If you defer it to a "changelog cleanup" pass before release, entries will be vague or missing. The person who wrote the code is the person best positioned to describe it.

For projects that publish to package registries, the changelog doubles as release notes. Write entries with your users in mind: what changed from their perspective, not yours. "Refactored query planner internals" means nothing to a consumer; "queries with nested JOINs now execute up to 40% faster" does.

Adopting a doc-as-code approach across all these artifacts keeps the barrier to contribution low. Contributors already know how to edit text files and open pull requests. No wiki logins, no CMS permissions, no separate toolchain to learn.
