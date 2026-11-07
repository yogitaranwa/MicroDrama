# E01 repair research and implementation, 2026-10-25

The runnable open-source fix is the audio rebuild: pyloudnorm's research-backed loudness implementation plus FFmpeg now produces a new 94.254s audio review candidate with all15 dialogue lines, the music source's1.65s pre-roll removed, dialogue ducking and music through the last frame. This is actual repaired media, not a new detector. It does not fix absent visual actions or prove emotional delivery.

| Route | Target | Verified status | Decision |
|---|---|---|---|
| pyloudnorm + FFmpeg | Opening silence, weak bed, inconsistent loudness | Executed on E01,7 behavior tests pass | Integrated audio repair tool into both codebases |
| VACE Wan2.1 | Action control with pose/depth/layout/reference/masks | Code, paper, guide and licenses inspected; no local GPU | Best next controlled-action experiment, not a promised solution |
| MuseTalk | Visible close-up lip repair | Repo permits commercial model use subject to dependencies;4GB GPU example | Smallest documented GPU lip route to test |
| LatentSync | Close-up lip repair with temporal diffusion | Apache2 repo;8GB/18GB VRAM | Alternate higher-memory test |
| Phantom / ConsisID | Reference-based identity | Paper/repo/docs examined, not run | Identity controls, not physics or action correctness guarantees |
| Wav2Lip | Lip repair | Noncommercial model restriction | Not integrated for product use |

## Implementation and evidence
Audio code, behavior tests, source hashes, mix stems, new MP3, exact retained dialogue timings and both independent meters are preserved in the repair package. Installed dependencies came only from official PyPI. No downloaded model weights or third-party neural code were executed. No paid GPU, generation, top-up or credits used.

The new prep manifest maps every action from the actual script. It corrects a problem in the earlier audit-derived gates: the wrist-string/heel action belongs to original shot8 and the trolley impact to shot9, rather than treating the audit's numbering as script truth. Line14 must move back to a visible Harry close-up, not a hands crop. No action is marked accepted from a freeze/motion metric.

## Remaining work and decisions
The actual episode remains REJECTED. Missing programme drop/pull, guest freezing and arrow impacts, mirrored steps, beat-timed evasion, Draconia's recognition, string cutting/wrapping/heel snap, trolley impact, table flip/chandelier impact and visible emotional dialogue need accepted coverage. Shot1 pacing/spark and shot9 expression/wand also need full review. No fixed final video has been exported.

No local GPU exists. Free remote GPU availability, rights-compatible checkpoint deployment, source action-control clips and end-to-end runtime have not been established. Installing a repo is not a compute solution. VACE's own setup uses git dependencies outside the current official-registry-only install rule, so running that exact setup requires a permitted installation route or an explicit exception, plus working GPU access. No public demo upload was used because publishing private project media is not implied.

At current public rates, MiniMax H3 720p is48credits/sec and Pro lip sync at24fps is48credits/sec. These are planning rates; first-pass estimates are not maximum commitments and repeat generations are not guaranteed to satisfy actions. A new generation budget and bounded experiment should be agreed only after choosing the actual compute route. Existing-account credit availability is not spending authority.

The candidate music/voice still needs real emotional and phone-speaker listening. Measurements and machine transcripts cannot establish it. Full-playback/review gates remain in place. Final attribution must accompany video; audio candidate carries a text sidecar and metadata.

## Sources
See sources.md for exact inspected URLs, licenses, papers and limitations.


## Update18:49
Grand Dark Waltz rejected by the user for tension fit; Dark Dance replaces it in the latest review candidate. Dialogue was called okayish, not final emotional approval. Audio bytes/timings retained. Free Colab T4 with15GB VRAM was allocated and verified; a single VACE reference+mask table-flip experiment started18:48 after official-PyPI install. Not a pose/depth-controlled trial, not a successful result. No Magic Hour credits spent. One experiment only, stop on memory/resource errors, no rerolls.
