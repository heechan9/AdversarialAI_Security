#!/usr/bin/env python3
"""CLI script to run independent research evidence audit."""

from __future__ import annotations

import sys
from pathlib import Path

# Add src/ to sys.path if needed
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from adversarial_ai.audit.__main__ import main

if __name__ == "__main__":
    main()
