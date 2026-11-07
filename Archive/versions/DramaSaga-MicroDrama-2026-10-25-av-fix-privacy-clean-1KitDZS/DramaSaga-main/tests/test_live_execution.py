import base64
import copy
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from magicdrama.audiofirst.execution import signature,verify_approval,RunLedger
from magicdrama.audiofirst.live import LiveAdapters,download_url
from magicdrama.audiofirst.local_writer import LocalWriter
from tests.test_audiofirst import brief
from tests.test_audiofirst_story import story


def fixture(kind='image'):
    day=dt.datetime.now(dt.timezone(dt.timedelta(hours=5,minutes=30))).date().isoformat()
    j={'id':'job1','episode_id':'ep1','provider':'magichour','kind':'image',
       'request':{'endpoint':'/v1/ai-image-generator','body':{'model':'nano-banana-2.1','resolution':'1k','image_count':1,'style':{'prompt':'test fixture'}}},
       'quote':{'amount':'50','unit':'credits','verified_on':day,'source_url':'https://docs.magichour.ai/api-reference/models'}}
    if kind=='voice':
        j.update(provider='elevenlabs',kind='voice',request={'endpoint':'/v1/text-to-dialogue/with-timestamps','body':{'model_id':'eleven_v3','inputs':[{'voice_id':'fixture','text':'[sad] Hello.'}]}})
        j['quote'].update(amount='12',unit='characters',billing={'unit':'credits','max_amount':'12','rate_verified':True})
    m={'run_id':'run1','batch_id':'batch1','jobs':[j]}
    return m,token(m)


def token(m):
    totals={};counts={}
    for j in m['jobs']:
        k=j['provider']+':'+j['quote']['unit'];totals[k]=str(int(totals.get(k,'0'))+int(j['quote']['amount']))
        k=j['provider']+':'+j['kind'];counts[k]=counts.get(k,0)+1
    return {'run_id':m['run_id'],'batch_id':m['batch_id'],'manifest_sha256':signature(m),'approval_reference':'TEST_FIXTURE_NOT_REAL_APPROVAL',
            'expires_at':(dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=1)).isoformat(),
            'job_counts':counts,'totals':totals,'billing_limits':{j['id']:j['quote']['billing'] for j in m['jobs'] if j['provider']=='elevenlabs'},
            'key_identities':{'magichour':'magichour:image-video-only','elevenlabs':'elevenlabs:voice-only'}}

class Response:
    status_code=200
    def __init__(self,data=None,content=b'fixture image bytes'):self.data=data;self.content=content
    def raise_for_status(self):pass
    def json(self):return self.data

class HTTP:
    def __init__(self,charge=50,fail=False,pending=False):self.posts=[];self.gets=[];self.charge=charge;self.fail=fail;self.pending=pending
    def post(self,url,**kwargs):
        self.posts.append(url)
        if self.fail:raise TimeoutError('fixture uncertain submission')
        if 'elevenlabs' in url:return Response({'audio_base64':base64.b64encode(b'fixture mp3').decode()})
        return Response({'id':'abc123','credits_charged':self.charge})
    def get(self,url,**kwargs):
        self.gets.append(url)
        if 'projects' in url:return Response({'id':'abc123','status':'rendering' if self.pending else 'complete','credits_charged':self.charge,'downloads':[{'url':'https://videos.magichour.ai/out.png'}]})
        return Response()

