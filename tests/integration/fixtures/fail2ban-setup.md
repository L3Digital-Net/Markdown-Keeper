---
title: Protecting Servers with fail2ban
tags: fail2ban,security,intrusion-prevention
category: security
concepts: fail2ban,intrusion,ban,jail,iptables
---

## Installation and Basic Configuration

fail2ban monitors log files for patterns indicating brute-force attacks and temporarily bans offending IP addresses using firewall rules. It is one of the first things to install on any internet-facing server.

```bash
apt install fail2ban
```

Never edit `/etc/fail2ban/jail.conf` directly since package upgrades overwrite it. Create a local override file instead:

```bash
cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
```

Or, better yet, create a drop-in file at `/etc/fail2ban/jail.d/custom.conf` with only your changes:

```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
banaction = nftables-multiport
ignoreip = 127.0.0.1/8 10.0.0.0/8

[sshd]
enabled = true
port = ssh
logpath = %(sshd_log)s
maxretry = 3
bantime = 7200
```

`findtime` is the window in which `maxretry` failures trigger a ban. With these settings, three failed SSH logins within 10 minutes result in a two-hour ban. The `ignoreip` directive whitelists your management network so you do not accidentally lock yourself out.

The `banaction` determines which firewall backend is used. On modern systems with nftables, use `nftables-multiport`. On older iptables-based systems, the default `iptables-multiport` works. Check which firewall your system uses before setting this.

## Filter Rules and Custom Jails

fail2ban ships with filters for common services: sshd, nginx, apache, postfix, dovecot, and many others. Filters are regex patterns that extract the offending IP from log lines.

View the built-in sshd filter:

```bash
cat /etc/fail2ban/filter.d/sshd.conf
```

To create a custom jail for a web application that logs failed logins to `/var/log/myapp/auth.log`:

```ini
# /etc/fail2ban/filter.d/myapp.conf
[Definition]
failregex = ^.*Authentication failed for .* from <HOST>.*$
ignoreregex =
```

```ini
# /etc/fail2ban/jail.d/myapp.conf
[myapp]
enabled = true
filter = myapp
logpath = /var/log/myapp/auth.log
maxretry = 5
bantime = 1800
```

Test your filter against real log data before enabling it:

```bash
fail2ban-regex /var/log/myapp/auth.log /etc/fail2ban/filter.d/myapp.conf
```

This shows how many lines matched the `failregex` and how many matched `ignoreregex`. If the match count is zero, your regex needs adjustment. Common mistakes include anchor characters not matching the full log format and timezone differences in timestamps.

## Monitoring and Management

Start fail2ban and check which jails are active:

```bash
systemctl enable --now fail2ban
fail2ban-client status
fail2ban-client status sshd
```

The status command shows the number of currently banned IPs and total bans since the last restart. To manually unban an IP (useful when you accidentally trigger the filter yourself):

```bash
fail2ban-client set sshd unbanip 203.0.113.50
```

To see all currently banned IPs across all jails:

```bash
fail2ban-client banned
```

For persistent visibility into ban activity, check the fail2ban log at `/var/log/fail2ban.log`. Each ban and unban action is logged with a timestamp and the triggering jail. Integrate this with your [monitoring stack](./prometheus-alerting.md) using a log exporter or a custom script that tracks ban frequency.

fail2ban works best as one layer in a defense-in-depth strategy. Combine it with [SSH key-only authentication](./ssh-key-management.md), rate limiting at the firewall level, and network segmentation. On its own, fail2ban reduces noise from automated scanners, but a determined attacker with a botnet can rotate source IPs faster than fail2ban can ban them. For more details on action configuration, see the [fail2ban wiki](https://github.com/fail2ban/fail2ban/wiki).
