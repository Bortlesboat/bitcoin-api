# Merchant Funnel Design

Date: 2026-04-19
Status: Drafted and approved in brainstorming; awaiting written-spec review and user signoff
Scope: `bitcoinsapi.com` merchant-acquisition path for the hosted x402 facilitator

## Summary

`bitcoinsapi.com` already has the technical pieces needed to look credible in the x402 ecosystem:

- a live seller surface with curated x402 discovery at `/.well-known/x402`, `/openapi.json`, and `/api/v1/x402-info`
- a live facilitator runtime at `https://facilitator.bitcoinsapi.com` with `/status`, `/.well-known/x402`, and `/discovery/resources`
- an x402 analytics page at `/x402`

The missing piece is a canonical merchant-conversion path. Today the story is discoverable if someone already knows where to look, but the site does not yet give merchants one clear page that says what the facilitator is, why it is credible, and what to do next.

This design adds that path without fragmenting the public site or creating a second competing microsite.

## Goals

- Create one canonical facilitator page on `bitcoinsapi.com` for merchants and ecosystem reviewers.
- Reuse the existing seller site, trust surface, and documentation tree instead of building a second marketing site.
- Turn the existing x402 and pricing pages into feeder pages that point toward one conversion target.
- Preserve a clean information architecture so `/x402` remains proof-oriented and `/facilitator` remains conversion-oriented.
- Expose live proof from the facilitator runtime without making the page depend entirely on live client-side fetches.
- Instrument the funnel so we can measure whether interest is moving toward docs or onboarding.

## Non-Goals

- Building a full self-serve merchant dashboard in this pass.
- Repositioning the homepage around x402 at the expense of the core API product.
- Creating a separate standalone marketing site on `facilitator.bitcoinsapi.com`.
- Expanding the facilitator protocol/runtime surface beyond what is already needed for current discovery and proof.

## Current Context

### Existing seller-facing surfaces

- `static/x402.html` is a live payment analytics page, not a merchant onboarding page.
- `static/pricing.html` covers hosted API, Pro, and self-hosted product pricing.
- `src/bitcoin_api/static_routes.py` controls which public static pages can be served and which URLs redirect.
- `src/bitcoin_api/x402_public.py` already centralizes public seller metadata for:
  - `/api/v1/x402-info`
  - `/api/v1/x402/pricing`
  - `/.well-known/x402`
  - paid-only `/openapi.json`

### Existing facilitator-facing surfaces

- `ops/x402-facilitator/app_factory.py` exposes:
  - `/status`
  - `/.well-known/x402`
  - `/discovery/resources`
  - `/discovery/merchant`
  - `/supported`
  - settlement and observability endpoints
- `ops/x402-facilitator/facilitator_metadata.py` defines merchant resources, registry metadata, and well-known payloads.

### Current gap

The public tree does not include a dedicated facilitator landing page, so the link graph currently asks merchants to infer the product from proof surfaces rather than guiding them through a clear story.

## Recommended Approach

Build the facilitator funnel on the main `bitcoinsapi.com` site and use `facilitator.bitcoinsapi.com` as the live proof/runtime domain.

This is preferred over:

- putting the full funnel on `facilitator.bitcoinsapi.com`, which would split trust and duplicate site content
- focusing first on deeper facilitator operations instead of acquisition, which helps later-stage adoption more than current discoverability

## Information Architecture

Each page should keep one clear job:

- `/` remains the broad product homepage for Satoshi API.
- `/pricing` remains the plan and packaging page for the core API.
- `/x402` remains the proof-first protocol and analytics page.
- `/facilitator` becomes the merchant conversion page for the hosted x402 facilitator.
- `/docs`, `/openapi.json`, `/.well-known/x402`, and facilitator runtime endpoints remain documentation and proof surfaces, not primary landing pages.

### Link tree

The intended primary path is:

`Home -> x402 -> Facilitator -> Docs or Onboarding`

Supporting internal-link rules:

- `/x402` should link strongly to `/facilitator`.
- `/pricing` should include one focused facilitator callout to `/facilitator`.
- `/facilitator` should link outward to live proof and docs.
- Footer and sitemap may include `/facilitator`, but the site should avoid repeating facilitator links in every surface.

## Proposed Public-Site Changes

### 1. Add `/facilitator`

Add a new static page and route entry for `/facilitator`.

Purpose:

- explain the offer in merchant language
- establish proof and trust
- give merchants two clear next steps

Required page sections:

#### Hero

- headline: hosted x402 facilitator for API sellers
- subhead: concise explanation that the product helps API operators, AI tools, and MCP sellers monetize endpoints with USDC on Base

#### Primary CTA row

- `View integration docs`
- `Start onboarding`

For now, onboarding can be a direct email path if there is not yet a self-serve intake flow.

#### Trust strip

Short proof chips that are sourced from existing reality, not aspirational claims:

- live facilitator
- Base USDC
- discovery enabled
- merchant endpoints live

#### Why Satoshi

This should stay specific rather than generic. It should emphasize:

- live seller plus facilitator in production
- public discovery and status surfaces
- focus on API and agent-native monetization
- more hands-on and specific than large generalist providers

