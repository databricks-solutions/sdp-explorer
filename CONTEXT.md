# SDP Explorer — Project Context

Condensed handoff doc. Everything needed to continue building without prior chat history.

## What this is

An interactive web **explorer that demystifies Lakeflow Spark Declarative Pipelines (SDP) features** for architects & devs — a more intuitive, visual alternative to the docs. Built for **field enablement, scaling SDP adoption in Canada**. Targets both Structured Streaming→SDP migration and net-new workloads.

Each feature is a browsable card whose hero is an **animation/interaction showing what the feature does to the data**, plus a "how it works / when to leverage / watch out" digest. It is shipped as a **Databricks App**.

> Product team is separately building the SS-vs-SDP comparison tool, migration assessor, and TCO calculator — **do NOT duplicate those**. This tool is the feature demystifier.

## Guiding principles (locked with user)

- **Communicate VALUE and COMPLEXITY to the customer, not just data.** Trim sample data to the minimum that makes the point. The animation/interaction IS the explanation.
- **NOT a heavy decision tree / taxonomy.** It's a flat, browsable gallery of bite-sized cards.
- **Lead with the demo, then the SQL.** Card section order: title + one-liner → interactive demo → "The flow" (SQL/Python) → "How it works" → "When to leverage it". Explanatory notes go *after* the syntax they reference (e.g. a `BY NAME` note sits under the SQL, not above it).
- **Honest "when NOT to use / watch out"** on every card — the differentiation vs docs.
- **Styling = Databricks docs look**: white bg, DM Sans font, dark-slate ink `#1b3139`, docs-blue `#2272b4` links, lava-red `#ff3621` accent, thin calm borders, airy spacing. Official logo lockup at `static/databricks-logo.svg` (from docs.databricks.com/aws/en/img/logo.svg).

## Architecture / files

```
sdp-explorer/
├── app.py            # FastAPI serving static/ on 0.0.0.0:$DATABRICKS_APP_PORT (deploy server)
├── app.yaml          # Databricks Apps runtime: command [python, app.py]
├── databricks.yml    # DAB: resources.apps.sdp-explorer, target dev (NO development mode — it prefixes app names invalidly)
├── requirements.txt  # fastapi==0.115.0, uvicorn[standard]==0.30.6
├── dev_server.py     # LOCAL ONLY: livereload server on :8000 (gitignored, not deployed)
├── .gitignore        # excludes .venv/, dev_server.py, __pycache__, .databricks/, .DS_Store
├── README.md
├── CONTEXT.md        # this file
└── static/
    ├── index.html         # THE APP — all cards, styles, animation logic in one file
    ├── gsap.min.js        # vendored GSAP 3.12.7 core (animations)
    ├── gsap-flip.min.js   # vendored GSAP Flip plugin (layout/FLIP animations)
    └── databricks-logo.svg
```

**Everything lives in `static/index.html`** — CSS in one `<style>`, all logic in one `<script>`. No build step, no frameworks. GSAP is vendored (no CDN) and loaded via two `<script src>` tags in `<head>`.

## Local dev loop

```bash
./.venv/bin/python dev_server.py        # livereload server, http://localhost:8000 (run in background)
```
- `.venv` has fastapi, uvicorn, livereload installed. Edits to `static/index.html` **auto-reload the browser** — no manual refresh, no re-open.
- **Always syntax-check JS after edits** (a parse error blanks the whole app at boot):
  ```bash
  awk '/<script>/{f=1;next} /<\/script>/{f=0} f' static/index.html > /tmp/sdp_check.js && node --check /tmp/sdp_check.js && echo "JS OK"
  ```

## Deploy (Databricks App)

```bash
databricks bundle deploy --profile <PROFILE>
databricks bundle run sdp-explorer --profile <PROFILE>
```
- **NOT yet deployed.** `e2-demo` profile is at its 300-app cap (create failed there; bundle files uploaded but no app created — `databricks bundle destroy --profile e2-demo` to clean). Likely target = Canada workspace (`canada-eh` / `azure-canada` profiles need `databricks auth login` first).
- App name `sdp-explorer` (≤26 chars). Static site → tiny FastAPI server; must bind `0.0.0.0:$DATABRICKS_APP_PORT`.

## App internals (how the SPA works)

