"""EXP27 native dynamics reference. No new research result is inferred from this test."""
from . import spec, runtime, audit
from .storage import digest, require

# Exact stored signatures in EXP27 analysis/signatures.csv at BASE_COMMIT.
REFERENCES = {
    'positive_cold': ('b803bfc0ab010dc490e7fcf74ca3eaf6c6ada354cb508a0a9dae8cdc74b7c6ec', 36),
    'positive_warm': ('c0fec31d522cea86e591869bcee572cfa075f1848d21d50f04b6eec9a85b499c', 29),
    'negative_cold': ('026b7de9dc93f166122f0395584ce49b82cd61f41f2f26e02a80bbfb21a98eb6', 28),
}

def run_reference():
    a, cs, w = spec.observations(); sources = {}; checks = []
    for v, ob in a.items():
        r = runtime.run_query(ob, spec.CONFIG); audit.audit_record(r)
        require(r['native_cost']['kernel_ticks'] == 33, 'EXP27 A tick regression')
        sources[v] = r
    for c in cs:
        for arm in ('cold', 'carry_both'):
            r = runtime.run_query(c['observation'], spec.CONFIG, arm, sources[c['variant']])
            ar = audit.audit_record(r, sources[c['variant']], w[c['id']])
            key = 'negative_cold' if c['scenario'] == 'premise_changed' else (
                'positive_warm' if c['scenario'] == 'extend' and arm == 'carry_both' else 'positive_cold')
            sh, nt = REFERENCES[key]
            require(digest(dict(ticks=r['ticks'], convergence=r['convergence'])) == sh, 'EXP27 full dynamics signature regression')
            require(r['native_cost']['kernel_ticks'] == nt, 'EXP27 B tick regression')
            checks.append(dict(case=c['id'], arm=arm, dynamics_sha256=sh, ticks=nt, verified=ar['verified']))
    return dict(population='implementation_regression_not_research', reference_commit=spec.BASE_COMMIT,
        reference_path=spec.PARENT_RUN+'/analysis/signatures.csv', shared_A=2, B_comparisons=12,
        comparisons=checks, verified=True, full_AdaptiveSession_replayed=False)
