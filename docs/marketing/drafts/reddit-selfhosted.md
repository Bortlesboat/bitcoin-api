# Platform: r/selfhosted

**Suggested Title:** Self-hosted Bitcoin REST API -- query your own node with 71 endpoints, zero third-party dependencies

---

I built an open-source REST API that sits on top of your Bitcoin Core node. One install, no external dependencies, no data leaves your network.

**Setup:**

```bash
pip install satoshi-api
export BITCOIN_RPC_USER=your_user BITCOIN_RPC_PASSWORD=your_password
satoshi-api
```

That is it. API runs on port 9332, interactive docs at `/docs`.

**Why I built it:** I run a full node at home and got tired of querying third-party APIs for data my own node already had. Every external call leaks which addresses and transactions you care about. This keeps everything local.

**What it gives you:**

- 48 REST endpoints: blocks, transactions, fees, mempool, mining, network, address lookups, real-time SSE streams
- Fee recommendations with context ("Fees are low. Good time to send.")
- Mempool congestion scoring
- Smart caching so you do not hammer your node (depth-aware TTLs, reorg-safe)
- Docker support (`docker-compose up -d`) or just pip install

**Privacy model:** The API only talks to your local Bitcoin Core RPC on localhost. No analytics, no telemetry, no phone-home. Rate limiting and API keys are there for when you want to expose it on your LAN or through a tunnel, but they are optional for local use.

**If you want to expose it publicly:** I use a free Cloudflare Tunnel for HTTPS and DDoS protection without opening ports. There is a self-hosting guide in the docs.

Apache-2.0 licensed, ~15 source files, minimal dependencies (FastAPI, httpx, bitcoinlib-rpc).

- **GitHub:** https://github.com/Bortlesboat/bitcoin-api
- **Self-hosting guide:** https://github.com/Bortlesboat/bitcoin-api/blob/main/docs/self-hosting.md
- **Live demo:** https://bitcoinsapi.com/docs
