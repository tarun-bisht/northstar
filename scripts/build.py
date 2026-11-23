#!/usr/bin/env python3
"""Validate, generate RSS and build the static site into _site/."""
import sys

import _bootstrap  # noqa: F401
from dsys.cli import main

raise SystemExit(main(["build", *sys.argv[1:]]))
