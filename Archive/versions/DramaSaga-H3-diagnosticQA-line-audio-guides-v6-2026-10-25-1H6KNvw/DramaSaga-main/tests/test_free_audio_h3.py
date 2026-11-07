import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
import wave
from magicdrama.audiofirst.free_audio import CommonsAudio,metadata_candidate
from magicdrama.audiofirst.h3_local import compile_workflow,runtime_preflight,submit_local
from magicdrama.audiofirst.core import digest


def page(license='CC0'):
    return {'pageid':1,'title':'File:Fixture.wav','imageinfo':[{'url':'https://upload.wikimedia.org/fixture.wav','descriptionurl':'https://commons.wikimedia.org/wiki/File:Fixture.wav',
        'mime':'audio/wav','size':32044,'extmetadata':{'LicenseUrl':{'value':'https://creativecommons.org/publicdomain/zero/1.0/'},
        'LicenseShortName':{'value':license},'Artist':{'value':'Fixture author'},'ImageDescription':{'value':'Door sound'}}}]}

class Response:
    status_code=200
    def __init__(self,data=None,content=b'',text='CC0 1.0 license fixture'):self.data=data;self.content=content;self.text=text
    def raise_for_status(self):pass
    def json(self):return self.data
    def iter_content(self,n):yield self.content
    def close(self):pass

class FreeAudioTests(unittest.TestCase):
    def test_metadata_combinations_reject_nonfree_unknown_restrictions(self):
        self.assertIsNotNone(metadata_candidate(page()))
        for license in ('CC BY-SA 4.0','CC BY-NC 4.0','Public domain','unknown',''):
            self.assertIsNone(metadata_candidate(page(license)))
        mutations=[('url','https://evil.invalid/a.wav'),('mime','video/webm'),('descriptionurl','http://commons.wikimedia.org/a')]
        for k,v in mutations:
            p=page();p['imageinfo'][0][k]=v;self.assertIsNone(metadata_candidate(p))
        p=page();p['imageinfo'][0]['extmetadata']['Restrictions']={'value':'trademark restriction'};self.assertIsNone(metadata_candidate(p))
    def test_search_download_decode_license_and_attribution(self):
        b=io.BytesIO()
        with wave.open(b,'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(b'\0\0'*16000)
        raw=b.getvalue();p=page();p['imageinfo'][0]['size']=len(raw)
        class HTTP:
            def get(self,url,**kw):
                if 'api.php' in url:return Response({'query':{'pages':{'1':p}}})
                if 'creativecommons' in url:return Response()
                return Response(content=raw)
        client=CommonsAudio(HTTP())
        with tempfile.TemporaryDirectory() as d:
            r=client.choose_and_download('door',Path(d)/'asset');self.assertTrue(Path(r['path']).exists())
            self.assertIn('Fixture author',r['attribution']);self.assertEqual(r['license'],'CC0-1.0')
            self.assertFalse((Path(d)/'asset/source.pending').exists())
    def test_changed_metadata_and_empty_results(self):
        class HTTP:
            def get(self,url,**kw):return Response({'query':{'pages':{}}})
        c=CommonsAudio(HTTP())
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):c.choose_and_download('door',Path(d)/'x')
        with self.assertRaises(ValueError):c.search('x',21)


def graph():
    return {n:{'class_type':k,'inputs':{}} for n,k in [('positive','CLIPTextEncode'),('latent','EmptyLatentImage'),('avae','VAELoader'),('vvae','VAELoader'),('sample','KSampler')]}

def bindings():return {'positive':'positive','video_latent':'latent','audio_vae':'avae','video_vae':'vvae','sampler':'sample'}

def clip():return {'seconds':1,'audio_asset':'voice.wav','pins':[{'seconds':0,'asset':'start.png'}]}

