import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from models import model_root


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['describe','track','track-real']);p.add_argument('--image');p.add_argument('--video');p.add_argument('--audio');p.add_argument('--speaker');p.add_argument('--dialogue-lines');p.add_argument('--references');p.add_argument('--device',choices=['cpu','cuda'],default='cpu');p.add_argument('--out',required=True);a=p.parse_args()
    dest=Path(a.out)
    if dest.exists():raise ValueError('Fresh output path required')
    if a.command=='describe':
        from magicdrama.audiofirst.transformers_vision import TransformersVision
        result=TransformersVision(model_root()/'vision',a.device).describe(a.image)
    elif a.command=='track':
        from magicdrama.audiofirst.mouth_tracker import track_mouth
        result=track_mouth(a.video,a.audio,model_root()/'face_landmarker.task',a.speaker)
    else:
        if not a.video or not a.dialogue_lines or not a.references:raise ValueError('track-real requires --video, --dialogue-lines and --references')
        from magicdrama.audiofirst.real_video_qa import extract_real_video_mouth_track
        lock=json.loads((Path(__file__).with_name('sources.lock.json')).read_text())
        provenance={
            'face_landmarker':{**lock['face'],'license':'Apache-2.0; official MediaPipe model page'},
            'opencv_zoo':lock['face_video'],
        }
        result=extract_real_video_mouth_track(
            a.video,json.loads(Path(a.dialogue_lines).read_text()),json.loads(Path(a.references).read_text()),
            face_landmarker_path=model_root()/'face_landmarker.task',
            yunet_path=model_root()/'face_detection_yunet_2023mar.onnx',
            sface_path=model_root()/'face_recognition_sface_2021dec.onnx',
            audio_path=a.audio,model_provenance=provenance)
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