#### How it works

Simple three-step explanation:

1. Merchant exposes or prepares paid routes.
2. Facilitator verifies and settles x402 payments.
3. Buyers and scanners discover the surface through x402-compatible endpoints.

#### Proof section

Deep-link to live proof surfaces:

- `https://facilitator.bitcoinsapi.com/status`
- `https://facilitator.bitcoinsapi.com/.well-known/x402`
- `https://facilitator.bitcoinsapi.com/discovery/resources`
- `https://bitcoinsapi.com/.well-known/x402`
- `https://bitcoinsapi.com/openapi.json`
- `https://bitcoinsapi.com/api/v1/x402-info`

#### Who this is for

Short cards for:

- API companies
- AI tool vendors
- MCP sellers
- developers monetizing premium endpoints

#### Final CTA block

End with one self-education path and one high-intent path:

- `Read docs`
- `Email api@bitcoinsapi.com for onboarding`

### 2. Strengthen `/x402` as a feeder page

`/x402` should remain the analytics and protocol-proof page, but the top of the page should explicitly acknowledge the merchant use case.

Required change:

- add a short merchant-oriented intro and a strong CTA toward `/facilitator`

This page should not become a second facilitator explainer; it should point toward the dedicated conversion page.

### 3. Add a facilitator callout to `/pricing`

`/pricing` should remain focused on hosted API plans, but it should include a concise facilitator section or callout that says:

- the company also offers hosted x402 facilitation for sellers
- the right place to learn more is `/facilitator`

This gives existing comparison-oriented traffic a clean handoff without turning the pricing page into mixed-intent content.

### 4. Review shared navigation and footer links

Navigation changes should be conservative:

- add `Facilitator` to the main nav only if it does not crowd the primary product-evaluation path
- otherwise, link it strongly from `/x402`, `/pricing`, and relevant docs first

Footer, sitemap, canonical tags, and crawl surfaces should all treat `/facilitator` as the canonical merchant page.

## Data and Rendering Model

The facilitator landing page should be mostly static HTML for speed, resilience, and crawlability.

Optional live-proof widgets may fetch from:

- `https://facilitator.bitcoinsapi.com/status`
- `https://facilitator.bitcoinsapi.com/discovery/resources`
- `https://bitcoinsapi.com/api/v1/x402-info`

Rules:

- the page must still read well if live fetches fail
- proof widgets are enhancement, not the page's only evidence
- live data should be additive and bounded to trust elements, not core comprehension

## Testing Plan

### Routing and regression coverage

- add tests that `/facilitator` is publicly routable
- add tests that feeder pages include the intended facilitator link(s)
- add tests for any new redirects, canonical tags, or sitemap entries

### Public HTML assertions

- verify the page contains the primary facilitator CTA(s)
- verify live proof links point at the intended facilitator and seller endpoints
- verify the page remains coherent if any client-side proof widget cannot load

### Manual smoke checks

- desktop and mobile review of `/facilitator`
- confirm the site tree remains understandable when navigating:
  - home -> x402 -> facilitator
  - pricing -> facilitator
  - facilitator -> docs / proof links

### Safety checks

- ensure no static route changes accidentally expose unrelated pages
- ensure new internal links do not create duplicate-intent page loops between `/x402` and `/facilitator`

## Instrumentation

Track a minimal event set:

- `facilitator_page_view`
- `facilitator_cta_docs`
- `facilitator_cta_contact`
- `x402_to_facilitator_click`
- `pricing_to_facilitator_click`

The events should retain attribution context sufficient to classify source, for example:

- internal navigation
- x402 ecosystem referral
- docs
- direct
- GitHub / social

## Expected Outcomes

### Low-variance outcomes

- clearer merchant story
- stronger internal-link and crawl structure
- better reviewer confidence because proof and conversion are separated cleanly
- one canonical page for ecosystem references and outreach

### Medium-variance outcomes

- higher click-through from x402-related traffic into a deliberate merchant path
- better signal on whether visitors want docs or onboarding help

### High-variance outcomes

- actual merchant adoption and market share, which also depends on external distribution, ecosystem listing status, and outbound efforts

## Risks and Mitigations

### Risk: page cannibalization between `/x402` and `/facilitator`

Mitigation:

- keep `/x402` proof-oriented
- keep `/facilitator` conversion-oriented
- avoid duplicating long explainer sections across both pages

### Risk: live widgets become stale or brittle

Mitigation:

- keep the core message static and durable
- use live widgets only as proof enhancement
- test the page in a degraded state

### Risk: navigation gets noisier

Mitigation:

- add facilitator links selectively
- prefer feeder-page handoffs before enlarging the global nav

## Implementation Boundaries

This spec intentionally stops at the merchant funnel. It does not include:

- seller self-serve onboarding flows
- merchant dashboards
- settlement export UX
- deeper facilitator operations tooling

Those should be designed as follow-on sub-projects if the funnel creates real demand.

## Approval Gate

After the written spec is reviewed and approved, the next step is to create a detailed implementation plan before making code changes.
