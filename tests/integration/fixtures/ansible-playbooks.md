---
title: Writing Ansible Playbooks for Configuration Management
tags: ansible,automation,configuration-management
category: automation
concepts: ansible,playbook,inventory,role,handler
---

## Inventory and Playbook Basics

Ansible manages infrastructure by connecting to hosts over SSH and executing tasks declaratively. No agent runs on the managed nodes; Ansible pushes configurations from a control machine.

An inventory file defines your hosts and groups:

```ini
# inventory/hosts.ini
[webservers]
web1.example.com
web2.example.com

[databases]
db1.example.com ansible_user=postgres

[all:vars]
ansible_python_interpreter=/usr/bin/python3
```

A playbook is a YAML file that maps groups to tasks:

```yaml
# playbooks/setup-webservers.yml
---
- name: Configure web servers
  hosts: webservers
  become: true
  vars:
    nginx_version: "1.25"
  tasks:
    - name: Install nginx
      apt:
        name: "nginx={{ nginx_version }}.*"
        state: present
        update_cache: true

    - name: Copy nginx config
      template:
        src: templates/nginx.conf.j2
        dest: /etc/nginx/nginx.conf
        owner: root
        group: root
        mode: '0644'
      notify: Reload nginx

    - name: Ensure nginx is running
      service:
        name: nginx
        state: started
        enabled: true

  handlers:
    - name: Reload nginx
      service:
        name: nginx
        state: reloaded
```

Run it with:

```bash
ansible-playbook -i inventory/hosts.ini playbooks/setup-webservers.yml
```

Every task should be idempotent. Running the playbook twice should produce the same result as running it once, with no changes reported on the second run. The `apt` module with `state: present` only installs if the package is missing. The `template` module only writes the file if the content differs. This idempotency is what makes Ansible safe to run repeatedly.

## Roles and Project Structure

As playbooks grow, roles provide a standard directory structure for organizing tasks, templates, handlers, variables, and defaults:

```
roles/
  nginx/
    tasks/
      main.yml
    handlers/
      main.yml
    templates/
      nginx.conf.j2
    defaults/
      main.yml
    vars/
      main.yml
```

Reference roles from a playbook:

```yaml
- name: Configure web servers
  hosts: webservers
  become: true
  roles:
    - nginx
    - certbot
    - firewall
```

Roles are reusable across projects. Ansible Galaxy (`ansible-galaxy install geerlingguy.docker`) provides community roles for common software, though you should review third-party roles before using them in production.

## Variables, Templates, and Handlers

Variables cascade with a well-defined precedence order. From lowest to highest: role defaults, inventory group vars, inventory host vars, playbook vars, extra vars (`-e` on the command line). This lets you set sensible defaults in roles and override them per-host or per-environment.

Jinja2 templates can reference any variable in scope:

```nginx
# templates/nginx.conf.j2
worker_processes {{ ansible_processor_vcpus }};
server {
    listen 443 ssl;
    server_name {{ inventory_hostname }};
    ssl_certificate /etc/letsencrypt/live/{{ domain_name }}/fullchain.pem;
}
```

`ansible_processor_vcpus` is a fact gathered automatically from each host. Custom variables like `domain_name` come from your inventory or vars files.

Handlers run once at the end of a play, regardless of how many tasks notify them. This prevents restarting a service multiple times when several configuration files change in the same run. Force immediate handler execution with `meta: flush_handlers` if a subsequent task depends on the restarted service.

For deploying [systemd service files](./systemd-service-files.md) across a fleet, Ansible's `systemd` module handles daemon-reload and service state management cleanly. The official [Ansible documentation](https://docs.ansible.com/ansible/latest/index.html) covers advanced patterns including dynamic inventory, vault-encrypted secrets, and callback plugins.