- **`NAV`** array → sidebar groups + items. Each item: `{ id, name, status }`. `status`: `ready` (clickable), `soon` (greyed, "soon" pill), `preview` (amber pill), `beta` (amber pill). `renderNav()` builds it; clicking a ready/preview/beta item calls `route(id)`.
- **`DEMOS`** map: `id → renderFn` returning the card's HTML string.
- **`route(id)`** sets `main.innerHTML = DEMOS[id]()`, then calls the card's `wireXxx()` to attach behavior; unbuilt ids render `placeholder()`.
- Boot: `routeFromHash()` — reads `location.hash` and routes to that card (falling back to `replace-where` for empty/unknown/`soon` ids). `route(id)` keeps the URL in sync via `history.replaceState("#"+id)`, and a `hashchange` listener handles back/forward + manual hash edits. Deep links like `/#enzyme` work.

### Adding a new card (recipe)
1. Set the `NAV` item's `status` to `ready`.
2. Add `"<id>": <renderFn>` to `DEMOS`.
3. In `route()`, add `if (id === "<id>") wire<Xxx>();`.
4. Write `function <renderFn>()` returning HTML (follow section order above).
5. Write `function wire<Xxx>()` for behavior (placed near the other wire fns, before the boot `route(...)` call).
6. Syntax-check.

## Animation system (GSAP — added on branch `animation-polish`)

All card animations run on **GSAP 3.12.7 + Flip** (vendored). Cards sequence steps with async/await where **every wait is a real tween finishing** (gsap tweens are thenable) — never a blind `setTimeout`. Shared primitives at the top of the `<script>`:

- **`anim(targets, vars)`** — thenable `gsap.to` with `power3.out` default ease. `EASE` = `{ out, in, inOut, pop }`.
- **`flyRow(fromEl, toEl)`** — clones a row and flies it from one table onto its landing row in another (source→target money shot). Hand-rolled delta math ÷ `PAGE_ZOOM`.
- **`renderTableAnimated(container, html)`** — animated re-render for `<table>` outputs (`tr[data-flip-id]`): leaving rows slide out, surviving rows FLIP to their new slot (mid-table inserts push neighbours smoothly), entering rows drop in. Rapid-step safe via per-container seq token. Used by all three AUTO CDC cards.
- **`flipStep(container, mutate)`** — general FLIP through a DOM mutation (available; cards mostly use the two above).
- **Collapse-out delete**: `anim(rows, { opacity:0, x:42, height:0, padding/margin/border→0, stagger })` — rows below glide up in the same tween (REPLACE WHERE, expectations DROP).
- **Count-up numbers**: tween a plain object + `onUpdate` writes formatted `textContent` (MV + Enzyme totals).
- **Run-guard pattern**: each card keeps `let run = 0` (or `run2`); `reset()` bumps it and removes stray `.fly-clone`s; async runs bail out via `if (!live(my)) return;` after every await → Reset mid-animation is always safe.

**Two hard-won gotchas (do not regress):**
1. **`body { zoom: 1.1 }` breaks GSAP Flip's cross-container math** (client rects are visual px, transforms are layout px). `Flip.fit` moved rows ~13px instead of ~800px. That's why `flyRow` does its own delta ÷ `PAGE_ZOOM` (=1.1, keep in sync with the CSS). Same-container FLIP (`renderTableAnimated`) only suffers a ~10% start-offset — imperceptible at row scale.
2. **CSS transitions on `transform`/`opacity` fight GSAP's per-frame styles** (elements creep instead of animating). Any container whose children GSAP drives carries class **`gsap-rows`**, which strips motion transitions and keeps only color crossfades; `.fly-clone` has `transition: none !important`. When adding a card: put `gsap-rows` on the row containers.

## Reusable patterns / primitives

- **source→target merge** (REPLACE WHERE): two `.tbl` panels + arrow; rows fly from source into target.
- **timeline lanes** (Rewind & Replay): stacked lanes sharing an x-axis; draggable handle (`pointerdown/move` on a ruler, snap to `frac = k/N`); today-anchored dates via `new Date()` (browser JS — fine here, unlike workflow sandbox).
- **manual stepper** (AUTO CDC family): `◀ Previous` / main step button / `Reset`. Convention: **when done, main button DISABLES and reads "All N applied"** — do NOT turn it into a second Reset. `Previous` re-enables. State derived purely from `applied` count so back/forward is consistent; rows flash via a `prevSig` Set diff.
- **`.cdc-out` tables**: shared table style for change-feed/output tables; `tr.flash` flash animation; column headers tie to SQL clauses.
- **banners**: `.recon` (amber, reconciliation/"engine did something") and `.recon.diff` (blue, informational per-step diff) and `.insight` (blue, static concept). Keep one consistent diff banner per card rather than scattering messages into a narration line.

