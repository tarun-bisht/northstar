#!/usr/bin/env python3
"""Entry point for the toolkit. Run `python scripts/dsys.py -h`."""
import _bootstrap  # noqa: F401
from dsys.cli import main

raise SystemExit(main())
