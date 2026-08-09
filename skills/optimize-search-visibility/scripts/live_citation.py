#!/usr/bin/env python3
"""
Live Citation Measurement (BYO-API) — measures whether a real AI answer engine
mentions / cites a given brand or domain, reported as a DISTRIBUTION across N
repeated queries (not a single number).

WHY this exists
---------------
The local citability/SEO heuristics in this skill operate on a fixed fetched
HTML document and are deterministic (variance 0). They do NOT prove how a live
LLM actually answers. True AI-engine citation is unstable across repeated
queries (SE Ranking: 9.2% same-prompt URL overlap; SparkToro: <1/100 brand-list
reappearance), so the only honest measurement is to query a live engine N times
and report the spread. This script closes that gap by calling a real LLM.

ENGINES
-------
- OpenAI (ChatGPT) — implemented. Calls the Chat Completions REST endpoint
  directly with stdlib urllib (no SDK, zero extra dependencies). Default model
  is a cheap one (gpt-4o-mini), prompts are short, default N=5 — to keep cost low.
- Perplexity — scaffolded. If PERPLEXITY_API_KEY is set, queries the Perplexity
  chat endpoint the same way; if not, it is explicitly SKIPPED (never silent).

KEY SAFETY
----------
API keys are read via credential.py from the environment and used only as a
Bearer header. They are never printed, logged, or placed in the output JSON.

DISTRIBUTIONAL REPORTING
------------------------
For each engine, the result is reported as:
  - cited_count / runs (how many of N answers mentioned the brand/domain)
  - citation_rate (cited_count / successful_runs)
  - per-run booleans + which signal matched (domain vs brand)
This mirrors distribution.py's philosophy: report a range / rate, not one number.

Usage
-----
    live_citation.py <brand_or_domain> <query> [more queries...] [--runs N]
                     [--model NAME] [--engine openai|perplexity|all]

    # also accepts: --brand X --domain Y  to score brand and domain separately
    live_citation.py --brand Anthropic --domain anthropic.com \\
        "what is claude code" --runs 5

stdlib only (urllib, json, argparse, os, sys, time, re). No external deps.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from credential import get_openai_key, get_perplexity_key  # noqa: E402

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"  # cheap by default to minimize cost

PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_DEFAULT_MODEL = "sonar"

# Short system prompt: ask for a normal informative answer naming real sources.
# Kept terse to save tokens (cost minimization).
SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's question concisely and "
    "name the specific products, companies, or websites you would point them to."
)

REQUEST_TIMEOUT = 60


def _post_json(url, payload, api_key):
    """POST JSON with a Bearer key; return (parsed_json, error_str).

    The api_key is sent only in the Authorization header — never returned.
    """
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", "Bearer " + api_key)
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
        return json.loads(body), None
    except urllib.error.HTTPError as exc:
        # Read the error body for diagnostics, but scrub nothing key-related is
        # echoed (the key is only in our outbound header, not the response).
        try:
            detail = exc.read().decode("utf-8")[:300]
        except Exception:
            detail = ""
        return None, f"HTTP {exc.code}: {detail}"
    except urllib.error.URLError as exc:
        return None, f"network error: {exc.reason}"
    except json.JSONDecodeError as exc:
        return None, f"response was not valid JSON: {exc}"
    except Exception as exc:  # pragma: no cover - defensive
        return None, f"request failed: {exc}"


def _normalize_domain(domain):
    """Strip scheme / www / path so 'https://www.x.com/a' -> 'x.com'."""
    if not domain:
        return None
    d = domain.strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = re.sub(r"^www\.", "", d)
    d = d.split("/")[0]
    return d or None


def _mentions(answer_text, brand, domain):
    """Detect whether the answer mentions the brand and/or the domain.

    Returns dict {brand: bool, domain: bool, cited: bool}. `cited` is True if
    either signal matched (the question is "did the engine surface us at all").
    """
    text = answer_text.lower()
    brand_hit = bool(brand) and brand.strip().lower() in text
    domain_hit = False
    if domain:
        norm = _normalize_domain(domain)
        if norm:
            # Match the bare domain (x.com) or the registrable root (x) as a word.
            domain_hit = norm in text
            if not domain_hit:
                root = norm.split(".")[0]
                if root and re.search(r"\b" + re.escape(root) + r"\b", text):
                    domain_hit = True
    return {
        "brand": brand_hit,
        "domain": domain_hit,
        "cited": brand_hit or domain_hit,
    }


def query_openai_once(query, api_key, model):
    """One OpenAI call; return (answer_text, error_str)."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        "temperature": 1.0,  # keep default-ish so repeated runs can vary
        "max_tokens": 400,  # short answers -> low cost
    }
    parsed, error = _post_json(OPENAI_URL, payload, api_key)
    if error is not None:
        return None, error
    try:
        text = parsed["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        return None, f"unexpected response shape: {exc}"
    return text, None


def query_perplexity_once(query, api_key, model):
    """One Perplexity call; return (answer_text, error_str). Same REST shape."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        "max_tokens": 400,
    }
    parsed, error = _post_json(PERPLEXITY_URL, payload, api_key)
    if error is not None:
        return None, error
    try:
        text = parsed["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        return None, f"unexpected response shape: {exc}"
    return text, None


def measure_engine(engine, query_fn, api_key, model, queries, runs, brand, domain):
    """Run an engine across queries x runs, return a distributional summary."""
    per_query = []
    total_cited = 0
    total_success = 0
    total_attempts = 0

    for query in queries:
        run_results = []
        cited_in_query = 0
        success_in_query = 0
        for i in range(1, runs + 1):
            total_attempts += 1
            answer, error = query_fn(query, api_key, model)
            if error is not None:
                run_results.append({"run": i, "error": error})
                continue
            success_in_query += 1
            total_success += 1
            hit = _mentions(answer, brand, domain)
            if hit["cited"]:
                cited_in_query += 1
                total_cited += 1
            run_results.append(
                {
                    "run": i,
                    "cited": hit["cited"],
                    "matched": {"brand": hit["brand"], "domain": hit["domain"]},
                    "answer_preview": answer.strip().replace("\n", " ")[:160],
                }
            )
            time.sleep(0.3)  # gentle pacing

        rate = (cited_in_query / success_in_query) if success_in_query else None
        per_query.append(
            {
                "query": query,
                "runs_requested": runs,
                "runs_succeeded": success_in_query,
                "cited_count": cited_in_query,
                "citation_rate": round(rate, 3) if rate is not None else None,
                "runs": run_results,
            }
        )

    overall_rate = (total_cited / total_success) if total_success else None
    return {
        "engine": engine,
        "model": model,
        "queries_tested": len(queries),
        "runs_per_query": runs,
        "total_attempts": total_attempts,
        "total_succeeded": total_success,
        "total_cited": total_cited,
        "overall_citation_rate": round(overall_rate, 3)
        if overall_rate is not None
        else None,
        "report_form": "distribution (cited_count / N), not a single number",
        "per_query": per_query,
    }


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Measure live AI-engine citation of a brand/domain across N "
            "repeated queries, reported as a distribution (cited_count / N)."
        )
    )
    parser.add_argument(
        "positional",
        nargs="*",
        help=(
            "positional args. With neither --brand nor --domain: first arg is "
            "the brand/domain target, the rest are queries. With --brand/--domain "
            "set: all positional args are queries."
        ),
    )
    parser.add_argument("--brand", help="brand name to detect in answers")
    parser.add_argument("--domain", help="domain to detect in answers")
    parser.add_argument(
        "--runs", type=int, default=5, help="repeated calls per query (default 5)"
    )
    parser.add_argument(
        "--model", default=OPENAI_DEFAULT_MODEL, help="OpenAI model (default gpt-4o-mini)"
    )
    parser.add_argument(
        "--engine",
        choices=["openai", "perplexity", "all"],
        default="openai",
        help="which engine(s) to query (default openai)",
    )
    args = parser.parse_args()

    if args.runs < 1:
        print("ERROR: --runs must be >= 1", file=sys.stderr)
        sys.exit(2)

    # Resolve brand/domain and queries from positional args.
    #   - If --brand/--domain is supplied, ALL positionals are queries.
    #   - Otherwise the first positional is the brand/domain target (a value
    #     with a dot is treated as a domain), the rest are queries.
    brand = args.brand
    domain = args.domain
    positional = list(args.positional)
    if brand or domain:
        queries = positional
    else:
        if not positional:
            print(
                "ERROR: provide a brand/domain target (positional, or --brand/--domain)",
                file=sys.stderr,
            )
            sys.exit(2)
        target = positional[0]
        queries = positional[1:]
        if "." in target:
            domain = target
        else:
            brand = target

    if not brand and not domain:
        print(
            "ERROR: provide a brand or domain (positional, or --brand/--domain)",
            file=sys.stderr,
        )
        sys.exit(2)
    if not queries:
        print("ERROR: provide at least one query", file=sys.stderr)
        sys.exit(2)

    output = {
        "brand": brand,
        "domain": domain,
        "runs_per_query": args.runs,
        "engines": [],
        "skipped": [],
    }

    want_openai = args.engine in ("openai", "all")
    want_perplexity = args.engine in ("perplexity", "all")

    if want_openai:
        key = get_openai_key()
        if not key:
            output["skipped"].append(
                {"engine": "openai", "reason": "OPENAI_API_KEY not set"}
            )
            print("[live_citation] OpenAI skip — no key", file=sys.stderr)
        else:
            print(
                f"[live_citation] OpenAI: {len(queries)} quer(y/ies) x {args.runs} runs, "
                f"model={args.model}",
                file=sys.stderr,
            )
            output["engines"].append(
                measure_engine(
                    "openai",
                    query_openai_once,
                    key,
                    args.model,
                    queries,
                    args.runs,
                    brand,
                    domain,
                )
            )

    if want_perplexity:
        key = get_perplexity_key()
        if not key:
            output["skipped"].append(
                {"engine": "perplexity", "reason": "PERPLEXITY_API_KEY not set"}
            )
            print("[live_citation] Perplexity skip — no key", file=sys.stderr)
        else:
            print(
                f"[live_citation] Perplexity: {len(queries)} quer(y/ies) x {args.runs} runs",
                file=sys.stderr,
            )
            output["engines"].append(
                measure_engine(
                    "perplexity",
                    query_perplexity_once,
                    key,
                    PERPLEXITY_DEFAULT_MODEL,
                    queries,
                    args.runs,
                    brand,
                    domain,
                )
            )

    if not output["engines"]:
        output["status"] = "NO_DATA"
        output["message"] = (
            "no engine ran (all skipped — missing keys). See 'skipped'. "
            "This is reported explicitly, not as a zero score."
        )
        print(json.dumps(output, indent=2, default=str))
        sys.exit(1)

    output["status"] = "OK"
    print(json.dumps(output, indent=2, default=str))
    sys.exit(0)


if __name__ == "__main__":
    main()
