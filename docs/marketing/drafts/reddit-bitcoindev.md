# Platform: r/BitcoinDev

**Suggested Title:** What would you want from a REST wrapper around Bitcoin Core RPC?

---

I've been running a full node for a while and kept hitting the same friction building apps on top of it. Fee estimates come back with no context, mempool data takes multiple calls to piece together, caching is tricky because of reorgs near the tip.

So I started building a REST layer that handles the annoying parts — unit conversion, depth-aware caching, combining multiple RPC calls into single analyzed responses. It's at the point where I use it daily but I'm not sure I'm prioritizing the right things.

A few design questions I'd genuinely like input on:

1. **Fee analysis** — right now I combine estimatesmartfee at multiple targets with mempool size to generate a "send now or wait" recommendation. Is that useful, or do wallet devs prefer raw numbers and doing their own analysis?

2. **RPC surface** — I whitelist 17 read-only commands (getblock, getblockchaininfo, getblockcount, getblockhash, getblockheader, getblockstats, getdifficulty, estimatesmartfee, getmempoolinfo, getrawmempool, getmempoolentry, getrawtransaction, decoderawtransaction, gettxout, getnetworkinfo, getchaintips, getmininginfo). Is there demand for more? I deliberately left out wallet and debug RPCs but maybe that's too conservative.

3. **What's missing?** If you had a clean REST interface to your node, what endpoints would you reach for first?

It's not an address indexer or block explorer — just a thin REST layer for the RPCs you already have, with depth-aware caching, rate limiting, and structured JSON responses.

I've open-sourced what I have so far: https://github.com/Bortlesboat/bitcoin-api

Also experimenting with MCP for AI agent access -- bitcoin-mcp is now listed on the official Anthropic MCP Registry and PyPI. If anyone has thoughts on AI agent use cases for Bitcoin node data, I would appreciate the feedback.

Not trying to sell anything, just want to build something actually useful. What would matter to you?
