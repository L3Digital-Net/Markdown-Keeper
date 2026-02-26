---
title: Setting Up Prometheus Alerting with Grafana
tags: prometheus,monitoring,alerting
category: monitoring
concepts: prometheus,alerting,grafana,metrics,alertmanager
---

## Defining Alert Rules

Prometheus evaluates alerting rules at regular intervals and fires alerts when conditions are met. Rules live in YAML files referenced by the `rule_files` directive in `prometheus.yml`:

```yaml
# prometheus.yml
rule_files:
  - /etc/prometheus/rules/*.yml

# /etc/prometheus/rules/node_alerts.yml
groups:
  - name: node_health
    interval: 30s
    rules:
      - alert: HighCpuUsage
        expr: 100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 85
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage on {{ $labels.instance }}"
          description: "CPU usage has exceeded 85% for more than 10 minutes."

      - alert: DiskSpaceLow
        expr: (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100 < 10
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Disk space below 10% on {{ $labels.instance }}"
```

The `for` clause prevents flapping by requiring the condition to hold continuously for the specified duration before the alert fires. Without it, a momentary CPU spike would trigger a notification immediately.

Use `promtool check rules /etc/prometheus/rules/node_alerts.yml` to validate syntax before reloading. A broken rules file will prevent Prometheus from starting entirely.

## Configuring Alertmanager

Prometheus sends fired alerts to Alertmanager, which handles deduplication, grouping, silencing, and routing to notification channels. A basic Alertmanager config:

```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'smtp.example.com:587'
  smtp_from: 'alerts@example.com'

route:
  receiver: 'email-default'
  group_by: ['alertname', 'instance']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty-critical'

receivers:
  - name: 'email-default'
    email_configs:
      - to: 'ops@example.com'

  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key: '<pagerduty-integration-key>'
```

The `group_by` setting bundles related alerts into a single notification. Grouping by `alertname` and `instance` means you get one email per host per alert type rather than a flood of individual messages. `repeat_interval` controls how often a still-firing alert re-sends; set this high enough to avoid alert fatigue but low enough that people do not forget about ongoing problems.

Point Prometheus at Alertmanager in `prometheus.yml`:

```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['localhost:9093']
```

## Building Grafana Dashboards

Grafana visualizes the same metrics Prometheus collects and can display alert states directly on dashboards. Add Prometheus as a data source in Grafana (Settings > Data Sources > Add > Prometheus) pointing to `http://localhost:9090`.

Create a dashboard with panels for the metrics your alerts monitor. A CPU usage panel querying `100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)` shows the same data your alert rule evaluates, making it easy to correlate spikes with fired alerts.

Grafana also has its own alerting system (Grafana Alerting, unified in v9+), which can evaluate queries and send notifications independently of Prometheus Alertmanager. For simple setups, using Grafana alerting alone is viable. For complex routing, silencing, and on-call schedules, Alertmanager remains the better choice.

Set up notification contact points in Grafana under Alerting > Contact Points. Slack webhooks, email, and PagerDuty are all supported natively. Test each contact point after creation to confirm delivery.

For monitoring your backup jobs and database health, integrate the PostgreSQL exporter and alert on failed [backup scripts](./postgresql-backup.md). The [Prometheus project documentation](https://prometheus.io/docs/alerting/latest/overview/) covers additional receiver types and advanced routing configurations.
