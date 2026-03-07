# Self-Hosting Guide

Deploy the Satoshi API on your own infrastructure with a full Bitcoin Core node.

## Prerequisites

- **Bitcoin Core** fully synced with `txindex=1` enabled
- **Python 3.10+** (or Docker)
- **Linux server** (Ubuntu 22.04+ recommended) with 4+ GB RAM
- A domain name (for Cloudflare Tunnel)

## 1. Bitcoin Core RPC Configuration

Copy the settings from [`bitcoin-conf-example.conf`](./bitcoin-conf-example.conf) into your `bitcoin.conf` (typically `~/.bitcoin/bitcoin.conf`).

Key points:
- **Change the password** in `rpcpassword` to a strong random value
- `txindex=1` is required for transaction lookup endpoints -- if you're enabling this on an existing node, you'll need to reindex (`bitcoind -reindex`)
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

### Option A: pip install

```bash
git clone https://github.com/Bortlesboat/bitcoin-api.git
cd bitcoin-api
python -m venv .venv
source .venv/bin/activate
pip install git+https://github.com/Bortlesboat/bitcoinlib-rpc.git
pip install .

# Configure
cp .env.production.example .env.production
# Edit .env.production with your RPC credentials

# Run
satoshi-api
# -> http://localhost:9332/docs
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

## 5. Monitoring

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

## 6. Security Checklist

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
