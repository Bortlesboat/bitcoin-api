# Satoshi API — 12-Month Roadmap

**Mission:** Make Bitcoin programmatically accessible to every developer and AI agent — with fee intelligence that saves real money on every transaction.

---

## Q2 2026 (Apr–Jun): Foundation & Adoption

### Indexer Expansion
- [ ] Full address balance + transaction history indexing (mainnet)
- [ ] UTXO set queries by address with pagination
- [ ] Historical fee data API (hourly/daily aggregates going back 1 year)
- [ ] Block reward + subsidy tracking endpoints

### Developer Experience
- [ ] Official Python SDK with typed models and async support
- [ ] JavaScript/TypeScript SDK (npm package)
- [ ] Interactive API playground improvements (saved queries, code generation)
- [ ] Comprehensive API reference documentation site

### MCP Ecosystem
- [ ] bitcoin-mcp v1.0 release with stable tool interface
- [ ] 10+ additional MCP tools (PSBT construction, multi-sig support, Lightning invoice decoding)
- [ ] MCP resource templates for common agent workflows

---

## Q3 2026 (Jul–Sep): Network Support & Intelligence

### Multi-Network
- [ ] Signet support (full API parity with mainnet)
- [ ] Testnet4 support
- [ ] Network-aware fee recommendations (different strategies per network)

### Advanced Fee Intelligence
- [ ] Fee prediction model (ML-based, 1hr/6hr/24hr forecasts)
- [ ] Historical fee percentile API (what fee would have confirmed in X blocks, Y days ago)
- [ ] Fee savings calculator with historical backtesting
- [ ] Mempool trend analysis (congestion forecasting)

### Security & Reliability
- [ ] PSBT construction and analysis endpoints
- [ ] Multi-sig wallet support endpoints
- [ ] 99.9% uptime SLA for hosted service
- [ ] Geographic redundancy (multi-region deployment)

---

## Q4 2026 (Oct–Dec): Ecosystem Integration

### Protocol Tools
- [ ] Ordinals/Inscriptions indexing and search
- [ ] BRC-20 token balance queries
- [ ] Runes protocol support
- [ ] OP_RETURN data indexing and search

### Agent Identity (BAIP Integration)
- [ ] BAIP-1 identity verification endpoints
- [ ] Agent-to-agent payment verification via Lightning
- [ ] Attestation validation API
- [ ] Agent capability discovery endpoints

### Community & Governance
- [ ] Public development roadmap with community voting
- [ ] Contributor bounty program
- [ ] Monthly development reports
- [ ] Plugin/extension system for community-built endpoints

---

## Q1 2027 (Jan–Mar): Scale & Sustainability

### Performance
- [ ] Sub-100ms response time for all cached endpoints
- [ ] WebSocket v2 with granular subscription topics
- [ ] Batch API for multiple queries in single request
- [ ] CDN-cached static data endpoints

### Ecosystem Growth
- [ ] Rust SDK
- [ ] Go SDK
- [ ] Docker one-click deployment (compose + node + API)
- [ ] Kubernetes Helm chart

### Sustainability
- [ ] Self-sustaining hosting via Pro tier revenue
- [ ] Open governance model (community advisory board)
- [ ] Annual transparency report (usage, costs, development hours)

---

## Success Metrics

| Metric | Current (Mar 2026) | 6-Month Target | 12-Month Target |
|--------|-------------------|----------------|-----------------|
| API Endpoints | 108 | 140+ | 180+ |
| Test Coverage | 725 tests | 900+ tests | 1,200+ tests |
| MCP Tools | 49 | 65+ | 80+ |
| SDKs | Python (PyPI) | +JS/TS | +Rust, Go |
| Network Support | Mainnet | +Signet | +Testnet4 |
| Daily API Requests | Growing | 10K+ | 100K+ |
| Community Contributors | 1 | 5+ | 15+ |

---

## How to Support

This project is funded through [OpenSats](https://opensats.org). All code is open source (Apache 2.0 / MIT) and will remain free to self-host forever. Grant funding enables dedicated full-time development, infrastructure costs, and community building.
