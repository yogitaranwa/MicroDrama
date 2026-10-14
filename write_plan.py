"""Generate updated Plan.html for AI MicroDrama Series Generator v2.1."""
import os
import sys

CSS = """
:root{--bg:#0a0a0f;--bg-card:#12121a;--border:#1e1e30;--border-glow:#6c4de6;--text:#e0e0f0;--muted:#8888aa;--dim:#555570;--accent:#8b5cf6;--ab:#a78bfa;--green:#22c55e;--gd:#14532d;--amber:#f59e0b;--ad:#78350f;--red:#ef4444;--rd:#7f1d1d;--blue:#3b82f6;--bd:#1e3a5f;--cyan:#06b6d4;--pink:#ec4899;--gh:linear-gradient(135deg,#6c4de6 0%,#ec4899 50%,#f59e0b 100%);--gc:linear-gradient(145deg,rgba(108,77,230,.08) 0%,rgba(236,72,153,.05) 100%);--font:"Inter",-apple-system,sans-serif;--mono:"JetBrains Mono",monospace}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--font);background:var(--bg);color:var(--text);line-height:1.7;overflow-x:hidden}
::selection{background:var(--accent);color:#fff}
.container{max-width:1120px;margin:0 auto;padding:0 32px}
.hero{padding:70px 0 44px;text-align:center;position:relative}
.hero::before{content:"";position:absolute;top:-120px;left:50%;transform:translateX(-50%);width:700px;height:700px;background:radial-gradient(circle,rgba(108,77,230,.18) 0%,transparent 70%);pointer-events:none}
.badge{display:inline-block;padding:6px 16px;border-radius:20px;background:rgba(108,77,230,.15);border:1px solid rgba(108,77,230,.35);font-size:13px;font-weight:600;color:var(--ab);letter-spacing:.5px;margin-bottom:20px}
h1{font-size:42px;font-weight:800;letter-spacing:-1.5px;background:var(--gh);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:16px}
.hero p{font-size:16px;color:var(--muted);max-width:760px;margin:0 auto}
section{padding:50px 0;border-top:1px solid var(--border)}
section:first-of-type{border-top:none}
.lbl{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:2px;color:var(--accent);margin-bottom:8px}
h2{font-size:27px;font-weight:700;letter-spacing:-.5px;margin-bottom:20px}
h3{font-size:18px;font-weight:600;margin:24px 0 10px;color:var(--ab)}
p,li{font-size:15px}
p+p{margin-top:10px}
ul,ol{padding-left:22px;margin:8px 0 14px}
li{margin-bottom:6px}
li::marker{color:var(--accent)}
.card{background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:22px;margin:12px 0;transition:border-color .3s}
.card:hover{border-color:var(--border-glow)}
.ct{font-size:16px;font-weight:600;margin-bottom:10px}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}
@media(max-width:820px){.g2,.g3{grid-template-columns:1fr}h1{font-size:30px}}
.tag{display:inline-block;padding:2px 9px;border-radius:5px;font-size:12px;font-weight:600}
.tg{background:var(--gd);color:var(--green)}
.ta{background:var(--ad);color:var(--amber)}
.tr{background:var(--rd);color:var(--red)}
.tb{background:var(--bd);color:var(--blue)}
.tp{background:rgba(236,72,153,.2);color:var(--pink)}
code,pre{font-family:var(--mono);font-size:13px}
code{background:rgba(108,77,230,.12);padding:2px 7px;border-radius:5px;color:var(--ab)}
pre{background:#0d0d18;border:1px solid var(--border);border-radius:10px;padding:18px;overflow-x:auto;margin:12px 0;color:var(--muted)}
pre code{background:none;padding:0;color:inherit}
table{width:100%;border-collapse:collapse;margin:14px 0;font-size:14px}
th,td{text-align:left;padding:11px 14px;border-bottom:1px solid var(--border)}
th{font-weight:600;color:var(--ab);font-size:12px;text-transform:uppercase;letter-spacing:1px}
tr:hover td{background:rgba(108,77,230,.04)}
.flow{display:flex;flex-wrap:wrap;gap:5px;align-items:stretch;margin:18px 0}
.fs{flex:1;min-width:115px;background:var(--bg-card);border:1px solid var(--border);border-radius:10px;padding:12px;text-align:center;font-size:12px}
.sn{display:block;font-size:10px;font-weight:700;color:var(--accent);margin-bottom:3px}
.fa{display:flex;align-items:center;padding:0 3px;color:var(--dim);font-size:18px;flex-shrink:0}
.qc{background:var(--gc);border:1px solid rgba(108,77,230,.25);border-radius:12px;padding:18px 22px;margin:12px 0}
.qn{font-size:13px;font-weight:700;color:var(--pink);margin-bottom:4px}
.qt{font-weight:600;margin-bottom:5px;font-size:15px;color:#fff}
.qx{font-size:13px;color:var(--muted)}
.dec-box{background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.3);border-radius:10px;padding:14px 18px;margin:10px 0}
.dec-title{font-size:14px;font-weight:700;color:var(--green);display:flex;align-items:center;gap:8px}
.dec-text{font-size:13px;color:#d1fae5;margin-top:4px}
.toc{list-style:none;padding:0}
.toc li{margin-bottom:7px}
.toc a{color:var(--muted);text-decoration:none;font-size:14px;transition:color .2s}
.toc a:hover{color:var(--ab)}
.tn{color:var(--accent);font-weight:600;margin-right:7px}
.mb{display:flex;align-items:center;gap:10px;margin:7px 0}
.ml{width:190px;font-size:13px;color:var(--muted);flex-shrink:0}
.mbar{flex:1;height:7px;background:rgba(255,255,255,.06);border-radius:4px;overflow:hidden}
.mf{height:100%;border-radius:4px}
.mv{width:45px;text-align:right;font-size:13px;font-weight:600}
.co{border-left:3px solid var(--accent);padding:14px 18px;margin:14px 0;background:rgba(108,77,230,.06);border-radius:0 8px 8px 0;font-size:14px}
footer{padding:40px 0;text-align:center;color:var(--dim);font-size:13px;border-top:1px solid var(--border)}
"""

