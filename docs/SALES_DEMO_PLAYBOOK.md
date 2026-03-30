# Sales Demo Playbook

## Goal

Turn the first live sales call into one clear pilot ask:

`Let's wire this into one real send or payout flow and review usage after a week.`

The call is not a broad platform tour. It is a proof-driven demo for one buyer, one problem, and one integration step.

## Ideal Buyer

- Technical founder, CTO, or product engineer at a wallet, payout, treasury, or payment product
- Owns a BTC send, withdrawal, settlement, or rebalance flow
- Already feels the pain of fee timing, batching, or overpaying during spikes

## Buyer Pain

- Current systems know the fee rate, but not whether sending now is smart
- Teams either overpay for urgency they do not need or underpay and create stuck transactions
- Payout operators need a rule they can trust, not raw mempool interpretation on every send

## Core Positioning

Satoshi API is not just a Bitcoin data API.

It is a fee-intelligence layer that tells a product whether to send now or wait.

Lead with the free hosted planner path:

- `GET /api/v1/fees/plan?profile=merchant_payout_batch&currency=usd`

Keep the premium lane secondary:

- `GET /api/v1/fees/landscape`
- deeper x402 or paid-tier analysis

## Opening Talk Track

Use this almost verbatim:

`You already know current fee numbers are not the real problem. The real problem is deciding whether to send now or wait. We help your product make that decision with a response your UI or automation can act on.`

## Flagship Proof Story

Use the same dates and numbers every time.

### Scenario

- Buyer: merchant payout operator
- Product context: wallet, payout, or treasury product
- Use case: daily merchant settlement batch
- Transaction shape: `5 inputs`, `100 outputs`, `segwit`
- Estimated size: `3451 vbytes`

### Decision Moment

- Decision time: `March 19, 2026 at 1:54 PM EDT`
- UTC timestamp: `2026-03-19T17:54:11Z`
- Fee rate at that moment: `4.22 sat/vB`

### Cost If Sent Immediately

- `3451 vB * 4.22 sat/vB = 14,563 sats`
- About `$9.69` at `$66,519/BTC`

### Better Window

- Wait-until time: `March 20, 2026 at 7:55 AM EDT`
- UTC timestamp: `2026-03-20T11:55:00Z`
- Fee rate then: `1.0 sat/vB`

### Cost If Delayed

- `3451 vB * 1.0 sat/vB = 3,451 sats`
- About `$2.30`

### Savings

- `11,112 sats`
- About `$7.39`
- `76.3%` cheaper

### Sales Point

The product value is not "we expose Bitcoin data."

The product value is: `do not send this payout batch yet`.

## Live Demo Structure

1. Historical proof page
   - `https://bitcoinsapi.com/best-time-to-send-bitcoin`
2. Live planner response
   - `https://bitcoinsapi.com/api/v1/fees/plan?profile=merchant_payout_batch&currency=usd`
3. Integration guide
   - `https://bitcoinsapi.com/api/v1/guide?use_case=fees&lang=curl`
4. MCP setup
   - `https://bitcoinsapi.com/mcp-setup`
5. Optional premium finish
   - `https://bitcoinsapi.com/api/v1/x402-info`

## Demo Language

Use these transitions:

- `First I'll show the proof case with a fixed historical window.`
- `Now I'll show the live hosted planner your team would actually call.`
- `Now here's the exact curl request your engineer would paste into a service today.`
- `If you want keyless one-shot premium analysis later, that's where x402 fits.`

## Likely Objections

### `We already check mempool.space.`

Response:

`That gives you fee data. It does not give your product a send-or-wait decision for a specific transaction shape. This planner does.`

### `Our users sometimes need immediate confirmation.`

Response:

`That is fine. The point is not "always wait." The point is knowing when waiting saves money and when the fee window is already cheap enough to send.`

### `We can compute this ourselves.`

Response:

`You can, but then you own the heuristics, thresholds, edge cases, and product interpretation layer. This gives you a stable response shape now and can still be self-hosted later.`

### `Why should I care if the fee difference is only a few dollars?`

Response:

`On one batch it may be a few dollars. On repeated payouts, withdrawals, or rebalances, those decisions compound. The bigger win is also trust: your UI stops guessing.`

## Pilot Ask

Always end with one specific ask:

`Let's wire this into one real send or payout flow and review usage after a week.`

Pilot scope:

- one call site
- one UI or automation surface
- one success metric

Suggested success metrics:

- planner is called on every send or payout attempt
- operator or user sees the verdict before confirming
- one week of decisions is logged and reviewed

## Follow-Up Email

Subject:

`BTC payout timing pilot`

Body:

`Thanks again. The key point from the demo was the March 19-20 payout batch example: 14,563 sats if sent immediately vs 3,451 sats if delayed, a 76.3% savings from timing alone.`

`The hosted path to start with is:`

`GET https://bitcoinsapi.com/api/v1/fees/plan?profile=merchant_payout_batch&currency=usd`

`The proof page is here: https://bitcoinsapi.com/best-time-to-send-bitcoin`

`If helpful, I can wire this into one of your real send or payout flows and we can review usage after a week.`

## DM Version

`Built a Bitcoin fee-intelligence API that tells apps whether to send now or wait. The proof case I show is a merchant payout batch that would have cost 14,563 sats on March 19, 2026 but only 3,451 sats the next morning, a 76.3% difference. If useful, I can mock this into one of your send flows this week.`
