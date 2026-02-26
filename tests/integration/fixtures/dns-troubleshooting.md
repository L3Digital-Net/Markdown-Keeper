---
title: Diagnosing and Fixing DNS Resolution Issues
tags: dns,networking,troubleshooting
category: networking
concepts: dns,nameserver,dig,nslookup,resolv
---

## Identifying the Problem

DNS resolution failures manifest in frustrating ways: services time out, curl reports "Could not resolve host," and applications log connection errors that look like network outages but are actually name resolution failures. The first step is confirming that DNS is the actual problem rather than a downstream connectivity issue.

Test basic resolution with `dig`:

```bash
dig example.com @8.8.8.8
```

If this returns an answer but `dig example.com` (using the system default resolver) does not, the problem is with your configured nameserver, not with DNS globally. Check `/etc/resolv.conf` to see which nameservers the system is using:

```bash
cat /etc/resolv.conf
```

On systems running systemd-resolved, this file is often a symlink to `/run/systemd/resolve/stub-resolv.conf` pointing to `127.0.0.53`. The actual upstream servers are configured elsewhere. Use `resolvectl status` to see the real upstream DNS servers and per-interface configuration.

`nslookup` provides a simpler output for quick checks:

```bash
nslookup example.com
nslookup example.com 1.1.1.1
```

If neither `dig` nor `nslookup` works against any resolver, check whether outbound UDP port 53 is blocked by a firewall. On cloud instances, security groups frequently block DNS traffic by default.

## Common Failures and Fixes

**Stale DNS cache.** If a record was recently changed but the old value persists, the local resolver or an upstream cache is serving stale data. On systemd-resolved systems, flush with:

```bash
resolvectl flush-caches
```

On systems using dnsmasq or nscd, restart the respective service. Browser DNS caches are separate from the OS cache; Chrome maintains its own at `chrome://net-internals/#dns`.

**Wrong or missing nameservers.** If `/etc/resolv.conf` is empty or points to a dead nameserver, nothing resolves. This commonly happens after DHCP lease changes, VPN connections overwriting the file, or misconfigured NetworkManager. Set reliable nameservers temporarily:

```bash
echo "nameserver 1.1.1.1" | sudo tee /etc/resolv.conf
```

For a permanent fix, configure the nameservers through NetworkManager or netplan rather than editing resolv.conf directly, since the file gets overwritten.

**NXDOMAIN for internal hostnames.** If public domains resolve fine but internal names fail, the `search` directive in resolv.conf may be wrong. This directive appends a domain suffix to unqualified hostnames. Verify it matches your internal domain:

```
search internal.example.com
nameserver 10.0.0.2
```

**Intermittent resolution failures.** If DNS works sometimes but not always, you likely have multiple nameservers configured and one is unhealthy. The resolver tries them in order with a timeout (typically 5 seconds), causing sporadic delays. Remove the dead nameserver or fix it.

## Advanced Diagnostics

For persistent issues, trace the full resolution path with `dig +trace`:

```bash
dig +trace example.com
```

This walks the delegation chain from root servers down to the authoritative nameserver, showing exactly where the resolution breaks. It bypasses local caching entirely.

To check whether a specific DNS record type is present (MX, TXT, CNAME), specify the type:

```bash
dig MX example.com
dig TXT _dmarc.example.com
```

Monitor DNS performance over time by logging query latency. A sudden increase in resolution time often precedes outright failures. Tools like `dnstop` or Prometheus with the [blackbox exporter](https://github.com/prometheus/blackbox_exporter) can track DNS health continuously.

For container environments, DNS problems have an additional layer. Kubernetes pods use CoreDNS, not the host resolver. If pod DNS fails but host DNS works, check the CoreDNS pods and configmap. See the [Kubernetes setup guide](./kubernetes-setup.md) for CoreDNS troubleshooting.
