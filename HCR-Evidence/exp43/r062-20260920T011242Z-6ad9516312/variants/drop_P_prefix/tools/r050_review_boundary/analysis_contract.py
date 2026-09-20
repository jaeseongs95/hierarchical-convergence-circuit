"""Read-only validation of audit tables and their rendered derivatives.

This module uses neither native inference nor the worker/controller. Native raw
replay still belongs to audit.py. These checks prevent a valid-looking summary
from substituting for raw evidence, and never change an existing evidence run.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
from .common import files, load, require, sha, unseal

ARMS = ('hold', 'same_input_restart', 'echo_revision_restart', 'strength_revision_restart')


def validate_audit_tables(audit: dict) -> None:
    require(audit.get('verified') is True, 'Only a verified raw audit can be reported')
    require(audit.get('baseline_count') == 24 and audit.get('arm_records') == 96,
            'Incorrect audit cardinality')
    rows = audit['rows']
    expected = {(f'c{i:03d}', a) for i in range(24) for a in ARMS}
    keys = [(r['case_id'], r['arm']) for r in rows]
    require(len(keys) == 96 and len(set(keys)) == 96 and set(keys) == expected,
            'Missing, duplicate, or extra audited rows')
    base, extra = Counter(), Counter()
    by_case = {}
    for row in rows:
        for name in ('restarts', 'probe_requests'):
            require(type(row[name]) is int and row[name] in (0, 1), 'Invalid event count: ' + name)
        for scope in ('baseline_counters', 'additional_counters'):
            require(all(type(v) is int and v >= 0 for v in row[scope].values()),
                    'Non-integer or negative native counter')
        for stage in ('initial', 'final'):
            item = row[stage]
            require(type(item['accepted']) is bool, 'Typed terminal acceptance')
            if item['accepted']:
                require(type(item['adopted_value']) is bool and type(item['adopted_correct']) is bool,
                        'Accepted terminal lacks its actual value/assessment')
            else:
                require(item['adopted_value'] is None and item['adopted_correct'] is None,
                        'An abstention was counted as a correct/incorrect adoption')
        previous = by_case.setdefault(row['case_id'], row)
        require(row['baseline_sha256'] == previous['baseline_sha256']
                and row['initial'] == previous['initial']
                and row['baseline_counters'] == previous['baseline_counters'],
                'Paired rows do not share the same initial evidence')
        require(row['probe_requests'] <= row['restarts'], 'Probe lacks its recorded restart')
        extra.update(row['additional_counters'])
        if row['arm'] == 'hold':
            require(row['restarts'] == row['probe_requests'] == 0, 'Hold arm contains hidden work')
            base.update(row['baseline_counters'])
    require(dict(base) == audit['unique_baseline_counters'], 'Baseline cost was omitted or recounted')
    require(dict(extra) == audit['additional_counters'], 'Additional cost total differs from audited rows')
    require(audit['restarts'] == sum(r['restarts'] for r in rows), 'Restart aggregate mismatch')
    require(audit['measurements'] == sum(r['probe_requests'] for r in rows), 'Measurement aggregate mismatch')
    comparisons = audit['numerical_comparisons']
    ckeys = [(r['case_id'], r['prediction']) for r in comparisons]
    require(len(ckeys) == 72 and len(set(ckeys)) == 72
            and set(ckeys) == {(f'c{i:03d}', p) for i in range(24) for p in ('P1','P2','P3')},
            'Numerical comparison coverage/identity mismatch')
    for row in comparisons:
        require(type(row['evaluated']) is bool, 'Typed comparison applicability')
        require((row['comparison'] is not None) is row['evaluated'],
                'Unevaluated comparison was silently filled with a result')


def validate_report_inputs(root: Path, audit: dict) -> None:
    validate_audit_tables(audit)
    plan_packet = load(root / 'plan.json')
    unseal(plan_packet, 'hcc-r050-plan-v1')
    require(audit['plan_sha256'] == plan_packet['sha256'], 'Report is bound to another plan')
    manifest = load(root / 'raw_manifest.json')
    inventory = {}
    for folder in ('baselines', 'raw', 'progress', 'measurements', 'interventions'):
        if (root / folder).exists():
            inventory.update({folder + '/' + name: digest for name, digest in files(root / folder).items()})
    require(manifest['files'] == inventory, 'Raw evidence changed after audit')


def verify_analysis(root: Path, recomputed_audit: dict) -> dict:
    """Compare a fresh independent raw audit with stored audit/summary/CSV/Markdown."""
    validate_report_inputs(root, recomputed_audit)
    saved = load(root / 'analysis' / 'audit.json')
    require(saved == recomputed_audit, 'Saved audit differs from independent raw recomputation')
    # Rendering is deterministic data formatting, not proof/outcome evaluation.
    from .reporting import render_artifacts
    _, expected = render_artifacts(recomputed_audit)
    checked = {}
    for name, content in expected.items():
        path = root / 'analysis' / name
        require(path.is_file() and path.read_bytes() == content,
                'Stored analysis differs from audited evidence: ' + name)
        checked[name] = sha(content)
    return dict(verified=True, files=checked, raw_audit_recomputed=True,
                existing_evidence_modified=False, new_inferences=0)