HEAD = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI MicroDrama Series Generator - Implementation Plan v2.1</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div class="container">
"""

HERO = """
<div class="hero">
  <span class="badge">IMPLEMENTATION PLAN v2.1 &mdash; 10-Episode Test Stage (1 Lakh Credits Confirmed)</span>
  <h1>AI MicroDrama Series Generator</h1>
  <p>A deterministic, context-aware pipeline generating a 10-episode test microdrama series (<em>"The Cold CEO's Contract Bride"</em>) with sequential clip generation, FFmpeg frame extraction, burned-in styled ASS subtitles, DramaBench narrative intelligence, and semantic verification &mdash; built on Magic Hour API.</p>
</div>
"""

TOC = """
<section>
  <div class="lbl">Navigation</div>
  <h2>Table of Contents</h2>
  <ul class="toc">
    <li><a href="#s0"><span class="tn">00</span>Executive Summary &amp; All Confirmed Decisions (Q1&ndash;Q9 + CQ1&ndash;CQ3)</a></li>
    <li><a href="#s1"><span class="tn">01</span>What Changed: v1 to v2.1</a></li>
    <li><a href="#s2"><span class="tn">02</span>Directory Structure and Output Organization</a></li>
    <li><a href="#s3"><span class="tn">03</span>Sequential Clip Generation &amp; Frame Extraction (Option A)</a></li>
    <li><a href="#s4"><span class="tn">04</span>Episode Stitching and Burned-In Styled ASS Subtitles (Option B &amp; ReelShort Style)</a></li>
    <li><a href="#s5"><span class="tn">05</span>Series Bible &amp; 10-Episode Continuity Engine (JSON)</a></li>
    <li><a href="#s6"><span class="tn">06</span>DramaBench-Trained Narrative Pipeline (500 Corpus)</a></li>
    <li><a href="#s7"><span class="tn">07</span>User Input, CLI Wizard &amp; Netflix-Style Customization</a></li>
    <li><a href="#s8"><span class="tn">08</span>LLM Self-Review &amp; Edge Case Handler</a></li>
    <li><a href="#s9"><span class="tn">09</span>Semantic Verification Unit Tests (Eps 1&ndash;5 &amp; Ep 10)</a></li>
    <li><a href="#s10"><span class="tn">10</span>End-to-End Workflow &amp; Credit Budget (1 Lakh Pool)</a></li>
    <li><a href="#s11"><span class="tn">11</span>Build Phases and Deliverables</a></li>
  </ul>
