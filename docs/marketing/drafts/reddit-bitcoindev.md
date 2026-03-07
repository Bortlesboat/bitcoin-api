# Platform: r/BitcoinDev

**Suggested Title:** What would you want from a REST wrapper around Bitcoin Core RPC?

---

I've been running a full node for a while and kept hitting the same friction building apps on top of it. Fee estimates come back with no context, mempool data takes multiple calls to piece together, caching is tricky because of reorgs near the tip.

So I started building a REST layer that handles the annoying parts — unit conversion, depth-aware caching, combining multiple RPC calls into single analyzed responses. It's at the point where I use it daily but I'm not sure I'm prioritizing the right things.

A few design questions I'd genuinely like input on:

1. **Fee analysis** — right now I combine estimatesmartfee at multiple targets with mempool size to generate a "send now or wait" recommendation. Is that useful, or do wallet devs prefer raw numbers and doing their own analysis?

2. **RPC surface** — I whitelist 17 read-only commands. Is there demand for more? I deliberately left out wallet and debug RPCs but maybe that's too conservative.

3. **MCP/AI agent access** — I built a Model Context Protocol server so Claude/GPT can query the node. Feels like it could be useful but might also be a solution looking for a problem. Anyone actually building agent workflows against Bitcoin data?

4. **What's missing?** If you had a clean REST interface to your node, what endpoints would you reach for first?

I've open-sourced what I have so far if anyone wants to look at the approach: https://github.com/Bortlesboat/bitcoin-api

You can also poke the live docs at https://bitcoinsapi.com/docs — no signup needed.

Not trying to sell anything, just want to build something actually useful. What would matter to you?
