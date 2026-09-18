"""Local HF1 diagnosis and deployment checks. Diagnostic queries are self-test only."""
from pathlib import Path
import argparse
import json
import sys
import traceback


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--mode',choices=['check','diagnose','snapshot'],required=True)
    p.add_argument('--parent-source',type=Path);p.add_argument('--snapshot',type=Path)
    a=p.parse_args();root=a.root.resolve();sys.path[:0]=[str(root/'src'),str(root)]
    from tools.r048_precision import io
    from tools.r049_signal_boundary import provenance,spec,device,audit,regression
    import hcr
    io.require(Path(hcr.__file__).resolve().is_relative_to(root/'src/hcr'),'incorrect hcr package origin')
    try:
        m=provenance.package_check(root);inherited=provenance.inherited_check(root)
        report=dict(schema='hcr-r049-hf1-local-diagnosis-v1',population='implementation_validation_not_research',
            python=sys.version,platform=sys.platform,release_files=len(m['files']),inherited=inherited,mode=a.mode,
            formal_EXP30_queries=0,old_failed_run_reexecuted=False)
        if a.mode=='diagnose':
            prior=io.load(root/'docs/R049_PRIOR_EXPLORATION.json');refs=regression.references(prior)
            plan=spec.body();cases={c['id']:c for c in plan['cases']};rows=[]
            for t in plan['trials']:
                if t['evidence_role']!='prior_exploration_replication':continue
                c=cases[t['case']]
                r=device.run_query(c['observation'],plan['kernel_config'],t['arm'])
                io.put(a.out.parent/'diagnostic_raw'/(t['id']+'.json'),dict(trial=t,record=r))
                native_audit=audit.audit_record(r,plan['worlds'][t['case']])
                ref=refs[c['strength'],c['pattern'],t['arm']]
                result=regression.compare(r,ref,io.digest(dict(ticks=ref['ticks'],convergence=ref['convergence'])))
                rows.append(dict(trial=t['id'],strength=c['strength'],variant=c['variant'],arm=t['arm'],
                    independent_audit=native_audit,**result))
            report.update(comparisons=rows,old_exact_sha_failures=sum(not x['dynamics_equal'] for x in rows),
                passed=all(x['regression_passed'] for x in rows),
                max_absolute_difference=max(x['max_absolute_difference'] for x in rows))
            report['diagnosis']=('substantive_divergence_stop_no_install' if not report['passed'] else
                'same_decisions_all_scalars_within_tolerance_but_original_SHA_comparison_failed' if report['old_exact_sha_failures'] else
                'current_execution_matches_original_SHA_no_original_failure_reproduced')
            io.put(a.out,report)
            for x in rows:print(f"{x['trial']} {x['arm']} exact={x['dynamics_equal']} numeric_and_discrete={x['regression_passed']} max_delta={x['max_absolute_difference']:.3g}",flush=True)
            io.require(report['passed'],'substantive regression; see '+str(a.out))
        elif a.mode=='snapshot':
            io.require(a.parent_source is not None and a.snapshot is not None,'snapshot arguments required')
            h=provenance.copy_source(root,a.parent_source,a.snapshot)
            provenance.package_check(a.snapshot);provenance.inherited_check(a.snapshot)
            report.update(passed=True,snapshot_files=len(h));io.put(a.out,report)
        else:
            report.update(passed=True);io.put(a.out,report)
        print(json.dumps({k:v for k,v in report.items() if k not in ('comparisons','inherited')},ensure_ascii=False),flush=True)
        return 0
    except BaseException as exc:
        if not a.out.exists():
            io.put(a.out,dict(passed=False,error_type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc()))
        raise

if __name__=='__main__':raise SystemExit(main())
