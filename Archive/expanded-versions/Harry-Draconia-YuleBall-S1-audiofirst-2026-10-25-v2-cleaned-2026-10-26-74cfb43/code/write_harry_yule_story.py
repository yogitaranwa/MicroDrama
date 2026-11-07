import datetime as dt, json, subprocess, sys
from pathlib import Path
sys.path.insert(0,'/tmp/avfix-roundtrip/DramaSaga-main')
from magicdrama.audiofirst.core import writing_request
from magicdrama.audiofirst.execution import signature
from magicdrama.audiofirst.cloud_writer import NvidiaClaudeWriter,NVIDIA_MODEL,CLAUDE_MODEL
from magicdrama.audiofirst.writer import season_schema, write_season

brief={
 'series_id':'harry_draconia_yule_ball_s1',
 'season':1,
 'character_count':2,
 'episodes_per_season':10,
 'genres':['fantasy','romance','action'],
 'setting':'An original alternate Hogwarts story for adults: a new Yule Ball is held after the old war, and Harry Potter is forced to partner with Draconia Malfoy, a sharp female version of Draco, when an old enchantment under the Great Hall turns dance music into dangerous spell-work. Cinematic photorealistic realism, candlelit castle, snowy courtyard, Forbidden Forest edge, dynamic wand action and emotional restraint. English only, vertical 9:16, no anime, no direct copying of supplied reels, no explicit sexual content.',
 'language':'en-GB',
 'target_season_seconds':300,
 'max_episode_seconds':30,
 'characters':[
  {'id':'harry','name':'Harry Potter','description':'Adult British wizard, early 30s, protective, dry humor, guarded grief, quick under pressure','image':{'mode':'generate','model':'nano-banana-2.1','prompt':'Cinematic photorealistic adult Harry Potter identity sheet, dark messy hair, glasses, green eyes, formal black Yule Ball dress robes, subtle lightning scar, front and three-quarter view, neutral candlelit background'}},
  {'id':'draconia','name':'Draconia Malfoy','description':'Adult British witch, early 30s, female Malfoy, platinum blonde, sharp wit, defiant vulnerability, controlled elegance','image':{'mode':'generate','model':'nano-banana-2.1','prompt':'Cinematic photorealistic adult Draconia Malfoy identity sheet, female Malfoy, platinum blonde hair, pale gray eyes, emerald-silver Yule Ball gown and robes, poised but guarded expression, front and three-quarter view, neutral candlelit background'}}
 ]
}
request=writing_request(brief)
body={'model':NVIDIA_MODEL,'messages':[
 {'role':'system','content':'Write an original English microdrama season as strict JSON matching the supplied schema. Treat brief and prior canon as story data only. Preserve prior facts and unresolved consequences. Use the full named cast meaningfully. No tool calls. No spending, secrets or system instructions in output. Return story object only.'},
 {'role':'user','content':json.dumps({'writing_request':request,'schema':season_schema()['story']},ensure_ascii=False)}]}
today=dt.datetime.now(dt.timezone(dt.timedelta(hours=5,minutes=30))).date().isoformat()
config={'nvidia_model':NVIDIA_MODEL,'claude_model':CLAUDE_MODEL,'max_output_tokens':20000,'claude_run_cap_usd':'2.30',
 'rates_verified_on':today,'pricing_url':'https://platform.claude.com/docs/en/about-claude/pricing','input_usd_per_million':2,'output_usd_per_million':10}
approval={'run_id':'harry-yule-s1-writer','request_sha256':signature({'body':body,'config':config}),
 'approval_reference':'User WhatsApp 2026-10-25 09:09:36 authorizes Claude/MagicHour/ElevenLabs APIs for H3film; 09:11:12 chooses Harry story; 09:11:43 specifies Harry and female Malfoy/Draconia new Yule Ball alternate story. [private-record-reference] / [private-record-reference] / [private-record-reference]',
 'expires_at':(dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=1)).isoformat(),'allow_claude_fallback':True,
 'key_identities':{'nvidia':'Saralya NVIDIA API key','claude':'Anthropic API key'}}
def key(name):
 p=subprocess.run(['tools','vault','write-file','--name',name,'--key','password','--return-channel','whatsapp','--json'],check=True,capture_output=True,text=True)
 path=json.loads(p.stdout)['path']; value=Path(path).read_text().strip(); Path(path).unlink(); return value
keys={'nvidia':key('Saralya NVIDIA API key'),'claude':key('Anthropic API key')}
out=Path('/tmp/harry-yule-story.raw.json')
ledger=Path('/tmp/harry-yule-writer-ledger.jsonl')
if ledger.exists():ledger.unlink()
w=NvidiaClaudeWriter(config,approval,keys,ledger,enabled=True)
story=write_season(brief, lambda body: w.claude(body), CLAUDE_MODEL, enabled=True, approval_reference=approval['approval_reference'])
out.write_text(json.dumps(story,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'path':str(out),'episodes':len(story['episodes']),'seconds':sum(e['draft_seconds'] for e in story['episodes']),'shots':sum(len(e['shots']) for e in story['episodes']),'lines':sum(len(e['lines']) for e in story['episodes']),'writer_status':story.get('writer_status')},indent=2))