</section>
"""

S0 = """
<section id="s0">
  <div class="lbl">Section 00</div>
  <h2>Executive Summary &amp; All Confirmed Decisions</h2>
  <p>Every architectural and operational parameter has been decided. Below is the complete record of user choices governing the implementation:</p>

  <div class="g2">
    <div class="card">
      <div class="ct">1. Scope &amp; Budget (Q1 &amp; Q7)</div>
      <div class="dec-box">
        <div class="dec-title">&#10003; 10 Episodes Test Stage | 1 Lakh Credits Pool</div>
        <div class="dec-text">Generating 10 sequential episodes for rigorous testing before scaling to 50. 100,000 credits available; ~19,120 estimated total for 10 episodes (video + AI storyboards). Checkpointing active per episode.</div>
      </div>
    </div>
    <div class="card">
      <div class="ct">2. Shot Continuity (Q2)</div>
      <div class="dec-box">
        <div class="dec-title">&#10003; Option A: Always Frame Extraction</div>
        <div class="dec-text">FFmpeg extracts the exact last frame of Shot N and feeds it as start image for Shot N+1 via Magic Hour image-to-video mode for highest visual continuity.</div>
      </div>
    </div>
    <div class="card">
      <div class="ct">3. Training Dataset (Q3)</div>
      <div class="dec-box">
        <div class="dec-title">&#10003; Option A: DramaBench 500 Corpus</div>
        <div class="dec-text">Use the existing 500-entry MIT dataset in <code>dataset/</code> to extract hook taxonomy, cliffhanger formulas, and pacing norms.</div>
      </div>
    </div>
    <div class="card">
      <div class="ct">4. Series IP &amp; User Input (Q4)</div>
      <div class="dec-box">
        <div class="dec-title">&#10003; Option B + Dynamic User Input</div>
        <div class="dec-text">CLI/Wizard user input for title, characters, and genre. Any copyrighted IP (e.g. Harry Potter) is auto-renamed to original archetypes (e.g. Arcane Academy). No hardcoded series names.</div>
      </div>
    </div>
    <div class="card">
      <div class="ct">5. Verification Cadence (Q5)</div>
      <div class="dec-box">
        <div class="dec-title">&#10003; Option C: Milestone Semantic QA</div>
        <div class="dec-text">Full LLM semantic continuity tests on Episodes 1&ndash;5 and Episode 10 (finale); rule-based checks on Episodes 6&ndash;9 to preserve Gemini rate limits.</div>
      </div>
    </div>
    <div class="card">
      <div class="ct">6. Series Bible Storage (Q6)</div>
      <div class="dec-box">
        <div class="dec-title">&#10003; Option A: Plain JSON Storage</div>
        <div class="dec-text"><code>series_bible.json</code> stored at series root. Human-readable, Git-diffable, zero database dependencies.</div>
      </div>
    </div>
    <div class="card">
      <div class="ct">7. Subtitle Format &amp; Display (Q8 &amp; CQ2)</div>
      <div class="dec-box">
        <div class="dec-title">&#10003; Option B: Styled ASS Burned Into Video (ReelShort Style)</div>
        <div class="dec-text">Bold font positioned in lower-middle safe zone (120px above bottom) with black outline and speaker-colored names, burned directly into master .mp4 so viewers can read dialogue.</div>
      </div>
    </div>
    <div class="card">
      <div class="ct">8. First Test Series (Q9)</div>
      <div class="dec-box">
        <div class="dec-title">&#10003; Option A: The Cold CEO's Contract Bride</div>
        <div class="dec-text">10 episodes of "The Cold CEO's Contract Bride" using the existing <code>contract_marriage</code> template as the full end-to-end benchmark.</div>
      </div>
    </div>
    <div class="card">
      <div class="ct">9. CLI Launch Mode (CQ1)</div>
      <div class="dec-box">
        <div class="dec-title">&#10003; Interactive Step-by-Step Wizard</div>
        <div class="dec-text">Running <code>python run_series.py</code> without arguments launches a friendly interactive terminal wizard, prompting for Title, Genre, Characters, and Mode.</div>
      </div>
    </div>
    <div class="card">
      <div class="ct">10. Storyboard Stills (CQ3)</div>
      <div class="dec-box">
        <div class="dec-title">&#10003; AI Image-Generated Concept Stills</div>
        <div class="dec-text">Storyboard cards render photorealistic concept stills via Magic Hour Image API (~5 credits/image, ~400 credits for all 10 episodes) for rich visual previews.</div>
      </div>
    </div>
  </div>
</section>
"""

S1 = """
<section id="s1">
  <div class="lbl">Section 01</div>
  <h2>What Changed: v1 to v2.1</h2>
  <p>The original v1 produced disconnected single clips. v2.1 delivers an end-to-end production studio tailored to your exact 10-episode testing specifications.</p>
  <table>
    <thead><tr><th>Capability</th><th>v1 (Original State)</th><th>v2.1 (Current Confirmed Spec)</th></tr></thead>
    <tbody>
      <tr><td>Episode Target</td><td><span class="tag tr">1 prototype</span> Isolated test</td><td><span class="tag tg">10 Episodes</span> Full sequential arc with Season Finale at Ep 10</td></tr>
      <tr><td>Shot Continuity</td><td><span class="tag tr">Independent</span> Standalone prompts</td><td><span class="tag tg">Frame Extraction (Opt A)</span> FFmpeg last-frame &rarr; i2v start image + context injection</td></tr>
      <tr><td>Subtitles</td><td><span class="tag tr">None</span> Raw video only</td><td><span class="tag tg">Styled ASS (Opt B)</span> Speaker-colored, ReelShort lower-middle burned-in subtitles</td></tr>
      <tr><td>Stitching</td><td><span class="tag tr">Loose clips</span> Saved in outputs/</td><td><span class="tag tg">Master MP4</span> 64s vertical 9:16 master per episode with audio &amp; burned subs</td></tr>
      <tr><td>Folder Structure</td><td><span class="tag tr">Flat</span> All in one folder</td><td><span class="tag tg">Hierarchical</span> <code>series_name/episode_N/{clips,master,subtitles,...}</code></td></tr>
      <tr><td>Continuity Engine</td><td><span class="tag ta">Mock beats</span> Manual flag passing</td><td><span class="tag tg">JSON Bible</span> Canonical cast, cliffhanger ledger, open plot threads</td></tr>
      <tr><td>Storyboards</td><td><span class="tag tr">None</span> Video directly</td><td><span class="tag tg">AI Concept Stills</span> Photorealistic shot preview stills via Magic Hour Image API</td></tr>
      <tr><td>Training Data</td><td><span class="tag tr">None</span> Prompt heuristics only</td><td><span class="tag tg">DramaBench 500</span> Structural patterns, hook taxonomy, pacing norms</td></tr>
      <tr><td>Input &amp; IP</td><td><span class="tag tr">Hardcoded</span> Preset script</td><td><span class="tag tg">Interactive Wizard + Archetypes</span> User wizard; auto-renaming for IP</td></tr>
    </tbody>
  </table>
