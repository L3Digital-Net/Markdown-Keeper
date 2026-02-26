---
title: Managing SSH Keys for Secure Server Authentication
tags: ssh,security,authentication
category: security
concepts: ssh,key,authentication,authorized_keys,ssh-agent
---

## Generating Keys

SSH key pairs consist of a private key (kept secret on your workstation) and a public key (deployed to servers). Ed25519 is the recommended algorithm: smaller keys, faster operations, and no known weaknesses compared to older RSA.

```bash
ssh-keygen -t ed25519 -C "chris@workstation" -f ~/.ssh/id_ed25519
```

The `-C` flag adds a comment to help identify the key later. Set a strong passphrase when prompted. A passphrase-protected key is useless to an attacker who copies it from a compromised workstation, at least until they crack the passphrase.

For systems that require RSA (older equipment, some Git hosting providers), generate a 4096-bit key:

```bash
ssh-keygen -t rsa -b 4096 -C "chris@workstation" -f ~/.ssh/id_rsa
```

Never generate keys without a passphrase for interactive use. Passphrase-less keys are acceptable only for automated service accounts with tightly scoped `authorized_keys` restrictions (covered below).

## Deploying and Managing authorized_keys

Copy the public key to a remote server:

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@server.example.com
```

This appends the public key to `~/.ssh/authorized_keys` on the remote server and sets correct permissions. If `ssh-copy-id` is not available, do it manually:

```bash
cat ~/.ssh/id_ed25519.pub | ssh user@server "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

Permissions are critical. OpenSSH refuses to use `authorized_keys` if the file, the `.ssh` directory, or the home directory are writable by anyone other than the owner. The most common "key authentication not working" issue is a permissions problem.

For service accounts, restrict what a key can do by prefixing the entry in `authorized_keys`:

```
command="/usr/local/bin/backup.sh",no-port-forwarding,no-X11-forwarding,no-agent-forwarding ssh-ed25519 AAAA... backup-agent
```

This limits the key to running a single command, regardless of what the connecting client requests.

## ssh-agent and Key Rotation

Typing your passphrase on every connection is tedious. `ssh-agent` caches decrypted keys in memory for the duration of your session:

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

On modern Linux desktops, the GNOME or KDE keyring often acts as the SSH agent automatically. Check with `ssh-add -l` to see which keys are loaded.

For forwarding your agent to a jump host (so you can SSH from there to other servers without copying your private key), use `ssh -A jumphost`. Be cautious: anyone with root on the jump host can hijack your forwarded agent. Only forward to hosts you fully trust.

Rotate keys periodically, especially when team members leave or a workstation is decommissioned. The process is straightforward: generate a new key pair, deploy the new public key to all servers, verify connectivity, then remove the old public key from every `authorized_keys` file. Automation tools like [Ansible](./ansible-playbooks.md) make this manageable across dozens of servers.

Once key authentication is working, disable password authentication entirely in `/etc/ssh/sshd_config`:

```
PasswordAuthentication no
ChallengeResponseAuthentication no
UsePAM no
```

Restart sshd after changes. Make absolutely sure your key authentication works before doing this, or you will lock yourself out. Keep a console session open as a safety net while testing. For additional brute-force protection even with password auth disabled, consider [fail2ban](./fail2ban-setup.md). The OpenSSH project maintains a full reference at [openssh.com](https://www.openssh.com/manual.html).
