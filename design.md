# Atelier — Design System & Interaction Spec

*Four pigments hit the page. Where they overlap, you have evidence.*

**Direction name:** WET INK
**Version:** 2.0 (replaces the paper-and-ink editorial direction entirely)
**Reference study:** microsoft.ai — structural and motion patterns only, see §0.2

---

## 0.1 What Atelier is

Atelier turns a research question into ranked multi-source evidence and a cited report. It gathers **Web** (Tavily), **News** (Google News RSS), **Papers** (Semantic Scholar, OpenAlex, Crossref, arXiv) and **GitHub** in parallel through FastAPI + LangGraph, caches on disk (`v5-categories`, 24h TTL), compiles a deterministic report, and optionally rewrites it with exactly one Gemini call. No auth, no saved history, session state only. Stack: Next.js 16, React 19, Tailwind v4.

This document covers **two surfaces built from one system**:

| Surface | Job | Register |
|---|---|---|
| **Site** (`/`) | Explain what Atelier does in 20 seconds and get the question typed | Expressive, illustrated, animated |
| **Desk** (`/desk`) | Run research and read evidence | Same palette and marks, dialled down 40% |

The site is where the system is loud. The desk is where it works.

## 0.2 What was taken from the reference, and what was not

| Pattern taken | How it is used here |
|---|---|
| Mixed display headline (one italic serif word inside a sans line) | Hero and section heads |
| Abstract painterly symbol per product object | One pigment sigil per **source family**, not per model |
| Image-led entity cards with kicker → title → line → link | Source family cards, mode cards |
| Horizontal expanding accordion for principles | "How Atelier works" step accordion |
| Full-bleed featured hero with overlaid title | Live specimen hero |
| An explicit accessibility toggle in the chrome | "Plain view" switch, §11 |
| Read-time / weight labels on cards | Source counts, API budgets, cache age |

**Not taken:** no assets, no illustrations, no photography, no copy, no colour values, no typefaces from that site. Atelier's palette is pigment-mixing based and its sigils are generated from Atelier's own source taxonomy. Do not download or trace anything from the reference.

---

# 1. Design intent

**The atelier is a mixing studio, not a library.**

Four sources drop onto wet paper. Web is cyanotype blue. News is vermilion. Papers is mulberry. GitHub is verdigris. Each spreads. Where two pigments overlap, the colour multiplies into a third — and that new colour is the entire product thesis rendered as physics: **a claim carried by two independent families is a different colour than a claim carried by one.**

Everything in this system descends from that one idea:

* Corroboration = overlap
* Authority = saturation
* Recency = wetness (edge softness)
* Uncertainty = an unfilled bloom outline
* Disagreement = two pigments that refuse to blend, printed off-register

Nothing is decorative. If a shape does not encode a real value from the API response, it does not ship.

---

# 2. The signature — GATHER BLOOM

The hero is a live canvas. On load, four pigment drops fall onto the page, spread with organic edges, and settle into an overlapping composition. Overlap regions render in multiply blend, producing the mixed hues.

```
        ┌─────────────────────────────────────────────┐
        │                                             │
        │        ●●●●●                                │
        │      ●●●●●●●●●     WEB · cyanotype          │
        │     ●●●●╳╳╳╳●●●●                            │
        │      ●●╳╳███╳╳●●●   ← 3-family overlap      │
        │       ●╳╳███╳╳●●      = strongest evidence  │
        │        ●●╳╳╳●●●●●●                          │
        │          ●●●●●●●●●●●  PAPERS · mulberry     │
        │            ●●●●●●●                          │
        │                                             │
        │   NEWS · vermilion      GITHUB · verdigris  │
        └─────────────────────────────────────────────┘
```

**It is not ambient.** It is wired to the product:

| Surface | What the bloom is doing |
|---|---|
| Site hero | Idle demo. Drops fall on a 9s loop, then hold. Hovering a family name in the legend isolates that pigment and fades the rest to 12%. |
| Studio (question typed) | Drops preview the **selected persona/category** — pick AI Engineer and the news drop disappears from the composition before you spend a call. |
| Pipeline loader | Each drop lands **when its LangGraph node actually returns**. Web comes back in 1.2s, its blue lands at 1.2s. A failed family lands as a dry grey outline. This replaces every spinner in the product. |
| Results header | Frozen final composition, sized by source count per family. It is the run's fingerprint. |
| Evidence row | A 32px miniature bloom per claim. Two overlapping pigments = two families support it. One flat circle = single source, unconfirmed. |

One canvas component, five contexts, zero fake states. This is the thing people will remember and it is also the honest status display.

**Implementation:** SVG with `feTurbulence` + `feDisplacementMap` for the wet edge, `mix-blend-mode: multiply` on each pigment group, GSAP or Web Animations API for the drop timing. Total budget under 40KB, no video, no Lottie. Under Plain view (§11) it renders as four flat labelled discs with no motion.

---

# 3. Visual identity

