"""Stop between native conditions until a separately produced review is supplied.

Receipts bind evidence; they do not authenticate the reviewer. The operator must
obtain them through the designated reviewer's verified file channel.
"""
from pathlib import Path
from tools.r050_review_boundary.common import dump, files, fingerprint, load, publish, require, sha


def check_source(out):
    manifest = load(out/'source_manifest.json')['files']
    require(files(out/'source') == manifest, 'Frozen source changed before native')
    require(load(out/'plan.json') == load(out/'source/experiments/exp-62-top-down/frozen_spec.json'),
            'Frozen plan changed before native')
    for folder, manifest_name in [('parent', 'input_manifest.json'), ('repeat', 'repeat_manifest.json')]:
        require(files(out/folder) == load(out/manifest_name)['files'], 'Frozen input changed: '+folder)


def request_for(out, cell_id):
    return dict(schema='hcc-r081-external-review-request-v1', run_id=out.name,
                subject='design' if cell_id is None else cell_id,
                source_sha256=fingerprint(load(out/'source_manifest.json')['files']),
                plan_sha256=sha((out/'plan.json').read_bytes()),
                raw_sha256=None if cell_id is None else fingerprint(files(out/'evaluation'/cell_id)))


def reviewed(out, review_dir, writer_id, reviewer_id, cell_id=None):
    request = request_for(out, cell_id)
    name = request['subject']+'.json'
    request_path = out/'review_requests'/name
    if request_path.exists():
        require(load(request_path) == request, 'Review request evidence changed')
    else:
        dump(request_path, request)
    path = out/'external_reviews'/name
    incoming = Path(review_dir)/name if review_dir is not None else None
    if not path.exists() and (incoming is None or not incoming.exists()):
        print('WAITING_EXTERNAL_REVIEW:', request_path, flush=True)
        return False
    raw = (path if path.exists() else incoming).read_bytes()
    receipt = load(path if path.exists() else incoming)
    require(bool(reviewer_id) and reviewer_id != writer_id, 'Separate reviewer identity required')
    require(receipt.get('schema') == 'hcc-r081-external-review-v1', 'External review schema')
    require(receipt.get('request') == request, 'External review target mismatch')
    require(receipt.get('reviewer_id') == reviewer_id, 'Designated external reviewer required')
    require(receipt.get('verdict') == 'PASS' and receipt.get('blocking_findings') == [], 'External review did not pass')
    require(isinstance(receipt.get('evidence'), str) and receipt['evidence'].strip(), 'Review evidence required')
    require(isinstance(receipt.get('reviewed_at'), str) and receipt['reviewed_at'].strip(), 'Review time required')
    if not path.exists():
        publish(path, raw)
    return True


def completed(out, review_dir, writer_id, reviewer_id):
    if not reviewed(out, review_dir, writer_id, reviewer_id):
        return False
    for cell in load(out/'plan.json')['cells']:
        location = out/'evaluation'/cell['id']
        if not (location/'inference.json').exists():
            return False
        if not reviewed(out, review_dir, writer_id, reviewer_id, cell['id']):
            return False
    return True
