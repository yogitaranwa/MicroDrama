import json,requests,pathlib,base64,sys,time
root=pathlib.Path(__file__).parent
key=pathlib.Path(json.load(open('/tmp/el-secretmeta.json'))['path']).read_text().strip();h={'xi-api-key':key}
plan=json.load(open(root/'plan.json'))
for i in map(int,sys.argv[1:]):
 out=root/f'scene{i:02d}'
 if out.with_suffix('.started').exists():raise SystemExit('Already attempted; reconcile before rerun')
 sub=requests.get('https://api.elevenlabs.io/v1/user/subscription',headers=h,timeout=25);sub.raise_for_status();before=sub.json()
 assert before['max_credit_limit_extension']==0 and not before['can_extend_character_limit']
 assert before['character_limit']-before['character_count']>20000
 assert before['character_count']-2999<=9319
 batch=plan['batches'][i-1];payload={'model_id':'eleven_v3','inputs':[{'voice_id':r['voice_id'],'text':r['text']} for r in batch],'settings':{'stability':0.35},'seed':4100+i}
 json.dump(payload,open(out.with_suffix('.request.json'),'w'),indent=2)
 out.with_suffix('.started').write_text(str(time.time()))
 r=requests.post('https://api.elevenlabs.io/v1/text-to-dialogue/with-timestamps',params={'output_format':'mp3_44100_128'},headers=h,json=payload,timeout=100)
 print('scene',i,'http',r.status_code,flush=True)
 if r.status_code!=200:
  out.with_suffix('.error.txt').write_text(r.text);raise SystemExit(r.text[:600])
 x=r.json();out.with_suffix('.mp3').write_bytes(base64.b64decode(x.pop('audio_base64')))
 json.dump(x,open(out.with_suffix('.alignment.json'),'w'))
 after=requests.get('https://api.elevenlabs.io/v1/user/subscription',headers=h,timeout=25);after.raise_for_status();after=after.json()
 receipt={'scene':i,'submitted':sum(len(z['text']) for z in batch),'before_count':before['character_count'],'after_count':after['character_count'],'delta':after['character_count']-before['character_count'],'headers':{k:v for k,v in r.headers.items() if any(t in k.lower() for t in ['request-id','character','credit','history'])},'overage':after['current_overage']}
 json.dump(receipt,open(out.with_suffix('.receipt.json'),'w'),indent=2);print(receipt,flush=True)
 assert after['character_count']-2999<=9319 and float(after['current_overage']['amount'])==0
