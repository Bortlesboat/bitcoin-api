# Platform: r/Bitcoin

**Suggested Title:** I built an open-source REST API for Bitcoin Core -- here's what it does

---

I built a free, open-source REST API that turns your Bitcoin Core node into something any app can talk to. It is called Satoshi API.

**The idea:** Bitcoin Core has a powerful RPC interface, but it is designed for developers who already know the protocol inside out. I wanted something that returns useful, analyzed data -- not just raw numbers.

For example, instead of just telling you the fee rate is 4 sat/vB, it tells you "Fees are low. Good time to send." It scores mempool congestion, analyzes blocks, and streams fee updates in real time.

**What makes it different:**

- **Self-hosted.** Runs on your machine next to your node. Your queries never leave your network.
- **One install.** `pip install satoshi-api` and you are running. Docker also supported.
- **54 endpoints.** Blocks, transactions, fees, mempool, mining stats, address lookups, and more.
- **AI-ready.** It is the only Bitcoin API with MCP support, meaning AI assistants like Claude can query your node directly.
- **Free and open source.** Apache-2.0 license. No subscriptions required for self-hosting.

There is also a hosted version at bitcoinsapi.com if you want to try it without running a node. Free tier, no signup needed for read endpoints.

This is a new project from a solo developer. I would love feedback from the community.

- **GitHub:** https://github.com/Bortlesboat/bitcoin-api
- **Try it live:** https://bitcoinsapi.com/docs
- **Install:** `pip install satoshi-api`
