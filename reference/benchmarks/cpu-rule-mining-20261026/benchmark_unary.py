"""Offline CPU/memory check for the bounded unary addition; no model/DB writes."""
import argparse
from contextlib import ExitStack
import io
import json
import logging
from pathlib import Path
import platform
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def blocked(*args, **kwargs):
    raise RuntimeError("Offline benchmark: external access disabled")


def peak_mib():
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [(name, ctypes.c_size_t) for name in (
                "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage",
                "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
        counters = Counters(); counters.cb = ctypes.sizeof(counters)
        ctypes.windll.kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if not ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise ctypes.WinError()
        return counters.PeakWorkingSetSize / 1024**2
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024**2 if sys.platform == "darwin" else 1024)


class TreeOnly:
    def __init__(self, *args, **kwargs):
        pass
    def candidates(self, *args, **kwargs):
        return iter(())
    def metrics(self):
        return {"mode":"tree_only_comparison"}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode",choices=("baseline","enhanced"),required=True)
    parser.add_argument("--rows",type=int,default=10000)
    parser.add_argument("--columns",type=int,default=100)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if not 32 <= args.rows <= 10000 or not 2 <= args.columns <= 100:
        parser.error("Bounded workload: 32..10000 rows and 2..100 columns")
    logging.disable(logging.CRITICAL)
    with ExitStack() as stack:
        for name in ("oracledb.connect","oracledb.create_pool","socket.create_connection","socket.socket.connect"):
            stack.enter_context(patch(name,side_effect=blocked))
        stack.enter_context(patch("dotenv.load_dotenv",return_value=False))
        stack.enter_context(patch("logging.FileHandler._open",lambda _:io.StringIO()))
        import numpy as np
        from backend.services.mixed_pattern_algorithm import analyze_pattern_rows
        if args.mode == "baseline":
            stack.enter_context(patch("backend.services.mixed_unary_patterns.SparseUnaryPatterns",TreeOnly))
        rng=np.random.default_rng(42)
        data=rng.integers(0,3,size=(args.rows,args.columns))
        names=[f"C{i+1:03d}" for i in range(args.columns)]
        rows=[dict(zip(names,map(str,row))) for row in data]
        columns=[{"name":name,"dataType":"VARCHAR2"} for name in names]
        options={"maxRows":10000,"maxColumns":100,"maxFeatures":2048,"maxTargets":24,"maxRules":64,
                 "continuousEnabled":False,"randomSeed":42}
        started=time.perf_counter(); result=analyze_pattern_rows(rows,columns,options); seconds=time.perf_counter()-started
        report={"mode":args.mode,"rows":args.rows,"columns":args.columns,"seconds":round(seconds,3),
                "peakWorkingSetMiB":round(peak_mib(),2),"python":platform.python_version(),"cpu":platform.processor(),
                "options":options,"metrics":result["metrics"],
                "scope":"10k x 100 categorical VARCHAR2 CPU workload, condition discovery only; process peak includes Python/imports/input"}
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps({key:report[key] for key in ("mode","rows","columns","seconds","peakWorkingSetMiB")}))


if __name__ == "__main__":
    main()