class H3LocalTests(unittest.TestCase):
    def test_fixed_audio_zero_mask_and_pins(self):
        g=graph();r=compile_workflow(g,bindings(),clip());out=r['workflow']
        self.assertEqual(out['md_mask']['inputs']['value'],0)
        self.assertEqual(out['sample']['inputs']['latent_image'],['md_av',0]);self.assertEqual(out['md_pin0']['inputs']['frame_idx'],0)
        self.assertEqual(r['frames']%17,5);self.assertNotIn('md_av',g)
    def test_pin_can_bind_source_supported_guide_audio(self):
        c=clip();c['pins']=[{'seconds':0,'asset':'start.png','audio_asset':'line-start.wav'}]
        r=compile_workflow(graph(),bindings(),c);out=r['workflow']
        self.assertEqual(out['md_pin0']['inputs']['audio'],['md_pin_audio0',0])
        self.assertEqual(out['md_pin0']['inputs']['audio_vae'],['avae',0])
        self.assertEqual(out['md_pin_audio0']['inputs']['audio'],'line-start.wav')

    def test_every_invalid_clip_or_unknown_node_rejects(self):
        for value in (-1,0,16,True,float('nan')):
            c=clip();c['seconds']=value
            with self.assertRaises(ValueError):compile_workflow(graph(),bindings(),c)
        for value in ('../../secret','https://a.invalid/x.wav','folder/a.wav'):
            c=clip();c['audio_asset']=value
            with self.assertRaises(ValueError):compile_workflow(graph(),bindings(),c)
        g=graph();g['bad']={'class_type':'ExecuteShell','inputs':{}}
        with self.assertRaises(ValueError):compile_workflow(g,bindings(),clip())
        for t in (-1,1,2):
            c=clip();c['pins'][0]['seconds']=t
            with self.assertRaises(ValueError):compile_workflow(graph(),bindings(),c)
    def test_default_license_runtime_and_duplicate_locks(self):
        with self.assertRaises(RuntimeError):runtime_preflight({})
        for key in ('free_local_compute','model_license_reference','owner_approval_reference'):
            c={'enabled':True,'free_local_compute':True,'model_license_reference':'fixture','owner_approval_reference':'fixture'};c[key]=False
            with self.assertRaises(ValueError):runtime_preflight(c)
        class HTTP:
            def get(self,*a,**kw):return Response({k:{} for k in ('MiniMaxH3AddGuide','VAEEncodeAudio','SetLatentNoiseMask','LTXVConcatAVLatent')})
            def post(self,*a,**kw):return Response({'prompt_id':'fixture'})
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'weights';p.write_bytes(b'fixture not real weights');compiled=compile_workflow(graph(),bindings(),clip())
            c={'enabled':True,'free_local_compute':True,'model_license_reference':'fixture','owner_approval_reference':'fixture','url':'http://127.0.0.1:8188',
               'model_files':[{'path':str(p),'sha256':digest(p)}],'approved_workflow_sha256':compiled['workflow_sha256']}
            r=submit_local(compiled,c,Path(d)/'job.json',HTTP());self.assertEqual(r['prompt_id'],'fixture')
            with self.assertRaises(RuntimeError):submit_local(compiled,c,Path(d)/'job.json',HTTP())
            c['url']='https://paid-gpu.invalid'
            with self.assertRaises(ValueError):runtime_preflight(c,HTTP())

    def test_collect_pending_complete_and_traversal(self):
        from magicdrama.audiofirst.h3_local import collect_local
        class HTTP:
            history={}
            def get(self,url,**kw):
                if 'object_info' in url:return Response({k:{} for k in ('MiniMaxH3AddGuide','VAEEncodeAudio','SetLatentNoiseMask','LTXVConcatAVLatent')})
                return Response(self.history)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);weight=root/'weights';weight.write_bytes(b'fixture');outputs=root/'runtime';outputs.mkdir();(outputs/'clip.mp4').write_bytes(b'fixture-video')
            receipt=root/'job.json';receipt.write_text(json.dumps({'state':'submitted','prompt_id':'p1'}))
            c={'enabled':True,'free_local_compute':True,'model_license_reference':'fixture','owner_approval_reference':'fixture','url':'http://127.0.0.1:8188',
                'model_files':[{'path':str(weight),'sha256':digest(weight)}],'runtime_output_root':str(outputs)}
            h=HTTP();self.assertEqual(collect_local(c,receipt,root/'got',h)['status'],'pending')
            h.history={'p1':{'outputs':{'x':{'videos':[{'filename':'clip.mp4','subfolder':'','type':'output'}]}}}}
            r=collect_local(c,receipt,root/'got',h);self.assertEqual(Path(r['path']).read_bytes(),b'fixture-video')
            receipt.write_text(json.dumps({'state':'submitted','prompt_id':'p1'}));h.history['p1']['outputs']['x']['videos'][0]['filename']='../secret.mp4'
            with self.assertRaises(ValueError):collect_local(c,receipt,root/'bad',h)
    def test_runtime_failure_leaves_unknown_no_retry(self):
        class HTTP:
            def get(self,*a,**kw):return Response({k:{} for k in ('MiniMaxH3AddGuide','VAEEncodeAudio','SetLatentNoiseMask','LTXVConcatAVLatent')})
            def post(self,*a,**kw):raise TimeoutError('fixture')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'w';p.write_bytes(b'fixture');compiled=compile_workflow(graph(),bindings(),clip())
            c={'enabled':True,'free_local_compute':True,'model_license_reference':'fixture','owner_approval_reference':'fixture','url':'http://127.0.0.1:8188','model_files':[{'path':str(p),'sha256':digest(p)}],'approved_workflow_sha256':compiled['workflow_sha256']}
            with self.assertRaises(TimeoutError):submit_local(compiled,c,root/'job.json',HTTP())
            self.assertEqual(json.loads((root/'job.json').read_text())['state'],'unknown')
            with self.assertRaises(RuntimeError):submit_local(compiled,c,root/'job.json',HTTP())

