import unittest,json,copy
from pathlib import Path
from validate_scene import validate
R=Path(__file__).resolve().parents[1];ROOT=R.parent
class GuardTest(unittest.TestCase):
 def setUp(self):self.s=json.loads((R/'scene-contract.json').read_text())
 def test_valid_preparation(self):self.assertTrue(validate(self.s,ROOT))
 def test_no_spend(self):
  self.s['paid_enabled']=True
  with self.assertRaises(ValueError):validate(self.s,ROOT)
 def test_no_observation_laundering(self):
  self.s['status']='OBSERVED'
  with self.assertRaises(ValueError):validate(self.s,ROOT)
 def test_axis_crossing(self):
  self.s['cameras']['draconia_close'][1]=2
  with self.assertRaises(ValueError):validate(self.s,ROOT)
 def test_intent(self):
  self.s['shots'][0]['intent']='Dry relief'
  with self.assertRaises(ValueError):validate(self.s,ROOT)
 def test_dialogue(self):
  self.s['shots'][1]['locked_dialogue']='Thank you'
  with self.assertRaises(ValueError):validate(self.s,ROOT)
 def test_take(self):
  self.s['shots'][0]['audio_sha256']='0'*64
  with self.assertRaises(ValueError):validate(self.s,ROOT)
 def test_timing(self):
  self.s['shots'][0]['duration_s']=5
  with self.assertRaises(ValueError):validate(self.s,ROOT)
if __name__=='__main__':unittest.main()
