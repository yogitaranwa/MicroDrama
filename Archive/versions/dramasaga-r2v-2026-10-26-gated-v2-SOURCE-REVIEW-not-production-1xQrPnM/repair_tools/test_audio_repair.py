import unittest
import numpy as np
from audio_repair import RATE,make_voice,mix_stems,rms_db
class AudioRepairTests(unittest.TestCase):
 def test_every_line_placed(self):
  source=np.ones((RATE*2,2))*.01
  lines=[{'line':1,'source_start':0,'source_end':.5}]
  x,w=make_voice(source,lines,[{'lines':[{'line':1,'start':1}]}],3)
  self.assertEqual(w,[(RATE,RATE*3//2)]);self.assertTrue(np.all(x[:RATE]==0));self.assertTrue(np.all(x[RATE:RATE*3//2]==.01))
 def test_missing_line_reject(self):
  with self.assertRaises(ValueError): make_voice(np.zeros((RATE,2)),[{'line':1}],[],1)
 def test_duplicate_line_reject(self):
  with self.assertRaises(ValueError):make_voice(np.ones((RATE*2,2)),[{'line':1,'source_start':0,'source_end':.2},{'line':2,'source_start':.4,'source_end':.6}],[{'lines':[{'line':1,'start':0},{'line':1,'start':1}]}],3)
 def test_overlap_reject(self):
  with self.assertRaises(ValueError):make_voice(np.ones((RATE*2,2)),[{'line':i,'source_start':0,'source_end':1} for i in [1,2]],[{'lines':[{'line':1,'start':0},{'line':2,'start':.5}]}],3)
 def test_truncation_reject(self):
  with self.assertRaises(ValueError):make_voice(np.ones((RATE*2,2)),[{'line':1,'source_start':0,'source_end':1}],[{'lines':[{'line':1,'start':.5}]}],1)
 def test_music_short_reject(self):
  with self.assertRaises(ValueError):mix_stems(np.zeros((RATE*2,2)),np.zeros((RATE,2)),[])
 def test_duck_and_peak(self):
  t=np.arange(RATE*3)/RATE; m=np.column_stack([np.sin(2*np.pi*440*t)]*2)*.1
  v=np.zeros_like(m);v[RATE:RATE*2]=m[RATE:RATE*2]
  x,b=mix_stems(v,m,[(RATE,RATE*2)])
  self.assertLessEqual(np.max(np.abs(x)),10**(-2/20)+1e-8)
  self.assertAlmostEqual(rms_db(b[RATE+100:2*RATE-100])-rms_db(b[100:RATE//2]),-6,delta=.1)
if __name__=='__main__':unittest.main()
