import importlib.util,json,tempfile,unittest,subprocess
from pathlib import Path
from types import SimpleNamespace
from magicdrama.audiofirst.mouth_tracker import mouth_geometry
from magicdrama.audiofirst.h3_local import runtime_preflight
from magicdrama.audiofirst.quality import tracked_lip_sync
ROOT=Path(__file__).resolve().parents[1]


def load(name):
    spec=importlib.util.spec_from_file_location('portable_'+name,ROOT/'portable'/f'{name}.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


class PortableTests(unittest.TestCase):
    def test_real_template_wiring(self):
        m=load('h3');clip=json.loads((ROOT/'portable/h3_clip.example.json').read_text());c=m.build(clip);g=c['workflow']
        self.assertEqual(c['frames'],124);self.assertEqual(g['md_av']['inputs']['video_latent'],['136',1])
        self.assertEqual(g['md_mask']['inputs']['value'],0)
        self.assertEqual(g['126']['inputs']['conditioning'],['md_pin0',0])
        self.assertNotIn('positive',g['125']['inputs']);self.assertEqual(g['125']['inputs']['latent_image'],['md_av',0])
        self.assertEqual(g['130']['inputs']['audio'],['md_audio',0])
        self.assertEqual(g['136']['inputs']['width'],480);self.assertEqual(g['136']['inputs']['height'],864)
        self.assertEqual(g['md_pin0']['inputs']['latent'],['136',1])
        self.assertEqual(g['136']['inputs']['ref_images.ref_image_0'],['reference_0',0])
    def test_h3_dimensions_and_refs_fail_closed(self):
        m=load('h3');base=json.loads((ROOT/'portable/h3_clip.example.json').read_text())
        for width in [63,481,2049]:
            with self.assertRaises(ValueError):m.build({**base,'width':width})
        for refs in [['../x.png'],['x.png']*10,['https://example.invalid/x']]:
            with self.assertRaises(ValueError):m.build({**base,'references':refs})
    def test_geometry(self):
        pts=[SimpleNamespace(x=0.,y=0.) for _ in range(478)]
        with self.assertRaises(ValueError):mouth_geometry(pts)
        pts[291].x=1;pts[14].y=.25
        self.assertEqual(mouth_geometry(pts),.25)
    def test_uncalibrated_tracks_cannot_accept(self):
        from magicdrama.audiofirst.core import digest
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'bytes';f.write_bytes(b'x')
            with self.assertRaisesRegex(ValueError,'identity'):tracked_lip_sync(f,f,{'video_sha256':digest(f),'audio_sha256':digest(f),'identity_verified':False})
    def test_lock_pins_publishers(self):
        lock=json.loads((ROOT/'portable/sources.lock.json').read_text())
        self.assertEqual(lock['models']['asr']['repo'],'Systran/faster-whisper-tiny.en')
        for m in lock['models'].values():self.assertEqual(len(m['revision']),40)
        self.assertEqual(len(lock['face']['sha256']),64)
        self.assertNotIn('nvfp4',' '.join(lock['models']['h3']['allow_patterns']))
    def test_notebook_is_clean_code(self):
        n=json.loads((ROOT/'portable/portable_runtime.ipynb').read_text())
        for c in n['cells']:
            if c['cell_type']=='code':
                compile(''.join(c['source']),'notebook','exec');self.assertEqual(c['outputs'],[]);self.assertIsNone(c['execution_count'])
    def test_stage_audio_grid_real_decode(self):
        import wave
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);audio=root/'a.wav'
            with wave.open(str(audio),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(b'\0\0'*16000)
            result=load('prepare_h3_inputs').prepare({'padded_audio_seconds':124/24,'trim_to_seconds':5},audio,[],[],root/'staged')
            with wave.open(str(root/'staged/dialogue.wav'),'rb') as f:self.assertAlmostEqual(f.getnframes()/f.getframerate(),124/24,places=3)
            self.assertEqual(result['audio_asset'],'dialogue.wav')
            with self.assertRaises(ValueError):load('prepare_h3_inputs').prepare({'padded_audio_seconds':2,'trim_to_seconds':2},audio,[],[],root/'staged')
    def test_finalizer_real_mux(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);v=r/'v.mp4';a=r/'a.wav'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=red:s=128x128:r=24:d=1','-c:v','libx264',str(v)],check=True)
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=300:duration=1',str(a)],check=True)
            result=load('finalize_h3').finalize(v,a,1,r/'out.mp4')
            self.assertEqual(result['status'],'muxed_not_quality_accepted')
            with self.assertRaises(ValueError):load('finalize_h3').finalize(v,a,1,r/'out.mp4')
    def test_shell_syntax(self):
        subprocess.run(['bash','-n',str(ROOT/'portable/setup.sh')],check=True)

if __name__=='__main__':unittest.main()
