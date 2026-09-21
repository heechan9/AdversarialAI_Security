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


def read_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("missing/duplicate CSV columns")
        return list(reader)


def compare_outputs(root, output, method, contract):
    reference = root / f"results/defenses/experimental/{method}_run_01"
    count = 0
    for model in ("cnn", "mobilenet"):
        for epsilon in contract["attack"]["epsilons"]:
            name = f"{model}_eps_{epsilon:g}_samples.csv"
            expected, actual = read_rows(reference/name), read_rows(output/name)
            if len(expected) != 781 or len(actual) != 781:
                raise ValueError(f"{method}/{name}: expected 781 rows")
            for index, (left, right) in enumerate(zip(expected, actual)):
                if left.keys() != right.keys():
                    raise ValueError(f"{method}/{name}: columns differ")
                for key in ("relative_path", "true_index") + tuple(p+"_pred" for p in PREDICTIONS):
                    if left[key].replace("\\", "/") != right[key].replace("\\", "/"):
                        raise ValueError(f"{method}/{name}/{index}/{key}: label/path mismatch")
                if float(right["epsilon"]) != epsilon:
                    raise ValueError("epsilon mismatch")
                for key in ("original_linf", "adaptive_linf"):
                    value = float(right[key])
                    if not math.isfinite(value) or not 0 <= value <= epsilon + contract["comparison"]["linf_tolerance"]:
                        raise ValueError(f"{method}/{name}/{index}: invalid perturbation")
                count += 1
    compare_json(_load_json(reference/"summary.json"), _load_json(output/"summary.json"),
                 contract["comparison"]["metric_abs_tolerance"])
    return {"method": method, "rows_compared": count, "status": "PASS"}


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
        for method, module in METHODS.items():
            command = [sys.executable, "-m", module, "--output", str(output/method)]
            report["commands"].append(command)
            print(f"Running {method}; log: {output / (method+'.log')}", flush=True)
            with (output/(method+".log")).open("x", encoding="utf-8") as log:
                subprocess.run(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
            report["comparisons"].append(compare_outputs(root, output/method, method, contract))
        if _sha256(contract_path) != report["contract_sha256"]:
            raise ValueError("external contract changed during execution")
        after = check_stage_b_readiness(root, contract_path)
        after["blockers"] = [b for b in after["blockers"] if b != "Stage-B output path already exists; overwrite is forbidden"]
        if after["blockers"]:
            raise ValueError(f"post-run integrity check failed: {after}")
        report["status"] = "PASS"
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
