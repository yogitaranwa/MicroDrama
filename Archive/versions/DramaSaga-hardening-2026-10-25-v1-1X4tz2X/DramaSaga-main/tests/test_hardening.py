import copy
import json
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import Mock, patch
from tests.test_execution import fixture
from magicdrama.audiofirst.execution import RunLedger, signature
from magicdrama.audiofirst.live import LiveAdapters
from magicdrama.audiofirst import mechanical
from magicdrama import config

class HardeningTests(unittest.TestCase):
    def test_batch_identity_cannot_change_on_resume(self):
        m,t=fixture()
        with tempfile.TemporaryDirectory() as tmp, closing(RunLedger(Path(tmp)/'l.db')) as ledger:
            ledger.reserve(m,t,True);m['batch_id']='b2';t.update(batch_id='b2',manifest_sha256=signature(m))
            with self.assertRaisesRegex(ValueError,'changed'):ledger.reserve(m,t,True)
    def test_cumulative_voice_ceiling_counts_unknown_jobs(self):
        m,t=fixture()
        with tempfile.TemporaryDirectory() as tmp, closing(RunLedger(Path(tmp)/'l.db')) as ledger:
            ledger.reserve(m,t,True);ledger.transition('r1','voice1','reserved','submitting');ledger.transition('r1','voice1','submitting','unknown')
            m['run_id']='r2';t.update(run_id='r2',manifest_sha256=signature(m))
            with self.assertRaisesRegex(ValueError,'ceiling'):ledger.reserve(m,t,True)
            self.assertIsNone(ledger.get('r2','voice1'))
    def test_missing_batch_voice_ceiling_blocks(self):
        m,t=fixture();t.pop('batch_billing_limits')
        with tempfile.TemporaryDirectory() as tmp, closing(RunLedger(Path(tmp)/'l.db')) as ledger:
            with self.assertRaisesRegex(ValueError,'ceiling'):ledger.reserve(m,t,True)
    def test_illegal_reset_to_reserved_refused(self):
        m,t=fixture()
        with tempfile.TemporaryDirectory() as tmp, closing(RunLedger(Path(tmp)/'l.db')) as ledger:
            ledger.reserve(m,t,True)
            with self.assertRaisesRegex(ValueError,'Illegal'):ledger.transition('r1','voice1','reserved','complete')
    def test_dependencies_checked_at_adapter_boundary(self):
        m,t=fixture();j=copy.deepcopy(m['jobs'][0]);j['id']='voice2';j['depends_on']=['voice1'];m['jobs'].append(j)
        t.update(manifest_sha256=signature(m),job_counts={'elevenlabs:voice':2},totals={'elevenlabs:characters':'10'},billing_limits={x['id']:x['quote']['billing'] for x in m['jobs']},batch_billing_limits={'USD':'.20'})
        http=Mock()
        with tempfile.TemporaryDirectory() as tmp, closing(RunLedger(Path(tmp)/'l.db')) as ledger:
            adapter=LiveAdapters(m,t,ledger,{'elevenlabs':'test'},True,http)
            with self.assertRaisesRegex(RuntimeError,'Dependency'):adapter.execute('voice2',Path(tmp)/'voice.mp3')
            http.post.assert_not_called()
    def test_empty_voice_preserves_result_and_no_resubmit(self):
        m,t=fixture();http=Mock();r=http.post.return_value;r.status_code=200;r.json.return_value={'audio_base64':''}
        with tempfile.TemporaryDirectory() as tmp, closing(RunLedger(Path(tmp)/'l.db')) as ledger:
            adapter=LiveAdapters(m,t,ledger,{'elevenlabs':'test'},True,http)
            for _ in range(2):
                with self.assertRaisesRegex(ValueError,'Empty'):adapter.execute('voice1',Path(tmp)/'out.mp3')
            self.assertEqual(http.post.call_count,1);self.assertEqual(ledger.get('r1','voice1')['state'],'submitted')
    def test_legacy_post_disabled_without_network(self):
        from magicdrama.clients.magichour import mh_post
        with patch.object(config,'DRY_RUN',False), patch('requests.post') as post:
            with self.assertRaisesRegex(RuntimeError,'retired'):mh_post('/v1/image-to-video',{})
            post.assert_not_called()
    def test_legacy_assembly_disabled(self):
        from magicdrama.stages.assembly import assemble_episode
        with patch.object(config,'DRY_RUN',False):
            with self.assertRaisesRegex(RuntimeError,'retired'):assemble_episode(None,None,{})
    def test_legacy_governor_disabled(self):
        from magicdrama.governor import Spend
        with patch.object(config,'DRY_RUN',False):
            with self.assertRaisesRegex(RuntimeError,'retired'):Spend(None).spend('test',1,Mock())
    def test_detector_failure_is_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'bad.mp4';path.write_bytes(b'bad')
            with self.assertRaises(Exception):mechanical.freeze_windows(path)

if __name__=='__main__':unittest.main()

class MediaReviewTests(unittest.TestCase):
    def test_bare_pixel_checked_is_not_review(self):
        from magicdrama.audiofirst.media_review import require_media_review
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'v';path.write_bytes(b'fixture')
            with self.assertRaisesRegex(ValueError,'stale'):require_media_review({'path':str(path),'pixel_checked':True},'input')
    def test_camera_or_speech_failure_blocks(self):
        from magicdrama.audiofirst.media_review import require_media_review
        from tests.helpers import synthetic_media_reviews
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'v';path.write_bytes(b'fixture')
            asset={'path':str(path),'input_sha256':'input'};synthetic_media_reviews({'v':asset})
            require_media_review(asset,'input')
            for check in ('camera','eyelines','speech_ownership'):
                asset['review']['checks'][check]=False
                with self.assertRaisesRegex(ValueError,'incomplete'):require_media_review(asset,'input')
                asset['review']['checks'][check]=True
    def test_review_bound_to_shot_input_version(self):
        from magicdrama.audiofirst.media_review import require_media_review
        from tests.helpers import synthetic_media_reviews
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'v';path.write_bytes(b'fixture');asset={'path':str(path),'input_sha256':'input'}
            synthetic_media_reviews({'v':asset})
            with self.assertRaisesRegex(ValueError,'stale'):require_media_review(asset,'changed-script-or-camera')

class SignalEdgeTests(unittest.TestCase):
    def test_black_missing_audio_and_full_silence(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);black=root/'black.mp4'
            subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','color=black:s=144x256:r=10:d=3','-c:v','libx264',str(black)],check=True)
            kinds={d['type'] for d in mechanical.episode_report(black)['defects']}
            self.assertIn('black_frame',kinds);self.assertIn('missing_audio',kinds)
            silent=root/'silent.mp4'
            subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','testsrc2=s=144x256:r=10:d=3','-f','lavfi','-i','anullsrc=r=44100:cl=stereo','-t','3','-c:v','libx264','-c:a','aac',str(silent)],check=True)
            self.assertIn('opening_silence',{d['type'] for d in mechanical.episode_report(silent)['defects']})
