from pathlib import Path
import subprocess,json,hashlib
root=Path(__file__).parent;src=Path('/home/sandbox/e01-repair/work/voice-v6');groups=[(1,3),(4,5),(6,8),(9,10)];report=[]
for ep,(a,b) in enumerate(groups,1):
 listing=root/f'ep{ep}.txt';listing.write_text('\n'.join("file '"+str(src/f'scene{i:02d}.mp3')+"'" for i in range(a,b+1)))
 dry=root/f'E{ep:02d}-dry.wav';subprocess.run(['ffmpeg','-v','error','-f','concat','-safe','0','-i',str(listing),'-ar','44100','-ac','2',str(dry),'-y'],check=True)
 dur=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(dry)]))
 out=Path(f'/downloads/E{ep:02d}-v6-tense-music-REVIEW.mp3')
 filt=f'[0:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,asplit=2[v][sc];[1:a]atrim=start=0.05,asetpts=PTS-STARTPTS,loudnorm=I=-30:TP=-7:LRA=9,afade=t=in:d=0.015,afade=t=out:st={dur-.8}:d=0.8,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[m];[m][sc]sidechaincompress=threshold=0.025:ratio=5:attack=30:release=250:makeup=1[duck];[v][duck]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-18:TP=-2:LRA=11[out]'
 subprocess.run(['ffmpeg','-v','error','-i',str(dry),'-stream_loop','-1','-i','/downloads/Dark_Dance.mp3','-filter_complex',filt,'-map','[out]','-ar','44100','-c:a','libmp3lame','-b:a','192k',str(out),'-y'],check=True)
 report.append({'episode':ep,'scenes':[a,b],'duration_seconds':dur,'file':out.name,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'voice_regenerated':False})
 print(report[-1],flush=True)
json.dump(report,open(root/'episode-cuts.json','w'),indent=2)
