"""Original bounded research runner. Four one-image attempts only. Never resumes a POST.
Credentials are read from a private file and deleted after each invocation.
No production imports, no external repository execution, no video endpoints.
"""
import hashlib,json,os,sys,time
from pathlib import Path
import requests
R=Path(__file__).resolve().parents[1]; I=R.parents[0]/'next-comparison/inputs'
API='https://api.magichour.ai'; F=R/'receipts.json'
def save(x):
 p=F.with_suffix('.tmp');p.write_text(json.dumps(x,indent=2));p.replace(F)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def req(method,url,**kw):
 r=requests.request(method,url,timeout=60,**kw);r.raise_for_status();return r

def make_specs():
 common='Create one photoreal cinematic vertical 9:16 film still, not a collage or grid. No text or captions. Reference1 gives composition only, not its incorrect background or clothing. Reference2 pins the same adult character identity, hair and costume colors. Reference3 is the authoritative CURRENT HALL STATE: cold ice-covered Gothic hall after the principal chandelier crashed; its wreckage remains on the floor, broken suspension above. Replace the warm intact-hall background of references1/2 with this aftermath. Preserve stone arches, window layout, ice and credible surviving side candles; do not delete unrelated smaller lamps. No large intact principal chandelier above or behind character. No new architecture or duplicate characters. Match cool moonlight with gentle candle rim light and natural skin. '
 harry='Harry wears round wire glasses, white shirt, black dress robes with deep red lapel lining, and a narrow STRAIGHT DARK NECKTIE hanging vertically below the collar. Explicitly replace the erroneous bowtie in references1/2. No bowtie. Harry occupies left/center, looks distinctly to screen RIGHT toward offscreen Draconia, never into lens. Concern settling into dry relief after surviving the crash. '
 drac='Draconia has the same braided platinum-blonde updo, earrings and fitted dark emerald green gold-embroidered gown as reference2. Draconia occupies right/center, turns her eyes and nose distinctly to screen LEFT toward offscreen Harry, never into lens, no frontal stare. Wry breathless disbelief after surviving the crash. '
 variants=[('harry-A',harry,'Tight chest-up three-quarter close-up, camera near her shoulder, a soft sliver of Draconia shoulder at far right edge; readable face, eye-level shot. Keep a small soft-focused floor-level wreckage glimpse in depth where composition permits, never float wreckage.'),('harry-B',harry,'Slightly wider waist-up reverse close-up at eye level, enough lower background to show fallen metal/crystal at floor level behind him, not a reinstated ceiling fixture. Draconia stays offscreen right. Restrained expression, mouth relaxed, no broad grin.'),('draconia-A',drac,'Chest-up reciprocal reverse close-up at eye level, Harry remains offscreen left. Keep both eyes and face readable despite looking left. A soft floor-level wreckage glimpse in depth if plausible, not a giant object over her head.'),('draconia-B',drac,'Slightly wider waist-up reciprocal reverse close-up, camera on the SAME side of their conversational axis, screen-left gaze. Lower background reveals fallen chandelier fragments on icy floor. Harry stays offscreen left. No extra people or posing for portrait.')]
 out=[]
 for name,c,v in variants:
  h=name.startswith('harry');files=[('e01-s17-b1-start.png' if h else 'e01-s18-b1-start.png'),('ref-harry-front-close.png' if h else 'ref-draconia-front-close.png'),'aftermath-existing-frame-0.7s.png']
  out.append({'name':name,'files':files,'body':{'name':'hybrid-research-'+name,'model':'nano-banana-2.1','image_count':1,'resolution':'1k','aspect_ratio':'9:16','style':{'prompt':common+c+v}}})
 return out

def main():
 mode=sys.argv[1];key=Path(os.environ['MAGICHOUR_KEY_FILE'])
 try:
  H={'Authorization':'Bearer '+key.read_text().strip()}
  if mode=='submit':
   if F.exists():raise RuntimeError('Existing receipt: no POST replay allowed')
   lock=json.load(open(R/'input-lock.json'))
   for row in lock:
    assert sha(I/row['file'])==row['sha256'],row['file']
   a=req('GET',API+'/v1/account',headers=H).json();assert a['credits']==113663 and a['tier']=='creator',a
   x={'cap':200,'count':4,'no_retries':True,'no_video':True,'approval_ref':'[private-record-reference]','account_before':a,'started_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'uploads':{},'jobs':[],'charged_total':0}
   save(x);specs=make_specs();(R/'exact-job-specs.json').write_text(json.dumps(specs,indent=2))
   for s in specs:
    fps=[]
    for fn in s['files']:
     if fn not in x['uploads']:
      d=req('POST',API+'/v1/files/upload-urls',headers=H,json={'items':[{'extension':'png','type':'image'}]}).json()['items'][0]
      req('PUT',d['upload_url'],data=(I/fn).read_bytes());x['uploads'][fn]={'file_path':d['file_path'],'sha256':sha(I/fn)};save(x)
     fps.append(x['uploads'][fn]['file_path'])
    b=dict(s['body']);b['assets']={'image_file_paths':fps}
    e={'name':s['name'],'state':'reserved_unknown_outcome','quote':50,'submitted_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'body':b};x['jobs'].append(e);save(x)
    j=req('POST',API+'/v1/ai-image-editor',headers=H,json=b).json();e.update({'response':j,'id':j.get('id'),'charged':j.get('credits_charged'),'state':'queued'});x['charged_total']+=j.get('credits_charged',0);save(x)
    assert j.get('id') and j.get('credits_charged')==50,j
    a=req('GET',API+'/v1/account',headers=H).json();e['balance_after']=a['credits'];save(x);assert a['credits']==113663-x['charged_total'],a
    print(s['name'],j['id'],j['credits_charged'],a['credits'],flush=True)
  elif mode=='poll':
   x=json.load(open(F))
   for e in x['jobs']:
    if e.get('state')=='downloaded':continue
    assert e.get('id'),'Unknown submission: hold and reconcile, never resubmit'
    j=req('GET',API+'/v1/image-projects/'+e['id'],headers=H).json()
    e['provider_details']=j;save(x);print(e['name'],j['status'],j.get('credits_charged'),flush=True)
    if j['status']=='complete':
     assert j['credits_charged']==50,j
     p=R/'outputs'/(e['name']+'.png');p.write_bytes(req('GET',j['downloads'][0]['url']).content);e.update({'state':'downloaded','output':p.name,'sha256':sha(p)});save(x)
    elif j['status'] in ['error','canceled']:raise RuntimeError('Provider failure: no retry')
   x['account_after']=req('GET',API+'/v1/account',headers=H).json();save(x)
  else:raise ValueError(mode)
 finally:key.unlink(missing_ok=True)
if __name__=='__main__':main()
