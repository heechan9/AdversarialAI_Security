"""Audit one explicit candidate run without promoting it."""
import argparse
import json
from pathlib import Path
from adversarial_ai.audit.exceptions import AuditError
from adversarial_ai.audit.official_candidate import audit_official_candidate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit_official_candidate(Path('.'), args.candidate)
    except AuditError as exc:
        print(json.dumps({'status': 'FAILED', 'error': str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
