"""Read-only EXP27 snapshot replay in a fresh interpreter. Called only after byte verification."""
from pathlib import Path
import argparse
import sys


def main():
    p=argparse.ArgumentParser();p.add_argument('--parent',required=True);args=p.parse_args()
    parent=Path(args.parent).resolve();snapshot=parent/'source'
    # Native equations are not called by the legacy auditor, but these paths match the
    # exact released snapshot rather than whichever package happens to be installed.
    sys.path[:0]=[str(snapshot/'src'),str(snapshot)]
    from tools.r046_thought_carry import storage as io, reporting
    from tools.r046_thought_carry.protocol import record_audit
    import tools.r046_thought_carry.evaluator as evaluator
    if not Path(evaluator.__file__).resolve().is_relative_to(snapshot):
        raise RuntimeError('legacy auditor did not come from pinned snapshot')
    plan=io.load(parent/'plan.json')
    src,rows,checks,sa,stream=record_audit(plan,parent)
    s=reporting.summarize(plan,src,rows,checks)
    audit=dict(schema='hcr-exp27-audit-v1',verified=True,source_queries=2,followups=24,stream_records=stream,
        native_scalar_ticks=sum(r['native_cost']['kernel_ticks'] for r in src.values())+sum(r['native_cost']['kernel_ticks'] for r in rows.values()),
        state_and_proof_replayed=True,old_EXP26_replayed_here=False,old_EXP26_verify_is_launcher_precondition=True,
        hypotheses_not_validity=True,full_AdaptiveSession_replay_claimed=False,raw_manifest_sha256=io.file_hash(parent/'manifest.json'))
    objects={'summary.json':s,'audit.json':audit,'source_audits.json':sa,'record_audits.json':checks,'claims.json':s['claims']}
    output={n:io.canonical(v)+b'\n' for n,v in objects.items()};output['summary.ko.md']=reporting.render(s)
    for name in ('trials','pairs','cost_differences','ID_controls','memo_controls','transfer_maps','proof_refs','signatures'):
        output[name+'.csv']=reporting.csv_bytes(s[name])
    expected=dict(schema='hcr-exp27-analysis-manifest-v1',files={n:io.bytes_hash(b) for n,b in output.items()})
    io.require(io.load(parent/'analysis/manifest.json')==expected,'parent analysis regenerated manifest mismatch')
    for n,b in output.items():io.require(io.read(parent/'analysis'/n)==b,'parent analysis differs from independent recomputation: '+n)
    print(io.canonical(dict(verified=True,source_queries=2,followups=24,stream_records=stream,
        native_scalar_ticks=audit['native_scalar_ticks'],ID_controls=s['ID_controls'],
        independent_research_samples_added=0,all_parent_analysis_files_recomputed=len(output))).decode('utf-8'))

if __name__=='__main__':main()
