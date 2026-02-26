---
title: Configuring Nginx with SSL/TLS via Let's Encrypt
tags: nginx,ssl,web-server
category: web
concepts: nginx,ssl,tls,certificate,reverse-proxy,letsencrypt
---

## Installing Certbot and Obtaining Certificates

Let's Encrypt provides free, automated TLS certificates through the ACME protocol. Certbot is the standard client. Install it alongside the Nginx plugin:

```bash
apt install certbot python3-certbot-nginx
```

Before requesting a certificate, make sure your domain's DNS A record points to the server's public IP and that ports 80 and 443 are open in the firewall. Certbot's HTTP-01 challenge serves a temporary file on port 80 to prove domain ownership, so Nginx must be running and reachable.

Request a certificate:

```bash
certbot --nginx -d example.com -d www.example.com
```

Certbot modifies your Nginx configuration automatically, adding the `ssl_certificate` and `ssl_certificate_key` directives. It also sets up a redirect from HTTP to HTTPS. The certificates land in `/etc/letsencrypt/live/example.com/` as symlinks pointing to the latest renewal.

Certificates expire every 90 days. Certbot installs a systemd timer (or cron job) that runs `certbot renew` twice daily. The renewal only triggers when a certificate is within 30 days of expiration. Test the renewal process with `certbot renew --dry-run` to catch permission or configuration problems before they cause a real outage.

## Server Block Configuration

A properly configured Nginx reverse proxy server block looks like this:

```nginx
server {
    listen 80;
    server_name example.com www.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name example.com www.example.com;

    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

The first block catches all HTTP traffic and issues a 301 redirect to HTTPS. The second block terminates TLS and proxies requests to a backend service on port 8080. The `X-Forwarded-*` headers are essential for the backend to know the original client IP and protocol; without them, applications generate incorrect URLs and log the wrong source addresses.

## Hardening and Performance Tuning

Add HSTS to prevent downgrade attacks. Once the header is sent, browsers refuse plain HTTP for the specified duration:

```nginx
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
```

Enable OCSP stapling so the server fetches certificate revocation status proactively, rather than making clients query the CA:

```nginx
ssl_stapling on;
ssl_stapling_verify on;
resolver 1.1.1.1 8.8.8.8 valid=300s;
```

For session resumption, configure a shared SSL session cache. This avoids a full TLS handshake on every connection from the same client:

```nginx
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 1d;
```

Test your configuration with `nginx -t` before reloading. A syntax error in any included file will take down the entire server on a restart. After reloading, verify your TLS setup at [SSL Labs](https://www.ssllabs.com/ssltest/) and aim for an A+ rating.

If you are proxying to multiple backends or need automatic service discovery, consider [Traefik as an alternative](./traefik-routing.md) since it handles Let's Encrypt certificate provisioning natively without a separate Certbot process.
