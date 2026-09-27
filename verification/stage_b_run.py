"""Run the existing evaluators in a separate environment and compare saved labels.

This is an independent operator/environment rerun, NOT an independently implemented
attack or inference algorithm. No completion is asserted until both runs compare.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from .stage_b_readiness import check_stage_b_readiness, _load_json, _sha256
except ImportError:
    from stage_b_readiness import check_stage_b_readiness, _load_json, _sha256

METHODS = {"gaussian": "adversarial_ai.evaluation.defense_evaluation",
           "mean": "adversarial_ai.evaluation.mean_defense_evaluation"}
PREDICTIONS = ("clean", "defended_clean", "attacked", "transfer_defended", "adaptive_defended")


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)


def compare_json(a, b, tolerance, location="summary"):
    if isinstance(a, dict):
        if not isinstance(b, dict) or a.keys() != b.keys():
            raise ValueError(f"{location}: keys differ")
        for key in a:
            compare_json(a[key], b[key], tolerance, f"{location}/{key}")
    elif isinstance(a, list):
        if not isinstance(b, list) or len(a) != len(b):
            raise ValueError(f"{location}: coverage differs")
        for i, (x, y) in enumerate(zip(a, b)):
            compare_json(x, y, tolerance, f"{location}/{i}")
    elif type(a) in (int, float):
        if type(b) not in (int, float) or not math.isfinite(a) or not math.isfinite(b) or abs(a-b) > tolerance:
            raise ValueError(f"{location}: numeric mismatch {a!r} vs {b!r}")
    elif type(a) is not type(b) or a != b:
        raise ValueError(f"{location}: value differs")


def collect_json_differences(a, b, tolerance, location, differences):
    """Like ``compare_json``, but a within-structure numeric metric mismatch
    is appended to ``differences`` instead of raising.

    Only a normal, comparable metric difference (both sides finite numbers,
    same structure) is collected. Anything that means the two summaries are
    not actually comparable -- different keys, different list lengths, a
    non-numeric value where a number is expected, a type mismatch on a
    non-numeric field -- still raises immediately, exactly like
    ``compare_json``. This mirrors the sample-identity vs. prediction split
    used in ``compare_outputs``: structure/identity problems abort, ordinary
    metric drift is recorded.
    """
    if isinstance(a, dict):
        if not isinstance(b, dict) or a.keys() != b.keys():
            raise ValueError(f"{location}: keys differ")
        for key in a:
            collect_json_differences(a[key], b[key], tolerance, f"{location}/{key}", differences)
    elif isinstance(a, list):
        if not isinstance(b, list) or len(a) != len(b):
            raise ValueError(f"{location}: coverage differs")
        for i, (x, y) in enumerate(zip(a, b)):
            collect_json_differences(x, y, tolerance, f"{location}/{i}", differences)
    elif type(a) in (int, float):
        if type(b) not in (int, float) or not math.isfinite(a) or not math.isfinite(b):
            raise ValueError(f"{location}: non-numeric or non-finite metric value")
        if abs(a - b) > tolerance:
            differences.append({"location": location, "reference": a, "actual": b,
                                 "abs_diff": abs(a - b), "tolerance": tolerance})
    elif type(a) is not type(b) or a != b:
        raise ValueError(f"{location}: value differs")


def read_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("missing/duplicate CSV columns")
        return list(reader)


def compare_outputs(root, output, method, contract):
    """Compare a rerun's saved outputs against the official reference.

    Two different kinds of mismatch are handled differently:

    - Structural / sample-identity / attack-scope problems (bad columns,
      wrong row count, a ``relative_path`` or ``true_index`` that doesn't
      match, an out-of-contract epsilon, an out-of-range perturbation) mean
      the two runs are not comparing the same data under the same attack, so
      they raise immediately and abort this comparison.
    - Ordinary prediction and metric differences (a ``*_pred`` column, or a
      numeric field in ``summary.json``) are normal, comparable outcomes of
      an independent rerun. They are collected into ``differences`` instead
      of raising, so the full set of mismatches is captured in one pass and
      the caller can still move on to the next defense method.

    The return value's ``status`` is ``"FAIL"`` whenever ``differences`` is
    non-empty; the caller decides what to do with a FAIL comparison (see
    ``run``), but this function itself never raises for a label/metric-only
    mismatch.
    """
    reference = root / f"results/defenses/experimental/{method}_run_01"
    count = 0
    differences = []
    for model in ("cnn", "mobilenet"):
        for epsilon in contract["attack"]["epsilons"]:
            name = f"{model}_eps_{epsilon:g}_samples.csv"
            expected, actual = read_rows(reference/name), read_rows(output/name)
            if len(expected) != 781 or len(actual) != 781:
                raise ValueError(f"{method}/{name}: expected 781 rows")
            for index, (left, right) in enumerate(zip(expected, actual)):
                if left.keys() != right.keys():
                    raise ValueError(f"{method}/{name}: columns differ")
                # Sample identity and ground truth: these say WHICH sample is
                # being compared, not how it was classified. A mismatch here
                # means the two runs disagree about what they even ran on,
                # so it is never collected -- it aborts immediately.
                for key in ("relative_path", "true_index"):
                    if left[key].replace("\\", "/") != right[key].replace("\\", "/"):
                        raise ValueError(f"{method}/{name}/{index}/{key}: label/path mismatch")
                if float(right["epsilon"]) != epsilon:
                    raise ValueError(f"{method}/{name}/{index}: epsilon mismatch")
                for key in ("original_linf", "adaptive_linf"):
                    value = float(right[key])
                    if not math.isfinite(value) or not 0 <= value <= epsilon + contract["comparison"]["linf_tolerance"]:
                        raise ValueError(f"{method}/{name}/{index}: invalid perturbation")
                # Predicted labels are the actual comparison outcome: collect
                # every difference and keep going rather than stopping at
                # the first one.
                for pred in PREDICTIONS:
                    key = pred + "_pred"
                    if left[key].replace("\\", "/") != right[key].replace("\\", "/"):
                        differences.append({
                            "method": method, "file": name, "row_index": index,
                            "relative_path": left["relative_path"].replace("\\", "/"),
                            "field": key, "reference": left[key], "actual": right[key],
                        })
                count += 1
    collect_json_differences(_load_json(reference/"summary.json"), _load_json(output/"summary.json"),
                              contract["comparison"]["metric_abs_tolerance"], "summary", differences)
    return {"method": method, "rows_compared": count,
            "status": "FAIL" if differences else "PASS", "differences": differences}


def run(root, contract_path):
    root, contract_path = root.resolve(), contract_path.resolve()
    readiness = check_stage_b_readiness(root, contract_path)
    if not readiness["ready"]:
        raise ValueError(json.dumps(readiness, ensure_ascii=False))
    contract = _load_json(contract_path)
    # Existing evaluator deliberately requires output outside the research checkout.
    output = contract_path.parent / ("stage-b-" + contract["outputs"]["run_id"])
    if output.is_relative_to(root) or root.is_relative_to(output):
        raise ValueError("run outputs must be outside the checkout")
    output.mkdir(exist_ok=False)
    write_json(output/"execution-contract.json", contract)
    report = {"status": "RUNNING", "source_commit": contract["source"]["commit_sha"],
              "started_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
              "platform": platform.platform(), "contract_sha256": _sha256(contract_path),
              "independence": "separate operator/environment; existing evaluator reused",
              "probability_comparison": "not performed; existing defense evaluator exports labels and L-infinity only",
              "outputs": str(output), "comparisons": [], "commands": []}
    env = dict(os.environ, PYTHONPATH=str(root/"src"), PYTHONUNBUFFERED="1")
    try:
        freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True, check=True)
        (output/"environment.txt").write_text(freeze.stdout, encoding="utf-8")
        command = [sys.executable, "-m", "verification.stage_b_preflight", "--contract", str(contract_path)]
        report["commands"].append(command)
        with (output/"preflight.log").open("x", encoding="utf-8") as log:
            subprocess.run(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        comparison_failed = False
        for method, module in METHODS.items():
            command = [sys.executable, "-m", module, "--output", str(output/method)]
            report["commands"].append(command)
            print(f"Running {method}; log: {output / (method+'.log')}", flush=True)
            with (output/(method+".log")).open("x", encoding="utf-8") as log:
                # A subprocess failure here (bad exit code) still raises via
                # check=True and aborts the run immediately -- only a FAIL
                # *comparison* (label/metric differences, see below) lets the
                # loop continue to the next defense method.
                subprocess.run(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
            comparison = compare_outputs(root, output/method, method, contract)
            report["comparisons"].append(comparison)
            if comparison["status"] != "PASS":
                comparison_failed = True
        if _sha256(contract_path) != report["contract_sha256"]:
            raise ValueError("external contract changed during execution")
        after = check_stage_b_readiness(root, contract_path)
        after["blockers"] = [b for b in after["blockers"] if b != "Stage-B output path already exists; overwrite is forbidden"]
        if after["blockers"]:
            raise ValueError(f"post-run integrity check failed: {after}")
        if comparison_failed:
            # Every defense method still ran and every comparison was
            # collected (see report["comparisons"]), but any label/metric
            # difference means this is not a completed, matching
            # verification: the overall run ends FAIL with a failing exit
            # code, exactly as before this change.
            raise ValueError("label/metric differences detected in one or more comparisons; see report['comparisons']")
        report["status"] = "PASS"
    except KeyboardInterrupt:
        report["status"] = "INTERRUPTED"
        report["error"] = "Execution interrupted by user; partial outputs are not a completed rerun"
        raise
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = str(exc)
        raise
    finally:
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        report["artifact_sha256"] = {p.relative_to(output).as_posix(): _sha256(p)
                                      for p in sorted(output.rglob("*")) if p.is_file()}
        write_json(output/"rerun-report.json", report)
        print(f"{report['status']}: {output/'rerun-report.json'}", flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--prepare", action="store_true", help="Create an external DRAFT; never invent reviewer approval")
    parser.add_argument("--run-id", default="hyeonsu-01")
    args = parser.parse_args()
    if args.prepare:
        root = args.repo_root.resolve()
        if args.contract.resolve().is_relative_to(root):
            parser.error("contract copy must be outside the checkout")
        contract = _load_json(root/"configs/stage_b_verification_contract.json")
        contract["source"]["commit_sha"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        contract["outputs"]["run_id"] = args.run_id
        write_json(args.contract, contract)
        print("Draft prepared. Record actual reviewer/tolerance confirmation before running.")
    else:
        run(args.repo_root, args.contract)


if __name__ == "__main__":
    main()