## Cards built

Sidebar groups (9): **Datasets · Streaming · Incremental refresh · Change data capture · Flows · Data quality · Governance · Recovery & operations · Deployment** (removed non-SDP MERGE & dynamic-overwrite). NOTE: an Auto Loader (`read_files`) card was built then removed per user ("too low level") — don't re-add.

**Coverage audit (2026-07):** two research agents compared the explorer against SDP docs + active previews. Built the top gaps as 7 new cards (below). Confirmed non-gaps / skipped: serverless perf-mode (no pipeline API — don't build), direct/default publishing mode (diagram not animation, not built), type widening, queued execution, environment versions, event hooks, event-log TVF, pipeline parameters, informational PK/FK (all low data-visual value).

**GOTCHA (cost me a debug cycle):** every card's render + wire fn must be DEFINED before use, but function *declarations* hoist, so DEMOS/route referencing them is fine. BUT if you add a real impl in one place AND leave the old empty `function wireX(){}` stub elsewhere, the **later declaration wins** → the stub shadows your impl (symptom: card renders but wiring is dead, no console error). When implementing a stubbed card, REPLACE its stub line, don't add a second definition.

| id | group | status | what it shows |
|----|-------|--------|---------------|
| `real-time-mode` | Streaming | preview | **Real-time mode** (`pipelines.trigger="RealTime"`, `@update_flow`, Public Preview). **Latency race**: same 8 events into two lanes (micro-batch vs real-time), dots travel along `.rt-track`s. Micro-batch dots stack at a batch-tick gate then flush together (latency = tick − arrival); real-time dots commit on arrival (~7ms). Driven by ONE `gsap.timeline()` with tweens at absolute positions = conceptual-ms × speed factor K; displayed latencies are conceptual-ms (realistic, speed-independent). Verdict banner "~82× lower latency". Speed selector. |
| `sinks` | Flows | ready | **Sinks** (`create_sink` + `append_flow`; GA). Left `events` ST → arrow → dark "external" panel (`.sink-panel`, ink bg = leaves the lakehouse). Format toggle Kafka/Event Hubs/Delta (updates name+badge+SQL). Stepper: ▶ micro-batch appends rows, append flow flies them to sink, offset/checkpoint advances (no re-send). **Money shot = ⟲ Full refresh gotcha**: sink NOT truncated → all rows re-emitted as amber `dup` messages (6→12). |
| `row-filters-masks` | Governance | ready | **Row filters & column masks** (`WITH ROW FILTER` / `col MASK`, recently GA — was a DLT limitation). **Viewer toggle Admin/Analyst** on one `customers` table (`.rf-table`). Admin: 6 rows, clear email/ssn. Analyst: non-CA rows collapse out (gsap height/opacity), email+ssn masked (`a•••@•••••`, `•••-••-8891`), policy chips light. Teaches query-time enforcement, one copy, no view. |
| `liquid-clustering` | Datasets | ready | **Liquid clustering** (`CLUSTER BY` / `CLUSTER BY AUTO`, GA). 8-file grid, query `WHERE region='CA'`. Toggle Unclustered / CLUSTER BY / AUTO. Run → scanned files highlight, pruned files dim (min/max skip). Stats: unclustered 8/8 scanned 0% skipped; clustered 2/8, 75% skipped, 8/32 rows. |
| `private-datasets` | Datasets | ready | **Private datasets** (`CREATE PRIVATE STREAMING TABLE`; `PRIVATE` replaced `TEMPORARY`). 3-node DAG orders_raw(pub)→orders_clean(PRIVATE, dashed ghost)→orders_daily(pub MV). Click a node → external `SELECT` console: published return rows (green), private → red `[TABLE_OR_VIEW_NOT_FOUND]`. Catalog panel lists only published. |
| `watermarks` | Streaming | ready | **Watermarks** (`withWatermark`, GA). Event-time axis (`.wm-axis`) with 3 ten-min window bands + advancing red watermark marker. Stepper feeds 8 out-of-order events; accepted dots stack in band, 2 late events (et<watermark) drop below axis red. Windows close when wm passes end (state freed, green). Chips: "windows in state: 1 · dropped: 2 · without watermark: 3 still open" = bounded-state teaching. |
| `replace-where` | Flows | preview | **REPLACE WHERE** (label, not "FLOW REPLACE WHERE" — that stays only in the SQL). Preview per docs (FLOW REPLACE WHERE badged preview). Source→target merge animation. 5-row today-anchored sample (2 old + last 3 days) demonstrating predicate `date >= current_date()-7`. `BY NAME` note sits under the SQL. Button "Run Refresh". |
| `rewind-replay` | Recovery & operations | preview | **Rewind & Replay** (Streaming Time Travel renamed → just "Rewind and Replay"). Interactive: drag rewind point T; live value meter (rewind vs full-refresh % compute saved); 3 lanes (source events / pipeline checkpoint / target revenue) sharing a today-anchored date axis; on run: ①checkpoint rollback ②erase target after T ③replay through fixed code (code badge buggy→fixed, bug marker ✗→✓ patched). Under-rewinding leaves leftover corrupted rows = consistency teaching moment. Speed selector (Slow default). |
| `auto-cdc` | Change data capture | ready | **AUTO CDC** (`APPLY CHANGES`). Change feed → target. **SCD 1 / SCD 2 toggle**. Manual stepper, **timestamps** (not seq#). Signature moment: a late, out-of-order UPDATE that arrives *after* a DELETE — SCD1 ignores it (stays deleted, no resurrection), SCD2 slots it into history. Column headers tie to `KEYS`/`APPLY AS DELETE WHEN`/`SEQUENCE BY`. |
| `auto-cdc-snapshot` | Change data capture | ready | **AUTO CDC FROM SNAPSHOT** (SCD2 only). Left = plain full snapshots (NO annotations/animation — raw input; a deleted key is simply absent). Right = SCD2 built by diffing consecutive snapshots (all value/flash here). One consistent blue diff banner per snapshot incl. delete-by-absence. Python `create_auto_cdc_from_snapshot_flow(stored_as_scd_type=2)`. |
| `enzyme` | Incremental refresh | ready | **Enzyme** (incremental MV refresh). **Two scheduled teaching moments in the continuous stream** (`fullAt=5`, `nextNewAt=3→7`): (a) a never-seen region key → brand-new group added incrementally; (b) **batch 5 = a change hitting ~80% of groups (4 of 5; `nextNewAt` moved to 6 so still 5 groups at batch 5) → engine picks a FULL REFRESH** — demonstrates runtime cost eval, NOT an all-groups trigger. Incoming touches 4, but ALL 5 rows show "full rebuild" (incl. the untouched 1) since a full refresh rebuilds everything; `incRecomputes += groups.length` on full. **amber** `.recon` banner (not blue `.recon.diff`), "changed 4 of 5 (80%)… full rebuild cheaper than 4 incremental updates… re-evaluates every refresh". `fullDone` fires it once. Continuous animation: click **Start** → batches of 1–2 orders stream into `orders`; the MV `sales_by_region` (5 regions, seeded with history) recomputes **only the touched groups** (blue flash + "recomputed"), the rest show "skipped" (dimmed). **One batch shown at a time** — the incoming panel clears before the next batch so it never grows long. Speed selector (Slow default / Normal / Fast, `speedMul` scales all waits, same pattern as Rewind). vmeter compares cumulative Enzyme recomputes vs full-refresh (all 5 groups every batch) with % saved; blue `.recon.diff` banner narrates each batch. Honest watch-outs: serverless-only, engine decides per-refresh (can fall back to full), event-log `num_output_rows` = total MV rows not work done. Links the 2022 DLT blog. No API — point made in the SQL note. |
| `streaming-table` | Datasets | ready | **Streaming Table**. Manual stepper (▶ Run next micro-batch / ⟲ Simulate restart / Reset). Append-only `raw_events` → `events`; each micro-batch pulls only rows past the checkpoint (offset badge + rows-in-table + read-this-run badges), flash-appends them, advances the offset. Signature moment: **Simulate restart** re-reads 0 committed rows — resumes from checkpoint, no dup/reprocess. `STREAM()` = the incremental switch. |
| `materialized-view` | Datasets | ready | **Materialized View** — simplified (per user: incremental removed, deferred to Enzyme). Stepper "▶ Apply next change" over `revenue_by_category` (5 cats): new orders land → the view refreshes, all rows flash "refreshed", reads hit precomputed totals. **NO toggle, NO vmeter, NO full-vs-incremental section.** Instead a **top-of-card clickable `a.xref` banner** (⚡, sits right under the intro so it's noticeable): one-line "how does it refresh? serverless → Enzyme" that navigates to `#enzyme`. (No longer a full section further down.) Watch-outs still note serverless-only. New reusable style: `a.xref` (blue clickable cross-reference banner w/ hover lift + "→" affordance). |
| `append-flow` | Flows | ready | **Append flow** — 3 flows into one `events` ST. Two continuous (`kafka_us` blue / `kafka_eu` orange) + one **`INSERT INTO ONCE`** backfill (`events_archive`, green). Stepper ▶ Next update: update 1 fires backfill + streams; update 2+ streams only, backfill shows "✓ complete · won't re-run" (greyed, per user "show append once too"). Target rows colored/tagged by provenance flow. |
| `expectations` | Data quality | ready | **Expectations** — 3-way toggle **WARN / DROP ROW / FAIL UPDATE** on one rule (`amount > 0`). Same 5-row batch (2 bad). WARN: all commit, bad flagged/kept (amber). DROP: bad rows animate-out at gate, good commit. FAIL: first violation outlined red, gate ✕ pulses, `.recon.fail` banner, 0 rows commit. Gate ring changes per mode. Links `#quarantine` from the DROP note. |
| `quarantine` | Data quality | ready | **Quarantine** — one stream forks on `is_valid` into `orders_clean` (green) + `orders_quarantine` (amber). 6-row batch (3 bad, incl. null region + amount≤0). ▶ Run batch splits rows into two stacked target panels; chips "3 → clean / 3 → quarantine / 0 rows lost". SQL = WARN expectation computes `is_valid`, two STs filter opposite sides. Teaches: bad rows **retained**, not dropped. |
| `auto-cdc-bitemporal` | Change data capture | beta | **AUTO CDC bitemporal** — SIMPLIFIED (user: concept too high-level; grid removed). Structure: ① "Two timelines, two questions" explainer boxes with the docs hedge-fund hook (price true Jan 1 / learned Jan 5 / report ran Jan 3) — business vs system time as two plain questions; ② step-through of the exact docs example (company A, XFv1→v2→v3 out-of-order→delete) building the 6-row two-axis table, superseded beliefs greyed, FLIP-animated; ③ **payoff = 3 curated question buttons** (`btQs`, replaces the old 4×4 as-of grid): "value at 12:10 as we know now?"→XFv3 (row 3), "what did we believe at 12:22?"→XFv1 (row 1), "does A still exist?"→deleted (row 5). Clicking highlights the answering row **in the table itself** (`.bt-hit`) + fast-forwards the stepper to the final state if mid-step; Run/Prev/Reset clear question state. Q1 vs Q2 = same business moment, different answer = the audit-trail teaching moment. SQL: `SEQUENCE BY` + `SYSTEM SEQUENCE BY` + `STORED AS BITEMPORAL`. |

| `cicd-bundles` | Deployment | ready | **CI/CD & Bundles** — how a pipeline ships as a DAB. **3-way mode toggle (`.cdc-toggle`): One bundle → many targets (default) / Dev inner loop / Prod release.** Whole scene is an animated node-graph: nodes positioned absolutely in a `.cc-map` (centre = `offsetLeft/offsetTop` since nodes use `translate(-50%,-50%)`), connectors are SVG `<path>` built in JS from node anchor points (`pathD()` cubic through waypoints), token travels a flow path via native `path.getPointAtLength()` (no MotionPath plugin). **Fan-out scene (headline value = write once / deploy many):** one `📦 sales_pipeline` bundle fans out to 4 targets — dev, staging, prod·CA-central, prod·CA-east (two Canada regions) — click Deploy → token clone flies to each concurrently (staggered), each lands `done`; insight = one `resources` block, N `targets` override only host/mode/catalog/run_as. **Dev scene:** all 3 routes (① CLI `bundle deploy -t dev` / ② Workspace editor / ③ Git push → CI) **auto-animate continuously & concurrently** (looping GSAP tweens along `.cc-edge.route` paths, staggered; NO select/run — user asked for all flows always-on); `startDevFlows()`/`stopDevFlows()` driven by `showScene` (killed on scene leave to avoid token accumulation — verified 0 leftover). `.cc-legend3` explains the 3 routes. **Prod scene:** main → cut `release/1.4.0` → CI/CD pipeline (3 `.step`s validate→deploy→run light sequentially) → PROD workspace `mode: production`; dashed blocked laptop→prod edge w/ ✕. **Rollback money shot:** deploy v1.4.0, then Roll back → prod flagged bad (⚠) → `git revert` → *same* pipeline redeploys v1.3.0 (green), banner narrates auditable rollback. Code cards: `databricks.yml` (4 targets, `${var.catalog}` per-target, `run_as` service principal) + GitHub Actions `release.yml` (on push release/**). Note: **must set `mode` explicitly** (unset ≠ development → prod semantics). New CSS all `.cc-`-prefixed. NOTE: `${{ secrets.X }}` and `${var.x}` in template-literal code blocks MUST be escaped `\${` (else parsed as JS interpolation → syntax error blanks the app). Verify animations under automation with `gsap.globalTimeline.timeScale(25)` (rAF is heavily throttled headless; screenshots time out — check state via evaluate_script). |

**All gallery cards now built.** (No `soon` items remain.) New primitives added for these: `.ck-badge` (checkpoint offset chips), `.flow-multi` + `.src-mini` (multi-source append fan-in with provenance tints), `.gate`/`.g-ring` (quality gate, mode-colored), `.recon.fail` (red abort banner), `.q-split` + `.fork` (quarantine two-target split), `.row.dropping`/`.row.warned`/`.row.appended`, `money()` helper for negative amounts.

## Key SDP feature facts (verified against docs)

- **REPLACE WHERE** (SDP form): `CREATE OR REFRESH STREAMING TABLE … SCHEDULE EVERY 1 DAY … FLOW REPLACE WHERE <predicate> BY NAME SELECT …`. Matched rows deleted → source query recomputed for that range → inserted, atomically. `BY NAME` **required**. Don't put the predicate in the SELECT — engine applies it. (Not Delta DML `INSERT … REPLACE WHERE`.)
- **AUTO CDC**: `AUTO CDC INTO t FROM STREAM(src) KEYS(...) APPLY AS DELETE WHEN ... SEQUENCE BY ... STORED AS SCD TYPE 1|2`. `SEQUENCE BY` makes it out-of-order safe (sequence order, not arrival). Late event with lower sequence than applied = stale.
- **AUTO CDC FROM SNAPSHOT**: Python `dlt.create_auto_cdc_from_snapshot_flow(target, source, keys, stored_as_scd_type=2)`. Diffs consecutive full snapshots; **deletes inferred from rows that disappear**. Source must be the complete table.
- **AUTO CDC bitemporal** (Beta): docs https://docs.databricks.com/aws/en/ldp/cdc#how-bitemporal-auto-cdc-works . Two time axes (business/valid vs system/awareness). On each change: close prior belief on system axis (`__SYSTEM_END_AT`) + insert corrected rows stamped with new system time; out-of-order corrects history in place. Sequencing cols must be sortable, no NULLs.
- **Rewind & Replay**: triggered SDP only (no continuous/SS); sources Delta+Kafka (no Auto Loader); sinks ST+MV; no stateful operators; CLI `databricks pipelines start-update <id> --json '{"cause":"API_CALL","rewind_spec":{rewind_timestamp,dry_run:false,datasets:[{identifier}]}}'` (CLI >0.283.0); rewind = metadata-only restore (Delta version+offsets+state), pipeline idle after; replay on restart; non-destructive; ~7-day/100-batch retention; can't rewind past FULL REFRESH.

## CSS tokens (in `:root`)

`--bg #fff` · `--ink #1b3139` · `--ink-2 #475a63` · `--muted #6b7c85` · `--line #e2e7ea` · `--panel #f7f8f9` · `--blue #2272b4` · `--blue-bg #eaf3fa` · `--red #ff3621` · greens `--keep #2f8a5b`/`--keep-soft`/`--keep-line` · oranges `--target #c2410c`/soft/line · blues `--src`/soft/line. Fonts: DM Sans (text), DM Mono (code/data).
