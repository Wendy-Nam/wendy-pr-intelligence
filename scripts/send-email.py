#!/usr/bin/env python3
"""Compatibility entry point; provider/config implementation lives in prmonitor."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prmonitor import email_service

# Preserve imports used by older callers, including private config helpers.
globals().update(
    {
        name: value
        for name, value in vars(email_service).items()
        if not name.startswith("__")
    }
)

if __name__ == "__main__":
    email_service.main()