class LiveTests(unittest.TestCase):
    def test_disabled_hash_expiry_count_key_refusal(self):
        m,t=fixture()
        with self.assertRaises(RuntimeError):verify_approval(m,t)
        for field,value in [('manifest_sha256','bad'),('job_counts',{}),('totals',{}),('key_identities',{}),('approval_reference',''),('expires_at','2000-01-01T00:00:00+00:00')]:
            x=copy.deepcopy(t);x[field]=value
            with self.assertRaises((ValueError,RuntimeError)):verify_approval(m,x,True)
    def test_no_calls_without_token(self):
        m,t=fixture();h=HTTP()
        with tempfile.TemporaryDirectory() as d:
            l=RunLedger(Path(d)/'ledger');
            with self.assertRaises(RuntimeError):LiveAdapters(m,t,l,{'magichour':'fixture'},http=h)
            self.assertEqual(h.posts,[]);l.close()
    def test_complete_resume_no_resend(self):
        m,t=fixture();h=HTTP()
        with tempfile.TemporaryDirectory() as d:
            l=RunLedger(Path(d)/'ledger');a=LiveAdapters(m,t,l,{'magichour':'fixture'},True,h)
            r=a.execute('job1',Path(d)/'image.png');self.assertTrue(Path(r['path']).exists())
            self.assertEqual(a.execute('job1',Path(d)/'image.png'),r);self.assertEqual(len(h.posts),1);l.close()
    def test_timeout_no_auto_repeat(self):
        m,t=fixture();h=HTTP(fail=True)
        with tempfile.TemporaryDirectory() as d:
            l=RunLedger(Path(d)/'ledger');a=LiveAdapters(m,t,l,{'magichour':'fixture'},True,h)
            with self.assertRaises(TimeoutError):a.execute('job1',Path(d)/'x')
            with self.assertRaises(RuntimeError):a.execute('job1',Path(d)/'x')
            self.assertEqual(len(h.posts),1);self.assertEqual(l.get('run1','job1')['state'],'unknown');l.close()
    def test_pending_resumes_same_provider_id(self):
        m,t=fixture();h=HTTP(pending=True)
        with tempfile.TemporaryDirectory() as d:
            l=RunLedger(Path(d)/'ledger');a=LiveAdapters(m,t,l,{'magichour':'fixture'},True,h,sleep=lambda x:None)
            with self.assertRaises(TimeoutError):a.execute('job1',Path(d)/'x',polls=1)
            h.pending=False;a.execute('job1',Path(d)/'x');self.assertEqual(len(h.posts),1);l.close()
    def test_provider_overcharge_halts_batch(self):
        m,t=fixture();h=HTTP(charge=51)
        with tempfile.TemporaryDirectory() as d:
            l=RunLedger(Path(d)/'ledger');a=LiveAdapters(m,t,l,{'magichour':'fixture'},True,h)
            with self.assertRaises(RuntimeError):a.execute('job1',Path(d)/'x')
            self.assertTrue(l.halt_overcharge('batch1'));l.close()
    def test_prior_reservations_count_toward_episode_cap(self):
        m,t=fixture()
        with tempfile.TemporaryDirectory() as d:
            l=RunLedger(Path(d)/'ledger');l.reserve(m,t,True)
            n=copy.deepcopy(m);n['run_id']='run2';n['image_cap_per_episode']=60;n['jobs']=[dict(copy.deepcopy(m['jobs'][0]),id='j'+str(i)) for i in range(60)]
            with self.assertRaises(ValueError):l.reserve(n,token(n),True)
            l.close()
    def test_changed_payload_cannot_resume(self):
        m,t=fixture()
        with tempfile.TemporaryDirectory() as d:
            l=RunLedger(Path(d)/'ledger');l.reserve(m,t,True);m['jobs'][0]['request']['body']['style']['prompt']='changed'
            with self.assertRaises(ValueError):l.reserve(m,token(m),True)
            l.close()
    def test_voice_count_and_credit_approval(self):
        m,t=fixture('voice');verify_approval(m,t,True)
        m['jobs'][0]['request']['body']['inputs'][0]['text']+='!'
        with self.assertRaises(ValueError):verify_approval(m,token(m),True)
    def test_voice_mock_decoding(self):
        m,t=fixture('voice');h=HTTP()
        with tempfile.TemporaryDirectory() as d:
            l=RunLedger(Path(d)/'ledger');a=LiveAdapters(m,t,l,{'elevenlabs':'fixture'},True,h)
            r=a.execute('job1',Path(d)/'voice.mp3');self.assertEqual(Path(r['path']).read_bytes(),b'fixture mp3');l.close()
    def test_download_host_and_wrong_model(self):
        with self.assertRaises(ValueError):download_url('http://127.0.0.1/private')
        m,t=fixture();m['jobs'][0]['request']['body']['model']='other'
        with tempfile.TemporaryDirectory() as d:
            l=RunLedger(Path(d)/'ledger')
            with self.assertRaises(ValueError):LiveAdapters(m,token(m),l,{},True,HTTP())
            l.close()
    def test_local_writer_only_existing_model(self):
        class LocalHTTP:
            def get(self,*a,**k):return Response({'models':[{'name':'fixture'}]})
            def post(self,*a,**k):return Response({'message':{'content':json.dumps(story())}})
        w=LocalWriter('fixture',LocalHTTP());self.assertTrue(w.available())
        from magicdrama.audiofirst.core import writing_request
        self.assertIn('MODEL_DRAFT',w(writing_request(brief()))['writer_status'])
        with self.assertRaises(RuntimeError):LocalWriter('absent',LocalHTTP())(writing_request(brief()))