| Element | Direction |
|---|---|
| Ground | Raw paper white `#FBFAF7`. Not cream, not grey. Sections alternate with `#F2EFE9` and one deep `#14161A` band. |
| Illustration | Painterly pigment sigils, one per source family and one per research mode. Soft edges, visible grain, no outlines, no icons-in-circles. |
| Shape language | Blooms, washes, off-register overlaps, torn edges. Nothing geometric. Radius is either 0 or 999px (a bloom), never 8px. |
| Photography | **None of people.** Atelier has no team page and stock faces would be a lie. Photography is macro texture only: ink on paper, pigment in water, paper fibre. Used at low opacity behind the deep band. |
| Iconography | Drawn as pigment strokes at 24px, not a downloaded icon set. Nine icons total, listed §8. |
| Chrome | Very light. Thin sticky header, generous air, no borders around content blocks. |
| Depth | Layering by blend mode and opacity, never by shadow. |

## 3.1 The sigil set

Each is a single-colour painterly mark, delivered as SVG plus a 2x PNG fallback.

| Sigil | Subject | Form | Colour |
|---|---|---|---|
| `web` | Live web | Three concentric ripples, off-centre, the outer ring broken | Cyanotype |
| `news` | Current developments | A fast diagonal stroke with a torn trailing edge | Vermilion |
| `papers` | Academic | Four translucent overlapping rectangles, slightly rotated, like stacked offprints | Mulberry |
| `github` | Implementations | A wet fork: one stroke splitting into two | Verdigris |
| `claim` | Evidence ledger row | A knot where three strokes converge | Ink |
| `agreement` | Consensus | Two blooms overlapping cleanly, the overlap darker | Verdigris + cyanotype |
| `disagreement` | Conflict | Two blooms printed off-register, a hard white gap between them | Vermilion + mulberry |
| `gap` | Research gap | A bloom with an unpainted hole at its centre | Gold |
| `cache` | Cached run | A bloom with a dry, hard, fully-set edge | Ink 40% |

Generate these once as a set so the strokes share a hand. Keep the source files in `/design/sigils/*.svg`.

---

# 4. Colour

Pigments, not brand colours. Every hue in the interface is either a pigment, a mix of pigments, or the ground.

## 4.1 Pigments

| Token | Hex | Family | Meaning |
|---|---|---|---|
| `--pig-web` | `#2E6E8E` | Web / Tavily | Cyanotype blue |
| `--pig-news` | `#D8592F` | News / RSS | Vermilion |
| `--pig-papers` | `#6B4E9B` | Papers | Mulberry |
| `--pig-github` | `#2F7F63` | GitHub | Verdigris |
| `--pig-gold` | `#C79A26` | Gaps, uncertainty, warnings | Ochre |

## 4.2 Mixes (computed, do not hand-pick)

These are what multiply blend produces. Hardcode them only for flat fallbacks and Plain view.

| Mix | Hex | Read as |
|---|---|---|
| web × papers | `#2A4A6B` | Strong technical + academic |
| web × github | `#276B6E` | Implemented and documented |
| papers × news | `#8A4F63` | Published and reported |
| all four | `#1F3A46` | Fully corroborated |

## 4.3 Ground and ink

| Token | Hex | Use |
|---|---|---|
| `--ground` | `#FBFAF7` | Default page |
| `--ground-2` | `#F2EFE9` | Alternating sections, cards |
| `--ground-3` | `#E7E2D8` | Hairlines, inactive |
| `--deep` | `#14161A` | One inverted band per page |
| `--ink` | `#14161A` | Type |
| `--ink-2` | `#4E5259` | Secondary |
| `--ink-3` | `#878B92` | Tertiary, placeholder |

**Rules.** Pigments never fill large areas — they are marks, sigils, blooms, and 2px rules. Body text is always ink on ground. The deep band appears exactly once per page. No gradients anywhere except inside pigment art.

---

# 5. Typography

| Role | Face | Notes |
|---|---|---|
| Display | **Fraunces** (variable) | `SOFT 40, WONK 1` at large sizes. Italic is used for exactly one word per headline. Optical size axis set per step. |
| UI / body | **Geist Sans** | 400/500/600 only |
| Utility | **Geist Mono** | Source codes `[S04]`, scores, counts, endpoints, timings |

## 5.1 The mixed headline

The signature type move, used on the site only:

```
   Four sources.
   One  answer  you can
        ▔▔▔▔▔▔ Fraunces italic, WONK 1
   actually check.
```

Rules: one italic word per headline, always the word carrying the argument (*answer*, *evidence*, *disagree*, *check*). Never two. Never on the desk surface.

## 5.2 Scale

| Token | Site | Desk | Face |
|---|---|---|---|
| `--t-hero` | 88 / 0.94 | — | Fraunces 300, tracking -0.03em |
| `--t-h1` | 56 / 1.02 | 34 / 1.1 | Fraunces 400 |
| `--t-h2` | 38 / 1.1 | 26 / 1.2 | Fraunces 400 |
| `--t-h3` | 24 / 1.25 | 20 / 1.3 | Geist 600 |
| `--t-lead` | 21 / 1.5 | 18 / 1.55 | Geist 400 |
| `--t-body` | 17 / 1.6 | 16 / 1.6 | Geist 400 |
| `--t-small` | 14 / 1.5 | 14 / 1.5 | Geist 400 |
| `--t-kicker` | 12 / 1.2, +0.12em, uppercase | same | Geist 600 |
| `--t-mono` | 13 / 1.4 | 13 / 1.4 | Geist Mono |

