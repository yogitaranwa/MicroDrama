# Audio notes
- v8: 7 slow lines rewritten with shorter words (same meaning, full sentences). 17 lines, 99 s.
- Per-line tempo 1.31-1.50 (v7 had every line at 1.5). Gate (WhisperX base, phrase WPM, band 290-360), measured in 3 chunks because the sandbox runs out of memory on a 99 s file: 30 phrases, median 326, mean 324, min 224, max 437.
- Raw Chatterbox speed is 140-250 WPM; cfg_weight barely moves it, word choice does.
- v9 (option B script, 19 lines): Chatterbox 0.1.2 on Kaggle T4 (needs setuptools<81 for the watermarker). Dialogue track 98.5 s (silent inserts and the cliffhanger add about 10 s on the timeline). Per-line tempo 1.155-1.5 (3 lines at the cap). Gate (WhisperX base, 3 chunks, all 478 words aligned): 19 phrases, median 334, mean 335, min 296, max 438, inside the 290-360 band.