class ExtraAdapterTests(unittest.TestCase):
    def test_upload_allowlisted_bytes_and_put(self):
        class UploadHTTP(HTTP):
            def post(self,url,**kwargs):return Response({'items':[{'upload_url':'https://videos.magichour.ai/api-assets/id/x.png?sig=fixture','file_path':'api-assets/id/x.png'}]})
            def put(self,url,**kwargs):self.uploaded=kwargs['data'].read();return Response()
        from magicdrama.audiofirst.core import digest
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.png';p.write_bytes(b'fixture image');m,t=fixture();m['uploads']=[{'sha256':digest(p),'kind':'image'}]
            h=UploadHTTP();l=RunLedger(Path(d)/'ledger');a=LiveAdapters(m,token(m),l,{'magichour':'fixture'},True,h)
            self.assertEqual(a.upload(p,'image'),'api-assets/id/x.png');self.assertEqual(h.uploaded,b'fixture image')
            p.write_bytes(b'changed')
            with self.assertRaises(ValueError):a.upload(p,'image')
            l.close()
    def test_video_endpoint_needs_real_reference_evidence(self):
        from magicdrama.audiofirst.core import digest
        from magicdrama.audiofirst.live import validate_job
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.png';p.write_bytes(b'fixture')
            m,t=fixture();j=m['jobs'][0];j.update(kind='video',request={'endpoint':'/v1/audio-to-video','body':{'assets':{'audio_file_path':'api-assets/id/a.wav','image_file_path':'api-assets/id/x.png'},'start_seconds':0,'end_seconds':1,'resolution':'720p','style':{'prompt':'fixture'}}})
            with self.assertRaises(ValueError):validate_job(j)
            plan={'uploaded_local_references':{},'tasks':[{'id':'frame'}],'plan_sha256':'fixture-plan'}
            j['image_evidence']={'plan':plan,'accepted':{'frame':{'path':str(p),'sha256':digest(p),'plan_sha256':'fixture-plan','reviewer':'test','reviewed_at':'2026-10-20',
                'checks':{k:True for k in ('identity','wardrobe','action','expression','prop_orientation','layout')}}}}
            l=RunLedger(Path(d)/'ledger');h=HTTP();a=LiveAdapters(m,token(m),l,{'magichour':'fixture'},True,h)
            r=a.execute('job1',Path(d)/'video.mp4');self.assertTrue(Path(r['path']).exists());self.assertIn('video-projects',h.gets[0]);l.close()
    def test_duplicate_and_global_batch_limit(self):
        m,t=fixture();m['jobs'].append(copy.deepcopy(m['jobs'][0]))
        with self.assertRaises(ValueError):verify_approval(m,token(m),True)
        m,t=fixture();m['image_cap_per_episode']=60;m['jobs']=[dict(copy.deepcopy(m['jobs'][0]),id='j'+str(i),episode_id='ep'+str(i//60)) for i in range(601)]
        with self.assertRaises(ValueError):verify_approval(m,token(m),True)