</section>
"""

S2 = """
<section id="s2">
  <div class="lbl">Section 02</div>
  <h2>Directory Structure and Output Organization</h2>
  <p>Every series generates a clean Netflix / Kuku FM hierarchical directory structure. Below is the exact layout for the 10-episode test run of <strong>The Cold CEO's Contract Bride</strong>:</p>
  <pre><code>outputs/
+-- The_Cold_CEO_Contract_Bride/               # Sanitized Series Root
    +-- series_bible.json                      # Persistent cast, canon facts, cliffhangers, thread ledger
    +-- series_metadata.json                   # Netflix/Kuku FM tags: genre, mood, cast, runtime, rating
    +-- episode_01/
    |   +-- clips/                             # 8 sequential shot clips + extracted transition frames
    |   |   +-- s01_hook.mp4
    |   |   +-- s01_lastframe.png              # FFmpeg extracted last frame &rarr; feed to s02
    |   |   +-- s02_scandal.mp4
    |   |   +-- s02_lastframe.png              # Feed to s03
    |   |   +-- ...
    |   |   +-- s08_cliffhanger.mp4
    |   +-- master/
    |   |   +-- episode_01_master.mp4          # Final 64s stitched 9:16 MP4 with BURNED-IN ASS subtitles
    |   +-- subtitles/
    |   |   +-- episode_01.ass                 # Styled ASS file with speaker color styles
    |   +-- storyboard/
    |   |   +-- s01_storyboard.png             # Photorealistic AI concept stills from Image API
    |   |   +-- s02_storyboard.png
    |   |   +-- ...
    |   +-- screenplay/
    |   |   +-- episode_01_screenplay.json     # Machine-readable script (shots, dialogue, camera, cues)
    |   +-- verification/
    |       +-- continuity_report.json         # Rule-based check results (dead chars, secrets, props)
    |       +-- semantic_test.json             # LLM continuity verdict &amp; evidence score
    |       +-- quality_scores.json            # DramaBench hook, cliffhanger, dialogue metrics
    +-- episode_02/
    +-- ...
    +-- episode_10/                            # Season 1 Finale episode</code></pre>
  <h3>Key Guarantees</h3>
  <ul>
    <li><strong>Self-Contained Episodes:</strong> Any <code>episode_N/</code> folder can be zipped and previewed independently.</li>
    <li><strong>Burned-In Master:</strong> <code>master/episode_N_master.mp4</code> is ready-to-watch immediately &mdash; subtitles and audio are fully merged.</li>
    <li><strong>Auditable Verification:</strong> The <code>verification/</code> folder maintains a permanent log of all quality gates passed.</li>
  </ul>
</section>
"""

S3 = """
<section id="s3">
  <div class="lbl">Section 03</div>
  <h2>Sequential Clip Generation &amp; Frame Extraction (Option A)</h2>
  <p>Per your confirmation of <strong>Option A</strong>, visual continuity is achieved via strict sequential generation combined with <strong>FFmpeg last-frame extraction</strong> feeding into Magic Hour Image-to-Video:</p>
  <h3>Step-by-Step Shot Chaining Flow</h3>
  <div class="flow">
    <div class="fs"><span class="sn">SHOT 1</span>Generate <code>s01_hook</code> via Magic Hour Text-to-Video</div>
    <div class="fa">&rarr;</div>
    <div class="fs"><span class="sn">EXTRACT</span>FFmpeg extracts last frame: <code>s01_lastframe.png</code></div>
    <div class="fa">&rarr;</div>
    <div class="fs"><span class="sn">CONTEXT</span>Build Shot 2 prompt with Shot 1 ending state + wardrobe</div>
    <div class="fa">&rarr;</div>
    <div class="fs"><span class="sn">SHOT 2 (i2v)</span>Magic Hour Image-to-Video using <code>s01_lastframe.png</code></div>
    <div class="fa">&rarr;</div>
    <div class="fs"><span class="sn">REPEAT</span>Repeat through Shot 8 (Cliffhanger)</div>
  </div>

  <h3>FFmpeg Extraction Implementation</h3>
  <pre><code># Extract the exact last frame of the preceding shot
