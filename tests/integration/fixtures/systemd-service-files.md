---
title: Writing and Managing systemd Service Unit Files
tags: systemd,linux,services
category: system
concepts: systemd,service,unit,timer,journalctl
---

## Anatomy of a Service Unit File

A systemd service unit file consists of three sections that define what the service is, how it runs, and when it should be enabled. Unit files live in `/etc/systemd/system/` for administrator-created services.

```ini
[Unit]
Description=My Application Server
Documentation=https://example.com/docs
After=network-online.target postgresql.service
Wants=network-online.target
Requires=postgresql.service

[Service]
Type=simple
User=appuser
Group=appuser
WorkingDirectory=/opt/myapp
ExecStart=/opt/myapp/venv/bin/python server.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=APP_ENV=production
EnvironmentFile=/etc/myapp/env

[Install]
WantedBy=multi-user.target
```

The `[Unit]` section declares ordering and dependencies. `After=` controls startup order (start this unit after those targets/services). `Requires=` creates a hard dependency: if PostgreSQL fails to start, this service will not start either. `Wants=` is a soft dependency; the service starts regardless of whether the wanted unit succeeds.

The `[Service]` section defines execution. `Type=simple` means the process started by `ExecStart` is the main process. Other common types: `forking` for daemons that fork and exit the parent, `oneshot` for scripts that run once and exit, and `notify` for processes that signal readiness via `sd_notify`.

`Restart=on-failure` restarts the process if it exits with a non-zero status. `RestartSec=5` adds a delay to prevent tight restart loops. For critical services, use `Restart=always` but combine it with `StartLimitIntervalSec` and `StartLimitBurst` to cap the number of restarts in a given window:

```ini
StartLimitIntervalSec=300
StartLimitBurst=5
```

This allows five restarts within five minutes before systemd gives up and marks the unit as failed.

## Timers as Cron Replacements

systemd timers offer more flexibility than cron: they log to the journal, can depend on other units, support randomized delays, and handle missed runs gracefully.

Create a timer unit alongside a service unit. The timer activates the matching service:

```ini
# /etc/systemd/system/backup.timer
[Unit]
Description=Daily database backup

[Timer]
OnCalendar=*-*-* 02:00:00
RandomizedDelaySec=900
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/backup.service
[Unit]
Description=Database backup job

[Service]
Type=oneshot
ExecStart=/usr/local/bin/backup-database.sh
```

`Persistent=true` means if the machine was off when the timer should have fired, it runs immediately at next boot. `RandomizedDelaySec` spreads execution across a window to avoid all servers hitting a backup target simultaneously.

Enable and start the timer (not the service):

```bash
systemctl enable --now backup.timer
systemctl list-timers --all
```

## Managing and Debugging Services

Reload systemd after creating or modifying unit files:

```bash
systemctl daemon-reload
systemctl enable --now myapp.service
```

View logs with journalctl. Filter by unit and follow in real time:

```bash
journalctl -u myapp.service -f
journalctl -u myapp.service --since "1 hour ago"
journalctl -u myapp.service -p err
```

The `-p err` flag filters to error-level messages and above, cutting through noise when debugging a startup failure.

Check unit status and recent log lines:

```bash
systemctl status myapp.service
```

If a service fails to start, `systemctl status` shows the exit code and last few journal lines. Common problems include wrong file permissions on the ExecStart binary, missing environment variables, and the `User=` account not existing. For automated deployment of service files across multiple servers, use [Ansible playbooks](./ansible-playbooks.md) with the `systemd` module. The [systemd documentation](https://www.freedesktop.org/software/systemd/man/) provides the full reference for all unit file directives.
