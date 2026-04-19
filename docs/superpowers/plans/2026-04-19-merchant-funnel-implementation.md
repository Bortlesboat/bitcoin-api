# Merchant Funnel Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a canonical `/facilitator` merchant landing page, turn `/x402` and `/pricing` into feeder pages, and wire the crawl + analytics surfaces so the hosted x402 facilitator is easier to discover, trust, and contact.

**Architecture:** Keep the public story on `bitcoinsapi.com` and keep `facilitator.bitcoinsapi.com` as the live proof/runtime domain. This pass intentionally does not add a self-serve merchant dashboard or a new standalone facilitator microsite; it adds one canonical merchant page, small feeder changes on existing public pages, and light shared instrumentation that works with the current static-page architecture.

**Tech Stack:** FastAPI static routing, static HTML pages, shared `site-helpers.js`, PostHog page instrumentation, pytest

---

## File Structure

- Modify: `src/bitcoin_api/static_routes.py`
  Responsibility: allow the new `/facilitator` static page without changing unrelated route behavior.
- Modify: `src/bitcoin_api/middleware.py`
  Responsibility: keep `/facilitator` public, pageview-logged, and crawlable without accidentally adding it to the noindex set.
- Create: `static/facilitator.html`
  Responsibility: canonical merchant-conversion page for the hosted x402 facilitator.
- Modify: `static/x402.html`
  Responsibility: keep `/x402` proof-first, but add a clear handoff to `/facilitator`.
- Modify: `static/pricing.html`
  Responsibility: add one facilitator callout without turning pricing into a second facilitator explainer.
- Modify: `static/js/site-helpers.js`
  Responsibility: add small shared support for `[data-track-event]` click instrumentation so tracking does not get duplicated inline across pages.
- Modify: `static/sitemap.xml`
  Responsibility: expose `/facilitator` as an indexable canonical public page.
- Modify: `static/llms.txt`
  Responsibility: expose `/facilitator` to lightweight AI-discovery readers.
- Modify: `static/llms-full.txt`
  Responsibility: add the richer merchant-page reference to the long-form AI-discovery surface.
- Modify: `tests/test_health.py`
  Responsibility: route, crawl, helper-asset, pricing, and sitemap regression coverage.
- Modify: `tests/test_x402_stats.py`
  Responsibility: x402 feeder-page assertions.
- Modify: `tasks/todo.md`
  Responsibility: mark plan completion and leave execution-ready tracking state.
- Modify: `tasks/lessons.md`
  Responsibility: capture any reusable implementation discoveries from the actual execution pass.

## Scope Notes

- Do **not** add a global `Facilitator` nav item in this pass. The spec explicitly prefers feeder-page handoffs first so we do not bloat the primary site tree.
- Do **not** add `/facilitator` to `_NOINDEX_PATHS` in `src/bitcoin_api/middleware.py`. `/x402` stays noindex; `/facilitator` becomes the crawlable merchant page.
- Reuse the existing shared helper injection model. Prefer small `data-track-event` attributes plus shared JS over new page-specific tracking code.

## Chunk 1: Canonical Facilitator Surface

### Task 1: Isolate the Work and Lock the Route Boundary

**Files:**
- Modify: `src/bitcoin_api/static_routes.py`
- Modify: `src/bitcoin_api/middleware.py`
- Modify: `tests/test_health.py`

- [ ] **Step 1: Create an isolated worktree before touching implementation files**

Run:

```powershell
git worktree add ../bitcoin-api-merchant-funnel -b codex/merchant-funnel
```

Expected:
- new worktree created at `../bitcoin-api-merchant-funnel`
- branch `codex/merchant-funnel` checked out there

- [ ] **Step 2: Write the failing route and crawlability tests in `tests/test_health.py`**

Add tests shaped like:

```python
def test_facilitator_page_served(client):
    resp = client.get("/facilitator")
    assert resp.status_code == 200
    assert "Hosted x402 facilitator" in resp.text


def test_facilitator_page_is_indexable(client):
    resp = client.get("/facilitator")
    assert resp.status_code == 200
    assert "X-Robots-Tag" not in resp.headers
    assert '<link rel="canonical" href="https://bitcoinsapi.com/facilitator">' in resp.text


def test_facilitator_page_loads_shared_site_helper(client):
    resp = client.get("/facilitator")
    assert resp.status_code == 200
    assert '/static/js/site-helpers.js' in resp.text
```

- [ ] **Step 3: Run the new tests and verify they fail for the right reason**

Run:

```powershell
pytest tests/test_health.py -k facilitator -v
```

Expected:
- FAIL with `404 != 200` for `/facilitator`

- [ ] **Step 4: Open the route boundary in `src/bitcoin_api/static_routes.py`**

