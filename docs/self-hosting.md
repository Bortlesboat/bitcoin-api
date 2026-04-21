# Self-Hosting Guide

Deploy Satoshi API on hardware you control, backed by your own Bitcoin Core node. The goal is to keep fee checks, transaction lookups, address research, and agent requests out of centralized Bitcoin API logs.

## Prerequisites

- **Bitcoin Core** synced enough for the mode you choose below
- **Python 3.10+** (or Docker)
- **Linux server** or **Raspberry Pi 4/5** with 4+ GB RAM
- **SSD storage** strongly recommended for Raspberry Pi deployments
- A domain name if you want public HTTPS through Cloudflare Tunnel

## Deployment Modes

Choose the mode that matches your hardware and privacy needs.

| Mode | Bitcoin Core settings | Best for | Tradeoff |
| ---- | --------------------- | -------- | -------- |
| Low-storage Pi mode | `prune=55000`, no `txindex` | Fee intelligence, mempool status, block data, transaction decode/broadcast, local agent access | Full historical transaction and address-history lookups are limited until compact indexing is complete |
| Full lookup mode | `txindex=1`, no pruning | Arbitrary historical transaction lookups and richer API coverage | Requires much more disk and a longer initial sync |

Do not enable both `prune` and `txindex=1` for the same node. If you start in low-storage mode, you can still use Satoshi API for the highest-value fee and network endpoints while the compact address-indexer roadmap closes the remaining address-history gap.

## Privacy Model

Centralized Bitcoin data APIs can observe sensitive metadata even when they never custody funds:

- which addresses or transactions you research
- when you check them
- which IP/network makes the request
- repeated query patterns that can link wallets, devices, or workflows
- whether you appear to be preparing to transact during a sensitive window

A self-hosted Satoshi API instance reduces that exposure by keeping Bitcoin data queries on hardware you control. The API talks to your Bitcoin node over local RPC, so address lookups, fee checks, transaction explanations, and agent requests do not need third-party API accounts.

This does not make Bitcoin itself private. Public-chain activity remains public, network-level privacy still depends on your node and wallet setup, and exposing the API publicly can create new logs unless access is restricted. The practical goal is narrower: remove centralized Bitcoin API query logs from your workflow.

## Raspberry Pi Quick Path

Use this path for a Raspberry Pi 4/5 or comparable ARM64 device.

### Hardware target

- Raspberry Pi 4 or 5
- 4 GB RAM minimum; 8 GB preferred
- 128 GB+ SSD for low-storage pruned mode; larger is better
- 1 TB+ SSD if you want full lookup mode with `txindex=1`
- 64-bit Raspberry Pi OS Lite or Ubuntu Server

### Base packages

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip git curl jq ufw
```

Install and sync Bitcoin Core before starting Satoshi API. For low-storage mode, configure Bitcoin Core with pruning. For full lookup mode, use `txindex=1` and do not prune.

## 1. Bitcoin Core RPC Configuration

Copy the settings from [`bitcoin-conf-example.conf`](./bitcoin-conf-example.conf) into your `bitcoin.conf` (typically `~/.bitcoin/bitcoin.conf`).

### Low-storage Pi mode

Use this when you want fee intelligence and core Bitcoin data on limited storage:

```ini
server=1
prune=55000

rpcuser=satoshiapi
rpcpassword=CHANGE_ME_TO_A_STRONG_PASSWORD

rpcwhitelist=satoshiapi:getblockchaininfo,getblockcount,getnetworkinfo,getmempoolinfo,estimatesmartfee,getmininginfo,getrawtransaction,gettxout,getmempoolentry,getrawmempool,getblockstats,getchaintips,decoderawtransaction,sendrawtransaction,getblocktemplate,getblockhash,getblock,getblockheader,validateaddress,gettxoutsetinfo,gettxoutproof

rpcbind=127.0.0.1
rpcallowip=127.0.0.1
```

### Full lookup mode

Use this when you need arbitrary historical transaction lookup support:

```ini
server=1
txindex=1

rpcuser=satoshiapi
rpcpassword=CHANGE_ME_TO_A_STRONG_PASSWORD

rpcwhitelist=satoshiapi:getblockchaininfo,getblockcount,getnetworkinfo,getmempoolinfo,estimatesmartfee,getmininginfo,getrawtransaction,gettxout,getmempoolentry,getrawmempool,getblockstats,getchaintips,decoderawtransaction,sendrawtransaction,getblocktemplate,getblockhash,getblock,getblockheader,validateaddress,gettxoutsetinfo,gettxoutproof

