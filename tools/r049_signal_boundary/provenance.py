"""Reuse R048's exact-byte/publication helpers, with a new pinned parent and release."""
from pathlib import Path
import sys
from tools.r048_precision import io, provenance as previous
from . import spec

ATTRIBUTES=previous.ATTRIBUTES
publication_check=previous.publication_check


def inherited_check(root):
    root=io.safe(root);raw=io.lf(io.read(root/'R048_MANIFEST.json'))
    io.require(io.blob(raw)==spec.R048_MANIFEST_BLOB,'inherited R048 manifest differs from pinned main')
    previous.package_check(root)
    found={}
    for n,h in spec.NATIVE_BLOBS.items():
        b=io.lf(io.read(io.child(root,n)));io.require(io.blob(b)==h,'native core drift: '+n);found[n]=io.sha(b)
    return dict(native_hashes=found,R048_manifest_blob=io.blob(raw))


def repository_check(repo):
    repo=io.safe(repo);top=Path(previous.git(repo,'rev-parse','--show-toplevel').decode('utf-8').strip()).resolve()
    io.require(repo.resolve()==top,'not repository root')
    head=previous.git(repo,'rev-parse','HEAD').decode().strip()
    previous.git(repo,'merge-base','--is-ancestor',spec.BASE_COMMIT,head)
    return dict(head=head,required_ancestor=spec.BASE_COMMIT,inherited=inherited_check(repo))


def package_check(root):
    root=io.safe(root);m=io.load(root/'R049_MANIFEST.json')
    io.require(set(m)=={'schema','base_commit','files'} and m['schema']=='hcr-r049-release-v1' and m['base_commit']==spec.BASE_COMMIT,'release identity')
    for n,h in m['files'].items():io.require(io.sha(io.lf(io.read(io.child(root,n))))==h,'R049 source changed: '+n)
    return m


def restore_copy(source,dest,manifest):
    source=io.safe(source);dest=io.safe(dest)
    io.require(not dest.exists(),'parent destination already exists')
    io.require(manifest['schema']=='hcr-exp29-bundle-v1','parent schema')
    expected=manifest['files'];actual=set(io.names(source))
    io.require(actual==set(expected)|{'bundle_manifest.json'},'parent inventory mismatch: '+str(dict(
        missing=sorted(set(expected)-actual),extra=sorted(actual-set(expected)-{'bundle_manifest.json'}))))
    staged={};journal=[]
    for n,h in sorted(expected.items()):
        data=io.read(io.child(source,n));candidate,method=previous.recover_bytes(data,h,n)
        staged[n]=candidate;journal.append(dict(path=n,method=method,input_sha256=io.sha(data),output_sha256=h))
    # All candidates must match the old seal before a copy is written. Original remains unchanged.
    dest.mkdir(parents=True,exist_ok=False)
    for n,b in staged.items():io.write(io.child(dest,n),b)
    io.write(dest/'bundle_manifest.json',io.lf(io.read(source/'bundle_manifest.json')))
    io.verify_files(dest,expected,extra=('bundle_manifest.json',))
    return dict(files=len(expected),entries=journal,restored=sum(x['method']!='exact' for x in journal),
                original_modified=False,expected_hashes_unchanged=True)


def parent_copy_from_repo(repo,dest):
    src=io.child(repo,spec.PARENT_RUN)
    sealed=previous.git(repo,'show',spec.BASE_COMMIT+':'+spec.PARENT_RUN+'/bundle_manifest.json')
    io.require(io.blob(sealed)==spec.PARENT_BUNDLE_BLOB,'parent manifest Git pin')
    io.require(io.lf(io.read(src/'bundle_manifest.json'))==sealed,'parent manifest differs from pinned commit')
    return restore_copy(src,dest,io.loads(sealed))


def verify_parent(root,log=None):
    root=io.safe(root);source=root/'source'
    m=io.load(root/'bundle_manifest.json');io.require(m['schema']=='hcr-exp29-bundle-v1','parent bundle schema')
    io.require(io.blob(io.read(root/'bundle_manifest.json'))==spec.PARENT_BUNDLE_BLOB,'pinned parent bytes')
    io.verify_files(root,m['files'],extra=('bundle_manifest.json',))
    return io.command([sys.executable,'-X','utf8','-B',str(source/'scripts/r048_cli.py'),'verify','--run',str(root)],
                      cwd=source/'src',log=log)


def copy_source(repo,parent_source,dest):
    dest=io.safe(dest);io.require(not dest.exists(),'source snapshot exists')
    m=package_check(repo);inherited_check(parent_source)
    files={n:io.read(io.child(parent_source,n)) for n in io.names(parent_source)}
    for n in list(m['files'])+['R049_MANIFEST.json']:
        b=io.read(io.child(repo,n));io.require(n not in files or files[n]==b,'source collision: '+n);files[n]=b
    for n,b in files.items():io.write(io.child(dest,n),b)
    inherited_check(dest);package_check(dest)
    return io.hashes(dest)
