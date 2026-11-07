import copy
import math
from pathlib import Path
import tempfile
import unittest
import wave
from array import array
from magicdrama.audiofirst.alignment import recover_alignment,LocalWhisper
from magicdrama.audiofirst.quality import decide_quality,visual_evidence,lip_sync_score,CHECKS
from magicdrama.audiofirst.acceptance import prepare_episode
from magicdrama.audiofirst.execution import signature
from magicdrama.audiofirst.core import digest


def tone(path,seconds=2):
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
        f.writeframes(array('h',[int(4000*math.sin(i*.1)) for i in range(round(seconds*16000))]).tobytes())


def words():return [{'word':'Hello,','start':0.01,'end':.6,'probability':.99},{'word':'there.','start':.7,'end':1.3,'probability':.99}]

class AlignmentAcceptanceTests(unittest.TestCase):
    def test_exact_alignment_and_source_punctuation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.wav';tone(p)
            lines=[{'id':'l1','speaker':'a','text':'Hello, there.'}]
            r=recover_alignment(p,lines,lambda *a:words())
            self.assertEqual(r['cues'][0]['text'],'Hello, there.');self.assertEqual(r['audio_sha256'],digest(p))
    def test_all_mismatch_confidence_time_combinations_reject(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.wav';tone(p);lines=[{'id':'l1','speaker':'a','text':'Hello, there.'}]
            cases=[]
            for field,value in [('word','wrong'),('probability',.1),('start',-1),('end',3),('probability',float('nan'))]:
                w=words();w[0][field]=value;cases.append(w)
            cases.extend([[],words()[:1],words()+words(),list(reversed(words()))])
            for w in cases:
                with self.subTest(words=w):
                    with self.assertRaises(ValueError):recover_alignment(p,lines,lambda *a:w)
    def test_bounded_recovery_repairs_missing_word(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.wav';tone(p)
            def asr(path,start,end):return words()[:1] if end is None else words()[1:]
            r=recover_alignment(p,[{'id':'l','speaker':'a','text':'Hello, there.'}],asr,[{'start':.65,'end':1.5}])
            self.assertEqual(len(r['words']),2)
            with self.assertRaises(ValueError):recover_alignment(p,[{'id':'l','speaker':'a','text':'Hello, there.'}],asr,[{'start':1,'end':.5}])
    def test_local_model_never_downloads(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            with self.assertRaises(ValueError):LocalWhisper(p)
            (p/'model.bin').write_bytes(b'fixture');calls=[]
            def factory(*a,**kw):calls.append(kw);return object()
            LocalWhisper(p,factory);self.assertEqual(calls[0]['device'],'cpu');self.assertTrue(calls[0]['local_files_only'])
    def test_semantic_gate_every_check_fail_unknown_or_low(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'frame.png';p.write_bytes(b'fixture-only')
            expectations={'props':['door'],'action':'opens door'}
            def ev(context):return {k:{'pass':True,'confidence':.99,'reason':'fixture only'} for k in CHECKS}
            engines=[{'id':'fixture-a','version':'1','local_free':True},{'id':'fixture-b','version':'1','local_free':True}]
            evidence=[visual_evidence(p,[p],[],expectations,ev,e) for e in engines]
            self.assertIn('passed',decide_quality(p,expectations,evidence)['status'])
            for key in CHECKS:
                for mode in ('failed','missing','low','nan'):
                    bad=copy.deepcopy(evidence)
                    if mode=='missing':bad[0]['checks'].pop(key)
                    elif mode=='failed':bad[0]['checks'][key]['pass']=False
                    else:bad[0]['checks'][key]['confidence']=.5 if mode=='low' else float('nan')
                    with self.subTest(key=key,mode=mode):
                        with self.assertRaises(ValueError):decide_quality(p,expectations,bad)
            with self.assertRaises(ValueError):decide_quality(p,expectations,evidence[:1])
            with self.assertRaises(ValueError):decide_quality(p,expectations,[evidence[0],evidence[0]])
            p.write_bytes(b'changed')
            with self.assertRaises(ValueError):decide_quality(p,expectations,evidence)
    def test_lipsync_screen_lag_and_no_motion(self):
        a=[math.sin(i*.6)+1 for i in range(100)]
        self.assertTrue(lip_sync_score(a,a)['screen_pass'])
        b=[0]*8+a[:-8]
        self.assertFalse(lip_sync_score(a,b)['screen_pass'])
        with self.assertRaises(ValueError):lip_sync_score([1]*100,[0]*100)
    def test_auto_prepare_does_not_fabricate_quality(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.wav';tone(p)
            ep={'audio':{'path':str(p),'sha256':digest(p)},'dialogue_lines':[{'id':'l','speaker':'a','text':'Hello, there.'}],'shots':[]}
            with self.assertRaises(ValueError):prepare_episode(ep,Path(d)/'qa',lambda *a:words())

class VisionAndAcceptanceTests(unittest.TestCase):
    def test_local_vision_batches_and_refuses_unverifiable_speech(self):
        from magicdrama.audiofirst.local_vision import OllamaVision
        class R:
            status_code=200
            def __init__(self,j):self.j=j
            def raise_for_status(self):pass
            def json(self):return self.j
        class HTTP:
            calls=0
            def get(self,*a,**kw):return R({'models':[{'name':'fixture'}]})
            def post(self,*a,**kw):
                self.calls+=1
                return R({'message':{'content':__import__('json').dumps({k:{'pass':k not in ('speech','lip_sync'),'confidence':.99,'reason':'fixture frames only'} for k in CHECKS})}})
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'p.png';p.write_bytes(b'fixture');h=HTTP();e=OllamaVision('fixture',h,max_frames=1)
            r=e({'frames':[{'path':str(p),'sha256':digest(p)}]*2,'references':[],'expectations':{}})
            self.assertEqual(h.calls,2);self.assertFalse(r['speech']['pass']);self.assertFalse(r['lip_sync']['pass'])
    def test_automatic_image_acceptance_real_pixels_and_unknown_rejection(self):
        from PIL import Image
        from magicdrama.audiofirst.acceptance import accept_asset
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'image.png';im=Image.new('RGB',(180,320),'white')
            for x in range(90):
                for y in range(320):im.putpixel((x,y),(0,60,100))
            im.save(p);asset={'path':str(p),'sha256':digest(p)}
            with self.assertRaises(ValueError):accept_asset(asset,{},[],Path(d)/'qa',kind='image')
            def evaluator(context):return {k:{'pass':True,'confidence':.99,'reason':'synthetic test evaluator, not real semantic validation'} for k in CHECKS}
            ev=[{'evaluate':evaluator,'engine':{'id':i,'version':'fixture','local_free':True}} for i in ('one','two')]
            r=accept_asset(asset,{},ev,Path(d)/'qa',kind='image');self.assertIn('passed',r['verdict']['status'])
            im=Image.new('RGB',(180,320),'black');im.save(p);asset['sha256']=digest(p)
            with self.assertRaises(ValueError):accept_asset(asset,{},ev,Path(d)/'bad',kind='image')
    def test_procedural_geometry_bounds(self):
        from magicdrama.audiofirst.procedural import box_prop
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'box.obj';r=box_prop(1,2,3,p);self.assertEqual(r['vertices'],8);self.assertEqual(r['faces'],6)
            for value in (0,-1,True,float('nan'),101):
                with self.assertRaises(ValueError):box_prop(value,1,1,Path(d)/'bad.obj')

class StressEvidenceTests(unittest.TestCase):
    def test_all_512_semantic_check_presence_combinations(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'frame.png';p.write_bytes(b'fixture');expectations={'test':'matrix'}
            def good(c):return {k:{'pass':True,'confidence':.99,'reason':'fixture only'} for k in CHECKS}
            evidence=[visual_evidence(p,[p],[],expectations,good,{'id':i,'version':'1','local_free':True}) for i in ('one','two')]
            passes=0;rejects=0
            for mask in range(1<<len(CHECKS)):
                e=copy.deepcopy(evidence)
                for i,key in enumerate(CHECKS):
                    if not mask&(1<<i):e[0]['checks'].pop(key)
                try:decide_quality(p,expectations,e);passes+=1
                except ValueError:rejects+=1
            self.assertEqual(passes,1);self.assertEqual(rejects,511)
    def test_alignment_confidence_boundary_matrix(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.wav';tone(p);lines=[{'id':'l','speaker':'a','text':'Hello, there.'}]
            for confidence in (0,.64,.65,.9,1,1.01):
                for mismatch in (False,True):
                    w=words();w[0]['probability']=confidence
                    if mismatch:w[1]['word']='wrong'
                    expected=.65<=confidence<=1 and not mismatch
                    try:r=recover_alignment(p,lines,lambda *a:w);accepted=True
                    except ValueError:accepted=False
                    self.assertEqual(accepted,expected,(confidence,mismatch))

class ProductionAutomaticTests(unittest.TestCase):
    def test_auto_prepare_then_real_assembly_with_fixture_evaluators(self):
        from PIL import Image
        from magicdrama.audiofirst.assembly import assemble_episode
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);audio=root/'a.wav';tone(audio);image=root/'image.png';im=Image.new('RGB',(180,320),'white')
            for x in range(90):
                for y in range(320):im.putpixel((x,y),(10,70,100))
            im.save(image)
            lines=[{'id':'l','speaker':'a','text':'Hello, there.'}]
            expectations={'lines':lines,'kind':'speech'}
            def evaluator(context):return {k:{'pass':True,'confidence':.99,'reason':'SYNTHETIC TEST ONLY, not actual semantic validation'} for k in CHECKS}
            engines=[{'id':i,'version':'fixture','local_free':True} for i in ('test-one','test-two')]
            evidence=[visual_evidence(audio,[image],[],expectations,evaluator,engine) for engine in engines]
            ep={'id':'e1','audio':{'path':str(audio),'sha256':digest(audio)},'dialogue_lines':lines,'audio_quality_evidence':evidence,
                'names':{'a':'Fixture'},'shots':[{'path':str(image),'sha256':digest(image),'kind':'image','frames':48,'expectations':{'action':'fixture only'}}]}
            prepared=prepare_episode(ep,root/'qa',lambda *a:words(),[{'evaluate':evaluator,'engine':e} for e in engines])
            self.assertTrue(prepared['audio_checked']);self.assertTrue(prepared['shots'][0]['pixel_checked'])
            r=assemble_episode(prepared,root/'assembled',size=(180,320));self.assertTrue(Path(r['path']).exists())
            self.assertNotIn('cues',ep)
    def test_track_bindings_fail_on_mismatched_media_or_ambiguity(self):
        from magicdrama.audiofirst.quality import tracked_lip_sync
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);audio=root/'a.wav';tone(audio);video=root/'v.mp4';video.write_bytes(b'fixture')
            track={'video_sha256':digest(video),'audio_sha256':digest(audio),'engine':'fixture','speaker_id':'a',
                   'samples':[{'seconds':i*.04,'visible_speakers':1,'confidence':.99,'mouth_open':1} for i in range(50)]}
            with self.assertRaises(ValueError):tracked_lip_sync(video,audio,track)
            track['video_sha256']='wrong'
            with self.assertRaises(ValueError):tracked_lip_sync(video,audio,track)
            track['video_sha256']=digest(video);track['samples'][0]['visible_speakers']=2
            with self.assertRaises(ValueError):tracked_lip_sync(video,audio,track)

class ProductionRefusalTests(unittest.TestCase):
    def test_production_auto_mode_missing_engines_never_outputs_season(self):
        from magicdrama.audiofirst.production_run import media_run
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);a=root/'tone.wav';tone(a)
            package={'automatic_acceptance':True,'season':{'series_id':'fixture','season':1,'canon':{'characters':[],'facts':[],'unresolved':[],'ending':'fixture'},
                'episodes':[{'id':'e1','audio':{'path':str(a),'sha256':digest(a)},'dialogue_lines':[{'id':'l','speaker':'a','text':'Hello, there.'}],'shots':[]}]}}
            with self.assertRaises(ValueError):media_run(package,root/'out',transcriber=lambda *a:words())
            self.assertFalse((root/'out').exists());self.assertFalse((root/'out.zip').exists())
