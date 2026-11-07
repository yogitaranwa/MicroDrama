"""Mechanical detectors on synthetic media: facts only, never semantic verdicts."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from magicdrama.audiofirst.mechanical import (dialogue_free_gaps, episode_report,
                                              freeze_windows, reject_frozen_video,
                                              silence_windows)


def make(path,video_src,audio_expr,seconds=4.0):
    subprocess.run(['ffmpeg','-y','-v','error','-nostdin','-f','lavfi','-i',video_src,
                    '-f','lavfi','-i',audio_expr,'-t',str(seconds),'-pix_fmt','yuv420p',
                    '-c:v','libx264','-c:a','aac','-shortest',str(path)],check=True,capture_output=True)
    return path


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'Existing ffmpeg and ffprobe required')
class MechanicalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();root=Path(cls.tmp.name)
        cls.moving=make(root/'moving.mp4','testsrc2=size=320x240:rate=10','sine=frequency=440')
        cls.frozen=make(root/'frozen.mp4','color=c=red:size=320x240:rate=10','sine=frequency=440')
        cls.silent_open=make(root/'silent.mp4','testsrc2=size=320x240:rate=10',"aevalsrc='if(lt(t,1.5),0,0.5*sin(440*2*PI*t))':d=4")
        cls.quiet_tail=make(root/'quiet.mp4','testsrc2=size=320x240:rate=10',"aevalsrc='if(lt(t,2),0.8*sin(440*2*PI*t),0.005*sin(220*2*PI*t))':d=4")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_static_clip_is_measured_frozen(self):
        self.assertTrue(freeze_windows(self.frozen,min_seconds=2.0))

    def test_moving_clip_has_no_freeze(self):
        self.assertEqual(freeze_windows(self.moving,min_seconds=2.0),[])

    def test_reject_frozen_video(self):
        with self.assertRaises(ValueError):reject_frozen_video(self.frozen)
        reject_frozen_video(self.moving)

    def test_opening_silence_flagged(self):
        kinds=[d['type'] for d in episode_report(self.silent_open)['defects']]
        self.assertIn('opening_silence',kinds)

    def test_tone_has_no_silence(self):
        self.assertEqual(silence_windows(self.moving),[])

    def test_quiet_gap_flagged(self):
        report=episode_report(self.quiet_tail,dialogue_windows=[{'start':0.0,'end':2.0}])
        self.assertIn('bed_level',[d['type'] for d in report['defects']])

    def test_gap_math(self):
        gaps=dialogue_free_gaps(10.0,[{'start':2.0,'end':4.0},{'start':5.0,'end':7.0}],min_gap=.5,pad=.15)
        self.assertEqual([(g['start'],g['end']) for g in gaps],[(0.0,1.85),(4.15,4.85),(7.15,10.0)])


if __name__=='__main__':unittest.main()


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'Existing ffmpeg and ffprobe required')
class AssemblyEnforcementTests(unittest.TestCase):
    """The final assembly path must refuse defective episodes, not report-and-ship."""

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def build(self,make_asset,kind):
        from magicdrama.audiofirst.bridge import accepted_package
        from magicdrama.audiofirst.core import digest
        from magicdrama.audiofirst.production_run import media_run
        from magicdrama.audiofirst.renderplan import compile_render_plan
        from tests.helpers import pilot, audio_fixture, profile, reference_images
        brief,story=pilot();ep,track=audio_fixture(self.root,story['episodes'][0]);story['episodes'][0]=ep
        plan=compile_render_plan(ep,track,profile(),reference_assets=reference_images(self.root,ep))
        media={}
        for job in plan['jobs']:
            path=make_asset(job['id'])
            media[job['id']]={'path':str(path),'sha256':digest(path),'kind':kind,'pixel_checked':True,'input_sha256':job['input_sha256']}
        from tests.helpers import synthetic_media_reviews
        synthetic_media_reviews(media)
        return accepted_package(brief,story,'ep1',track,plan,media),media_run

    def test_frozen_video_episode_is_refused(self):
        def frozen(job_id):
            path=self.root/(job_id+'.mp4')
            subprocess.run(['ffmpeg','-v','error','-nostdin','-y','-f','lavfi','-i','color=c=red:s=144x256:r=24',
                            '-frames:v','72','-c:v','libx264','-pix_fmt','yuv420p',str(path)],check=True,capture_output=True)
            return path
        package,media_run=self.build(frozen,'video')
        with self.assertRaises(ValueError) as ctx:
            media_run(package,self.root/'season-frozen')
        self.assertIn('freeze',str(ctx.exception))
        out=self.root/'season-frozen'
        for _root,_dirs,files in os.walk(out):
            self.assertNotIn('clean.mp4',files);self.assertNotIn('captioned.mp4',files)
        # Conformed per-shot cache clips may remain; the episode deliverables may not.

    def test_still_animatic_mode_still_assembles(self):
        # assemble_episode directly: image shots are intended static pictures,
        # so the freeze class must not fire; continuous tone keeps audio clean.
        from PIL import Image
        from magicdrama.audiofirst.assembly import assemble_episode
        from magicdrama.audiofirst.core import digest
        root=self.root
        subprocess.run(['ffmpeg','-y','-v','error','-nostdin','-f','lavfi','-i','sine=frequency=440',
                        '-t','2.0','-c:a','pcm_s16le',str(root/'master.wav')],check=True,capture_output=True)
        Image.new('RGB',(144,256),(120,90,30)).save(root/'a.png');Image.new('RGB',(144,256),(30,90,120)).save(root/'b.png')
        audio={'path':str(root/'master.wav'),'sha256':digest(root/'master.wav')}
        def shot(name):return {'path':str(root/name),'sha256':digest(root/name),'kind':'image','frames':24,'pixel_checked':True}
        spec={'audio':audio,'audio_checked':True,'cue_audio_sha256':audio['sha256'],'spoken_lines':['One line.'],
              'cues':[{'line_id':'l1','speaker':'A','text':'One line.','start':0.0,'end':1.5,'actual_audio_checked':True}],
              'names':{'A':'A'},'shots':[shot('a.png'),shot('b.png')],'soundtrack':[]}
        result=assemble_episode(spec,root/'episode')
        self.assertTrue(Path(result['path']).is_file())
        self.assertEqual(result['mechanical']['defects'],[])
