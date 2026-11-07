"""Verify package files and optionally stage only verified paths. Never commit/push."""
from pathlib import Path
import argparse,hashlib,json,subprocess,tempfile,os,sys
root=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--stage',action='store_true');a=p.parse_args()
m=json.loads((root/'PACKAGE_MANIFEST.json').read_text());bad=[]
for x in m['files']:
 path=root/x['path']
 if not path.is_file() or path.stat().st_size!=x['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=x['sha256']:bad.append(x['path'])
if bad:raise SystemExit('FAILED manifest verification: '+str(bad[:20]))
expected={x['path'] for x in m['files']}|{'PACKAGE_MANIFEST.json'}
extra=[str(x.relative_to(root)) for x in root.rglob('*') if x.is_file() and '.git' not in x.relative_to(root).parts and str(x.relative_to(root)) not in expected]
print('PASS:',len(m['files']),'manifest files; extra files:',len(extra))
if extra:print('Unlisted files are NOT staged:',extra[:20])
if a.stage:
 def run(*args):return subprocess.run(['git',*args],cwd=root,check=True)
 run('rev-parse','--show-toplevel')
 run('lfs','version')
 fd,name=tempfile.mkstemp(prefix='magicdrama-paths-')
 try:
  with os.fdopen(fd,'wb') as f:
   for namepath in sorted(expected):f.write(namepath.encode()+b'\0')
  run('add','--force','--pathspec-from-file='+name,'--pathspec-file-nul')
 finally:os.unlink(name)
 print('Verified paths staged locally. No commit, push or history rewrite performed.')