Hero clamps to `clamp(44px, 7vw, 88px)`. Measure caps at 62ch on the site, 72ch on the desk.

---

# 6. Layout

## 6.1 Site page rhythm

```
┌──────────────────────────────────────────────────────────────┐
│ ▸ HERO            full-bleed bloom canvas + mixed headline    │  100vh
├──────────────────────────────────────────────────────────────┤
│ ▸ ASK             the question field, floating over paper     │  auto
├──────────────────────────────────────────────────────────────┤
│ ▸ FAMILIES        4 sigil cards, staggered heights            │  auto
├──────────────────────────────────────────────────────────────┤
│ ▸ HOW IT WORKS    horizontal accordion, 5 steps               │  auto
├──────────────────────────────────────────────────────────────┤
│ ▸ SPECIMEN        deep band · live desk screenshot + callouts │  auto
├──────────────────────────────────────────────────────────────┤
│ ▸ MODES           5 mode cards with mode sigils               │  auto
├──────────────────────────────────────────────────────────────┤
│ ▸ HONESTY         what Atelier will not do                    │  auto
├──────────────────────────────────────────────────────────────┤
│ ▸ FOOTER          ask field repeated + repo + stack           │  auto
└──────────────────────────────────────────────────────────────┘
```

Grid: 12 columns, 1280 max, 24px gutters, 32px page margin (16 on mobile). Vertical rhythm on an 8px base with section padding of 128 / 96 / 64 by breakpoint.

**Deliberate asymmetry.** The family cards sit at four different vertical offsets (0, 48, 24, 72px) so the row reads as marks laid on a desk rather than a grid of tiles. This offset is removed under 900px.

## 6.2 Desk layout

```
┌──────────────────────────────────────────────────────────────┐
│ ⬤◗ atelier   "does rag still beat long context?"    EXPLORE  │ 56px sticky
│              ▲ run bloom, 28px, live                         │
├────────────┬─────────────────────────────────────────────────┤
│ BRIEF      │                                                 │
│ EVIDENCE   │   reading area, 72ch                            │
│ SOURCES    │                                                 │
│ CONFLICTS  │                                                 │
│ GAPS       │                                                 │
│ ────────   │                                                 │
│ ⬤ 8 web    │                                                 │
│ ⬤ 4 news   │                                                 │
│ ⬤ 9 papers │                                                 │
│ ⬤ 3 github │                                                 │
└────────────┴─────────────────────────────────────────────────┘
```

The run bloom sits in the header at 28px and stays there for the whole session. It is the anchor, and clicking it reopens the run summary.

---

# 7. Motion

Motion is the interactive layer the product was missing. It is spent in four places and nowhere else.

| # | Moment | Behaviour | Timing |
|---|---|---|---|
| 1 | **Gather bloom** | Four drops fall, spread, multiply. Staggered 0 / 320 / 640 / 900ms | 2.4s total, then hold |
| 2 | **Section reveal** | On scroll: sigil paints in via `stroke-dashoffset` + mask wipe, then text rises 16px with 60ms stagger | 700ms sigil, 400ms text |
| 3 | **Accordion open** | Horizontal panel expands from 88px to 420px, sigil rotates 4°, body cross-fades in | 420ms |
| 4 | **Bloom spread on data** | Score, agreement, and family counts animate their bloom radius on first paint | 500ms |

Micro-interactions, all 150–200ms:

* Card hover: sigil scales to 1.04 and its edge softens (blur 0 → 1.5px). The card itself does not move or lift.
* Citation `[S04]` hover: the marker fills with its family pigment, its source row in the drawer highlights.
* Question field focus: the underline wets — a 2px rule spreads from centre in the mix colour of the active families.
* Button hover: pigment fills from the bottom edge upward, text inverts to ground.
* Copy / export success: a small bloom stamps at the cursor, once, no toast.

**Easing:** `--ease-wet: cubic-bezier(.16,.84,.34,1)` for spreads, `--ease-ui: cubic-bezier(.2,.6,.2,1)` for everything else.

**Never:** parallax on text, scroll-jacking, cursor followers, marquees, typewriter effects, number counters, looping ambient particles, page transitions over 400ms.

```css
@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition-duration: 1ms !important; }
  .bloom { --bloom-state: settled; }  /* renders final frame only */
}
```

---

# 8. Components