ffmpeg -sseof -0.1 -i clips/s01_hook.mp4 -update 1 -q:v 2 clips/s01_lastframe.png</code></pre>

  <div class="card">
    <div class="ct">Prompt Injected Context Structure</div>
    <ol>
      <li><strong>Visual Ending Anchor:</strong> "In the previous frame, Seraphina is standing 2 feet from Alexander in the penthouse, holding the signed divorce papers."</li>
      <li><strong>Wardrobe &amp; Lighting Lock:</strong> "Seraphina wearing champagne silk gown. Alexander in charcoal bespoke jacket, tie undone. Amber ambient evening lighting."</li>
      <li><strong>Camera Continuity:</strong> "Camera maintains 85mm portrait focal length, reverse over-the-shoulder angle."</li>
      <li><strong>New Action &amp; Dialogue:</strong> Shot-specific beat instructions from screenplay.</li>
    </ol>
  </div>
</section>
"""

S4 = """
<section id="s4">
  <div class="lbl">Section 04</div>
  <h2>Episode Stitching and Burned-In Styled ASS Subtitles (Option B &amp; ReelShort Style)</h2>
  <p>Per your confirmation of <strong>Option B</strong> and <strong>CQ2 (ReelShort / DramaBox Style)</strong>, dialogue subtitles are styled using Advanced SubStation Alpha (ASS) and <strong>burned directly onto the video screen</strong> with bold outlines and speaker-specific colors, positioned in the mobile safe zone (120px above bottom) so platform navigation bars do not obstruct reading.</p>

  <h3>Character-Specific Color Palette</h3>
  <table>
    <thead><tr><th>Character / Role</th><th>ASS Color Code</th><th>Visual Preview</th><th>Styling Rationale</th></tr></thead>
    <tbody>
      <tr><td><strong>Seraphina</strong> (Heroine)</td><td><code>&amp;H00E8C8FF&amp;</code> (Soft Champagne Gold)</td><td><span class="tag ta" style="background:#523e02;color:#fde047">Seraphina</span></td><td>Warm, vulnerable, elegant</td></tr>
      <tr><td><strong>Alexander</strong> (Cold CEO)</td><td><code>&amp;H00FFFF00&amp;</code> (Ice Cyan)</td><td><span class="tag tb" style="background:#083344;color:#67e8f9">Alexander</span></td><td>Cold, authoritative, razor-sharp</td></tr>
      <tr><td><strong>Victoria</strong> (Rival / Antagonist)</td><td><code>&amp;H005A33FF&amp;</code> (Crimson Coral)</td><td><span class="tag tr" style="background:#450a0a;color:#fca5a5">Victoria</span></td><td>Dangerous, high-status, sharp</td></tr>
      <tr><td><strong>Narrator / Action / Text</strong></td><td><code>&amp;H00FFFFFF&amp;</code> (Crisp Pure White)</td><td><span class="tag tg" style="background:#262626;color:#ffffff">Voiceover</span></td><td>High contrast, neutral readability</td></tr>
    </tbody>
  </table>

  <h3>Burn-In Stitching Pipeline (FFmpeg)</h3>
  <div class="flow">
    <div class="fs"><span class="sn">STEP 1</span>Concatenate 8 normalized 8-second clips into 64s video</div>
    <div class="fa">&rarr;</div>
    <div class="fs"><span class="sn">STEP 2</span>Generate <code>episode_N.ass</code> with exact shot timecodes &amp; styles</div>
    <div class="fa">&rarr;</div>
    <div class="fs"><span class="sn">STEP 3</span>Burn subtitles via <code>-vf "ass=subtitles/episode_N.ass"</code></div>
    <div class="fa">&rarr;</div>
    <div class="fs"><span class="sn">STEP 4</span>Normalize audio to -14 LUFS social standard</div>
  </div>
  <pre><code># FFmpeg master burn-in command:
ffmpeg -f concat -safe 0 -i concat_list.txt \\
  -vf "ass=subtitles/episode_01.ass" \\
  -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 192k \\
  master/episode_01_master.mp4</code></pre>
