# Harry + Draconia Yule Ball E01 QA

Final: `/tmp/Harry-Draconia-YuleBall-E01-final.mp4`
- Duration: 94.048s
- Delivery frame: 570x1024, 24fps, h264/AAC 48kHz mono
- Lip Sync Pro downscales the 720p-requested base to 570x1024, so this is not labeled true 720p delivery.
- Dialogue: 17/17 lines transcript-exact
- Black-frame check: no blackdetect intervals reported

## Lip-sync audio QA
All Pro lip jobs had 0.000s lag versus source audio. Correlation was approximately 1.0 for every checked clip.

- Shot 4 / line 3: `cmvnlzcsz012khf01j0ibfvno`, 124 credits, lag 0.0s, corr 0.9999 - This is how Slytherins ask?
- Shot 5 / line 4: `cmvnlze5b0bprhu01uvc2zppc`, 100 credits, lag 0.0s, corr 1.0022 - It's how they keep you alive.
- Shot 6 / line 5: `cmvnlzgg7035kgn01zp116p8j`, 112 credits, lag 0.0s, corr 1.0006 - They follow the offbeat.
- Shot 7 / line 6: `cmvnlzhlf012rhf01gum89k3q`, 94 credits, lag 0.0s, corr 0.9996 - Then count faster.
- Shot 15 / line 14: `cmvnlziuq007eet01xtei3izr`, 132 credits, lag 0.0s, corr 1.0015 - Left side, three beats, red table.
- Shot 17 / line 16: `cmvnlzk4i09txfu010957cwaa`, 62 credits, lag 0.0s, corr 1.0074 - What did you do?
- Shot 18 / line 17: `cmvnlzl8q035qgn01h8oetocx`, 112 credits, lag 0.0s, corr 1.0005 - I tried to warn you.

## Base QA
- 17/17 original bases completed.
- Five failed visual QA and were selectively rerolled: 5 (overacted), 6 (red arrows instead of ice), 7 (overacted grin), 12 (gown color changed), 13 (missed waltz-grid action).
- All five rerolls passed frame review.
- Shot 13 dialogue is intentionally off-screen over the waltz-grid visual because the selected shot is mostly over-shoulder; forcing lip sync there would lower quality.

## Credit ledger
- Diagnostics/reusable shot 2: 555 credits
- 17 original E01 bases: 4368 credits
- Five QA base rerolls: 1296 credits
- Seven E01 Pro lip jobs: 736 credits
- Total Magic Hour usage for current E01 work: 6955 credits
- ElevenLabs current character_count after remaining dialogue: 1012; remaining E01 dialogue generation used 91 characters after the earlier accepted six-line audio.

## Known caveats
- Best available verified workaround, not original private H3Film/ComfyUI parity.
- Magic Hour bases were requested at 720p but Pro lip-sync returns 570x1024; final is standardized to 570x1024 for consistency.
- Shot 2 is 3.042s because the existing reusable 720p base is 3.042s; this naturally tightened the episode to 94s instead of padding it to 95s.