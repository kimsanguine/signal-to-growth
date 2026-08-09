#!/usr/bin/env python3
"""
Credential helper for external APIs (DataForSEO, OpenAI, Perplexity).

Keys are read from environment variables only. They are NEVER printed, logged,
or echoed by these helpers — callers receive the value or None and must keep it
out of any output.
"""
import os


def get_dataforseo_credentials() -> tuple:
    """Get DataForSEO login and password from environment"""
    login = os.environ.get("DATAFORSEO_LOGIN")
    password = os.environ.get("DATAFORSEO_PASSWORD")
    return login, password


def get_openai_key():
    """OpenAI API key from environment, or None if unset.

    Used by live_citation.py for BYO-API live citation measurement.
    Returns the raw key; callers MUST NOT print or log it.
    """
    return os.environ.get("OPENAI_API_KEY")


def get_perplexity_key():
    """Perplexity API key from environment, or None if unset.

    Returns None when PERPLEXITY_API_KEY is not set so callers can explicitly
    skip the Perplexity path ("Perplexity skip — no key") instead of failing
    silently.
    """
    return os.environ.get("PERPLEXITY_API_KEY")
