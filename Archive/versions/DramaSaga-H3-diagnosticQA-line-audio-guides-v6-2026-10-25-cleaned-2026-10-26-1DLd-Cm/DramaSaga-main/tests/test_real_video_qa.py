import tempfile,unittest
from pathlib import Path
from magicdrama.audiofirst.real_video_qa import _mouth_open,_padded_box,extract_real_video_mouth_track

class Point:
    def __init__(self,x,y):self.x=x;self.y=y

class RealVideoQATests(unittest.TestCase):
    def test_mouth_geometry_and_box_validation(self):
        landmarks=[Point(0,0) for _ in range(478)]
        landmarks[61]=Point(0,0);landmarks[291]=Point(2,0);landmarks[13]=Point(1,0);landmarks[14]=Point(1,.5)
        self.assertEqual(_mouth_open(landmarks),.25)
        self.assertEqual(_padded_box([10,10,20,20],100,100,.5),(0,0,40,40))
        with self.assertRaises(ValueError):_padded_box([10,10,0,20],100,100,.5)
    def test_extractor_fails_closed_before_imports_when_files_or_refs_missing(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);video=root/'v.mp4';video.write_bytes(b'not-a-video');ref=root/'ref.png';ref.write_bytes(b'x')
            lines=[{'id':'L1','speaker':'harry','start':0,'end':1}]
            with self.assertRaisesRegex(ValueError,'MediaPipe'):
                extract_real_video_mouth_track(video,lines,{'harry':[ref]},face_landmarker_path=root/'missing.task',yunet_path=root/'y.onnx',sface_path=root/'s.onnx')
            with self.assertRaisesRegex(ValueError,'No reference images'):
                extract_real_video_mouth_track(video,lines,{'draconia':[ref]},face_landmarker_path=ref,yunet_path=ref,sface_path=ref)

if __name__=='__main__':unittest.main()
