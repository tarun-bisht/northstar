#!/usr/bin/env python3
"""Validate content, then write the seven RSS feeds to feeds/."""
import _bootstrap  # noqa: F401
from dsys.cli import main

raise SystemExit(main(["rss"]))