| Component | Purpose | States |
|---|---|---|
| `GatherBloom` | The signature canvas, five contexts (§2) | idle-loop, preview, live, frozen, failed-family, plain |
| `MixedHeading` | Display headline with one italic word | — |
| `AskField` | Question input, oversized, wet underline | empty, typing, too-short, submitting, error |
| `FamilyCard` | One source family: sigil, kicker, name, what it gets you, count | rest, hover, disabled (no API key) |
| `ModeCard` | Explore / Compare / Evaluate / Academic / News | rest, selected, planned-badge |
| `DepthPicker` | Quick 4 · Standard 6 · Deep 10 per source, budget printed | selected, disabled |
| `StepAccordion` | Horizontal 5-step "how it works" | collapsed, expanded, mobile-stacked |
| `PipelineBloom` | Loader: drops land as nodes return | queued, running, landed, dry (failed), cached |
| `SpecimenBand` | Deep-band product shot with pigment callout lines | static, in-view (callouts draw in) |
| `SourceRow` | Ruled row: code, title, family sigil, date, score bloom | rest, hover, open, dead-link |
| `SourceDrawer` | Provenance: why ranked, quality blooms, original | opening, open, no-preview, unscored |
| `CitationChip` | Inline `[S04]`, mono, family-tinted | rest, hover, focus, active |
| `ClaimRow` | Claim + supporting chips + mini bloom + strength | multi-family, single-source, conflicting |
| `ConflictPair` | Two off-register blooms, positions side by side | planned-placeholder, populated |
| `GapCard` | Numbered gap with hollow bloom | populated, none-found |
| `ScoreBloom` | Quality as bloom radius, five steps, no decimals | 1–5, unscored |
| `PlainToggle` | Kills all pigment art and motion (§11) | on, off |
| `ReportBar` | Compile / Enhance (1 call) / Export | idle, compiling, enhancing, done |

## 8.1 Icon set (drawn, not imported)

`ask` · `refresh` · `open-external` · `download` · `close` · `expand` · `check` · `alert` · `plain-view`

24px, 1.75px stroke, painterly terminals, single colour, inherits `currentColor`.

---

# 9. Screens

Every screen: purpose, wireframe, components, states.

## A. Site hero

**Purpose** — say what this is and start the bloom in the first second.

```
┌──────────────────────────────────────────────────────────────────────┐
│ ⬤◗ atelier              how it works   sources   modes   [ open desk ]│
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   RESEARCH DESK                    ╭──────────────────────╮          │
│                                    │      ●●●●●           │          │
│   Four sources.                    │    ●●●╳╳╳●●●         │          │
│   One  answer  you                 │   ●●╳╳███╳╳●●●       │          │
│        ▔▔▔▔▔▔                      │    ●●╳╳╳╳●●●●●       │          │
│   can actually check.              │      ●●●●●●●         │          │
│                                    ╰──────────────────────╯          │
│   Ask a question. Atelier searches                                   │
│   the web, the news, the papers and    ⬤ web    ⬤ news              │
│   the code, then shows you which       ⬤ papers ⬤ github            │
│   sources back which claim.            ↑ hover to isolate            │
│                                                                      │
│   [ Ask a question ↓ ]   no signup · nothing saved                   │
│                                                                      │
│                              ⌄ scroll                                │
└──────────────────────────────────────────────────────────────────────┘
```

**Components** — `GatherBloom` (idle-loop), `MixedHeading`, legend, primary CTA.
**States** — *loading* (ground + headline paint first, bloom joins at 400ms so the page is never blank) · *reduced-motion* (settled frame, legend still interactive) · *plain view* (four labelled discs).

## B. Ask

**Purpose** — the field is the product. It gets its own section and full attention.

```
│                                                                      │
│   ── ASK ─────────────────────────────────────────────────────       │
│                                                                      │
│   What are you trying to find out?                                   │
│                                                                      │
│   ┌────────────────────────────────────────────────────────────┐     │
│   │  Does retrieval still beat long-context for enterprise…    │     │
│   └────────────────────────────────────────────────────────────┘     │
│    ══════════════════════════════════ wet underline, mix colour      │
│                                                                      │
│   MODE   ⬤ Explore  ○ Compare  ○ Evaluate  ○ Academic  ○ News        │
│   DEPTH  ○ Quick 4   ⬤ Standard 6   ○ Deep 10   per source           │
│   ASKING ⬤ web  ⬤ papers  ⬤ github        ≈ 18 results · 0 AI calls  │
│                                                                      │
│                                    [ Run research → ]                │
│                                                                      │
│   Or try:  agent frameworks 2026 · RAG vs long context · multimodal   │
```

Selecting or deselecting a family animates that pigment in or out of the hero bloom above. The cost line updates live.

**States** — *empty* ("Type a question. Not keywords.") · *short* (submit disabled, hint under the rule) · *submitting* (underline saturates, button fills) · *no Tavily key* (web family greys with the reason printed inline).

## C. Families

**Purpose** — make the four sources concrete and show what each one is good for.

```
│   ── WHAT GETS SEARCHED ──────────────────────────────────────       │
│                                                                      │
│   ╭─────────╮      ╭─────────╮      ╭─────────╮     ╭─────────╮      │
│   │ ((( ))) │      │  ╱╱╱╱   │      │ ▤▤▤▤    │     │  ⑂      │      │
│   │  ripples│      │  torn   │      │ stacked │     │  fork   │      │
│   ╰─────────╯      ╰─────────╯      ╰─────────╯     ╰─────────╯      │
│   LIVE WEB         NEWS             PAPERS          CODE             │
│   Tavily           Google News      S2 · OpenAlex   GitHub Search    │
│                    RSS              Crossref·arXiv                   │
│   Docs, analysis,  What shipped     Peer-reviewed   Who actually     │
│   engineering      this month       work and its    built it, and    │
│   writing          and when         citations       how active       │
│                                                                      │
│   offset 0px       offset 48px      offset 24px     offset 72px      │
```

