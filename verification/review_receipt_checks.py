"""Five standalone, fictional review-receipt QA checks; no model or live I/O."""
from collections import Counter
from dataclasses import asdict, dataclass, replace
import json
import re

ID = re.compile(r"[a-z][a-z0-9-]{0,31}\Z", re.ASCII)
RESULTS = frozenset(("reviewable", "hold"))


@dataclass(frozen=True)
class Receipt:
    schema: int
    receipt_id: str
    session: str
    revision: int
    step: int
    state: str
    completed: bool

    @classmethod
    def read(cls, raw):
        if type(raw) is not dict or raw.keys() != cls.__dataclass_fields__.keys():
            raise ValueError("receipt shape")
        r = cls(**raw)
        if type(r.schema) is not int or r.schema != 1:
            raise ValueError("schema version")
        if any(type(x) is not str or not ID.fullmatch(x) for x in (r.receipt_id, r.session)):
            raise ValueError("receipt identity")
        if any(type(x) is not int or x < 1 for x in (r.revision, r.step)):
            raise ValueError("revision or sequence")
        if type(r.state) is not str or r.state not in RESULTS or type(r.completed) is not bool:
            raise ValueError("receipt state")
        return r


def current_context(receipt, expected_session, expected_revision):
    """Reject a well-formed record tied to an earlier session/revision."""
    return receipt.session == expected_session and receipt.revision == expected_revision


def unique_receipts(receipts):
    """Count exact retransmission once; stop an audit on conflicting identity."""
    seen = {}
    for receipt in receipts:
        key = (receipt.session, receipt.revision, receipt.receipt_id)
        if key in seen and seen[key] != receipt:
            raise ValueError("conflicting receipt identity")
        seen.setdefault(key, receipt)
    return tuple(seen.values())


def recovery_trace(receipts):
    """Two consecutive finished reviewable checkpoints needed after a hold."""
    if len({(r.session,r.revision) for r in receipts}) > 1:
        raise ValueError("recovery requires one pinned context")
    if any(r.step <= prev.step for prev,r in zip(receipts,receipts[1:])):
        raise ValueError("recovery records must have strictly increasing steps")
    out, good = [], 0
    last_step = None
    for r in receipts:
        if r.state == "hold" or not r.completed:
            good, reason = 0, "hold_or_unfinished"
        elif last_step is not None and r.step != last_step + 1:
            good, reason = 1, "sequence_gap_restarts_confirmation"
        else:
            good += 1
            reason = "confirmed" if good >= 2 else "await_second_checkpoint"
        out.append({"step":r.step,"state":"reviewable" if good >= 2 else "hold","reason":reason})
        last_step = r.step
    return out


def audit_ledger(rows, session, revision):
    """Preserve a reason and denominator for each raw receipt; never claim pass."""
    decisions = []
    validated = []
    for i, raw in enumerate(rows, start=1):
        try:
            r = Receipt.read(raw)
        except (ValueError,TypeError):
            decisions.append((i,"invalid_receipt"))
            continue
        if not current_context(r,session,revision):
            decisions.append((i,"historical_context"))
            continue
        validated.append((i,r))
    # Inspect all candidates first: a conflicting ID must not leave an earlier
    # row countable simply because it was read first.
    signatures = {}
    for _,r in validated:
        signatures.setdefault(r.receipt_id,set()).add(r)
    seen = set()
    for i,r in validated:
        if len(signatures[r.receipt_id]) > 1:
            reason = "conflicting_receipt"
        elif r.receipt_id in seen:
            reason = "repeat_not_counted"
        else:
            reason = "eligible_for_trace"
        decisions.append((i,reason))
        seen.add(r.receipt_id)
    decisions.sort()
    return {"n_raw": len(decisions), "counts": dict(sorted(Counter(x[1] for x in decisions).items())),
            "ledger":[{"row":i,"reason":reason} for i,reason in decisions]}


A=Receipt(1,"r-a","review-a",2,1,"hold",True)
B=Receipt(1,"r-b","review-a",2,2,"reviewable",True)
C=Receipt(1,"r-c","review-a",2,3,"reviewable",True)
D=Receipt(1,"r-d","review-a",2,5,"reviewable",True)
E=Receipt(1,"r-e","review-a",2,6,"reviewable",True)


def report():
    rows = [asdict(A), asdict(B), asdict(B), asdict(replace(B,state="hold")),
            asdict(replace(C,revision=1)), {**asdict(D),"completed":"false"}, asdict(E)]
    return {"scope":"fictional offline acceptance checks; not PaulGuard runtime or model results",
            "receipt_ledger":audit_ledger(rows,"review-a",2),
            "recovery_fixture":recovery_trace([A,B,C,D,E])}


if __name__=="__main__":
    print(json.dumps(report(),indent=2))
