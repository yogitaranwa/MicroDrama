import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from magicdrama.audiofirst.assembly import assemble_episode,assemble_season,caption_file
from magicdrama.audiofirst.production_run import media_run
from magicdrama.audiofirst.core import digest
from magicdrama.audiofirst.season import inspect_season_zip
from magicdrama.audiofirst.h3_wrapper import render_h3


def fixture(root):
    # Generated local synthetic media for integration tests, not a speech/acting sample.
    audio=root/'tone.wav';image=root/'image.png'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=300:duration=1','-c:a','pcm_s16le',str(audio)],check=True)
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=teal:s=180x320','-frames:v','1','-threads','1',str(image)],check=True)
    return {'id':'ep1','audio':{'path':str(audio),'sha256':digest(audio)},'audio_checked':True,
            'cue_audio_sha256':digest(audio),'cues':[{'start':0,'end':1,'text':'Hello.','speaker':'lead','actual_audio_checked':True}],
            'spoken_lines':['Hello.'],'names':{'lead':'Test character'},
            'shots':[{'path':str(image),'sha256':digest(image),'kind':'image','frames':24,'pixel_checked':True}]}

@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'ffmpeg required')
class MediaTests(unittest.TestCase):
    def test_own_assembly_real_ffmpeg(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);s=fixture(p);r=assemble_episode(s,p/'out',size=(180,320))
            self.assertTrue(Path(r['path']).is_file());self.assertAlmostEqual(r['duration'],1)
            self.assertEqual(r['paid_requests'],0)
            self.assertTrue((p/'out/captions.srt').is_file())
    @unittest.skipUnless(shutil.which('node'),'node required')
    def test_h3_join_assembly_real_join(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);s=fixture(p);r=assemble_episode(s,p/'out',backend='h3_join',size=(180,320))
            self.assertEqual(r['backend'],'h3_join');self.assertTrue(Path(r['path']).is_file())
    def test_media_run_local_assets_no_live_token(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);s=fixture(p)
            season={'series_id':'test','season':1,'episodes':[s], 'canon':{'characters':['Test character'],'facts':['fixture only'],'unresolved':[],'ending':'fixture'}}
            r=media_run({'season':season},p/'season')
            self.assertEqual(len(r['episodes']),1);self.assertTrue(Path(r['archive']).is_file())
            self.assertEqual(inspect_season_zip(r['archive'])['series_id'],'test')
    def test_changed_audio_missing_pixels_bad_coverage_fail(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);s=fixture(p);s['cue_audio_sha256']='changed'
            with self.assertRaises(ValueError):assemble_episode(s,p/'out')
            s['cue_audio_sha256']=s['audio']['sha256'];s['shots'][0]['pixel_checked']=False
            with self.assertRaises(ValueError):assemble_episode(s,p/'out')
            s['shots'][0]['pixel_checked']=True;s['shots'][0]['frames']=23
            with self.assertRaises(ValueError):assemble_episode(s,p/'out')
    def test_captions_exact_text_timing_and_safe_markup(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);s=fixture(p);s['cues'][0]['text']='Different.'
            with self.assertRaises(ValueError):assemble_episode(s,p/'out')
            c={'start':0,'end':1,'text':'{override}','speaker':'lead','actual_audio_checked':True}
            with self.assertRaises(ValueError):caption_file([c],{'lead':'Test'},1,p/'x.ass')
            c['text']='Hello';c['actual_audio_checked']=False
            with self.assertRaises(ValueError):caption_file([c],{'lead':'Test'},1,p/'x.ass')
    def test_license_mixing_and_unlicensed_refusal(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);s=fixture(p);terms=p/'license.txt';terms.write_text('Synthetic fixture only. No real track.')
            asset={**s['audio'],'license':'CC0-1.0','source_url':'https://example.invalid/fixture','license_url':'https://example.invalid/license',
                   'creator':'unit test','title':'synthetic tone','license_checked_at':'2026-10-20','license_terms_path':str(terms),'license_terms_sha256':digest(terms),
                   'commercial_use_verified':True,'sync_use_verified':True,'gain':.05,'start_seconds':0}
            s['soundtrack']=[asset];r=assemble_episode(s,p/'out',size=(180,320));self.assertTrue(Path(r['path']).is_file())
            s['soundtrack'][0]['license']='unknown'
            with self.assertRaises(ValueError):assemble_episode(s,p/'bad')
    def test_h3_model_is_blocked(self):
        with self.assertRaises(RuntimeError):render_h3()