**States** — *rest* · *in-view* (sigil paints in, staggered 90ms) · *hover* (sigil edge softens) · *unavailable* (sigil desaturates to 20%, kicker reads "needs a key").

## D. How it works

**Purpose** — kill the "is this a chatbot?" question in one glance.

Horizontal accordion. Collapsed panels show a vertical label and the sigil. One is open at a time.

```
│  ┌────┬────┬──────────────────────────────────┬────┬────┐            │
│  │ 01 │ 02 │  03  GATHER IN PARALLEL          │ 04 │ 05 │            │
│  │ A  │ R  │  ────────────────────────        │ R  │ E  │            │
│  │ S  │ O  │  All four families run at once   │ A  │ X  │            │
│  │ K  │ U  │  in a LangGraph node each. One   │ N  │ P  │            │
│  │    │ T  │  failing does not stop the rest. │ K  │ O  │            │
│  │    │ E  │                                  │    │ R  │            │
│  │    │    │  ●●●╳╳●●●  ← bloom fills here    │    │ T  │            │
│  └────┴────┴──────────────────────────────────┴────┴────┘            │
```

Steps: **01 Ask** · **02 Route** (persona picks which families run) · **03 Gather** · **04 Rank & link** · **05 Compile or enhance** (one Gemini call, optional).

**States** — *collapsed* · *expanded* · *mobile* (stacks vertically, all open, no accordion).

## E. Specimen band

**Purpose** — one inverted band showing the real desk with pigment callouts.

```
├══════════════════════════════════════════════════════════════════════┤ deep
│                                                                      │
│   Every claim carries its receipts.                                  │
│                                                                      │
│      ┌────────────────────────────────────────┐                      │
│      │  [ real screenshot of the desk ]        │──── callout line     │
│      │                                        │     drawn on scroll   │
│      └────────────────────────────────────────┘                      │
│           │                    │                                     │
│      ⬤ family sigil       ⬤ mini bloom = 3 families agree           │
│                                                                      │
├══════════════════════════════════════════════════════════════════════┤
```

Callout lines are hairline pigment strokes that draw in with `stroke-dashoffset` when the band is 40% in view.

## F. Modes

Five cards, each with its own mode sigil. Compare and Evaluate carry a small mono badge: `shapes the report, not the search yet`.

```
│  ╭──────────╮ ╭──────────╮ ╭──────────╮ ╭──────────╮ ╭──────────╮   │
│  │ EXPLORE  │ │ COMPARE  │ │ EVALUATE │ │ ACADEMIC │ │ NEWS     │   │
│  │ open     │ │ two      │ │ one      │ │ papers   │ │ last 30  │   │
│  │ question │ │ options  │ │ choice   │ │ first    │ │ days     │   │
│  │          │ │ PLANNED  │ │ PLANNED  │ │          │ │          │   │
│  ╰──────────╯ ╰──────────╯ ╰──────────╯ ╰──────────╯ ╰──────────╯   │
```

## G. Desk — pipeline

**Purpose** — replace the spinner with the truth.

```
│  "Does retrieval still beat long-context…"              STANDARD     │
│                                                                      │
│              ╭─────────────────────────╮                             │
│              │        ●●●●●            │   web landed    6  1.2s     │
│              │      ●●●●●●●            │   news landed   4  0.8s     │
│              │        ·  ·             │   papers …                  │
│              │      ( dry outline )    │   github ✕ rate limited     │
│              ╰─────────────────────────╯                             │
│                                                                      │
│              10 sources in · 2 of 4 families                         │
```

A landed family = its pigment blooms into the composition. A failed family = a dry grey outline that stays visible, never removed.

## H. Desk — brief

```
┌──────────┬──────────────────────────────────────────────────────────┐
│ BRIEF ▌  │  ⬤◗ THE SHORT ANSWER                                     │
│ Evidence │                                                          │
│ Sources  │  For enterprise search, retrieval still wins on cost     │
│ Conflicts│  and freshness. Long context wins on multi-document      │
│ Gaps     │  reasoning. Most 2026 deployments run both. [S04] [P02]  │
│          │                                                          │
│ ──────── │  ── WHERE SOURCES AGREE ──                               │
│ ⬤ 8 web  │  ◉ Latency favours retrieval at scale                    │
│ ⬤ 4 news │    3 families · 6 sources    [S01][S04][P02]             │
│ ⬤ 9 papr │  ◉ Context windows removed most chunking work            │
│ ⬤ 3 gh   │    2 families · 4 sources    [P07][G02]                  │
│          │                                                          │
│          │  ── WHERE IT IS THIN ──                                  │
│          │  ○ Cost at production volume is claimed, not measured    │
│          │    1 family · 1 source       [N03]                       │
└──────────┴──────────────────────────────────────────────────────────┘
```

`◉` is a mini bloom sized and coloured by the families backing it. `○` hollow means single-source.

