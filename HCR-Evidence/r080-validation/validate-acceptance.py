"""Bind inspected R080 evidence to the four frozen acceptance criteria."""
from pathlib import Path
import json
import os
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from tools.r050_review_boundary.common import load,dump,sha,fingerprint

V=ROOT/'HCR-Evidence/r080-validation'
RUN='HCR-Evidence/exp61/r080-20261001T030938Z-3e5b710c6f'
EX='experiments/exp-61-small-positive'
AGS=Path('C:/Users/sjs95/.codex/plugins/cache/agent-governance/agent-governance-suite/2.7.6')
ITEMS=[
    ('freeze',RUN+'/plan.json',['AC-001'],'Pre-native fixed seven cells and finite predictions'),
    ('selftest',RUN+'/validation/selftest.json',['AC-001','AC-003'],'Prior11 replay,grammar7 and synthetic measurement checks;new native0'),
    ('integrity','HCR-Evidence/r080-validation/delivery-verification.json',['AC-001','AC-003','AC-004'],'Bundle1217/ZIP/current source/historical inputs exact;freeze before native'),
    ('native',RUN+'/verification.json',['AC-002','AC-003'],'Independent7 replay,endpoint2 journals,network/advance/readout/ancestry,raw15 rejections including semantic6'),
    ('summary',RUN+'/summary.json',['AC-002'],'First and all subsequent states/routes/pending/coverage;duration/link semantics separate;pool null OFF'),
    ('summary-check',RUN+'/validation/summary-verification.json',['AC-003'],'Raw-grounded recomputation and20 corruption rejections'),
    ('regression',RUN+'/validation/core_regression.json',['AC-003'],'Final core1:602/599pass/3existing symlink skips,new failure/skip0'),
    ('results',EX+'/results.ko.md',['AC-004'],'Finite H1falsified/H2supported/H3falsified;provisional False versus final True;claim limits'),
    ('next',EX+'/NEXT.ko.md',['AC-004'],'Unexecuted finite refinement and separate fixed-point/gain contract options'),
    ('scope','HCR-Evidence/r080-validation/scope-report.after-delivery.json',['AC-004'],'PASS:excluded/unplanned/overlap0,preexisting264 untouched'),
    ('git','HCR-Evidence/r080-validation/research-git-delivery.json',['AC-004'],'Research864f5e0 localmain and actual remote match;research branch deleted'),
    ('peer','HCR-Evidence/r080-validation/peer-final-artifact-audit.json',['AC-003','AC-004'],'Independent researcher reports raw/docs/bundle disagreement0;not authorization'),
    ('failure','HCR-Evidence/r080-validation/first-failure-preservation.json',['AC-001','AC-004'],'First selftest error/source/logs preserved,native/core0;corrected input separate'),
    ('source-after','HCR-Evidence/r080-validation/source-after-merge-verification.json',['AC-003','AC-004'],'Launcher EOL-only restoration,current source exact,no content patch or execution'),
]


def main():
    target=dict(research_commit='864f5e0668b25c7cf9cd81cba79b54014691ae8a',
        frozen_spec_sha256='sha256:'+sha((ROOT/EX/'frozen_spec.json').read_bytes()),
        manifest_sha256='sha256:'+sha((ROOT/'R080_MANIFEST.json').read_bytes()),
        evidence=[dict(locator=p,digest='sha256:'+sha((ROOT/p).read_bytes())) for _,p,_,_ in ITEMS],
        acceptance_metadata_closure='Metadata-only branch closes afterward;final refreceipt under .git/r080-final-delivery.json;no revised research')
    dump(V/'acceptance-target.json',target);digest='sha256:'+fingerprint(target)
    request=dict(schemaVersion='1.0.0',taskEnvelope=load(V/'task-envelope.json'),
        target=dict(kind='artifact',identifier='R080-sealed-seven-cell-small-positive-research-and-primary-delivery',digest=digest),
        evidence=[dict(id=i,kind='document' if i in ('results','next') else 'file',locator=p,
            digest='sha256:'+sha((ROOT/p).read_bytes()),targetDigest=digest,verified=True,
            criterionIds=criteria,direction='supports',observedResult=observed) for i,p,criteria,observed in ITEMS],
        verificationCommands=[dict(id='oneclick-corrected',command='cmd /c Run-HCR-R080.cmd (corrected pre-native input)',
            criterionIds=['AC-001','AC-002','AC-003'],exitCode=0,locator='HCR-Evidence/r080-validation/oneclick-corrected-execution.json',targetDigest=digest),
            dict(id='research-delivery',command='Primary commit/localmain merge/ordinary push/remote check/completed research branch deletion',
            criterionIds=['AC-004'],exitCode=0,locator='HCR-Evidence/r080-validation/research-git-delivery.json',targetDigest=digest)],
        criterionOverrides=[],knownLimitations=[
            'Single authored graph/memory;reproduction2 not new evidence,new inputs5,independent discovery0',
            'H1/H2 one stable-state comparison;H3 only finite5 points,no precise/continuum threshold',
            'First False provisional readyFalse,not terminal misconvergence;final all True',
            'First apparatus error native/core0 preserved,three pre-native amendments;automaticretry0',
            'Duration and prior-state centered/terminal centered/uncentered products separate;OFF pool null;energy/peak memorynull',
            'Equal selftest/native UTC permitted with subprocess/source sequencing and monotonic intervals',
            'Core602/599pass/3existing Windows skips,cloud not run',
            'Metadata-only closure afterward;final commit/remote/ref receipt in .git avoids self-referential SHA'])
    dump(V/'acceptance-request.json',request)
    dump(V/'acceptance-request-artifact.json',dict(artifactId='r080-final-acceptance-request',
        digest='sha256:'+fingerprint(request),locator='HCR-Evidence/r080-validation/acceptance-request.json',
        schemaId='https://agent-governance-skills.local/acceptance-evidence-validator/contracts/acceptance-evidence-input.v1.schema.json'))
    env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
    r=subprocess.run(['node',str(AGS/'skills/acceptance-evidence-validator/scripts/cli.mjs'),'--input',str(V/'acceptance-request.json')],capture_output=True,text=True,env=env)
    assert r.returncode==0,r.stdout+r.stderr
    report=json.loads(r.stdout);dump(V/'acceptance-report.json',report);assert report['verdict']=='PASS',report
    r=subprocess.run(['node',str(AGS/'skills/acceptance-evidence-validator/scripts/validate-report.mjs'),
        '--request',str(V/'acceptance-request.json'),'--request-artifact',str(V/'acceptance-request-artifact.json'),
        '--report',str(V/'acceptance-report.json')],capture_output=True,text=True,env=env)
    assert r.returncode==0,r.stdout+r.stderr
    dump(V/'acceptance-validation.json',json.loads(r.stdout))
    print('Acceptance PASS,criteria',[x['status'] for x in report['criteria']],';request/report binding validated')


if __name__=='__main__':main()
