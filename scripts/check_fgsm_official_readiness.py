"""Check, but never execute, a future official FGSM run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from adversarial_ai.audit.official_readiness import check_official_fgsm_readiness


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=Path("configs/fgsm_official_contract.json"))
    args = parser.parse_args()
    result = check_official_fgsm_readiness(Path("."), args.contract)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
