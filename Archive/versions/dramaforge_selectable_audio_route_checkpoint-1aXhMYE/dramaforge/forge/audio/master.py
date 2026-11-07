"""Loudness mastering: pyloudnorm (MIT) to -16 LUFS (vertical-video norm)."""
def master(in_path, out_path, target=-16.0):
    import soundfile as sf, pyloudnorm as pyln
    data, sr = sf.read(in_path)
    loud = pyln.Meter(sr).integrated_loudness(data)
    sf.write(out_path, pyln.normalize.loudness(data, loud, target), sr)
    return loud
