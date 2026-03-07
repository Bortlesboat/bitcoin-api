# Satoshi API -- Umbrel & Start9 App Store Submission Guide

Last updated: 2026-03-07

This document covers everything needed to submit Satoshi API to the Umbrel App Store and Start9 Marketplace.

---

## Table of Contents

1. [Umbrel App Store](#umbrel-app-store)
   - [Overview](#umbrel-overview)
   - [Required Files](#umbrel-required-files)
   - [Draft Manifest](#umbrel-draft-manifest)
   - [Draft docker-compose.yml](#umbrel-draft-docker-composeyml)
   - [Icon & Gallery Requirements](#umbrel-icon--gallery-requirements)
   - [Testing](#umbrel-testing)
   - [Submission Process](#umbrel-submission-process)
   - [Submission Checklist](#umbrel-submission-checklist)
2. [Start9 Marketplace](#start9-marketplace)
   - [Overview](#start9-overview)
   - [Required Files](#start9-required-files)
   - [Draft manifest.yaml](#start9-draft-manifestyaml)
   - [Additional Files Needed](#start9-additional-files-needed)
   - [Packaging & Testing](#start9-packaging--testing)
   - [Submission Process](#start9-submission-process)
   - [Submission Checklist](#start9-submission-checklist)
3. [Shared Prerequisites](#shared-prerequisites)
4. [Docker Image Preparation](#docker-image-preparation)

---

## Umbrel App Store

### Umbrel Overview

- **Repository:** [getumbrel/umbrel-apps](https://github.com/getumbrel/umbrel-apps)
- **Process:** Fork repo, add app directory, open PR
- **Apps run as Docker containers** behind an `app_proxy` that handles Umbrel authentication
- **Must serve a web UI** (or a simple connection-info page)
- **Supports ARM64 and x86_64** (multi-arch Docker images required)

### Umbrel Required Files

Each app lives in its own directory under `umbrel-apps/<app-id>/`. Required files:

| File | Purpose |
|------|---------|
| `umbrel-app.yml` | App manifest (name, version, description, dependencies, etc.) |
| `docker-compose.yml` | Docker Compose service definitions |
| `exports.sh` | (Optional) Export env vars for other apps to consume |

The app ID must be lowercase alphanumeric + dashes only. Proposed ID: **`satoshi-api`**

### Umbrel Draft Manifest

```yaml
manifestVersion: 1
id: satoshi-api
category: bitcoin
name: Satoshi API
version: "1.0.0"
tagline: Professional REST API for your Bitcoin node
description: >-
  Satoshi API gives you a clean, well-documented REST API on top of your
  Bitcoin Core node. Query blocks, transactions, addresses, mempool stats,
  network info, and more through 34 production-ready endpoints.


  Built with FastAPI for high performance, it includes tiered API key
  authentication, rate limiting, intelligent caching, and comprehensive
  request logging. Perfect for developers building Bitcoin applications,
  wallets, dashboards, or automated trading systems.


  Use your own node's data through a modern REST interface instead of
  trusting third-party APIs. Your node, your data, your API.
releaseNotes: ""
developer: Satoshi API
website: https://bitcoinsapi.com
dependencies:
  - bitcoin
repo: https://github.com/Bortlesboat/bitcoin-api
support: https://github.com/Bortlesboat/bitcoin-api/issues
port: 9332
gallery: []
path: ""
defaultUsername: ""
defaultPassword: ""
submitter: Bortlesboat
submission: ""
```

**Key fields explained:**

- `manifestVersion`: Use `1` (version `1.1` only needed for lifecycle hooks)
- `category`: `bitcoin` (matches mempool, btc-rpc-explorer)
- `dependencies`: `bitcoin` means Bitcoin Core must be installed first
- `port`: 9332 (Satoshi API's default port) -- Umbrel may reassign if conflicts exist
- `gallery`: Leave empty on initial submission; Umbrel helps finalize
- `releaseNotes`: Leave empty on first submission

### Umbrel Draft docker-compose.yml

```yaml
version: "3.7"

services:
  app_proxy:
    environment:
      APP_HOST: satoshi-api_web_1
      APP_PORT: 9332
      # API endpoints should bypass Umbrel auth so external tools can use API keys
      PROXY_AUTH_WHITELIST: "/api/*,/docs,/openapi.json,/healthz,/redoc"

  web:
    image: bortlesboat/satoshi-api:v1.0.0@sha256:<DIGEST>
    restart: on-failure
    stop_grace_period: 1m
    volumes:
      - ${APP_DATA_DIR}/data:/app/data
    environment:
      # Bitcoin Core RPC connection (provided by Umbrel)
      # Pydantic Settings reads these case-insensitively as field names from config.py
      BITCOIN_RPC_HOST: $APP_BITCOIN_NODE_IP
      BITCOIN_RPC_PORT: $APP_BITCOIN_RPC_PORT
      BITCOIN_RPC_USER: $APP_BITCOIN_RPC_USER
      BITCOIN_RPC_PASSWORD: $APP_BITCOIN_RPC_PASS

      # App configuration
      API_HOST: "0.0.0.0"
      API_PORT: "9332"

      # Database path (persistent volume)
      API_DB_PATH: "/app/data/bitcoin_api.db"
```

**Important notes:**

- `APP_HOST` format: `<app-id>_<service-name>_1` (e.g., `satoshi-api_web_1`)
- The `@sha256:<DIGEST>` must be the **multi-architecture digest**, not per-platform
- `${APP_DATA_DIR}/data` persists the SQLite database across restarts
- Umbrel provides `$APP_BITCOIN_*` variables automatically when `bitcoin` is a dependency
- `PROXY_AUTH_WHITELIST` lets API consumers use API keys directly without Umbrel login
- Umbrel reviewers will assign unique IP addresses and verify no port conflicts

### Umbrel Icon & Gallery Requirements

**Icon:**
- 256x256 SVG format
- No rounded corners (Umbrel applies CSS rounding dynamically)
- Upload in the PR description (not in the app directory)

**Gallery images:**
- 1440x900px PNG format
- 3 to 5 images
- Can submit screenshots; Umbrel team helps design final gallery images
- Upload in the PR description

### Umbrel Testing

Two testing methods available:

**Option A: Local dev environment (umbrel-dev)**
1. Requires Docker with container IPs exposed to host (Linux native, OrbStack on macOS, WSL2 on Windows)
2. Clone [getumbrel/umbrel](https://github.com/getumbrel/umbrel)
3. Run `npm run dev` to start local umbrelOS
4. Copy app directory to app-store path:
   ```sh
   rsync -av --exclude=".gitkeep" ./satoshi-api \
     umbrel@umbrel-dev.local:/home/umbrel/umbrel/app-stores/getumbrel-umbrel-apps-github-53f74447/
   ```
5. Install via UI or CLI: `npm run dev client -- apps.install.mutate -- --appId satoshi-api`

**Option B: Physical device**
1. Install umbrelOS on Raspberry Pi 5, x86 system, VM, or Umbrel Home
2. rsync app directory to device
3. Install via app store UI

**Testing checklist:**
- App installs without errors
- App starts and serves the web UI / docs page
- API endpoints respond correctly using Bitcoin Core RPC
- Persistent data survives app restart
- App uninstalls cleanly

### Umbrel Submission Process

1. Fork [getumbrel/umbrel-apps](https://github.com/getumbrel/umbrel-apps)
2. Create `satoshi-api/` directory with all required files
3. Open a PR with this template in the description:

```markdown
# App Submission

### App name
Satoshi API

### 256x256 SVG icon
_(attach icon)_

### Gallery images
_(attach 3-5 screenshots at 1440x900px PNG)_

### I have tested my app on:
- [ ] umbrelOS on a Raspberry Pi
- [ ] umbrelOS on an Umbrel Home
- [ ] umbrelOS on Linux VM
```

4. Umbrel team reviews, may adjust docker-compose (IP assignments, port conflicts, pin digests)
5. Once merged, app appears in the Umbrel App Store

**Post-launch updates:** Build new Docker image, open PR updating `version`, `releaseNotes`, and image tag/digest in docker-compose.

### Umbrel Submission Checklist

- [ ] Docker image published to Docker Hub (`bortlesboat/satoshi-api`)
- [ ] Multi-arch build (linux/arm64 + linux/amd64) via `docker buildx`
- [ ] Image pinned to sha256 digest in docker-compose.yml
- [ ] `umbrel-app.yml` manifest completed
- [ ] `docker-compose.yml` uses Umbrel-provided Bitcoin Core env vars
- [ ] Persistent data mapped to `${APP_DATA_DIR}/data`
- [ ] App does not run as root in container (already handled -- uses `apiuser`)
- [ ] SVG icon created (256x256, no rounded corners)
- [ ] 3-5 gallery screenshots (1440x900px PNG)
- [ ] Tested on umbrelOS (dev environment or physical device)
- [ ] Fork getumbrel/umbrel-apps and create PR
- [ ] Env var mapping: verify `BITCOIN_RPC_HOST` etc. match what Satoshi API expects in `config.py`

---

## Start9 Marketplace

### Start9 Overview

- **Platform:** StartOS (runs on Raspberry Pi, x86 hardware)
- **Package format:** `.s9pk` (built with `start-sdk`)
- **Submission:** Email to submissions@start9.com
- **Key difference from Umbrel:** More involved packaging with health checks, config spec, backup/restore, and a Rust-based SDK tool
- **All services must be open source**

### Start9 Required Files

The service "wrapper" repository needs these files:

| File | Purpose |
|------|---------|
| `manifest.yaml` | Service metadata, volumes, interfaces, health checks, dependencies |
| `Dockerfile` | Builds the service image |
| `docker_entrypoint.sh` | Container entrypoint script with error handling |
| `instructions.md` | User-facing documentation shown in StartOS UI |
| `Makefile` | Build automation (targets for `.s9pk` creation) |
| `prepare.sh` | Sets up Debian-based build environment |
| `icon.svg` (or `icon.png`) | Service icon for the UI |
| `LICENSE` | Open source license |

### Start9 Draft manifest.yaml

Based on the Bitcoin Core wrapper at `Start9Labs/bitcoind-startos`:

```yaml
id: satoshi-api
title: "Satoshi API"
version: 1.0.0
eos-version: 0.3.5.x
release-notes: |
  * Initial release
  * 48 REST API endpoints for Bitcoin Core
  * API key authentication with rate limiting
  * Intelligent caching and request logging
license: Apache-2.0
wrapper-repo: https://github.com/Bortlesboat/satoshi-api-startos
upstream-repo: https://github.com/Bortlesboat/bitcoin-api
support-site: https://github.com/Bortlesboat/bitcoin-api/issues
marketing-site: https://bitcoinsapi.com
build: ["make"]
description:
  short: Professional REST API for your Bitcoin node
  long: |
    Satoshi API provides a clean, well-documented REST API on top of your
    Bitcoin Core node. Query blocks, transactions, addresses, mempool stats,
    network info, and more through 34 production-ready endpoints. Built with
    FastAPI for high performance, includes tiered API key authentication,
    rate limiting, intelligent caching, and comprehensive request logging.
assets:
  license: LICENSE
  icon: icon.svg
  instructions: instructions.md
main:
  type: docker
  image: main
  entrypoint: "docker_entrypoint.sh"
  args: []
  mounts:
    main: /app/data
  sigterm-timeout: 30s
health-checks:
  api:
    name: API
    success-message: Satoshi API is ready for requests
    type: docker
    image: main
    system: false
    entrypoint: check-api.sh
    args: []
    mounts: {}
    io-format: yaml
    inject: true
config:
  get:
    type: script
  set:
    type: script
properties:
  type: script
volumes:
  main:
    type: data
alerts:
  install: >-
    Satoshi API requires Bitcoin Core to be installed and synced.
    API keys can be managed through the API's admin endpoints.
  uninstall: >-
    Uninstalling Satoshi API will remove all API keys and request logs.
    The Bitcoin Core data is not affected.
interfaces:
  api:
    name: API Interface
    description: REST API for Bitcoin Core queries
    tor-config:
      port-mapping:
        9332: "9332"
    lan-config:
      443:
        ssl: true
        internal: 9332
    ui: true
    protocols:
      - tcp
      - http
dependencies:
  bitcoind:
    version: ">=25.0.0"
    requirement:
      type: required
    description: Bitcoin Core full node for RPC data
backup:
  create:
    type: docker
    image: main
    system: true
    entrypoint: /bin/sh
    args:
      - "-c"
      - "cp -r /app/data /mnt/backup"
    mounts:
      main: /app/data
      BACKUP: /mnt/backup
  restore:
    type: docker
    image: main
    system: true
    entrypoint: /bin/sh
    args:
      - "-c"
      - "cp -r /mnt/backup/* /app/data/"
    mounts:
      main: /app/data
      BACKUP: /mnt/backup
```

### Start9 Additional Files Needed

**docker_entrypoint.sh** -- Container startup script:
```bash
#!/bin/bash
set -e

# Configure Bitcoin Core RPC connection from StartOS
# StartOS injects dependency connection info
export BITCOIN_RPC_HOST="${BITCOIND_RPC_HOST:-127.0.0.1}"
export BITCOIN_RPC_PORT="${BITCOIND_RPC_PORT:-8332}"
export BITCOIN_RPC_USER="${BITCOIND_RPC_USER:-bitcoin}"
export BITCOIN_RPC_PASSWORD="${BITCOIND_RPC_PASSWORD}"

exec python -m bitcoin_api.main
```

**check-api.sh** -- Health check script:
```bash
#!/bin/bash
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9332/healthz)
if [ "$STATUS" = "200" ]; then
  echo '{"result": "running"}'
else
  echo '{"result": "starting"}'
fi
```

**instructions.md** -- User-facing docs shown in StartOS UI:
```markdown
# Satoshi API

## Getting Started
Satoshi API provides a REST API for querying your Bitcoin Core node.

## API Documentation
Visit the API at your Tor or LAN address to see interactive Swagger docs.

## API Keys
Create an API key via POST /api/v1/auth/register to unlock higher rate limits.

## Endpoints
- GET /api/v1/blocks/latest -- Latest block info
- GET /api/v1/blocks/{hash} -- Block by hash
- GET /api/v1/transactions/{txid} -- Transaction details
- GET /api/v1/address/{address}/balance -- Address balance
- GET /api/v1/mempool -- Mempool statistics
- GET /api/v1/network -- Network info
- Full docs at /docs (Swagger) or /redoc
```

**Makefile** (typical structure):
```makefile
SATOSHI_API_SRC := $(shell find ./src -name '*.py')
PKG_ID := satoshi-api
PKG_VERSION := 1.0.0

.DELETE_ON_ERROR:

all: $(PKG_ID).s9pk

$(PKG_ID).s9pk: manifest.yaml instructions.md icon.svg LICENSE Dockerfile docker_entrypoint.sh check-api.sh $(SATOSHI_API_SRC)
	start-sdk pack

install:
	start-sdk install $(PKG_ID).s9pk

clean:
	rm -f $(PKG_ID).s9pk
```

**prepare.sh** (sets up build environment):
```bash
#!/bin/bash
set -e
# Install Start SDK
if ! command -v start-sdk &> /dev/null; then
    cargo install start-sdk
fi
# Install Docker buildx if needed
docker buildx version || echo "Please install docker buildx"
```

### Start9 Packaging & Testing

**Build tools required:**
- Docker with buildx (multi-platform builds)
- Rust & Cargo (for `start-sdk`)
- `start-sdk` CLI tool (`cargo install start-sdk` or via `start-sdk init`)

**Build process:**
1. `./prepare.sh` -- install dependencies
2. `make` -- builds Docker image and packages into `.s9pk`
3. `start-sdk verify satoshi-api.s9pk` -- validates the package

**Testing:**
- Sideload the `.s9pk` via StartOS UI (drag and drop) or CLI
- Verify: install, start, health checks pass, API responds, restart preserves data, backup/restore works, uninstall is clean
- Must work on low-resource devices (Raspberry Pi 8GB)

### Start9 Submission Process

1. **Prepare:** Polish the wrapper repo with all required files, ensure it builds cleanly
2. **Email:** Send to **submissions@start9.com** with a link to the public wrapper repository
3. **Review:** Start9 team:
   - Snapshots the repo
   - Reviews code for completeness and integrity
   - Builds the `.s9pk` on their Debian build box using `prepare.sh` + `make`
   - Tests on StartOS hardware (install, config, health checks, interfaces, logs, backup/restore)
   - Verifies it works on low-resource devices (RPi 8GB equivalent)
4. **Publication:** Initially published to **Community Beta Registry** for community testing
5. **Production:** After several days in beta, email Start9 to request promotion to production registry

### Start9 Submission Checklist

- [ ] Create separate wrapper repo (e.g., `satoshi-api-startos`)
- [ ] `manifest.yaml` with all required fields
- [ ] `Dockerfile` builds multi-arch (arm64/amd64)
- [ ] `docker_entrypoint.sh` handles StartOS dependency injection
- [ ] `check-api.sh` health check script
- [ ] `instructions.md` user documentation
- [ ] `Makefile` with `start-sdk pack` target
- [ ] `prepare.sh` for build environment setup
- [ ] `icon.svg` service icon
- [ ] `LICENSE` file (Apache-2.0)
- [ ] Config get/set scripts (for user-configurable settings)
- [ ] Properties script (shows connection info in UI)
- [ ] Backup/restore works correctly
- [ ] Tested on StartOS (sideload)
- [ ] Works on Raspberry Pi 8GB
- [ ] Source code is public
- [ ] Email submissions@start9.com with repo link

---

## Shared Prerequisites

Before submitting to either platform, these must be done:

### 1. Verify Satoshi API Config Accepts Environment Variables

The existing `config.py` uses Pydantic Settings which reads from env vars. Verify these env var names match what the platforms provide:

| What | Umbrel Provides | Start9 Provides | Satoshi API Config Field | Env Var |
|------|----------------|-----------------|--------------------------|---------|
| RPC Host | `$APP_BITCOIN_NODE_IP` | Injected via dependency | `bitcoin_rpc_host` | `BITCOIN_RPC_HOST` |
| RPC Port | `$APP_BITCOIN_RPC_PORT` | Injected via dependency | `bitcoin_rpc_port` | `BITCOIN_RPC_PORT` |
| RPC User | `$APP_BITCOIN_RPC_USER` | Injected via dependency | `bitcoin_rpc_user` | `BITCOIN_RPC_USER` |
| RPC Pass | `$APP_BITCOIN_RPC_PASS` | Injected via dependency | `bitcoin_rpc_password` | `BITCOIN_RPC_PASSWORD` |
| DB Path | N/A (set in compose) | N/A (set in entrypoint) | `api_db_path` | `API_DB_PATH` |

The docker-compose (Umbrel) or entrypoint script (Start9) maps platform vars to what Satoshi API expects.

### 2. Existing Dockerfile Assessment

The current Dockerfile at `bitcoin-api/Dockerfile` is already well-structured:
- Uses `python:3.12-slim` (lightweight)
- Runs as non-root user (`apiuser`)
- Has a health check (`/healthz`)
- Exposes port 9332

**Changes needed for app store submission:**
- Build multi-arch images: `docker buildx build --platform linux/arm64,linux/amd64`
- Push to Docker Hub under a public repository (e.g., `bortlesboat/satoshi-api:v1.0.0`)
- Pin the image to its sha256 digest in Umbrel's docker-compose

### 3. Web UI Requirement (Umbrel)

Umbrel expects apps to serve a web UI. Satoshi API serves:
- `/docs` -- Swagger UI (interactive API docs)
- `/redoc` -- ReDoc (alternative docs)
- Root `/` could redirect to `/docs`

This satisfies the requirement. The app proxy will front this with Umbrel auth, while API endpoints can be whitelisted for direct API key access.

---

## Docker Image Preparation

### Build & Push Multi-Arch Image

```bash
# One-time: create a buildx builder
docker buildx create --name multiarch --use

# Build and push multi-arch image
docker buildx build \
  --platform linux/arm64,linux/amd64 \
  --tag bortlesboat/satoshi-api:v1.0.0 \
  --output "type=registry" \
  .

# Get the multi-arch digest for Umbrel's docker-compose
docker buildx imagetools inspect bortlesboat/satoshi-api:v1.0.0
```

The digest from `imagetools inspect` goes into the Umbrel docker-compose as:
```
image: bortlesboat/satoshi-api:v1.0.0@sha256:<MULTI_ARCH_DIGEST>
```

### Docker Hub Repository

- Create `bortlesboat/satoshi-api` on Docker Hub (public)
- Or use GitHub Container Registry: `ghcr.io/bortlesboat/satoshi-api`

---

## Priority & Effort Estimate

| Platform | Effort | Reach | Priority |
|----------|--------|-------|----------|
| **Umbrel** | Low (2-4 hours) | Large (500K+ users) | **Do first** |
| **Start9** | Medium (6-10 hours) | Smaller but dedicated | Second |

Umbrel is significantly easier -- just a docker-compose + manifest YAML + PR. Start9 requires a separate wrapper repo with health checks, config scripts, backup/restore logic, and the `start-sdk` toolchain.

### Recommended Order of Operations

1. Build and push multi-arch Docker image to Docker Hub
2. Create SVG icon and gallery screenshots
3. Submit to Umbrel (fork repo, add files, open PR)
4. Create `satoshi-api-startos` wrapper repo
5. Implement Start9 health checks, config, and backup scripts
6. Build `.s9pk`, test on StartOS
7. Email Start9 for submission
