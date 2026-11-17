"""Capture the full suite as reproducible evidence, including explicit skips."""
import io
import json
import platform
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    import sys
    sys.path.insert(0,str(ROOT))
    stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT/'tests')))
    output=ROOT/'evaluation/unit_results'
    output.mkdir(exist_ok=True)
    (output/'test_log.txt').write_text(stream.getvalue())
    (output/'summary.json').write_text(json.dumps({'tests':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),'skipped':[{'test':str(t),'reason':r} for t,r in result.skipped],'failures':len(result.failures),'errors':len(result.errors),'python':platform.python_version(),'platform':platform.platform()},indent=2))
    print(stream.getvalue())
    return 0 if result.wasSuccessful() else 1

if __name__=='__main__':
    raise SystemExit(main())
