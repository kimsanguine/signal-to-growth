# Platform Citation Factors

Per-platform citation source distribution and top optimization factors for AI answer engines.

> **Status: reporting/reference aid only.** This document records what was observed in one vendor's dataset. It is NOT a directive to build separate strategies per platform — see the REFUTED warning below.

---

## ⚠️ Read This First — Data Honesty Warnings

### 1. Staleness (high severity)

- All numbers below come from a **2024-08 to 2025-06 snapshot** — roughly a year stale as of this document.
- Citation mixes are **already shifting**. By 2026, YouTube is reported to be overtaking Reddit on several surfaces. Treat any rank order below as a historical reading, not a current target.
- **Re-verify against fresh data before acting on any number here.**

### 2. Single-vendor source + measurement variance

- Primary source is **Profound** (a GEO analytics vendor with a marketing incentive to make AI-citation tracking look tractable). Do not treat its framing as neutral ground truth.
- Numbers for the same source disagree across vendors due to differing methodology / sampling:

  | Source for "Wikipedia citation share" | Reported value |
  |---|---|
  | Profound (this doc) | 7.8% (ChatGPT, of all citations) |
  | Similarweb | 13.15% |
  | Analyze AI | 12.1% |

  The spread (7.8% → 13.15%) is a methodology artifact, not a contradiction to resolve. Cite the vendor and date whenever you quote a figure.

### 3. REFUTED claim — do NOT use this doc to justify it

- The claim **"each platform fundamentally requires a different strategy (encyclopedic vs community)"** was **REFUTED in adversarial verification (verdict 1-2)**.
- A single well-structured, well-sourced, authoritative content asset tends to perform across platforms simultaneously. The per-platform source skew below does **not** prove that one strategy cannot serve multiple platforms.
- Use this document only as a **reporting / reference aid** for where citations have historically come from — not as evidence for fragmenting your content strategy.

---

## Per-Platform Citation Source Distribution (Profound, 2024-08 – 2025-06)

| Platform | Top source | Share (all citations) | Share within top-10 sources | Distribution shape |
|---|---|---|---|---|
| **ChatGPT** | Wikipedia | 7.8% | 47.9% | Highly concentrated — Wikipedia dominates |
| **Perplexity** | Reddit | 6.6% | 46.7% | Highly concentrated — Reddit dominates |
| **Google AI Overviews** | Reddit | 2.2% | — | More balanced / flatter (Reddit leads but only narrowly) |

Google AI Overviews secondary sources (illustrating the flatter distribution):

| Rank | Source | Share (all citations) |
|---|---|---|
| 1 | Reddit | 2.2% |
| 2 | YouTube | 1.9% |
| 3 | Quora | 1.5% |

Read: ChatGPT and Perplexity each lean heavily on a single source type; Google AIO spreads citations across more sources, so no single source clears ~2.2%.

---

## Per-Platform Top Factor Summary

| Platform | Top historical citation factor |
|---|---|
| **Google AI Overviews (AIO)** | Top-10 organic ranking + Q&A structure |
| **ChatGPT** | Wikipedia presence + clear entity definition |
| **Perplexity** | Reddit presence + original / primary research |
| **Gemini** | YouTube presence + Google Knowledge Panel |
| **Bing Copilot** | IndexNow submission + Bing Webmaster Tools coverage |

These are correlational observations from the snapshot period, not validated causal levers. The REFUTED warning above applies: do not read this table as "build five separate strategies."

---

## How to Use This Document

- **Do**: use it to explain *where* AI citations have historically originated when reporting or contextualizing an audit.
- **Do**: pull a fresh measurement before quoting any percentage to a client.
- **Don't**: cite it as proof that platforms need fundamentally different content strategies (REFUTED).
- **Don't**: treat the rank order as current — it is a ~1-year-old, single-vendor snapshot already in motion.

---

## Sources

- **Profound** GEO citation analysis, 2024-08 – 2025-06 snapshot (primary; single vendor, marketing incentive).
- **Similarweb** — Wikipedia citation share 13.15% (methodology differs from Profound).
- **Analyze AI** — Wikipedia citation share 12.1% (methodology differs from Profound).

_Snapshot window: 2024-08 to 2025-06. Document last reviewed against the source set on 2026-06-02. Re-verify before use._
