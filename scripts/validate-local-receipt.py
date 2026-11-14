#!/usr/bin/env python3
"""Reject incomplete, stale, altered or mismatched local verification evidence."""
from pathlib import Path
import argparse,datetime,hashlib,json,re,subprocess,sys

def main():
 p=argparse.ArgumentParser();p.add_argument('receipt');a=p.parse_args()
 root=Path(__file__).resolve().parent.parent;path=Path(a.receipt).expanduser().resolve();directory=path.parent
 r=json.loads(path.read_text());cfgpath=root/'scripts/local-verification.json';cfg=json.loads(cfgpath.read_text())
 git=lambda *args:subprocess.check_output(['git',*args],cwd=root,text=True).strip()
 digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 def require(condition,message):
  if not condition:raise ValueError(message)
 require(r.get('complete') is True and r.get('passed') is True,'Incomplete or failed receipt')
 require(r.get('working_tree_after')=='','Post-check working tree was not clean')
 require(git('status','--porcelain','--untracked-files=normal')=='','Current working tree is not clean')
 require(r.get('repo')==cfg['repo'] and r.get('commit')==git('rev-parse','HEAD'),'Receipt repository/commit mismatch')
 require(r.get('commit_after')==r.get('commit'),'Candidate changed during verification')
 if cfg.get('require_clean_ignored_start'):require(r.get('ignored_start')=='','Ignored state existed before verification')
 require(re.fullmatch(r'[0-9a-f]{40}',r.get('base',''))is not None,'Invalid base')
 subprocess.run(['git','merge-base','--is-ancestor',r['base'],r['commit']],cwd=root,check=True)
 if cfg.get('target_ref'):
  target=git('rev-parse',cfg['target_ref']+'^{commit}')
  expected=git('rev-parse',r['commit']+'^1') if target==r['commit'] else target
  require(r['base']!=r['commit'] and r['base']==expected,'Wrong target-anchored base')
  require(subprocess.run(['git','diff','--quiet',r['base'],r['commit']],cwd=root).returncode==1,'Empty or unreadable candidate diff')
 require(r.get('contract_sha256')==digest(cfgpath),'Contract changed')
 require(r.get('runner_sha256')==digest(root/'scripts/verify-local.py'),'Runner changed')
 started=datetime.datetime.fromisoformat(r['started_at']);ended=datetime.datetime.fromisoformat(r['finished_at']);now=datetime.datetime.now(datetime.timezone.utc)
 require(started.tzinfo is not None and ended.tzinfo is not None,'Timestamp lacks timezone')
 require(started<=ended and datetime.timedelta(0)<=now-ended<=datetime.timedelta(hours=24),'Future or stale receipt')
 def check_log(name,expected):
  require(isinstance(name,str) and Path(name).name==name,'Unsafe log filename')
  target=directory/name;require(target.is_file()and not target.is_symlink(),'Missing or symlinked log')
  require(digest(target)==expected,'Log hash mismatch: '+name)
 require(set(r.get('tools',{}))==set(cfg.get('tool_versions',{})),'Tool coverage mismatch')
 for name,command in cfg.get('tool_versions',{}).items():
  t=r['tools'][name];require(t.get('command')==command and t.get('exit_code')==0,'Failed/mismatched tool check: '+name);check_log('tool-'+name+'.log',t.get('log_sha256'))
 require([j.get('id')for j in r.get('jobs',[])]==[j['id']for j in cfg['jobs']],'Job coverage mismatch')
 for job,expected in zip(r['jobs'],cfg['jobs']):
  require(job.get('status')=='passed','Failed job')
  commands=job.get('commands',[]);require([x.get('command')for x in commands]==expected['commands'],'Command coverage mismatch')
  for c in commands:
   require(c.get('exit_code')==0 and c.get('cwd')==expected.get('cwd','.'),'Failed command/cwd mismatch');check_log(c.get('log'),c.get('log_sha256'))
 print(json.dumps({'valid':True,'commit':r['commit'],'receipt':str(path)}));return 0
if __name__=='__main__':
 try:sys.exit(main())
 except Exception as e:print('Receipt rejected: '+str(e),file=sys.stderr);sys.exit(1)
