"""Apply reviewed final story fixes after the 64s expansion: emotional performance tags and canonical recurring props."""
import json
PROP_MAP={
 'candelabra':('undercroft-candelabra','green-flamed silver candelabra marking the buried stair'),
 'candles':('floating-candles','floating wax candles used as ball lights'),
 'program':('ball-program','folded Yule Ball programme'),
 'card':('enchanted-dance-card','silver-edged enchanted dance card that writes and rewrites Harry and Draconia as partners'),
 'wand':('draconias-wand','Draconia’s dark polished wand in its silver holster'),
 'mirror':('mirror-lake','enchanted mirror surface beneath the ballroom floor'),
 'orb':('green-song-orb','palm-sized glowing green musical orb'),
 'ribbon':('green-ribbon','thin green silk ribbon sent by the forest')}
def finalize(path):
 s=json.load(open(path))
 for line in s['episodes'][8]['lines']:
  if line['text'].startswith('Then we are both done'): line['performance']='quiet, resolute'
  if line['text'].startswith('For once, I do not want'): line['performance']='quiet, vulnerable'
 for ep in s['episodes']:
  for shot in ep['shots']:
   shot['recurring_props']=[{'id':PROP_MAP[p][0],'description':PROP_MAP[p][1]} for p in shot['props']]
 return s
if __name__=='__main__':
 import sys
 p=sys.argv[1];s=finalize(p)
 open(p,'w').write(json.dumps(s,indent=2,ensure_ascii=False)+'\n')
