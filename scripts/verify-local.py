#!/usr/bin/env python3
"""Execute the repository's complete local verification contract and retain evidence."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,re,signal,subprocess,sys,time

def main():
 p=argparse.ArgumentParser();p.add_argument('--receipt-dir',required=True);p.add_argument('--base',required=True);a=p.parse_args()
 root=Path(__file__).resolve().parent.parent
 requested=Path(a.receipt_dir).expanduser()
 if not requested.is_absolute():raise SystemExit('Receipt directory must be absolute')
 out=requested.resolve()
 if not out.is_absolute() or out==root or root in out.parents:raise SystemExit('Receipt directory must be outside the checkout')
 if out.exists():raise SystemExit('Refusing to overwrite an existing receipt directory')
 git=lambda *args:subprocess.check_output(['git',*args],cwd=root,text=True).strip()
 head=git('rev-parse','HEAD');base=git('rev-parse',a.base+'^{commit}')
 if git('status','--porcelain','--untracked-files=normal'):raise SystemExit('Verification requires a clean committed candidate')
 if not re.fullmatch(r'[0-9a-f]{40}',head+'' ):raise SystemExit('Unknown candidate commit')
 cfgpath=root/'scripts/local-verification.json';cfg=json.loads(cfgpath.read_text())
 ignored_start=git('status','--porcelain','--ignored','--untracked-files=normal')
 if cfg.get('require_clean_ignored_start') and ignored_start:raise SystemExit('Fresh checkout required: ignored state exists; use an owned disposable checkout')
 if cfg.get('target_ref'):
  target=git('rev-parse',cfg['target_ref']+'^{commit}')
  expected=git('rev-parse',head+'^1') if target==head else target
  if base==head or base!=expected:raise SystemExit('Base must match the target ref, or the merged commit first parent')
  subprocess.run(['git','merge-base','--is-ancestor',base,head],cwd=root,check=True)
  if subprocess.run(['git','diff','--quiet',base,head],cwd=root).returncode!=1:raise SystemExit('Verification requires a nonempty base-to-candidate diff')
 out.mkdir(parents=True)
 env={k:v for k,v in os.environ.items() if k in ['PATH','HOME','TMPDIR','LANG','LC_ALL','SHELL','USER','LOGNAME','TERM','DEVELOPER_DIR','JAVA_HOME']}
 env.update({'CI':'1','GITHUB_WORKSPACE':str(root),'GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_SYSTEM':'/dev/null','PHD_LOCAL_RECEIPT_DIR':str(out),'PHD_LOCAL_BASE':base})
 receipt={'version':1,'repo':cfg['repo'],'commit':head,'base':base,'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'contract_sha256':hashlib.sha256(cfgpath.read_bytes()).hexdigest(),'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'tools':{},'jobs':[],'complete':False,'passed':False,'ignored_start':ignored_start}
 def save(final=False):
  receipt['complete']=final
  receipt['passed']=final and 'working_tree_after' in receipt and receipt['working_tree_after']=='' and receipt.get('commit_after')==head and bool(receipt['jobs']) and all(j['status']=='passed' for j in receipt['jobs']) and all(t['exit_code']==0 for t in receipt['tools'].values())
  receipt['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat() if final else None
  temporary=out/'receipt.json.partial'
  temporary.write_text(json.dumps(receipt,indent=2)+'\n')
  temporary.replace(out/'receipt.json')
 def run(command,cwd,log,seconds):
  start=time.monotonic()
  with log.open('wb') as f:
   child=subprocess.Popen(command,shell=True,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
   try:return child.wait(timeout=seconds),round(time.monotonic()-start,3)
   except subprocess.TimeoutExpired:
    os.killpg(child.pid,signal.SIGTERM)
    try:child.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
    return 124,round(time.monotonic()-start,3)
 for name,command in cfg.get('tool_versions',{}).items():
  log=out/('tool-'+name+'.log');code,dur=run(command,root,log,30);receipt['tools'][name]={'command':command,'exit_code':code,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()}
 for job in cfg['jobs']:
  row={'id':job['id'],'source':job['source'],'commands':[],'status':'passed'}
  for idx,command in enumerate(job['commands'],1):
   log=out/(job['id']+'-'+str(idx)+'.log');code,dur=run(command,root/job.get('cwd','.'),log,job.get('timeout_seconds',900));row['commands'].append({'command':command,'cwd':job.get('cwd','.'),'exit_code':code,'duration_seconds':dur,'log':log.name,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
   if code:row['status']='failed';row['blocked_commands']=job['commands'][idx:];break
  receipt['jobs'].append(row);save()
 receipt['commit_after']=git('rev-parse','HEAD');receipt['ignored_after']=git('status','--porcelain','--ignored','--untracked-files=normal');receipt['working_tree_after']=git('status','--porcelain','--untracked-files=normal');save(final=True)
 print(json.dumps({'commit':head,'passed':receipt['passed'],'receipt':str(out/'receipt.json'),'failed_jobs':[j['id'] for j in receipt['jobs'] if j['status']!='passed']}))
 return 0 if receipt['passed'] else 1
if __name__=='__main__':sys.exit(main())