class LicenseStressTests(unittest.TestCase):
    def test_license_url_shortname_restriction_mime_host_matrix(self):
        from itertools import product
        accepted=0;rejected=0
        for license_ok,short_ok,restricted,audio_ok,host_ok in product((False,True),repeat=5):
            p=page();info=p['imageinfo'][0];m=info['extmetadata']
            if not license_ok:m['LicenseUrl']['value']='https://creativecommons.org/licenses/by-nc/4.0/'
            if not short_ok:m['LicenseShortName']['value']='unknown'
            if restricted:m['Restrictions']={'value':'unclear rights'}
            if not audio_ok:info['mime']='video/mp4'
            if not host_ok:info['url']='https://evil.invalid/x.wav'
            result=metadata_candidate(p)
            expected=license_ok and short_ok and not restricted and audio_ok and host_ok
            self.assertEqual(result is not None,expected)
            accepted+=result is not None;rejected+=result is None
        self.assertEqual((accepted,rejected),(1,31))

class DownloadFailureTests(unittest.TestCase):
    def test_download_limits_license_decode_redirect_matrix(self):
        import io
        b=io.BytesIO()
        with wave.open(b,'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(b'\0\0'*1600)
        raw=b.getvalue()
        for fault in ('size','terms','redirect','decode','changed_license'):
            p=page();p['imageinfo'][0]['size']=len(raw)
            candidate=metadata_candidate(p)
            class HTTP:
                def get(self,url,**kw):
                    if 'api.php' in url:
                        q=copy.deepcopy(p)
                        if fault=='size':q['imageinfo'][0]['size']=100000000
                        if fault=='changed_license':q['imageinfo'][0]['extmetadata']['LicenseShortName']['value']='unknown'
                        return Response({'query':{'pages':{'1':q}}})
                    if 'creativecommons' in url:return Response(text='not terms' if fault=='terms' else 'CC0 fixture')
                    r=Response(content=b'not audio'+b' '*max(0,len(raw)-9) if fault=='decode' else raw)
                    if fault=='redirect':r.status_code=302
                    return r
            with tempfile.TemporaryDirectory() as d:
                root=Path(d)/'asset'
                with self.subTest(fault=fault):
                    with self.assertRaises((ValueError,__import__('subprocess').CalledProcessError)):CommonsAudio(HTTP()).download(candidate,root)
                    self.assertFalse(root.exists())

class WorkflowTamperTests(unittest.TestCase):
    def test_changed_graph_never_submits(self):
        class HTTP:
            calls=0
            def get(self,*a,**kw):return Response({k:{} for k in ('MiniMaxH3AddGuide','VAEEncodeAudio','SetLatentNoiseMask','LTXVConcatAVLatent')})
            def post(self,*a,**kw):self.calls+=1;raise AssertionError('must not submit')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);w=root/'weights';w.write_bytes(b'fixture');compiled=compile_workflow(graph(),bindings(),clip())
            c={'enabled':True,'free_local_compute':True,'model_license_reference':'fixture','owner_approval_reference':'fixture','url':'http://127.0.0.1:8188','model_files':[{'path':str(w),'sha256':digest(w)}],'approved_workflow_sha256':compiled['workflow_sha256']}
            compiled['workflow']['md_mask']['inputs']['value']=1;http=HTTP()
            with self.assertRaises(ValueError):submit_local(compiled,c,root/'job.json',http)
            self.assertEqual(http.calls,0);self.assertFalse((root/'job.json').exists())
