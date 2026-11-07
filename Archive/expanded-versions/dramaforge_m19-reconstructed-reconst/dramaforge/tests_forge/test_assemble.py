import subprocess
from forge.assemble.compose import compose, burn_captions
from forge.assemble.captions import words_to_ass
from forge.assemble.qa import cuts, write_timeline

def mk(path, color, secs=2):
    subprocess.run(["ffmpeg","-v","error","-y","-f","lavfi","-i",f"color=c={color}:s=360x640:d={secs}:r=30","-f","lavfi","-i","anullsrc=r=44100:cl=mono","-shortest","-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac",path],check=True)

def test_end_to_end(tmp_path):
    a, b = str(tmp_path/"a.mp4"), str(tmp_path/"b.mp4"); mk(a,"red"); mk(b,"blue")
    voice = str(tmp_path/"v.wav")
    subprocess.run(["ffmpeg","-v","error","-y","-f","lavfi","-i","sine=f=300:d=4",voice],check=True)
    out = compose([a,b], voice, None, str(tmp_path/"ep.mp4"))
    ass = words_to_ass([{"word":"hello","start":0.2,"end":0.6},{"word":"there","start":0.7,"end":1.1}], str(tmp_path/"c.ass"))
    final = burn_captions(out, ass, str(tmp_path/"final.mp4"))
    assert len(cuts(final)) == 2          # one hard cut between red and blue
    tl = write_timeline([("a",2),("b",2)], str(tmp_path/"t.otio"))
    import opentimelineio as otio
    assert len(list(otio.adapters.read_from_file(tl).find_clips())) == 2