Add `"facilitator"` to the allowed static page set:

```python
allowed = {
    ...,
    "mcp-setup", "ai", "fees", "x402", "guides", "facilitator",
}
```

- [ ] **Step 5: Make `/facilitator` public and pageview-logged in `src/bitcoin_api/middleware.py`**

Add `/facilitator` to the public static page sets that already cover pages like `/pricing` and `/guide`:

```python
_PAGEVIEW_LOG_PATHS = {
    ...,
    "/pricing", "/mcp-setup", "/guide", "/facilitator",
}

_RATE_LIMIT_SKIP = {
    ...,
    "/terms", "/privacy", "/disclaimer", "/about", "/pricing", "/facilitator",
    ...
}
```

Do **not** add `/facilitator` to `_NOINDEX_PATHS`.

- [ ] **Step 6: Re-run the route tests**

Run:

```powershell
pytest tests/test_health.py -k facilitator -v
```

Expected:
- still FAIL because the page file does not exist yet, or because canonical copy is missing

- [ ] **Step 7: Commit the route-boundary change once the public route behavior is defined**

Run:

```powershell
git add src/bitcoin_api/static_routes.py src/bitcoin_api/middleware.py tests/test_health.py
git commit -m "feat: expose facilitator landing route"
```

### Task 2: Build the Canonical `/facilitator` Page

**Files:**
- Create: `static/facilitator.html`
- Modify: `tests/test_health.py`

- [ ] **Step 1: Extend the failing tests to pin the page's real contract**

Add assertions for the exact elements the spec requires:

```python
def test_facilitator_page_contains_core_ctas_and_proof_links(client):
    resp = client.get("/facilitator")
    assert resp.status_code == 200
    assert 'data-track-event="facilitator_cta_docs"' in resp.text
    assert 'data-track-event="facilitator_cta_contact"' in resp.text
    assert 'https://facilitator.bitcoinsapi.com/status' in resp.text
    assert 'https://facilitator.bitcoinsapi.com/.well-known/x402' in resp.text
    assert 'https://bitcoinsapi.com/openapi.json' in resp.text


def test_facilitator_page_contains_required_sections(client):
    resp = client.get("/facilitator")
    assert resp.status_code == 200
    for marker in (
        "Live facilitator",
        "Why Satoshi",
        "How it works",
        "Who this is for",
        "Email api@bitcoinsapi.com for onboarding",
    ):
        assert marker in resp.text
```

- [ ] **Step 2: Run the tests and verify they fail on missing markup**

Run:

```powershell
pytest tests/test_health.py -k facilitator -v
```

Expected:
- FAIL on missing title, CTA, proof-link, or required-section assertions

- [ ] **Step 3: Create `static/facilitator.html` with the canonical merchant content**

Build the page with these exact sections:

```html
<title>Hosted x402 Facilitator for API Sellers - Satoshi API</title>
<link rel="canonical" href="https://bitcoinsapi.com/facilitator">

<h1>Hosted x402 facilitator for API sellers</h1>
<p>Monetize APIs, AI tools, and MCP endpoints with USDC on Base.</p>

<a href="/docs" data-track-event="facilitator_cta_docs">View integration docs</a>
<a href="mailto:api@bitcoinsapi.com?subject=x402%20facilitator%20onboarding"
   data-track-event="facilitator_cta_contact">Start onboarding</a>

<a href="https://facilitator.bitcoinsapi.com/status">Live status</a>
<a href="https://facilitator.bitcoinsapi.com/.well-known/x402">Facilitator well-known</a>
<a href="https://facilitator.bitcoinsapi.com/discovery/resources">Merchant resources</a>
<a href="https://bitcoinsapi.com/.well-known/x402">Seller well-known</a>
<a href="https://bitcoinsapi.com/openapi.json">Paid seller OpenAPI</a>
<a href="https://bitcoinsapi.com/api/v1/x402-info">Seller x402 info</a>
```

Content requirements:
- hero, trust strip, "Why Satoshi", "How it works", "Proof", "Who this is for", final CTA
- reuse the existing dark visual language from `static/x402.html` and `static/index.html`
- keep the nav/footer conservative; do **not** introduce a new global `Facilitator` nav item
- keep the page meaningful even if any live-proof fetch fails

- [ ] **Step 4: Keep live proof additive, not required**

If you add a small live-proof widget, keep the copy readable without it and limit the enhancement to trust chips or proof cards. Do not make the hero or CTA depend on JavaScript.

- [ ] **Step 5: Run the facilitator-page tests again**

Run:

```powershell
pytest tests/test_health.py -k facilitator -v
```

Expected:
- PASS for the facilitator-specific tests

- [ ] **Step 6: Commit the canonical page**

Run:

