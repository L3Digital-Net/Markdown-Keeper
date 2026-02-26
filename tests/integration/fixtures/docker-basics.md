---
title: Docker Fundamentals for Beginners
tags: docker,containers
category: infrastructure
concepts: docker,container,image,dockerfile,volumes
---

## Images and Containers

A Docker image is a read-only template built from a series of layers. Each instruction in a Dockerfile creates a layer, and Docker caches layers aggressively so rebuilds only redo what changed. A container is a running instance of an image with a writable layer on top.

Pull an image from Docker Hub with `docker pull nginx:1.25` and run it:

```bash
docker run -d --name webserver -p 8080:80 nginx:1.25
```

The `-d` flag detaches the container, `--name` gives it a human-readable handle, and `-p` maps host port 8080 to container port 80. List running containers with `docker ps` and inspect logs with `docker logs webserver`.

Stopped containers stick around and consume disk space. Clean up with `docker rm webserver` or use `docker run --rm` to auto-remove when the container exits. Dangling images (layers no longer referenced by any tagged image) accumulate quickly. Run `docker image prune` periodically, or `docker system prune` to sweep containers, networks, and images all at once.

## Writing a Dockerfile

A Dockerfile describes how to build an image. Start from a base, copy your application code, install dependencies, and define the entrypoint.

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "server.py"]
```

Order matters for cache efficiency. Put instructions that change rarely (installing OS packages, copying requirements files) early. Put instructions that change often (copying application source) late. A single changed line invalidates that layer and everything after it.

Multi-stage builds reduce final image size dramatically. Use a full build image for compilation, then copy only the binary or wheel into a minimal runtime image like `python:3.12-slim` or `gcr.io/distroless/python3`. This also reduces the attack surface since build tools never ship in production.

Build with `docker build -t myapp:latest .` from the directory containing the Dockerfile. The build context (everything in `.`) gets sent to the daemon, so add a `.dockerignore` to exclude `.git`, `node_modules`, virtual environments, and test data.

## Volumes and Networking

Containers are ephemeral by default. Anything written inside the container disappears when it is removed. Volumes solve this by mounting host directories or Docker-managed volumes into the container filesystem.

```bash
docker volume create pgdata
docker run -d --name postgres -v pgdata:/var/lib/postgresql/data postgres:16
```

Named volumes like `pgdata` persist across container restarts and removals. Bind mounts (`-v /host/path:/container/path`) are useful during development but tie you to a specific host directory layout.

For container-to-container communication, create a user-defined bridge network:

```bash
docker network create backend
docker run -d --name db --network backend postgres:16
docker run -d --name app --network backend myapp:latest
```

Containers on the same user-defined network can reach each other by container name. The default bridge network does not provide this DNS resolution, which is why you should always create your own. For more complex networking with service discovery, see [the Kubernetes setup guide](./kubernetes-setup.md).

External reference for Docker networking details: [Docker networking documentation](https://docs.docker.com/network/).