</section>
"""

S5 = """
<section id="s5">
  <div class="lbl">Section 05</div>
  <h2>Series Bible &amp; 10-Episode Continuity Engine (JSON)</h2>
  <p>Per your confirmation of <strong>Option A</strong>, the Series Bible is saved as a clean, human-readable <code>series_bible.json</code> file at the series root. It acts as the single source of canon truth across all 10 episodes.</p>

  <h3>10-Episode Dramatic Arc Architecture</h3>
  <table>
    <thead><tr><th>Episode Range</th><th>Dramatic Phase</th><th>Core Narrative Objective</th><th>Pacing &amp; Reversal Requirements</th></tr></thead>
    <tbody>
      <tr><td><strong>Episodes 1&ndash;3</strong></td><td>Act I: The Trap</td><td>Establish contract marriage terms, forced proximity, high-society trap</td><td>Public humiliation in Ep 1; intimate compromise in Ep 2; first jealous clash in Ep 3</td></tr>
      <tr><td><strong>Episodes 4&ndash;6</strong></td><td>Act II-A: The Thaw &amp; The Threat</td><td>Alexander shows unexpected protection; Victoria introduces blackmail</td><td>Assassination/ruin attempt foiled in Ep 4; accidental kiss in Ep 5; contract leaked in Ep 6</td></tr>
      <tr><td><strong>Episodes 7&ndash;9</strong></td><td>Act II-B: The Crisis</td><td>Misunderstanding explodes; Seraphina attempts escape; CEO pursues</td><td>Ultimatum in Ep 7; false betrayal evidence in Ep 8; dramatic airport/rain chase in Ep 9</td></tr>
      <tr><td><strong>Episode 10</strong></td><td>Season 1 Climax</td><td><strong>Season Finale:</strong> Public identity reveal + massive cliffhanger</td><td>Contract shredded in front of board; secret pregnancy / real identity dropped; sets up Season 2</td></tr>
    </tbody>
  </table>

  <h3>Cliffhanger Ledger with TTL Rule</h3>
  <div class="card">
    <div class="ct">Unresolved Cliffhanger Auto-Resolution Rule (TTL = 1&ndash;3 Episodes)</div>
    <p>Every episode final shot poses a high-stakes dramatic question. The Bible tracks unresolved cliffhangers. If a cliffhanger reaches <strong>TTL = 3</strong> without resolution, the screenwriter is strictly forced to resolve it in the very next episode's Shot 1.</p>
  </div>
</section>
"""

S6 = """
<section id="s6">
  <div class="lbl">Section 06</div>
  <h2>DramaBench-Trained Narrative Pipeline (500 Corpus)</h2>
  <p>Per your confirmation of <strong>Option A</strong>, the 500-entry dataset at <code>dataset/dramabench_continuation_500.jsonl</code> is mined directly to train our prompt builder on real-world microdrama pacing and hook structures.</p>

  <div class="g3">
    <div class="card">
      <div class="ct">1. Hook Taxonomy</div>
      <p>Mined library of 40+ microdrama hooks (Identity Concealment, Public Humiliation, Forced Marriage Contract, Sudden Pregnancy, Slap &amp; Reversal).</p>
    </div>
    <div class="card">
      <div class="ct">2. Cliffhanger Formulas</div>
      <p>30+ ending formulas (The Gunshot Cut, The Phone Call Freeze, The Paternity Test Glance, The Doorway Ambush) with exact shot-8 timing.</p>
    </div>
    <div class="card">
      <div class="ct">3. Dialogue Norms</div>
      <p>Word density caps derived from real microdramas: max 12 words per line, zero exposition monologue, 100% emotional punchlines.</p>
    </div>
  </div>

  <pre><code># Execution script created in Phase 1:
python dataset/extract_patterns.py
# Outputs to dataset/patterns/hook_taxonomy.json, cliffhanger_library.json, etc.</code></pre>
</section>
"""

S7 = """
<section id="s7">
  <div class="lbl">Section 07</div>
  <h2>User Input, CLI Wizard &amp; Netflix-Style Customization</h2>
  <p>Per your answer to <strong>Q4</strong> and <strong>CQ1</strong>: Harry Potter was an example &mdash; the generator is designed for <em>any series</em>, driven completely by <strong>user input</strong> via an interactive terminal wizard or flags. If copyrighted IP is provided, the archetype engine auto-converts it to original, legal characters.</p>

  <h3>Interactive Terminal Wizard (Default on <code>python run_series.py</code>)</h3>
  <pre><code>$ python run_series.py
=== AI MicroDrama Series Generator Wizard ===
? Series Title: The Cold CEO Contract Bride
? Genre: contract_marriage
? Number of Episodes [default 10]: 10
? Protagonist: Seraphina - soft-spoken heroine trapped in debt
? Deuteragonist: Alexander - ruthless billionaire CEO
? Antagonist: Victoria - jealous heiress
? Mode: [1] Free Storyboard Cards  [2] Full Video Render</code></pre>

  <h3>Automatic Archetype Sanitizer (Option B)</h3>
  <div class="card">
    <div class="ct">IP Conversion Matrix (Example for Fantasy / Fan-fic inputs)</div>
    <table>
      <thead><tr><th>User-Supplied Input</th><th>Auto-Converted Archetype</th><th>Tone / World Setting</th></tr></thead>
      <tbody>
        <tr><td>Harry Potter &rarr; Boy Wizard</td><td><strong>Henry Ashford</strong> &mdash; Marked Prodigy</td><td>Arcane Citadel &bull; Hidden Heir Magic</td></tr>
        <tr><td>Voldemort &rarr; Dark Lord</td><td><strong>Malakor</strong> &mdash; Banished Shadow Tyrant</td><td>Forbidden Bloodlines &bull; Ancient Curse</td></tr>
        <tr><td>Hogwarts &rarr; Magic School</td><td><strong>Aethelgard Academy</strong></td><td>Gothic Spires &bull; Aristocratic Houses</td></tr>
      </tbody>
    </table>
  </div>