```powershell
git add static/facilitator.html tests/test_health.py
git commit -m "feat: add facilitator landing page"
```

## Chunk 2: Feeder Pages, Tracking, and Verification

### Task 3: Turn `/x402` into a Merchant Feeder Page

**Files:**
- Modify: `static/x402.html`
- Modify: `tests/test_x402_stats.py`

- [ ] **Step 1: Add the failing feeder-page test**

Add a test shaped like:

```python
def test_x402_dashboard_links_to_facilitator_page(client):
    resp = client.get("/x402")
    assert resp.status_code == 200
    assert 'href="/facilitator"' in resp.text
    assert 'data-track-event="x402_to_facilitator_click"' in resp.text
```

- [ ] **Step 2: Run the x402 page test and verify it fails**

Run:

```powershell
pytest tests/test_x402_stats.py -k facilitator -v
```

Expected:
- FAIL on missing `/facilitator` link or tracking attribute

- [ ] **Step 3: Add a merchant intro + CTA near the top of `static/x402.html`**

Add a short proof-first handoff block above the dashboard body:

```html
<p class="subtitle">Live stablecoin micropayment activity on Satoshi API.</p>
<p class="merchant-intro">
  Selling premium API or MCP endpoints? Use the hosted Satoshi x402 facilitator.
</p>
<a href="/facilitator" data-track-event="x402_to_facilitator_click">Use the facilitator</a>
```

Keep the rest of the page analytics-first. Do not rewrite `/x402` into a second full landing page.

- [ ] **Step 4: Re-run the x402 tests**

Run:

```powershell
pytest tests/test_x402_stats.py -v
```

Expected:
- PASS for the new feeder-page assertion and existing x402 stats tests

- [ ] **Step 5: Commit the x402 feeder change**

Run:

```powershell
git add static/x402.html tests/test_x402_stats.py
git commit -m "feat: link x402 dashboard to facilitator page"
```

### Task 4: Add the Pricing Handoff and Shared Tracking Hook

**Files:**
- Modify: `static/facilitator.html`
- Modify: `static/pricing.html`
- Modify: `static/js/site-helpers.js`
- Modify: `tests/test_health.py`

- [ ] **Step 1: Add the failing pricing + shared-helper tests**

Add assertions shaped like:

```python
def test_pricing_page_links_to_facilitator(client):
    resp = client.get("/pricing")
    assert resp.status_code == 200
    assert 'href="/facilitator"' in resp.text
    assert 'data-track-event="pricing_to_facilitator_click"' in resp.text


def test_facilitator_page_contains_page_view_event(client):
    resp = client.get("/facilitator")
    assert resp.status_code == 200
    assert "facilitator_page_view" in resp.text


def test_shared_site_helper_binds_tracked_click_targets(client):
    resp = client.get("/static/js/site-helpers.js")
    assert resp.status_code == 200
    assert "bindTrackedElement" in resp.text
    assert "[data-track-event]" in resp.text
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```powershell
pytest tests/test_health.py -k "pricing_page_links_to_facilitator or tracked_click_targets" -v
```

Expected:
- FAIL on missing pricing link, missing facilitator page-view marker, or missing helper behavior

- [ ] **Step 3: Extend `static/js/site-helpers.js` to bind tracked clicks globally**

Add a small shared binder that captures `data-track-event` clicks when `window.posthog.capture` exists:

```javascript
function bindTrackedElement(element) {
  if (!element || element.dataset.siteHelperTrackedBound === "true") {
    return;
  }

  element.addEventListener("click", function () {
    if (window.posthog && typeof window.posthog.capture === "function") {
      window.posthog.capture(element.dataset.trackEvent, {
        location: element.dataset.trackLocation || "",
        target: element.dataset.trackTarget || "",
      });
    }
  });

  element.dataset.siteHelperTrackedBound = "true";
}
```

Then call it from `processTree(root)` for `[data-track-event]`.

- [ ] **Step 4: Add the facilitator page-view event and the pricing handoff markup**

In `static/facilitator.html`, add a guarded page-load event:

```html
<script>
if (window.posthog && typeof window.posthog.capture === "function") {
  window.posthog.capture("facilitator_page_view", {
    location: "facilitator",
    page: "/facilitator",
  });
}
</script>
```

Use a concise block, not a second pricing table:

```html
<section class="enterprise">
  <p>
    Selling paid API or MCP endpoints? We also run a hosted x402 facilitator.
    <a href="/facilitator"
       data-track-event="pricing_to_facilitator_click"
       data-track-location="pricing"
       data-track-target="facilitator">Learn about the facilitator</a>
  </p>
