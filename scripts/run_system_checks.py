#!/usr/bin/env python3
"""Run offline service checks and write labelled, machine-readable traces.

Only evaluation/system_results is written. No evaluation root scripts are used.
"""
import json
import os
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"


def main():
    import test_service
    start = time.monotonic()
    suite = unittest.defaultTestLoader.loadTestsFromModule(test_service)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    directory = ROOT / "evaluation" / "system_results"
    directory.mkdir(parents=True, exist_ok=True)
    summary = {
        "tests_run": result.testsRun, "successful": result.wasSuccessful(),
        "elapsed_seconds": round(time.monotonic() - start, 3),
        "failures": [{"test": str(test), "traceback": text} for test, text in result.failures],
        "errors": [{"test": str(test), "traceback": text} for test, text in result.errors],
        "skipped": [{"test": str(test), "reason": reason} for test, reason in result.skipped],
        "scope": "Actual in-process ASGI requests, SQLite, worker, generated media, FFmpeg rendering and full decode. Injected cases explicitly labelled. No browser or external-server coverage.",
        "offline": "No network/model downloads; speech test uses only an existing model and local speech synthesis, or skips.",
    }
    (directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (directory / "traces.json").write_text(json.dumps(test_service.TRACES, indent=2) + "\n")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
