"""Source pins, lossless parent recovery, and Git publication byte checks.

No previous evidence file or manifest is edited. A newline transformation is accepted
ONLY if its output equals the original, commit-pinned sealed SHA256 exactly.
"""
from pathlib import Path
import subprocess
import sys
from . import io,spec

ATTRIBUTES=b'# Immutable experiment evidence: preserve exact bytes.\n* -text -filter -ident !working-tree-encoding\n'
TEXT_EXTENSIONS={'.cmd','.ps1','.py','.json','.jsonl','.csv','.md','.txt','.log','.sh'}

def git(repo,*args,input=None):
    p=subprocess.run(['git','-C',str(io.safe(repo)),*args],input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    io.require(p.returncode==0,'git read failed: '+p.stderr.decode('utf-8','replace'))
    return p.stdout

def inherited_check(root):
    out={}
    for n,w in spec.NATIVE_BLOBS.items():
        b=io.lf(io.read(io.child(root,n)));io.require(io.blob(b)==w,'native baseline drift: '+n);out[n]=io.sha(b)
    for n,w in spec.INHERITED_HASHES.items():
        b=io.lf(io.read(io.child(root,n)));io.require(io.sha(b)==w,'inherited adapter/auditor drift: '+n);out[n]=w
    return out

def repository_check(repo):
    repo=io.safe(repo)
    top=Path(git(repo,'rev-parse','--show-toplevel').decode('utf-8').strip()).resolve()
    io.require(top==repo.resolve(),'not repository root')
    head=git(repo,'rev-parse','HEAD').decode().strip()
    git(repo,'merge-base','--is-ancestor',spec.BASE_COMMIT,head)
    return dict(head=head,required_ancestor=spec.BASE_COMMIT,inherited=inherited_check(repo))

def package_check(root):
    m=io.load(Path(root)/'R048_MANIFEST.json')
    io.require(set(m)=={'schema','base_commit','files'} and m['schema']=='hcr-r048-release-v1' and
               m['base_commit']==spec.BASE_COMMIT,'R048 release identity')
    for n,h in m['files'].items():
        io.require(io.sha(io.lf(io.read(io.child(root,n))))==h,'R048 source changed: '+n)
    return m

def recover_bytes(data,expected,name):
    if io.sha(data)==expected:return data,'exact'
    # No fuzzy match, ignored field, rewritten manifest, or generated log is allowed.
    io.require(Path(name).suffix.lower() in TEXT_EXTENSIONS or Path(name).name in ('.gitignore','.gitattributes'),
               'non-text hash mismatch: '+name)
    data.decode('utf-8','strict')
    io.require(b'\0' not in data,'binary input is not newline-restorable: '+name)
    normalized=io.lf(data)
    choices=[(normalized,'restore_LF'),(normalized.replace(b'\n',b'\r\n'),'restore_CRLF')]
    for candidate,method in choices:
        if io.sha(candidate)==expected:return candidate,method
    raise io.ContractError('not an exact original-byte newline restoration: '+name)

def restore_parent_copy(source,dest,manifest):
    source=io.safe(source);dest=io.safe(dest)
    io.require(not dest.exists(),'parent copy already exists')
    io.require(manifest['schema']=='hcr-exp28-bundle-v1' and isinstance(manifest['files'],dict),'parent bundle schema')
    expected=manifest['files'];actual=set(io.names(source))
    # Nothing is silently omitted, including extra errors/logs inside a sealed parent.
    io.require(actual==set(expected)|{'bundle_manifest.json'},
        'parent inventory mismatch: '+str(dict(missing=sorted(set(expected)-actual),extra=sorted(actual-set(expected)-{'bundle_manifest.json'}))))
    staged={};journal=[]
    for n,h in sorted(expected.items()):
        before=io.read(io.child(source,n));after,method=recover_bytes(before,h,n)
        staged[n]=after;journal.append(dict(path=n,input_sha256=io.sha(before),output_sha256=h,method=method))
    # Validate all candidates before copying any parent file.
    dest.mkdir(parents=True,exist_ok=False)
    for n,b in staged.items():io.write(io.child(dest,n),b)
    # This JSON itself was LF-canonical at sealing. Verify against the pinned Git blob upstream.
    io.write(dest/'bundle_manifest.json',io.lf(io.read(source/'bundle_manifest.json')))
    io.verify_files(dest,expected,extra=('bundle_manifest.json',))
    return dict(files=len(expected),restored=sum(x['method']!='exact' for x in journal),entries=journal,
                previous_parent_modified=False,manifest_rewritten=False,expected_hashes_unchanged=True)

def parent_copy_from_repo(repo,dest):
    src=io.child(repo,spec.PARENT_RUN)
    raw=git(repo,'show',spec.BASE_COMMIT+':'+spec.PARENT_RUN+'/bundle_manifest.json')
    io.require(io.blob(raw)==spec.PARENT_BUNDLE_GIT_BLOB,'parent manifest pin mismatch')
    io.require(io.lf(io.read(src/'bundle_manifest.json'))==raw,'local parent manifest changed')
    return restore_parent_copy(src,dest,io.loads(raw))

def verify_parent(root,log):
    root=io.safe(root);snapshot=root/'source'
    io.verify_files(root,io.load(root/'bundle_manifest.json')['files'],extra=('bundle_manifest.json',))
    # Fresh interpreter uses the parent's actual, sealed original protocol. No monkey patch.
    return io.command([sys.executable,'-X','utf8','-B',str(snapshot/'scripts/r047_cli.py'),
        'verify','--run',str(root)],cwd=snapshot/'src',log=log)

def copy_source(repo,parent_source,dest):
    dest=io.safe(dest);io.require(not dest.exists(),'source snapshot exists')
    m=package_check(repo);inherited_check(parent_source)
    files={n:io.read(io.child(parent_source,n)) for n in io.names(parent_source)}
    for n in list(m['files'])+['R048_MANIFEST.json']:
        b=io.read(io.child(repo,n))
        io.require(n not in files or files[n]==b,'source snapshot name collision: '+n)
        files[n]=b
    for n,b in files.items():io.write(io.child(dest,n),b)
    package_check(dest);inherited_check(dest)
    return io.hashes(dest)

def publication_check(repo,run):
    """Read-only dry-run of effective clean filters; never writes the Git index/objects."""
    repo=io.safe(repo);run=io.safe(run)
    paths=[io.child(run,n).relative_to(repo).as_posix() for n in io.names(run)]
    io.require(paths and all('\n' not in p and '\r' not in p for p in paths),'publication path list')
    attrs=git(repo,'check-attr','-z','--stdin','text','filter','ident','working-tree-encoding',
        input=('\0'.join(paths)+'\0').encode('utf-8')).decode('utf-8').split('\0')
    io.require(attrs[-1]=='','git attribute terminator');attrs=attrs[:-1]
    io.require(len(attrs)==len(paths)*12,'git attribute row count')
    for i in range(0,len(attrs),3):
        path,attribute,value=attrs[i:i+3]
        io.require(value==('unspecified' if attribute=='working-tree-encoding' else 'unset'),
            'evidence attribute can alter bytes: '+repr((path,attribute,value)))
    # stdin-paths applies each path's normal clean conversion unless --no-filters is passed.
    ignored=subprocess.run(['git','-C',str(repo),'check-ignore','--no-index','-z','--stdin'],
        input=('\0'.join(paths)+'\0').encode('utf-8'),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    io.require(ignored.returncode in (0,1) and not ignored.stdout,
        'evidence would be omitted by git ignore: '+ignored.stdout.decode('utf-8','replace'))
    ids=git(repo,'hash-object','--stdin-paths',input=('\n'.join(paths)+'\n').encode('utf-8')).decode().splitlines()
    expected=[io.blob(io.read(io.child(repo,p))) for p in paths]
    io.require(ids==expected,'Git clean path changes sealed bytes')
    return dict(verified=True,files=len(paths),ignored_files=0,index_written=False,git_objects_written=False,
                scope='current_worktree_effective_attributes_and_clean_filter_output_not_remote_push_verification')
