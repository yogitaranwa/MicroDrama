import math
import tempfile
import unittest
import wave
from array import array
from pathlib import Path
from magicdrama.audiofirst.dialogue_timing import validate_dialogue_alignment

class DialogueTimingTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.addCleanup(self.t.cleanup)
        self.p = Path(self.t.name) / 'test.wav'
        with wave.open(str(self.p), 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
            w.writeframes(array('h', (int(5000 * math.sin(2 * math.pi * 220 * i / 16000)) for i in range(16000))).tobytes())
        self.inputs = [{'text': 'Hi', 'voice_id': 'a'}]
        self.r = {'alignment': {'characters': ['H','i'], 'character_start_times_seconds': [0,.5], 'character_end_times_seconds': [.5,1]},
                  'voice_segments': [{'voice_id':'a','dialogue_input_index':0,'character_start_index':0,'character_end_index':2,'start_time_seconds':0,'end_time_seconds':1}]}
    def test_valid_structure_not_certification(self):
        self.assertIn('not_word_sync_certified',validate_dialogue_alignment(self.p,self.r,self.inputs)['status'])
    def test_uncovered_audible_tail(self):
        self.r['alignment']['character_end_times_seconds'][-1] = .6
        with self.assertRaises(ValueError): validate_dialogue_alignment(self.p,self.r,self.inputs)
    def test_wrong_speaker(self):
        self.r['voice_segments'][0]['voice_id']='wrong'
        with self.assertRaises(ValueError): validate_dialogue_alignment(self.p,self.r,self.inputs)
    def test_wrong_text(self):
        self.inputs[0]['text']='No'
        with self.assertRaises(ValueError): validate_dialogue_alignment(self.p,self.r,self.inputs)
    def test_out_of_range(self):
        self.r['alignment']['character_end_times_seconds'][-1]=2
        with self.assertRaises(ValueError): validate_dialogue_alignment(self.p,self.r,self.inputs)
