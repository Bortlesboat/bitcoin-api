# Video Production Brief

## Asset

- Format: screen-led founder demo
- Length: `4-6 minutes`
- Style: narrated walkthrough with burned-in captions
- Use: prospect follow-up, homepage proof clip source, short social teaser source

## Goal

Show one buyer, one problem, one proof story, one live product path, and one pilot ask.

## Audience

- Technical founder
- CTO
- Product engineer at a wallet, payout, or treasury product

## Narrative Order

1. Buyer problem
2. Fixed historical proof
3. Live product walkthrough
4. Integration path
5. Pilot ask

## Screen Order

1. `/best-time-to-send-bitcoin`
2. `/api/v1/fees/plan?profile=merchant_payout_batch&currency=usd`
3. `/api/v1/guide?use_case=fees&lang=curl`
4. `/mcp-setup`
5. `/api/v1/x402-info`

## Voiceover Script

### Shot 1: Problem

`If you run a Bitcoin payout or withdrawal flow, the expensive question is not "what is the fee rate?" It is "should we send now or wait?"`

### Shot 2: Proof Case

`Here is the fixed proof case I use in every demo. On March 19, 2026 at 1:54 PM Eastern, this merchant payout batch would have cost 14,563 sats to send. Waiting until the next morning fee window dropped that to 3,451 sats. That is 11,112 sats saved, or 76.3 percent, from one timing decision.`

### Shot 3: Live Planner

`This is the hosted response shape a product would call right now. It gives a recommendation, the reasoning, fee tiers, and the savings from waiting. This is the default free demo path.`

### Shot 4: Integration

`And this is the exact curl request your engineer would paste into a service today. If your team prefers agent workflows, the MCP setup page leads with the same planner call through plan_transaction.`

### Shot 5: Premium Finish

`If you want deeper one-shot analysis later, that is where x402 fits. But the first touch is the free planner.`

### Shot 6: Close

`If this fits your send or payout flow, the next step is simple: let's wire it into one real path and review usage after a week.`

## Burned-In Captions

Use short caption cards:

- `Problem: fee rate is not the decision`
- `Proof: 14,563 sats vs 3,451 sats`
- `Savings: 11,112 sats (76.3%)`
- `Live path: /api/v1/fees/plan`
- `Agent path: plan_transaction`
- `Optional premium: x402`
- `Pilot ask: one real send flow`

## Shot Notes

- Keep cursor movement slow and deliberate
- Pause over the dated numbers on the proof page
- Pause over `recommendation`, `reasoning`, and `delay_savings_pct` in the planner response
- Zoom or crop tightly on the curl example in the guide
- Show `plan_transaction(profile="merchant_payout_batch")` clearly on the MCP page

## Fallback Assets

Use these if the live network is calm or the live planner looks less dramatic than the proof story:

- `docs/demo-assets/merchant-payout-batch-march-2026.json`
- `https://bitcoinsapi.com/api/v1/fees/scenarios/merchant-payout-batch-march-2026`

## Derivative Assets

### Homepage Proof Clip

- Length: `20-30 seconds`
- Focus only on:
  - `14,563 sats`
  - `3,451 sats`
  - `76.3%`
  - CTA: `See if you should send now or wait`

### Social Teaser

- Length: `15-20 seconds`
- Script:
  - `One Bitcoin payout batch. Same transaction shape.`
  - `Send on March 19, 2026: 14,563 sats.`
  - `Wait until the next morning: 3,451 sats.`
  - `That is what fee intelligence is supposed to do.`

## Recording Gate

Record only after:

- proof page, planner, guide, and MCP setup all match the same story
- smoke checks pass
- the live demo checklist is fully checked

## Render Workflow

- Render command: `python scripts/render_sales_demo_video.py --keep-captures`
- Default outputs:
  - `output/sales-demo-video/bitcoinsapi-sales-demo-full.mp4`
  - `output/sales-demo-video/bitcoinsapi-sales-demo-full.srt`
  - `output/sales-demo-video/bitcoinsapi-sales-demo-teaser.mp4`
  - `output/sales-demo-video/bitcoinsapi-sales-demo-teaser.srt`
- The renderer pulls the live proof page, planner path, guide output, and MCP setup page from production, then falls back to the frozen merchant payout scenario for the dated proof case.
- Narration is designed to work without external TTS dependencies by defaulting to a local Windows voice, so the demo can be rerendered on the production workstation even if an API key is unavailable.
