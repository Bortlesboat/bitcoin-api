# Show HN Post Draft

## Title

Show HN: I built a Bitcoin fee API that tells you when to send (not just the fee rate)

## Body

Every Bitcoin API gives you a fee rate — "4.12 sat/vB." That number alone doesn't tell you what to do. Is the mempool clearing? Should you wait an hour and save 60%? Is now actually a good time?

I built Satoshi API to answer the actual question: **should I send now, or wait?**

    curl https://bitcoinsapi.com/api/v1/fees/landscape

That returns a fee recommendation with mempool context — congestion level, trend direction, and a plain-English verdict like "Fees are low. Good time to send."

**Why this exists:**

I was building a wallet side project and realized I was writing the same fee analysis logic for the third time — fetching multiple fee targets, checking mempool depth, deciding whether to recommend waiting. That code should be an API.

**What it actually saves you:**

- **Money.** If you're batching payouts or consolidating UTXOs, sending during a high-fee spike vs waiting 2 hours can be a 10x difference. The `/fees/landscape` endpoint tells you which situation you're in.
- **Time.** Real-time SSE streams push fee updates every 30s. Build alerts ("notify me when fees drop below 5 sat/vB") without polling. Stop watching mempool.space.
- **Developer time.** It's also the only Bitcoin API with MCP support (on the Anthropic MCP Registry), so AI agents can check fees and verify payments without custom code.

**What it's NOT:** Not an address indexer (that's Electrum/Esplora), not multi-chain, not trying to be mempool.space. It's fee intelligence + a clean REST interface to your node's data.

**Honest limitations:** Address lookups use `scantxoutset` (~30s on first call). SQLite backend won't scale past moderate traffic. The fee analysis is only as good as what Bitcoin Core's `estimatesmartfee` provides — I'm combining and contextualizing it, not reinventing it.

Free hosted at bitcoinsapi.com (no signup for GET endpoints). Self-hostable: `pip install satoshi-api`.

- GitHub: https://github.com/Bortlesboat/bitcoin-api
- PyPI: https://pypi.org/project/satoshi-api/
- Live API: https://bitcoinsapi.com
- Docs: https://bitcoinsapi.com/docs

Happy to answer questions about the fee analysis approach, Bitcoin Core RPC quirks, or the MCP integration.
