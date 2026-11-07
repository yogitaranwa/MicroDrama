import copy, hashlib, tempfile, unittest
from pathlib import Path
from reference_bridge import compile_camera_plan

class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.file=Path(self.tmp.name)/'fixture.bin';self.file.write_bytes(b'test-only non-media')
  self.sha=hashlib.sha256(self.file.read_bytes()).hexdigest()
  self.refs=[{'id':'a','kind':'character','characters':['a'],'views':['close'],'primary':True,'sha256':self.sha}, {'id':'loc','kind':'location','location':'hall','views':['wide'],'primary':True,'sha256':self.sha}]
  self.shots=[{'id':'s1','visible_characters':['a'],'framing':'close','location':'hall','seconds':4,'line_ids':['l1'],'speakers':['a']}]
  self.cameras=[{'id':'c1','shots':['s1']}]
  self.files={'a':str(self.file),'loc':str(self.file)}
  self.audio={'l1':{'path':str(self.file),'sha256':self.sha}}
 def run_plan(self): return compile_camera_plan(self.shots,self.cameras,{'references':self.refs},self.files,self.audio)
 def test_prepared_not_rendered(self):
  result=self.run_plan();self.assertFalse(result['live_enabled']);self.assertEqual(result['shots'][0]['status'],'prepared_not_rendered_not_quality_accepted')
 def test_audio_missing(self):
  self.audio={}
  with self.assertRaises(ValueError): self.run_plan()
 def test_audio_mutated(self):
  self.audio['l1']['sha256']='0'*64
  with self.assertRaises(ValueError): self.run_plan()
 def test_view_missing(self):
  self.refs[0]['views']=['wide']
  with self.assertRaises(ValueError): self.run_plan()
 def test_duplicate_camera_membership(self):
  self.cameras.append({'id':'c2','shots':['s1']})
  with self.assertRaises(ValueError): self.run_plan()
 def test_parent_missing(self):
  self.cameras[0].update(parent_camera='missing',parent_shot='s1')
  with self.assertRaises(ValueError): self.run_plan()
 def test_cycle(self):
  self.cameras[0].update(parent_camera='c1',parent_shot='s1')
  with self.assertRaises(ValueError): self.run_plan()
 def test_hash_change(self):
  before=self.run_plan()['plan_sha256'];self.shots[0]['seconds']=5
  self.assertNotEqual(before,self.run_plan()['plan_sha256'])
 def test_reference_hash_mismatch(self):
  self.refs[0]['sha256']='0'*64
  with self.assertRaises(ValueError): self.run_plan()

if __name__=='__main__':unittest.main()
