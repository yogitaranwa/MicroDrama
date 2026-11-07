import base64
from contextlib import closing
import copy
import datetime as dt
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch

from magicdrama.audiofirst.benchmark import compare_trials
from magicdrama.audiofirst.core import digest
from magicdrama.audiofirst.execution import RunLedger, signature, verify_approval
from magicdrama.audiofirst.live import LiveAdapters
from magicdrama.audiofirst.production_run import media_run


def fixture():
    today=dt.datetime.now(dt.timezone(dt.timedelta(hours=5,minutes=30))).date().isoformat()
    job={'id':'voice1','episode_id':'ep1','provider':'elevenlabs','kind':'voice',
         'request':{'endpoint':'/v1/text-to-dialogue/with-timestamps','body':{'model_id':'eleven_v3','inputs':[{'text':'Wait.','voice_id':'test-voice'}]}},
         'quote':{'amount':5,'unit':'characters','verified_on':today,'source_url':'https://example.test/fixture',
                  'billing':{'unit':'USD','max_amount':'0.10','rate_verified':True}}}
    manifest={'run_id':'r1','batch_id':'b1','jobs':[job]}
    token={'run_id':'r1','batch_id':'b1','expires_at':(dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=1)).isoformat(),
           'approval_reference':'synthetic-test-only','manifest_sha256':signature(manifest),'job_counts':{'elevenlabs:voice':1},
           'totals':{'elevenlabs:characters':'5'},'billing_limits':{'voice1':job['quote']['billing']},
           'batch_billing_limits':{'USD':'0.10'},
           'key_identities':{'magichour':'image-video-key:restricted','elevenlabs':'voice-key:approved'}}
    return manifest,token