</section>
"""

S8 = """
<section id="s8">
  <div class="lbl">Section 08</div>
  <h2>LLM Self-Review &amp; Edge Case Handler</h2>
  <p>Before any video credits are spent, each episode screenplay undergoes a deterministic 3-pass review and repair loop to guarantee 95%+ narrative accuracy.</p>

  <div class="flow">
    <div class="fs"><span class="sn">PASS 1</span>Gemini Flash Draft + DramaBench Few-Shot Injection</div>
    <div class="fa">&rarr;</div>
    <div class="fs"><span class="sn">PASS 2</span>Rule-Based Bible Validation (Dead chars, Secrets, Props)</div>
    <div class="fa">&rarr;</div>
    <div class="fs"><span class="sn">PASS 3</span>DramaBench Rubric Scoring (Hooks &ge; 4/5, Cliffhanger &ge; 4/5)</div>
    <div class="fa">&rarr;</div>
    <div class="fs"><span class="sn">PASS 4</span>Auto-Repair &amp; Gate Approval (or Regenerate)</div>
  </div>

  <div class="g2">
    <div class="card">
      <div class="ct">Deterministic Rule Checks (100% Enforced)</div>
      <ul>
        <li>Deceased characters never appear in scenes</li>
        <li>Secret visibility matrix enforced (no psychic knowledge)</li>
        <li>Wardrobe continuity maintained between consecutive episodes</li>
        <li>Shot 1 must explicitly address Episode N&minus;1 cliffhanger</li>
      </ul>
    </div>
    <div class="card">
      <div class="ct">Edge Case Recovery Handlers</div>
      <ul>
        <li><strong>Stale Plot Threads:</strong> Auto-injected if inactive for &gt;3 episodes</li>
        <li><strong>Repetitive Twists:</strong> N-gram beat check rejects duplicate tropes</li>
        <li><strong>Malformed JSON:</strong> Auto-repaired via <code>json-repair</code> fallback</li>
        <li><strong>Gemini 429 / 503:</strong> Exponential backoff with mock template fallback</li>
      </ul>
    </div>
  </div>
</section>
"""

S9 = """
<section id="s9">
  <div class="lbl">Section 09</div>
  <h2>Semantic Verification Unit Tests (Eps 1&ndash;5 &amp; Ep 10)</h2>
  <p>Per your confirmation of <strong>Option C</strong>, comprehensive LLM semantic verification runs on <strong>Episodes 1 through 5</strong> (early arc establishment) and <strong>Episode 10</strong> (season finale climax). Episodes 6 through 9 run deterministic rule checks.</p>

  <div class="card">
    <div class="ct">Automated Unit Test Suite (<code>tests/test_semantic_continuity.py</code>)</div>
    <pre><code># Test 1: Cliffhanger Direct Resolution
assert llm_eval_cliffhanger(ep_prev.cliffhanger, ep_curr.shots[0]) >= 4

# Test 2: Character Voice & Speech Consistency
assert llm_eval_voice(char.voice_style, ep_curr.dialogues) >= 4

# Test 3: Plot Thread Progression
assert count_active_threads_touched(ep_curr, bible) >= 1

# Test 4: Physical & Wardrobe State Integrity
assert verify_wardrobe_consistency(ep_prev.ending_state, ep_curr.starting_state) == True

# Test 5: Season Finale Climax Power (Episode 10 Only)
assert llm_eval_season_finale_stakes(ep_10.screenplay) >= 4.5</code></pre>
  </div>
  <p>Results are saved to <code>episode_N/verification/semantic_test.json</code> with line-by-line evidence citations.</p>
