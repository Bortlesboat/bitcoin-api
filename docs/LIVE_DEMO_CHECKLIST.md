# Live Demo Checklist

## Goal

Keep the live demo under 6 minutes and make it resilient even if the current network is calm.

## Standard Close

`Let's wire this into one real send or payout flow and review usage after a week.`

## Browser Tabs

Open these in order before the call:

1. `https://bitcoinsapi.com/best-time-to-send-bitcoin`
2. `https://bitcoinsapi.com/api/v1/fees/plan?profile=merchant_payout_batch&currency=usd`
3. `https://bitcoinsapi.com/api/v1/guide?use_case=fees&lang=curl`
4. `https://bitcoinsapi.com/mcp-setup`
5. `https://bitcoinsapi.com/api/v1/x402-info`

## Live Flow

### 1. Proof Story

- Start on `/best-time-to-send-bitcoin`
- Say:
  - `This is the fixed proof case I use so the story does not depend on today's fee conditions.`
- Point to:
  - `March 19, 2026 at 1:54 PM EDT`
  - `March 20, 2026 at 7:55 AM EDT`
  - `14,563 sats`
  - `3,451 sats`
  - `76.3%`

### 2. Live Planner

- Open `/api/v1/fees/plan?profile=merchant_payout_batch&currency=usd`
- Say:
  - `This is the hosted response shape your product would call right now.`
- Highlight:
  - `recommendation`
  - `reasoning`
  - `delay_savings_pct`
  - fee tiers

### 3. Integration Path

- Open `/api/v1/guide?use_case=fees&lang=curl`
- Show the quickstart step for the planner
- Say:
  - `This is the exact request your engineer can paste into a service today.`

### 4. Agent Path

- Open `/mcp-setup`
- Show:
  - `plan_transaction(profile="merchant_payout_batch")`
- Say:
  - `If your team wants the same verdict in Claude or another MCP client, this is the setup path.`

### 5. Premium Finish

- Open `/api/v1/x402-info`
- Say:
  - `This is optional. The free planner is the first-touch path. x402 is there when you want keyless premium one-shot analysis.`

## Terminal Rehearsal Commands

Run these before the call if you want a terminal-first demo path ready:

```bash
curl "https://bitcoinsapi.com/api/v1/fees/plan?profile=merchant_payout_batch&currency=usd"
curl "https://bitcoinsapi.com/api/v1/fees/scenarios/merchant-payout-batch-march-2026"
curl "https://bitcoinsapi.com/api/v1/guide?use_case=fees&lang=curl"
curl -i "https://bitcoinsapi.com/api/v1/fees/landscape"
```

## Fallback Assets

If production conditions are boring or a page is temporarily degraded, fall back to:

- `docs/demo-assets/merchant-payout-batch-march-2026.json`
- `https://bitcoinsapi.com/api/v1/fees/scenarios/merchant-payout-batch-march-2026`

## Happy-Path Rehearsal

Checklist:

- [x] Proof page contains the March 19-20, 2026 merchant payout case
- [x] Planner endpoint returns the `merchant_payout_batch` profile
- [x] Guide endpoint exposes the planner curl example
- [x] MCP setup page leads with `plan_transaction`
- [x] x402 info remains available as an optional finish

## Fallback Rehearsal

Checklist:

- [x] Frozen scenario endpoint loads
- [x] Local JSON backup exists
- [x] Demo can be delivered from proof case plus frozen JSON alone

## Abort Conditions

Do not record or run a first external demo if any of these fail:

- proof page missing the dated payout example
- planner endpoint does not return the payout profile
- MCP page still leads with `get_fee_landscape`
- public pages imply `fees/landscape` is the free default