class ExecutionTests(unittest.TestCase):
    def test_music_needs_separate_approval_and_duration_based_quote(self):
        manifest,token=fixture();j=manifest['jobs'][0]
        j.update(provider='magichour',kind='music',request={'endpoint':'/v1/ai-music-generator','body':{'duration':56,'style':{'prompt':'Original quiet orchestral suspense.','instrumental':True}}})
        j['quote']={**j['quote'],'amount':56,'unit':'credits'};j['quote'].pop('billing')
        token.update(manifest_sha256=signature(manifest),job_counts={'magichour:music':1},totals={'magichour:credits':'56'},billing_limits={})
        with self.assertRaisesRegex(ValueError,'separate explicit approval'):verify_approval(manifest,token,True)
        token['magichour_music_approved']=True;token['key_identities']['magichour']='image-video-music-key:approved'
        verify_approval(manifest,token,True)
        j['request']['body']['duration']=57;token['manifest_sha256']=signature(manifest)
        with self.assertRaisesRegex(ValueError,'quote must match requested seconds'):verify_approval(manifest,token,True)

    def test_talking_photo_requires_supported_settings_and_conservative_cost(self):
        from magicdrama.audiofirst.live import validate_job
        job={'provider':'magichour','kind':'video','quote':{'amount':72},
             'request':{'endpoint':'/v1/ai-talking-photo','body':{'start_seconds':0,'end_seconds':3,'resolution':'480p',
                        'style':{'generation_mode':'prompted'},'assets':{'image_file_path':'api-assets/image','audio_file_path':'api-assets/audio'}}},
             'image_evidence':{'plan':{'tasks':[{'id':'frame'}]},'accepted':{}}}
        with patch('magicdrama.audiofirst.images.require_rendered_images') as checked:
            validate_job(job);checked.assert_called_once()
        job['quote']['amount']=20
        with self.assertRaisesRegex(ValueError,'quote must cover'):validate_job(job)
        job['quote']['amount']=72;job['request']['body']['style']['generation_mode']='realistic'
        with self.assertRaisesRegex(ValueError,'explicit prompted'):validate_job(job)

    def mh_voice(self):
        manifest,token=fixture();j=manifest['jobs'][0]
        j.update(provider='magichour',request={'endpoint':'/v1/ai-voice-generator','body':{'style':{'prompt':'Wait.','voice_name':'Harry Potter'}}})
        j['quote']={**j['quote'],'amount':1,'unit':'credits'};j['quote'].pop('billing')
        token.update(manifest_sha256=signature(manifest),job_counts={'magichour:voice':1},totals={'magichour:credits':'1'},billing_limits={})
        return manifest,token

    def test_magichour_voice_needs_separate_approval_and_exact_quote(self):
        manifest,token=self.mh_voice()
        with self.assertRaisesRegex(ValueError,'separate explicit approval'):verify_approval(manifest,token,True)
        token['magichour_voice_approved']=True
        token['key_identities']['magichour']='image-video-voice-key:approved'
        verify_approval(manifest,token,True)
        manifest['jobs'][0]['request']['body']['style']['prompt']='A longer line with a different price.'
        token['manifest_sha256']=signature(manifest)
        with self.assertRaisesRegex(ValueError,'exact submitted characters'):verify_approval(manifest,token,True)

    def mh_clone(self, source='project_generated_audio', sample='api-assets/abc/sample.mp3', text='Funny. Your office closed at six.'):
        manifest,token=self.mh_voice()
        j=manifest['jobs'][0]
        j['request']={'endpoint':'/v1/ai-voice-cloner','body':{'assets':{'audio_file_path':sample},'style':{'prompt':text}}}
        j['quote']={**j['quote'],'amount':-(-len(text)//10)}
        if source:j['voice_source']=source
        token.update(manifest_sha256=signature(manifest),totals={'magichour:credits':str(j['quote']['amount'])},magichour_voice_approved=True)
        token['key_identities']['magichour']='image-video-voice-key:approved'
        return manifest,token

    def test_voice_cloning_is_allowed_only_from_project_audio_with_exact_pricing(self):
        manifest,token=self.mh_clone()
        verify_approval(manifest,token,True)
        manifest,token=self.mh_clone(source=None)
        with self.assertRaisesRegex(ValueError,'only from project-generated audio'):verify_approval(manifest,token,True)
        manifest,token=self.mh_clone(sample='https://example.com/real-person.mp3')
        with self.assertRaisesRegex(ValueError,'Invalid Magic Hour voice clone request'):verify_approval(manifest,token,True)
        manifest,token=self.mh_clone()
        manifest['jobs'][0]['request']['body']['style']['prompt']='A much longer line than the one that was priced.'
        token['manifest_sha256']=signature(manifest)
        with self.assertRaisesRegex(ValueError,'exact submitted characters'):verify_approval(manifest,token,True)

    def test_voice_cloning_still_needs_the_separate_voice_approval(self):
        manifest,token=self.mh_clone()
        token['magichour_voice_approved']=False
        with self.assertRaisesRegex(ValueError,'separate explicit approval'):verify_approval(manifest,token,True)

    def test_magichour_voice_download_and_resume_use_audio_project(self):
        manifest,token=self.mh_voice();token['magichour_voice_approved']=True
        token['key_identities']['magichour']='image-video-voice-key:approved'
        created=Mock(status_code=200);created.json.return_value={'id':'audio123','credits_charged':1}
        detail=Mock(status_code=200);detail.json.return_value={'status':'complete','credits_charged':1,'downloads':[{'url':'https://videos.magichour.ai/audio.mp3'}]}
        downloaded=Mock(status_code=200,content=b'fixture-audio');http=Mock();http.post.return_value=created;http.get.side_effect=[detail,downloaded]
        with tempfile.TemporaryDirectory() as tmp, closing(RunLedger(Path(tmp)/'ledger.sqlite')) as ledger:
            adapter=LiveAdapters(manifest,token,ledger,{'magichour':'fixture'},True,http)
            output=Path(tmp)/'voice.mp3';adapter.execute('voice1',output);adapter.execute('voice1',output)
            self.assertEqual(http.post.call_count,1)
            self.assertIn('/v1/audio-projects/audio123',http.get.call_args_list[0].args[0])
            self.assertEqual(output.read_bytes(),b'fixture-audio')

    def test_custom_batch_cap_includes_prior_reservations(self):
        manifest,token=self.mh_voice();token['magichour_voice_approved']=True
        token['key_identities']['magichour']='image-video-voice-key:approved';token['magichour_credit_cap']=1
        with tempfile.TemporaryDirectory() as tmp, closing(RunLedger(Path(tmp)/'ledger.sqlite')) as ledger:
            ledger.reserve(manifest,token,True)
            manifest['run_id']='r2';token.update(run_id='r2',manifest_sha256=signature(manifest))
            with self.assertRaisesRegex(ValueError,'combined episode/batch cap'):ledger.reserve(manifest,token,True)

    def test_provider_overcharge_is_retained_and_blocks_further_execution(self):
        manifest,token=self.mh_voice();token['magichour_voice_approved']=True
        token['key_identities']['magichour']='image-video-voice-key:approved'
        created=Mock(status_code=200);created.json.return_value={'id':'audio123','credits_charged':1}
        detail=Mock(status_code=200);detail.json.return_value={'status':'complete','credits_charged':2,'downloads':[]}
        http=Mock();http.post.return_value=created;http.get.return_value=detail
        with tempfile.TemporaryDirectory() as tmp, closing(RunLedger(Path(tmp)/'ledger.sqlite')) as ledger:
            adapter=LiveAdapters(manifest,token,ledger,{'magichour':'fixture'},True,http)
            with self.assertRaisesRegex(RuntimeError,'above quote'):adapter.execute('voice1',Path(tmp)/'voice.mp3')
            self.assertEqual(ledger.get('r1','voice1')['state'],'overcharge')
            self.assertEqual(ledger.get('r1','voice1')['actual'],'2')
            with self.assertRaisesRegex(RuntimeError,'Prior provider overcharge'):adapter.execute('voice1',Path(tmp)/'voice.mp3')
            self.assertEqual(http.post.call_count,1)

    def test_explicit_larger_episode_cap_preserves_batch_limit(self):
        manifest,token=fixture();j=manifest['jobs'][0]
        j.update(provider='magichour',kind='video')
        j['quote']={**j['quote'],'amount':2000,'unit':'credits'};j['quote'].pop('billing')
        token.update(manifest_sha256=signature(manifest),job_counts={'magichour:video':1},totals={'magichour:credits':'2000'},billing_limits={},magichour_credit_cap=5000)
        with tempfile.TemporaryDirectory() as tmp, closing(RunLedger(Path(tmp)/'ledger.sqlite')) as ledger:
            ledger.reserve(manifest,token,True)
            manifest['run_id']='r2';token.update(run_id='r2',manifest_sha256=signature(manifest))
            with self.assertRaisesRegex(ValueError,'combined episode/batch cap'):ledger.reserve(manifest,token,True)
            token['magichour_episode_credit_cap']=5000;ledger.reserve(manifest,token,True)
            manifest['run_id']='r3';token.update(run_id='r3',manifest_sha256=signature(manifest))
            with self.assertRaisesRegex(ValueError,'combined episode/batch cap'):ledger.reserve(manifest,token,True)

    def test_upload_only_phase_resumes_without_retransmitting(self):
        from magicdrama.audiofirst.bridge import upload_inputs
        manifest,token=fixture();manifest['jobs']=[]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'reference.png';path.write_bytes(b'synthetic-upload-fixture')
            asset={'path':str(path),'sha256':digest(path),'kind':'image'}
            manifest['uploads']=[{'sha256':asset['sha256'],'kind':'image'}]
            token.update(manifest_sha256=signature(manifest),job_counts={},totals={},billing_limits={})
            http=Mock();http.post.return_value.status_code=200
            http.post.return_value.json.return_value={'items':[{'upload_url':'https://storage.googleapis.com/fixture','file_path':'api-assets/fixture/reference'}]}
            http.put.return_value.status_code=200
            first=upload_inputs(manifest,token,{'frame-test':asset},Path(tmp)/'ledger.sqlite',Path(tmp)/'uploads',{'magichour':'fixture'},True,http)
            second=upload_inputs(manifest,token,{'frame-test':asset},Path(tmp)/'ledger.sqlite',Path(tmp)/'uploads',{'magichour':'fixture'},True,http)
            self.assertEqual(first,second);self.assertEqual(http.post.call_count,1);self.assertEqual(http.put.call_count,1)

    def test_dependencies_rejected_before_reservation(self):
        manifest,token=fixture();manifest['jobs'][0]['depends_on']=['missing'];token['manifest_sha256']=signature(manifest)
        with self.assertRaisesRegex(ValueError,'dependency'):verify_approval(manifest,token,True)

    def test_uncertain_paid_submission_is_not_repeated(self):
        manifest,token=fixture();http=Mock();http.post.side_effect=TimeoutError
        with tempfile.TemporaryDirectory() as tmp, closing(RunLedger(Path(tmp)/'ledger.sqlite')) as ledger:
            adapter=LiveAdapters(manifest,token,ledger,{'elevenlabs':'fixture'},True,http)
            with self.assertRaises(TimeoutError):adapter.execute('voice1',Path(tmp)/'voice.mp3')
            with self.assertRaisesRegex(RuntimeError,'never auto-resubmit'):adapter.execute('voice1',Path(tmp)/'voice.mp3')
            self.assertEqual(http.post.call_count,1)

    def test_completed_submission_reuses_bytes(self):
        manifest,token=fixture();response=Mock(status_code=200);response.json.return_value={'audio_base64':base64.b64encode(b'synthetic-audio').decode()}
        http=Mock();http.post.return_value=response
        with tempfile.TemporaryDirectory() as tmp, closing(RunLedger(Path(tmp)/'ledger.sqlite')) as ledger:
            adapter=LiveAdapters(manifest,token,ledger,{'elevenlabs':'fixture'},True,http)
            output=Path(tmp)/'voice.mp3';first=adapter.execute('voice1',output);second=adapter.execute('voice1',output)
            self.assertEqual(first['sha256'],second['sha256']);self.assertEqual(http.post.call_count,1)

    def test_crash_after_download_reconciles_without_resubmission(self):
        manifest,token=fixture();data={'audio_base64':base64.b64encode(b'fixture').decode()}
        with tempfile.TemporaryDirectory() as tmp, closing(RunLedger(Path(tmp)/'ledger.sqlite')) as ledger:
            adapter=LiveAdapters(manifest,token,ledger,{'elevenlabs':'fixture'},True,Mock())
            ledger.transition('r1','voice1','reserved','submitting');ledger.transition('r1','voice1','submitting','submitted',data)
            output=Path(tmp)/'voice.mp3';output.write_bytes(b'fixture')
            self.assertEqual(adapter.execute('voice1',output)['sha256'],digest(output))
            adapter.http.post.assert_not_called()

    def test_native_audio_rejected_before_provider_instantiation(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'Native audio'):
                media_run({'audio_mode':'native','manifest':{}},Path(tmp)/'out',enabled=True)
            self.assertFalse((Path(tmp)/'out-state').exists())

    def test_changed_manifest_cannot_reuse_old_approval(self):
        manifest,token=fixture();manifest['jobs'][0]['request']['body']['inputs'][0]['text']='Changed'
        with self.assertRaisesRegex(ValueError,'Exact approved'):verify_approval(manifest,token,True)


class BenchmarkTests(unittest.TestCase):
    def trial(self,name,**extra):
        return {'name':name,'input_sha256':'a'*64,'accepted_seconds':10,'generated_seconds':20,'total_cost':{'amount':2,'unit':'USD'},
                'critical_errors':[],'viewer_scores':[],'elapsed_seconds':60,'manual_minutes':3,'rerolls':1,**extra}

    def test_cost_counts_rejects_and_no_invented_quality_winner(self):
        report=compare_trials([self.trial('baseline'),self.trial('candidate',accepted_seconds=0)])
        self.assertEqual(report['trials'][0]['cost_per_accepted_second'],.2)
        self.assertIsNone(report['trials'][1]['cost_per_accepted_second'])
        self.assertIsNone(report['automatic_winner'])

    def test_unequal_inputs_cannot_claim_controlled_comparison(self):
        with self.assertRaisesRegex(ValueError,'same script'):
            compare_trials([self.trial('a'),self.trial('b',input_sha256='b'*64)])


if __name__=='__main__':unittest.main()