**States** — *compiled* · *enhanced* (mono note: "rewritten by Gemini · one call · sources unchanged") · *degraded* (gold note: "enhance failed, showing the compiled brief") · *thin* (under 5 sources).

## I. Desk — sources and drawer

```
│  SOURCES        ⬤ web 8   ⬤ news 4   ⬤ papers 9   ⬤ github 3        │
│  ──────────────────────────────────────────────────────────────      │
│  S01  ((( ))) Retrieval at scale: what we kept   2026-06  ●●●●●      │
│  P02  ▤▤▤▤    Long-context limits in multi-hop   2026-01  ●●●●○      │
│  N03  ╱╱╱╱    Vendor claims 90% cost cut         2026-08  ●●○○○      │
│  G02  ⑂       langgraph/retrieval-bench          2026-07  ●●●○○      │
│                                                                      │
│                   ┌──────────────────────────────────────┐           │
│                   │  P02  ▤▤▤▤                    close ×│           │
│                   │  Long-context limits in multi-hop QA │           │
│                   │  arXiv · 2601.08812 · 14 Jan 2026    │           │
│                   │                                      │           │
│                   │  WHY IT RANKED                       │           │
│                   │  Title and abstract match both key   │           │
│                   │  terms. 41 citations. 8 months old.  │           │
│                   │                                      │           │
│                   │  Relevance ●●●●●   Authority ●●●●○   │           │
│                   │  Recency   ●●●●●   Evidence  ●●●●○   │           │
│                   │                                      │           │
│                   │  CITED IN  claim 01, claim 03        │           │
│                   │  [ Open original ↗ ]                 │           │
│                   └──────────────────────────────────────┘           │
```

Scores are five blooms, never a percentage, never a decimal. Unscored renders `○○○○○` with the word "not scored".

## J. Desk — conflicts and gaps

```
│  CONFLICTS                                                           │
│  ────────────────────────────────────────────────                    │
│        ●●●●●●        ●●●●●●     ← off-register, hard white gap       │
│      ●●●●●●●●●    ●●●●●●●●●                                          │
│                                                                      │
│      Not built yet. Atelier will show where credible sources         │
│      reach different conclusions. It needs the evidence layer        │
│      first, so it lands in phase 3.                                  │
│      Meanwhile: claim 03 is marked conflicting in Evidence.          │
│                                                                      │
│  GAPS                                                                │
│  ────────────────────────────────────────────────                    │
│  ◍ 1  No source measures cost at production volume. All four         │
│       cost claims trace back to vendor material.                     │
│  ◍ 2  Benchmarks reuse the same two datasets. [P02][P07]             │
│  ◍ 3  Nothing published after June 2026 on hybrid deployment.        │
```

`◍` is the hollow gap sigil. Empty states are always written as a sentence explaining what is missing and when it arrives, never as a shrug.

---

# 10. Asset production list

Nothing here is downloadable from anywhere. Produce it once, keep the source files.

| Asset | Format | Size | Notes |
|---|---|---|---|
| 4 family sigils | SVG + PNG@2x | 240×240 | One pigment each, painterly edge |
| 5 mode sigils | SVG | 160×160 | Ink only, lighter weight than family sigils |
| 5 state sigils (claim, agreement, disagreement, gap, cache) | SVG | 120×120 | |
| Bloom shader assets | SVG filters | inline | `feTurbulence` seeds 1–4, one per family |
| 9 UI icons | SVG sprite | 24×24 | 1.75px stroke |
| 3 texture plates | WebP | 1600w, ≤120KB | Ink in water, paper fibre, dried wash. Deep band only, ≤14% opacity |
| Specimen screenshots | WebP | 2400w | Real desk, real run, no mockup frames, no floating devices |
| OG image | PNG | 1200×630 | Frozen bloom + wordmark |
| Favicon / wordmark | SVG | — | `⬤◗` — a wet drop meeting a dry edge |

**Do not use:** stock photography of people, 3D renders, gradient meshes, isometric illustration, device mockups, AI-generated faces.

Performance budget: hero under 180KB total, `LCP` under 2.0s on 4G, all sigils inlined as SVG rather than fetched, textures lazy.

---

# 11. Accessibility

* **Plain view toggle** in the header, persisted in `localStorage`. It flattens every bloom to a labelled disc, disables all motion, and switches score blooms to `4/5` text. This is a first-class view, not a degraded one, and it is tested at every release.
* Contrast on ground `#FBFAF7`: ink 15.1:1, ink-2 7.4:1, web 5.3:1, papers 6.9:1, news 4.6:1 (14px+/600 only), github 5.1:1, gold 4.5:1 (large text and marks only, never body).
* **No colour-only meaning.** Every pigment is always paired with the family name or its sigil shape. A colourblind user reads "papers" from the stacked-rectangle mark, not the mulberry.
* Blooms are `aria-hidden`. The data they encode is exposed as text: `aria-label="Supported by 3 families, 6 sources"`.
* Citation chips are real buttons with descriptive labels, in reading order, and the drawer traps focus and returns it on close.
* Pipeline progress is `aria-live="polite"` and announces each family once as it lands or fails.
* Focus: 2px outline in the active mix colour, 2px offset, never removed.
* Keyboard: `/` focus ask · `1–5` desk sections · `[` `]` prev/next source · `Esc` close · `Cmd/Ctrl+Enter` run.
* WCAG **AA** minimum throughout, AAA on body copy.

