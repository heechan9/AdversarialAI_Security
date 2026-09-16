"""Separate record consistency from human interpretation and label truth.

Follow-up adapters must supply explicit meaning and its confirmation source.
Never infer meaning from a reviewer name or the text '라벨 정확'.
"""
from collections import Counter
from .exceptions import AuditError

MEANINGS = frozenset({'description_confirmation', 'class_label_opinion'})


def audit_claim_boundary():
    """Fresh metadata for the immutable legacy record audit; no reclassification."""
    return {
        'scope': 'record_integrity_and_consistency',
        'judgment_counts_meaning': 'verbatim_legacy_record_values',
        'label_correctness_verified': False,
        'independent_double_review_verified': False,
        'limitation': 'PASS verifies records, not image class correctness or expert visual validation.',
    }


def summarize_followup_reviews(records, *, meaning):
    """Count one explicitly declared kind of opinion, never verified truth.

    This is a normalized-record API, not an importer for private CSVs. Each row
    needs sample_id, reviewer, judgment, meaning and meaning_source. Unknown,
    absent or mixed semantics fail before any summary is returned. Calling
    separately for two meanings does not authorize adding their counts.
    """
    if not isinstance(meaning, str) or meaning not in MEANINGS:
        raise AuditError('Unknown or unconfirmed review meaning')
    rows = list(records)
    if not rows:
        raise AuditError('Empty follow-up review input')
    counts = Counter()
    seen = set()
    required = {'sample_id', 'reviewer', 'judgment', 'meaning', 'meaning_source'}
    for row in rows:
        if not isinstance(row, dict) or set(row) != required:
            raise AuditError('Follow-up review schema mismatch')
        if any(not isinstance(v, str) or not v.strip() for v in row.values()):
            raise AuditError('Missing follow-up review value or meaning source')
        if row['meaning'] != meaning:
            raise AuditError('Mixed or unconfirmed review meanings cannot be aggregated')
        key = (row['sample_id'].strip(), row['reviewer'].strip())
        if key in seen:
            raise AuditError('Duplicate follow-up review')
        seen.add(key)
        counts[row['judgment']] += 1
    return {
        'meaning': meaning,
        'record_count': len(rows),
        'raw_judgment_counts': dict(counts),
        'label_correctness_verified': False,
        'meaning_sources': sorted({row['meaning_source'] for row in rows}),
    }
