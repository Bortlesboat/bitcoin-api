# Customer Proof Clip Brief

## Goal

Ship one customer-facing proof clip that makes `bitcoinsapi.com` feel credible, sharp, and useful in under `45 seconds`.

This asset is **not** a founder walkthrough and **not** a product tour. It exists to make the buyer believe one thing:

`This API can help my product avoid overpaying Bitcoin fees.`

## Audience

- Technical founder
- CTO
- Product engineer
- Builder who lands on the site, sees a post, or gets the clip in a DM

## Strong Recommendation

Do **not** use the current narrated slide-render as the public asset.

Keep that longer render for:

- prospect follow-up
- internal demo rehearsal
- async explanation after interest already exists

Build the public asset as a separate proof clip:

- `30-45 seconds`
- real product screens, not synthetic slide decks
- caption-led
- either no voice or a human-recorded voice
- one story, one proof case, one CTA

## Why The Current Draft Misses

- It feels like internal enablement, not a premium product artifact.
- The synthetic narration lowers trust instead of raising it.
- There are too many static slide moments and not enough real-product motion.
- MCP and x402 appear too early for a cold audience.
- JSON and code are useful later, but they are not the first emotional hook.
- The clip does not create a clear "I want this in my stack" moment.

## What The Public Clip Should Do

1. Open with the expensive question:
   - `Should I send this Bitcoin payout batch now or wait?`
2. Show the fixed proof case fast:
   - `March 19, 2026: 14,563 sats`
   - `March 20, 2026: 3,451 sats`
   - `76.3% saved`
3. Show the live product briefly:
   - one real page or response
   - one clear verdict
4. End with one CTA:
   - `See if you should send now or wait`

## Narrative Structure

### Scene 1: Hook (`0-6s`)

Large caption over live site or dark motion background:

`The costly question is not the fee rate.`

Then:

`It is whether to send now or wait.`

### Scene 2: Proof (`6-20s`)

Use the merchant payout case with big contrast:

- `Send March 19, 2026 -> 14,563 sats`
- `Wait until next morning -> 3,451 sats`
- `Saved: 11,112 sats (76.3%)`

This is the emotional core of the clip.

### Scene 3: Product (`20-32s`)

Show the real proof page or live planner page.

Only one message matters:

`Satoshi API turns live mempool data into a send-or-wait verdict.`

### Scene 4: CTA (`32-45s`)

Close on:

- `For wallets, payout tools, and AI agents`
- `bitcoinsapi.com/best-time-to-send-bitcoin`
- `See if you should send now or wait`

## Visual Direction

- Prefer live browser captures over fully synthetic slides
- Use tighter crops and motion on real product UI
- Put the biggest numbers on screen with heavy emphasis
- Remove dense code blocks from the public clip
- Keep typography bold and simple
- Keep one visual idea per scene

## Audio Direction

Default recommendation:

- caption-led with no synthetic voice

Better option:

- short human-recorded founder voiceover

Do not publish a customer-facing clip with robotic TTS unless it is dramatically better than the current local Windows voice.

## Copy Direction

Use short outcome-led lines:

- `Should I send now or wait?`
- `One payout batch. Same transaction shape.`
- `14,563 sats vs 3,451 sats.`
- `76.3% saved by timing alone.`
- `Satoshi API tells apps when to send Bitcoin.`
- `See if you should send now or wait.`

## What To Leave Out

- x402 in the main public clip
- MCP in the first `20-30 seconds`
- detailed curl examples
- long explanations
- anything that makes the viewer read like they are in docs

## Asset Split

### Public Homepage / Social Clip

- `30-45 seconds`
- proof-first
- caption-led
- one CTA

### Prospect Follow-Up Demo

- `60-120 seconds`
- can include planner JSON, curl path, MCP path
- can reuse the current demo renderer as a base, but should still get a higher-quality voice and tighter pacing before external use

## Acceptance Criteria

The public clip is ready only if:

- it feels like a product proof asset, not a generated slide deck
- the viewer can understand the value with the sound off
- the viewer sees the proof numbers within the first `15 seconds`
- the clip has exactly one CTA
- the clip makes the product feel more credible, not more improvised
