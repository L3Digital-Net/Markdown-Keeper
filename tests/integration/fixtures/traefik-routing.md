---
title: Configuring Traefik as a Reverse Proxy and Load Balancer
tags: traefik,proxy,load-balancer
category: infrastructure
concepts: traefik,routing,load-balancer,middleware,docker
---

## Entrypoints and Static Configuration

Traefik discovers services automatically and routes traffic based on rules, which makes it particularly well-suited for dynamic container environments. Configuration is split into two layers: static configuration (entrypoints, providers, certificate resolvers) and dynamic configuration (routers, services, middleware).

Static configuration lives in `traefik.yml` or is passed as CLI arguments:

```yaml
# traefik.yml
entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
  websecure:
    address: ":443"

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
  file:
    directory: /etc/traefik/dynamic/
    watch: true

certificatesResolvers:
  letsencrypt:
    acme:
      email: admin@example.com
      storage: /data/acme.json
      httpChallenge:
        entryPoint: web

api:
  dashboard: true
  insecure: false
```

The `web` entrypoint listens on port 80 and redirects everything to HTTPS. The `websecure` entrypoint on 443 handles TLS-terminated traffic. The Docker provider watches for container events and automatically creates routes based on container labels; `exposedByDefault: false` ensures only containers with explicit labels get routed.

## Routers and Docker Labels

With the Docker provider, route configuration lives on the containers themselves as labels. No Traefik restart needed when containers come and go.

```yaml
# docker-compose.yml
services:
  myapp:
    image: myapp:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.myapp.rule=Host(`app.example.com`)"
      - "traefik.http.routers.myapp.entrypoints=websecure"
      - "traefik.http.routers.myapp.tls.certresolver=letsencrypt"
      - "traefik.http.services.myapp.loadbalancer.server.port=8080"
    networks:
      - traefik

  api:
    image: api-server:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`app.example.com`) && PathPrefix(`/api`)"
      - "traefik.http.routers.api.entrypoints=websecure"
      - "traefik.http.routers.api.tls.certresolver=letsencrypt"
      - "traefik.http.services.api.loadbalancer.server.port=3000"
    networks:
      - traefik

networks:
  traefik:
    external: true
```

Traefik provisions a Let's Encrypt certificate automatically for `app.example.com` the first time a request arrives. Certificates are stored in `acme.json` and renewed before expiration without any manual intervention. This is a significant advantage over the [Nginx + Certbot approach](./nginx-ssl-config.md), which requires a separate renewal daemon.

Router rules support `Host`, `PathPrefix`, `Headers`, and boolean combinations. Priority is determined automatically by rule specificity, but you can override it with `traefik.http.routers.myapp.priority=100`.

## Middleware and Load Balancing

Middleware modifies requests or responses in the routing pipeline. Common middleware includes rate limiting, basic auth, path stripping, and header manipulation.

```yaml
# /etc/traefik/dynamic/middleware.yml
http:
  middlewares:
    rate-limit:
      rateLimit:
        average: 100
        burst: 50

    strip-api-prefix:
      stripPrefix:
        prefixes:
          - "/api"

    secure-headers:
      headers:
        stsSeconds: 63072000
        stsIncludeSubdomains: true
        contentTypeNosniff: true
        frameDeny: true
```

Attach middleware to a router via Docker labels:

```
traefik.http.routers.api.middlewares=rate-limit,strip-api-prefix,secure-headers
```

Middleware executes in the order listed. For the API router above, requests first hit the rate limiter, then have `/api` stripped from the path, then get security headers added to the response.

For load balancing, scale a service with `docker compose up --scale myapp=3`. Traefik detects all three container instances and distributes traffic across them using round-robin by default. Health checks can be configured to remove unhealthy backends:

```yaml
traefik.http.services.myapp.loadbalancer.healthcheck.path=/health
traefik.http.services.myapp.loadbalancer.healthcheck.interval=10s
```

When running Traefik in a [Kubernetes cluster](./kubernetes-setup.md), use the IngressRoute CRD instead of Docker labels. The concepts (routers, middleware, services) remain the same; only the configuration format changes. Full documentation is available at [doc.traefik.io](https://doc.traefik.io/traefik/).
