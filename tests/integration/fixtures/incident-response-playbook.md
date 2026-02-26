---
title: Incident Response Playbook
tags: incident-response,operations,reliability
category: operations
concepts: incident,response,escalation,postmortem,sla
---

# Incident Response Playbook

Production incidents are inevitable. What separates resilient teams from chaotic ones is not the absence of failure but the speed and clarity of the response. This playbook defines severity levels, escalation paths, and communication expectations for any production-impacting event.

## Severity Levels and Escalation

We use four severity levels. The on-call engineer who first acknowledges the alert assigns the initial severity; it can be adjusted up or down as more information emerges.

**SEV-1 (Critical):** Complete service outage or data loss affecting all users. SLA target: acknowledge within 5 minutes, mitigate within 30 minutes. Escalate immediately to the engineering lead and notify the VP of Engineering. Open a dedicated incident channel. Customer-facing status page must be updated within 10 minutes of declaration.

**SEV-2 (Major):** Significant degradation affecting a large subset of users, or a single critical workflow is broken. SLA target: acknowledge within 15 minutes, mitigate within 2 hours. The on-call engineer leads response and pages additional domain experts as needed. Status page update within 20 minutes.

**SEV-3 (Minor):** Partial degradation with a known workaround, or a non-critical feature is unavailable. SLA target: acknowledge within 1 hour, resolve within 1 business day. No status page update required unless customer support volume spikes.

**SEV-4 (Low):** Cosmetic issue or minor inconvenience with no measurable user impact. Tracked as a normal bug ticket. No paging, no incident channel.

Escalation is not a sign of failure. If the on-call engineer has not identified a root cause within 15 minutes on a SEV-1, they should page the next tier without hesitation. Refer to the [on-call rotation schedule](https://wiki.internal.example.com/oncall) for current contacts.

## Communication During Incidents

Use a structured update format in the incident channel every 15 minutes for SEV-1 and every 30 minutes for SEV-2. Each update should include: current status (investigating / identified / mitigating / resolved), what changed since the last update, and the next action being taken.

External communication goes through the status page and, for SEV-1 events lasting more than 30 minutes, a direct email to affected enterprise customers. Draft the email from the template in the [communication runbook](./onboarding-new-developers.md) and have the incident commander approve it before sending.

Avoid speculation in public communications. Statements like "we believe the issue is related to a recent deployment" create liability. Stick to observable facts: what is affected, what users can expect, and when the next update will be posted.

## Root Cause Analysis and Postmortems

Every SEV-1 and SEV-2 incident gets a written postmortem within 5 business days. The postmortem is blameless; its purpose is to improve systems, not to assign fault to individuals.

The format follows five sections: summary (2-3 sentences), timeline (timestamped events from detection to resolution), root cause (technical explanation), contributing factors (process or tooling gaps that allowed the root cause to manifest), and action items (each assigned to a specific owner with a due date).

Postmortems are stored in the `postmortems/` directory of the engineering wiki and reviewed in a weekly incident review meeting. Action items are tracked as tickets in the team's backlog with the `postmortem` label so they can be reported on separately.

The most common antipattern in postmortem culture is writing them and never reading them again. Schedule a quarterly review of open postmortem action items. If items are consistently deprioritized, that itself is a finding worth discussing.