</section>
```

Do not convert `/pricing` into a facilitator explainer. Keep it as a single handoff.

- [ ] **Step 5: Re-run the health/static tests**

Run:

```powershell
pytest tests/test_health.py -k "pricing_page_links_to_facilitator or facilitator_page_contains_page_view_event or tracked_click_targets or site_helper" -v
```

Expected:
- PASS for the pricing callout, facilitator page-view marker, and helper asset assertions

- [ ] **Step 6: Run a behavioral smoke check for tracked events**

In a browser on `/pricing`, stub PostHog and click the pricing CTA:

```javascript
window.__trackCalls = [];
window.posthog = {
  capture: (event, props) => window.__trackCalls.push({ event, props }),
};
document.querySelector('[data-track-event="pricing_to_facilitator_click"]').click();
window.__trackCalls;
```

Expected:
- one captured event with `event === "pricing_to_facilitator_click"`
- `props.location === "pricing"`
- `props.target === "facilitator"`

- [ ] **Step 7: Commit the shared tracking and pricing handoff**

Run:

```powershell
git add static/facilitator.html static/pricing.html static/js/site-helpers.js tests/test_health.py
git commit -m "feat: add facilitator pricing handoff"
```

### Task 5: Update Crawl and AI-Discovery Surfaces

**Files:**
- Modify: `static/sitemap.xml`
- Modify: `static/llms.txt`
- Modify: `static/llms-full.txt`
- Modify: `tests/test_health.py`

- [ ] **Step 1: Add the failing crawl-surface tests**

Add tests shaped like:

```python
def test_sitemap_includes_facilitator_page(client):
    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "https://bitcoinsapi.com/facilitator" in resp.text


def test_llms_surfaces_reference_facilitator_page(client):
    for path in ("/llms.txt", "/llms-full.txt"):
        resp = client.get(path)
        assert resp.status_code == 200
        assert "https://bitcoinsapi.com/facilitator" in resp.text
```

- [ ] **Step 2: Run the crawl-surface tests and verify they fail**

Run:

```powershell
pytest tests/test_health.py -k "sitemap_includes_facilitator or llms_surfaces_reference_facilitator" -v
```

Expected:
- FAIL because `/facilitator` is not yet present in the crawl/discovery text surfaces

- [ ] **Step 3: Add `/facilitator` to `static/sitemap.xml`**

Add a normal public-page entry, matching the format used for other indexable landing pages. Do not mark it noindex anywhere else.

- [ ] **Step 4: Add `/facilitator` to `static/llms.txt` and `static/llms-full.txt`**

Use concise wording that tells AI readers this is the canonical merchant landing page for the hosted x402 facilitator.

- [ ] **Step 5: Re-run the crawl-surface tests**

Run:

```powershell
pytest tests/test_health.py -k "sitemap_includes_facilitator or llms_surfaces_reference_facilitator" -v
```

Expected:
- PASS

- [ ] **Step 6: Commit the crawl/discovery updates**

Run:

```powershell
git add static/sitemap.xml static/llms.txt static/llms-full.txt tests/test_health.py
git commit -m "feat: surface facilitator page in crawl assets"
```

### Task 6: Final Verification, Smoke Test, and Notes

**Files:**
- Modify: `tasks/todo.md`
- Modify: `tasks/lessons.md`

- [ ] **Step 1: Run the focused regression suite**

Run:

```powershell
pytest tests/test_health.py tests/test_x402_stats.py tests/test_public_discovery_paths.py -v
```

Expected:
- all selected tests PASS

- [ ] **Step 2: Run the repo structural diagnostic required by the repo instructions**

Run:

```powershell
./diagnose.sh
```

Expected:
- no import-cycle, startup, or silo-regression errors

- [ ] **Step 3: Run a manual public-page smoke pass**

Check these routes in a browser:

- `/facilitator`
- `/x402`
- `/pricing`
- `/sitemap.xml`
- `/llms.txt`

Confirm:
- `/facilitator` is crawlable and not tagged `noindex`
- `/facilitator` fires `facilitator_page_view` once on load in the PostHog/network view
- `/x402` still reads as a proof page first
- `/pricing` only contains one facilitator handoff
- `/x402` and `/pricing` CTA clicks emit the expected event names
- CTA links resolve to the intended docs, email, and proof destinations
- no console errors caused by the shared helper change

- [ ] **Step 4: Update task tracking and durable lessons**

In `tasks/todo.md`:
- mark the merchant-funnel implementation plan as complete
- add a short execution checklist if work will continue in a separate session

In `tasks/lessons.md`:
- record any real implementation discovery, especially if route logging, crawlability, or shared helper behavior behaved differently than expected

- [ ] **Step 5: Commit the verification/docs pass**

Run:

```powershell
git add tasks/todo.md tasks/lessons.md
git commit -m "docs: record merchant funnel rollout verification"
```