---

# 12. Responsive

| Breakpoint | Behaviour |
|---|---|
| ≥1280 | Full system. Bloom at 560px, family cards staggered, accordion horizontal. |
| 1024–1279 | Bloom 420px, stagger reduced by half. |
| 768–1023 | Hero stacks: headline then bloom. Family cards 2×2, no offsets. Accordion goes vertical. |
| <768 | Bloom 300px and drops to 2 pigments per frame for performance. Ask field full width, sticky CTA bar at the bottom. Desk sections become a horizontal scrolling tab bar; drawer becomes an 85vh bottom sheet; source table becomes stacked records. Order: **Brief → Evidence → Sources → Conflicts → Gaps**. |

On mobile the bloom animation runs once and does not loop, saving battery.

---

# 13. Tokens

```css
:root {
  /* pigments */
  --pig-web:      #2E6E8E;
  --pig-news:     #D8592F;
  --pig-papers:   #6B4E9B;
  --pig-github:   #2F7F63;
  --pig-gold:     #C79A26;

  /* mixes (flat fallbacks for Plain view) */
  --mix-web-papers:  #2A4A6B;
  --mix-web-github:  #276B6E;
  --mix-papers-news: #8A4F63;
  --mix-all:         #1F3A46;

  /* ground and ink */
  --ground:   #FBFAF7;
  --ground-2: #F2EFE9;
  --ground-3: #E7E2D8;
  --deep:     #14161A;
  --ink:      #14161A;
  --ink-2:    #4E5259;
  --ink-3:    #878B92;

  /* type */
  --font-display: "Fraunces", Georgia, serif;
  --font-ui:      "Geist Sans", system-ui, sans-serif;
  --font-mono:    "Geist Mono", ui-monospace, monospace;

  --t-hero:   clamp(2.75rem, 7vw, 5.5rem);
  --t-h1:     clamp(2rem, 4vw, 3.5rem);
  --t-h2:     clamp(1.625rem, 3vw, 2.375rem);
  --t-h3:     1.5rem;
  --t-lead:   1.3125rem;
  --t-body:   1.0625rem;
  --t-small:  0.875rem;
  --t-kicker: 0.75rem;
  --t-mono:   0.8125rem;
  --track-kicker: 0.12em;
  --track-hero:  -0.03em;

  /* space */
  --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:24px;
  --s6:32px; --s7:48px; --s8:64px; --s9:96px; --s10:128px;

  /* layout */
  --max-w:      1280px;
  --measure:    62ch;
  --measure-desk: 72ch;
  --header-h:   56px;
  --rail-w:     200px;
  --drawer-w:   440px;

  /* edge */
  --hair: 1px solid var(--ground-3);
  --r-none: 0;
  --r-bloom: 999px;
  --focus: 2px solid currentColor;

  /* motion */
  --ease-wet: cubic-bezier(.16,.84,.34,1);
  --ease-ui:  cubic-bezier(.2,.6,.2,1);
  --d-micro:  160ms;
  --d-ui:     240ms;
  --d-reveal: 420ms;
  --d-bloom:  2400ms;
}
```

Bloom edge filter:

```html
<filter id="wet-web">
  <feTurbulence type="fractalNoise" baseFrequency="0.012" numOctaves="3" seed="1"/>
  <feDisplacementMap in="SourceGraphic" scale="26" xChannelSelector="R" yChannelSelector="G"/>
  <feGaussianBlur stdDeviation="1.2"/>
</filter>
```

Each pigment group: `mix-blend-mode: multiply; opacity: .82;` on a `--ground` backdrop. Seeds 1–4 per family so no two blooms have the same edge.

Scroll reveal:

```js
const io = new IntersectionObserver((entries) => {
  entries.forEach((e) => e.isIntersecting && e.target.classList.add("is-in"));
}, { threshold: 0.35, rootMargin: "0px 0px -10% 0px" });
document.querySelectorAll("[data-reveal]").forEach((el) => io.observe(el));
```

---

# 14. Feature status

| Feature | Purpose | Status |
|---|---|---|
| Parallel multi-source gather | Four families in one pass | **SHIPPED** |
| Persona/category routing | Chip picks which families run | **SHIPPED** |
| Depth budgets 4 / 6 / 10 | Bounded, printed cost | **SHIPPED** |
| Source explorer + drawer | Audit every source, see why it ranked | **SHIPPED** |
| Research brief | Usable answer before the report | **SHIPPED** |
| Deterministic report compile | Cited report, zero LLM cost | **SHIPPED** |
| Gemini enhance | One structured call, compile as fallback | **SHIPPED** |
| Export MD / JSON / print PDF | Handoff | **SHIPPED** |
| Disk cache, `force_refresh` | Never pay twice | **SHIPPED** |
| Research gaps | Deterministic, thin | **SHIPPED** |
| Gather bloom (all five contexts) | Signature + honest status | **PLANNED** |
| Unified quality score → bloom radius | Explain ranking | **PLANNED** |
| Evidence layer, claim → families | Mini blooms, agreement counts | **PLANNED** |
| Research modes with backend routing | Modes change output shape | **PLANNED** |
| Conflicts panel | Off-register pair, populated | **PLANNED** |
| Compare matrix | Criteria grid | **PLANNED** |
| Source-independence clustering | "8 of 12 share one origin" | **PLANNED** |