rpcbind=127.0.0.1
rpcallowip=127.0.0.1
```

Key points:
- **Change the password** in `rpcpassword` to a strong random value
- `txindex=1` is required for arbitrary historical transaction lookup endpoints
- if you enable `txindex=1` on an existing node, you need to reindex (`bitcoind -reindex`)
- The `rpcwhitelist` restricts the API user to only the commands the API actually needs
- `rpcbind=127.0.0.1` ensures RPC is never exposed to the network

After editing, restart Bitcoin Core:

```bash
bitcoin-cli stop
bitcoind -daemon
```

Verify RPC works:

```bash
bitcoin-cli -rpcuser=satoshiapi -rpcpassword=YOUR_PASSWORD getblockchaininfo
```

## 2. Firewall Rules

Block Bitcoin Core's RPC port (8332) from external access. Only localhost and Tailscale (if used) should reach it.

```bash
# UFW example
sudo ufw default deny incoming
sudo ufw allow ssh
sudo ufw allow from 100.64.0.0/10 to any port 8332 comment "Tailscale RPC"
sudo ufw deny 8332
sudo ufw enable
```

The API itself listens on port 9332. With Cloudflare Tunnel, you don't need to open this port either -- traffic routes through the tunnel.

## 3. API Installation

### Option A: pip install (from PyPI)

```bash
python -m venv .venv
source .venv/bin/activate
pip install satoshi-api

# Configure
cp .env.production.example .env.production
# Edit .env.production with your RPC credentials
# (grab the example from the GitHub repo if you don't have it)

# Run
satoshi-api
# or: bitcoin-api (both commands work)
# -> http://localhost:9332/docs
```

For Raspberry Pi low-storage mode, you can start with a minimal environment:

```bash
export BITCOIN_RPC_HOST=127.0.0.1
export BITCOIN_RPC_PORT=8332
export BITCOIN_RPC_USER=satoshiapi
export BITCOIN_RPC_PASSWORD=YOUR_PASSWORD
export API_HOST=127.0.0.1
export API_PORT=9332

satoshi-api
```

Keep `API_HOST=127.0.0.1` if the API is only for your own machine, Tailscale network, or Cloudflare Tunnel. Binding to all interfaces is only appropriate when you understand the network exposure.

**Optional extras** -- install only what you need:

```bash
pip install satoshi-api[all]        # billing + email + redis + analytics
pip install satoshi-api[billing]    # Stripe billing
pip install satoshi-api[email]      # Resend transactional email
pip install satoshi-api[redis]      # Upstash Redis rate limiting
pip install satoshi-api[analytics]  # PostHog analytics
```

#### Development install (from source)

```bash
git clone https://github.com/Bortlesboat/bitcoin-api.git
cd bitcoin-api
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Option B: Docker

```bash
git clone https://github.com/Bortlesboat/bitcoin-api.git
cd bitcoin-api

cp .env.production.example .env.production
# Edit .env.production with your RPC credentials

docker compose -f docker-compose.prod.yml up -d
```

## 4. Cloudflare Tunnel Setup

Cloudflare Tunnel exposes your API to the internet without opening any inbound ports.

### Install cloudflared

```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb
```

### Create and configure the tunnel

```bash
cloudflared tunnel login
cloudflared tunnel create satoshi-api
```

Copy the tunnel ID and credentials file path, then edit [`cloudflared-config.yml.example`](../cloudflared-config.yml.example) and save it as `~/.cloudflared/config.yml`.

### Add DNS record

```bash
cloudflared tunnel route dns satoshi-api api.yourdomain.dev
```

### Run as a service

```bash
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

## 5. Optional External Services

The API can optionally integrate with Upstash Redis (persistent rate limiting), Resend (transactional email), and PostHog (landing page analytics). **All default to disabled and are not required for self-hosting.** In-memory rate limiting works fine for single-instance deployments. See `.env.production.example` for configuration details.

## 6. Monitoring

### Smoke tests

Run these locally after startup:

```bash
curl http://localhost:9332/api/v1/health | jq
curl http://localhost:9332/api/v1/fees/recommended | jq
curl http://localhost:9332/api/v1/fees/landscape | jq
curl http://localhost:9332/api/v1/network | jq
```

If a transaction or address-history endpoint fails on a pruned node, first check whether that endpoint needs historical data unavailable in low-storage mode. The expected path is:

- low-storage mode today for fee, mempool, block, network, and agent utility
- full lookup mode when you need `txindex=1`
- compact address indexing as the roadmap item that removes the remaining storage barrier

### UptimeRobot

Set up a free HTTP monitor on [UptimeRobot](https://uptimerobot.com):
- **URL:** `https://api.yourdomain.dev/api/v1/health`
- **Interval:** 5 minutes
- **Alert contacts:** your email/Telegram/Discord

### Log Rotation

Docker handles log rotation via the `json-file` driver config in `docker-compose.prod.yml` (10 MB max, 3 files).

For non-Docker deployments, configure logrotate:

```
/var/log/satoshi-api/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

## 7. Security Checklist

- [ ] `rpcpassword` is a strong random value (not the default)
- [ ] `rpcbind=127.0.0.1` is set in bitcoin.conf
- [ ] `rpcwhitelist` restricts commands to only what the API needs
- [ ] Port 8332 is blocked from external access (firewall)
- [ ] Port 9332 is bound to `127.0.0.1` (traffic goes through Cloudflare Tunnel)
- [ ] `.env.production` has restrictive file permissions (`chmod 600`)
- [ ] Cloudflare Tunnel is running as a systemd service
- [ ] UptimeRobot (or equivalent) monitors `/api/v1/health`
- [ ] Log rotation is configured
- [ ] Bitcoin Core and API run as non-root users
- [ ] Server OS and packages are kept up to date
