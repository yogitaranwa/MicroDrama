import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from microdrama.reviewgate import evaluate_shot, scaffold_receipt, validate_requirements, load_receipts
from microdrama.assembly_safety import ffconcat_entry, validate_assembly_inputs
from microdrama.detectors import mechanical_report, detect_freezes
from microdrama.stitch import stitch

ROOT=Path(__file__).resolve().parents[1]
REQ={'beat':'1','start':0,'end':3,'required_actions':['walk'],'lines':[]}

class HardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.p=Path(self.tmp.name)/'fixture.bin';self.p.write_bytes(b'local-fixture')
        self.receipt=scaffold_receipt(self.p,'1',REQ)
        self.receipt.update(reviewer='test-reviewer',reviewed_at='2026-10-25T10:00:00Z')
        self.receipt['checks']={k:True for k in self.receipt['checks']}
    def result(self,req=REQ):return evaluate_shot(req,self.p,self.receipt,{'defects':[]})
    def test_changed_action_invalidates_receipt(self):
        self.assertEqual(self.result({**REQ,'required_actions':['run']})['status'],'REVIEW_REQUIRED')
    def test_wrong_beat_invalidates_receipt(self):
        self.receipt['beat']='2';self.assertEqual(self.result()['status'],'REVIEW_REQUIRED')
    def test_future_review_pauses(self):
        self.receipt['reviewed_at']='2999-01-01T00:00:00Z';self.assertEqual(self.result()['status'],'REVIEW_REQUIRED')
    def test_freeze_cannot_be_downgraded_by_stale_receipt(self):
        self.receipt['asset_sha256']='old'
        r=evaluate_shot(REQ,self.p,self.receipt,{'defects':[{'type':'freeze','start':0,'end':3}]})
        self.assertEqual(r['status'],'REJECTED')
    def test_duplicate_beat_rejected(self):
        with self.assertRaises(ValueError):validate_requirements({'beats':[REQ,REQ]})
    def test_timeline_gap_rejected(self):
        with self.assertRaises(ValueError):validate_requirements({'beats':[REQ,{**REQ,'beat':'2','start':4,'end':5}]})
    def test_nonfinite_and_boolean_time_rejected(self):
        for value in (float('nan'),float('inf'),True):
            with self.assertRaises(ValueError):validate_requirements({'beats':[{**REQ,'end':value}]})
    def test_line_outside_beat_rejected(self):
        with self.assertRaises(ValueError):validate_requirements({'beats':[{**REQ,'lines':[{'start':2,'end':4}]}]})
    def test_duplicate_receipts_rejected(self):
        for name in ('a','b'):(self.p.parent/(name+'.receipt.json')).write_text(json.dumps(self.receipt))
        with self.assertRaises(ValueError):load_receipts(self.p.parent)
    def test_path_newline_rejected(self):
        with self.assertRaises(ValueError):ffconcat_entry('a\nb.mp4')
    def test_apostrophe_escaped(self):self.assertIn("'\\''",ffconcat_entry("a'b.mp4"))
    def test_lowlevel_bypass_blocked(self):
        with self.assertRaises(RuntimeError):stitch('absent','out')
    def test_historical_custom_assembler_blocks_before_encoding(self):
        p=subprocess.run([sys.executable,str(ROOT/'assemble_v43_final_v3.py')],capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0);self.assertIn('retired',p.stderr)
    def test_submit_scripts_block_before_secret_or_network(self):
        for p in ROOT.glob('submit_*.py'):
            proc=subprocess.run([sys.executable,str(p)],capture_output=True,text=True,env={})
            self.assertNotEqual(proc.returncode,0,p.name);self.assertIn('retired',proc.stderr,p.name)
    def test_detector_failure_is_not_clean_report(self):
        with self.assertRaises(subprocess.CalledProcessError):detect_freezes(self.p)
    def test_output_alias_refused_before_probe(self):
        with self.assertRaisesRegex(ValueError,'alias'):validate_assembly_inputs({'beats':[REQ]},{'1':str(self.p)},'audio',self.p)
    def test_existing_output_preserved(self):
        out=self.p.parent/'out';out.write_bytes(b'keep')
        with self.assertRaisesRegex(ValueError,'Fresh'):validate_assembly_inputs({'beats':[REQ]},{'1':str(self.p)},'audio',out)
        self.assertEqual(out.read_bytes(),b'keep')

if __name__=='__main__':unittest.main()

class SignalEdgeTests(unittest.TestCase):
    def test_missing_audio_and_black_are_reported(self):
        from test_detectors import make_video
        with tempfile.TemporaryDirectory() as tmp:
            p=make_video(Path(tmp)/'black.mp4','color=c=black:size=144x256:rate=10',None,3)
            kinds={d['type'] for d in mechanical_report(p)['defects']}
            self.assertIn('missing_audio',kinds);self.assertIn('black_frame',kinds)
    def test_full_silence_is_not_a_clean_open(self):
        from test_detectors import make_video
        with tempfile.TemporaryDirectory() as tmp:
            p=make_video(Path(tmp)/'silent.mp4','testsrc2=size=144x256:rate=10','anullsrc=r=44100:cl=stereo',3)
            self.assertIn('opening_silence',{d['type'] for d in mechanical_report(p)['defects']})
    def test_assembly_rejects_short_audio_and_wrong_geometry(self):
        from test_detectors import make_video
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);a=make_video(root/'a.mp4','testsrc2=size=144x256:rate=10',None,3)
            b=make_video(root/'b.mp4','testsrc2=size=256x144:rate=10',None,3)
            subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','sine=frequency=440','-t','1',str(root/'audio.wav')],check=True)
            with self.assertRaisesRegex(ValueError,'audio duration'):validate_assembly_inputs({'beats':[REQ]},{'1':str(a)},root/'audio.wav',root/'out.mp4')
            req2={**REQ,'beat':'2','start':3,'end':6}
            with self.assertRaisesRegex(ValueError,'geometry'):validate_assembly_inputs({'beats':[REQ,req2]},{'1':str(a),'2':str(b)},root/'audio.wav',root/'out.mp4')
    def test_apostrophe_path_actually_decodes(self):
        from test_detectors import make_video
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=make_video(root/"a'b.mp4",'testsrc2=size=144x256:rate=10',None,1)
            listing=root/'concat.txt';listing.write_text(ffconcat_entry(p))
            subprocess.run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(listing),'-f','null','-'],check=True,capture_output=True)