---

# 15. Constraints the design must respect

| Constraint | Consequence |
|---|---|
| `POST /api/research/multi { topic, limit, force_refresh, category? }` | Mode is UI-only today. Compare and Evaluate cards carry the honest badge. |
| `POST /api/research/synthesize { sources…, use_llm }` | Report is a separate explicit action. Enhance says "one call" next to it. Never auto-run. |
| Depth: quick 4, standard 6, deep 10 per source | The number is printed, not described as "more thorough". |
| Codes S / N / P / G | Codes appear in chips, rows, drawer, exports. Never renamed in UI. |
| Cache key `v5-categories`, 24h, not per user | Cache age is shown with Refresh. Copy never says "your history". |
| Errors merge per family, run completes | Every screen has a partial state. Dry outline, not a hidden failure. |
| No auth, no history, session only | No account chrome anywhere. "Nothing saved" is stated on the hero as a feature. |

---

# 16. Rules

1. Every shape encodes a value from the response. No decoration.
2. Overlap means corroboration. Never fake an overlap for looks.
3. Motion reports state. If it does not report state, cut it.
4. Pigment marks, ink type. Body copy is never coloured.
5. No fake precision. Five blooms, never 87.4%.
6. Failures stay on screen as dry outlines.
7. One italic word per headline, and only on the site.
8. Plain view is a real view, tested every release.
9. Modes change output shape, not just filters.
10. Name the actual work. No "AI is thinking".

---

# 17. Roadmap

| Phase | Ships | Design work |
|---|---|---|
| **1 · Ink** | Token system, type, site hero, ask, families, footer | Pigment palette, sigil set, `GatherBloom` idle + preview |
| **2 · Desk** | Desk under the new system: brief, sources, drawer, report bar | Bloom as pipeline loader, score blooms, family-tinted citation chips |
| **3 · Evidence** | Evidence layer, unified scoring, agreement counts | Mini blooms per claim, conflict pair, populated gaps |
| **4 · Modes** | Backend routing, per-mode report templates | Mode sigils go live, badges come off, per-mode section order |
| **5 · Return** | Persistence, saved runs, "what changed?" | Run blooms as a session index — every past run is its own fingerprint |

---

# 18. What Atelier is NOT

* **Not a chatbot.** No message list, no turns, no assistant persona. A question produces a document.
* **Not a Perplexity replacement.** It works on questions where the evidence needs inspecting, not on everything.
* **Not an autonomous agent.** No ReAct loop, no self-directed re-querying. The budget is fixed before the run starts.
* **Not a dashboard.** No KPI tiles, no widget grid, no charts nobody asked for.
* **Not a citation manager.** No library, no BibTeX, no tags. Export is the handoff.
* **Not a decoration exercise.** Every bloom on screen is data. Remove the data and the bloom goes with it.

---

# 19. Position

Principles only, nothing copied.

| | Elicit | Litmaps | Consensus | Perplexity | **Atelier** |
|---|---|---|---|---|---|
| Primary object | Paper table | Citation graph | Claim + meter | Chat answer | **Question + evidence set** |
| Families | Papers | Papers | Papers | Web | **Web, news, papers, code** |
| Ranking transparency | Partial | Graph shape | Aggregated | Opaque | **Per-factor, in the drawer** |
| LLM usage | Per paper | None | Classification | Every turn | **One optional call** |
| Conflict handling | Weak | N/A | Meter | Averaged away | **Named section, phase 3** |
| Code / implementations | No | No | No | Incidental | **First-class family** |
| Session model | Accounts | Accounts | Accounts | Threads | **Stateless, export-first** |
| Visual model | Spreadsheet | Node graph | Search list | Chat | **Pigment overlap as corroboration** |

Given up: library, persistence, paper-level extraction depth. Gained: four families in one pass, a visible reason behind every rank, bounded cost per question, and a status display that cannot lie.

---

# 20. Build checklist

- [ ] Fraunces + Geist Sans + Geist Mono loaded, subset, `font-display: swap`
- [ ] Token block in `globals.css`, Tailwind v4 `@theme` mapped to it
- [ ] Sigil set drawn and inlined as React components
- [ ] `GatherBloom` built once, driven by props for all five contexts
- [ ] Pipeline wired to real LangGraph node completion, not fake timing
- [ ] Plain view toggle, persisted, tested
- [ ] `prefers-reduced-motion` path verified on every animated component
- [ ] Every screen has empty, loading, partial, and error states written as sentences
- [ ] Contrast audit passes AA on every pigment pairing
- [ ] Hero under 180KB, LCP under 2.0s on 4G
- [ ] No stock photos of people, no device mockups, no gradient meshes