#!/usr/bin/env python3
"""Validate content/, state/, feedback/ and examples/. Exit code 1 on any error."""
import sys

import _bootstrap  # noqa: F401
from dsys.cli import main

raise SystemExit(main(["validate", "--all", *sys.argv[1:]]))