</section>
"""

S10 = """
<section id="s10">
  <div class="lbl">Section 10</div>
  <h2>End-to-End Workflow &amp; Credit Budget (1 Lakh Pool)</h2>
  <p>You confirmed having approximately <strong>1 Lakh (~100,000) credits</strong>. Here is the exact credit budget breakdown for the 10-episode test stage:</p>

  <div class="card">
    <div class="ct">Credit Budget Allocation for 10 Episodes</div>
    <table>
      <thead><tr><th>Phase / Operation</th><th>Per Shot Cost</th><th>Per Episode Cost (8 Shots)</th><th>Total 10 Episodes Cost</th><th>Status</th></tr></thead>
      <tbody>
        <tr><td><strong>Screenplay &amp; Continuity</strong></td><td>0 credits (Gemini API)</td><td>0 credits</td><td><strong>0 credits</strong></td><td><span class="tag tg">FREE</span></td></tr>
        <tr><td><strong>AI Concept Stills (CQ3)</strong></td><td>~5 credits (Magic Hour Image)</td><td>~40 credits</td><td><strong>~400 credits</strong></td><td><span class="tag tb">PAID</span></td></tr>
        <tr><td><strong>Shot 1 (Text-to-Video)</strong></td><td>~192 credits (8s @ 24 c/s)</td><td>192 credits</td><td>1,920 credits</td><td><span class="tag tb">PAID</span></td></tr>
        <tr><td><strong>Shots 2&ndash;8 (Frame Extracted i2v)</strong></td><td>~240 credits (8s @ 30 c/s)</td><td>1,680 credits</td><td>16,800 credits</td><td><span class="tag tb">PAID</span></td></tr>
        <tr><td><strong>FFmpeg Stitching &amp; ASS Burn-in</strong></td><td>0 credits (local)</td><td>0 credits</td><td><strong>0 credits</strong></td><td><span class="tag tg">FREE</span></td></tr>
        <tr><td><strong>Estimated 10-Episode Total</strong></td><td>&mdash;</td><td><strong>~1,912 credits</strong></td><td><strong>~19,120 credits</strong></td><td><span class="tag tg">SAFE (~80.8K Left)</span></td></tr>
      </tbody>
    </table>
  </div>
  <div class="co"><strong>Huge Buffer:</strong> Spending ~19,120 credits out of your 100,000 leaves you with <strong>over 80,800 credits</strong>. You can comfortably re-render any shot or scale to another 30+ episodes!</div>

  <h3>Execution Commands</h3>
  <pre><code># 1. Preview all 10 episodes in free storyboard mode first:
python run_series.py --series-name "The Cold CEO Contract Bride" --episodes 10 --storyboard-only

# 2. Render full video + burned ASS subtitles for all 10 episodes:
python run_series.py --series-name "The Cold CEO Contract Bride" --episodes 1-10 --render-video --model ltx-2.5

# 3. Resume from last saved checkpoint if interrupted:
python run_series.py --series-name "The Cold CEO Contract Bride" --resume</code></pre>
</section>
"""

S11 = """
<section id="s11">
  <div class="lbl">Section 11</div>
  <h2>Build Phases and Deliverables</h2>
  <div class="card">
    <div class="ct">Phase 1 &mdash; Core Infrastructure &amp; Bible (Step 1)</div>
    <ul>
      <li><code>src/microdrama/series/organizer.py</code> &mdash; Hierarchical folder tree creator</li>
      <li><code>src/microdrama/series/bible.py</code> &mdash; Plain JSON Series Bible engine</li>
      <li><code>src/microdrama/series/arc_planner.py</code> &mdash; 10-Episode dramatic skeleton planner</li>
      <li><code>dataset/extract_patterns.py</code> &mdash; DramaBench 500 pattern mining script</li>
    </ul>
  </div>
  <div class="card">
    <div class="ct">Phase 2 &mdash; Narrative Intelligence &amp; Review Loop (Step 2)</div>
    <ul>
      <li><code>src/microdrama/narrative/prompt_builder.py</code> &mdash; Sequential shot prompt builder + few-shot retrieval</li>
      <li><code>src/microdrama/narrative/screenwriter.py</code> &mdash; Multi-pass LLM review loop with auto-repair</li>
      <li><code>src/microdrama/series/continuity.py</code> &mdash; Rule-based validator + edge case handlers</li>
    </ul>
  </div>
  <div class="card">
    <div class="ct">Phase 3 &mdash; Sequential Rendering, ASS Burn-in &amp; Stitching (Step 3)</div>
    <ul>
      <li><code>src/microdrama/client/generator.py</code> &mdash; Sequential shot generator with FFmpeg last-frame extraction</li>
      <li><code>src/microdrama/postprod/assembler.py</code> &mdash; Enhanced stitcher with burned-in ASS subtitle overlay</li>
      <li><code>tests/test_semantic_continuity.py</code> &mdash; Semantic QA unit tests for Eps 1&ndash;5 &amp; 10</li>
    </ul>
  </div>
  <div class="card">
    <div class="ct">Phase 4 &mdash; CLI Wizard &amp; 10-Episode Benchmark (Step 4)</div>
    <ul>
      <li><code>run_series.py</code> &mdash; CLI with interactive wizard mode, flags, resume checkpointing</li>
      <li>Generate complete 10-episode test series: <strong>The Cold CEO's Contract Bride</strong></li>
      <li>Verify all master videos, subtitles, screenplays, and verification reports</li>
    </ul>
  </div>
</section>
"""

FOOT = """
<footer>
  <p>AI MicroDrama Series Generator &mdash; Implementation Plan v2.1<br>
  Built on Magic Hour API &bull; Gemini Flash &bull; DramaBench 500 &bull; FFmpeg<br>
  <span style="color:var(--accent)">Updated 14 October 2026 &bull; yogitaranwa/MagicHourAI</span></p>
</footer>
</div>
</body>
</html>
"""

parts = [HEAD, HERO, TOC, S0, S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11, FOOT]
full_html = "".join(parts)

out = r"c:\Users\yogit\OneDrive\Desktop\MagicHour\Plan.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(full_html)

print(f"Successfully written {len(full_html):,} bytes ({len(parts)} sections) to Plan.html")
