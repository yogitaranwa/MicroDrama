# E01 timed voice and coverage plan, v4.3

The final voice render is 49.40 seconds across 15 lines. The episode plan is 100 seconds, leaving room for entry, trolley impact, table/chandelier action, reactions and music. Line boundaries below come from waveform silence inspection of the final MP3, not the API normalized alignment.

| Beat | Target time | Visual anchor | Dialogue placement |
|---|---:|---|---|
| 1 | 0.0-7.0 | shot01 entry spark | none |
| 2 | 7.0-15.0 | shot02 Draconia pull | line 1 at 8.00-12.27 |
| 3 | 15.0-24.0 | shot03 floor-warning insert | line 2 at 16.00-19.54; line 3 at 20.00-21.41 |
| 4 | 24.0-32.0 | shot04 masked window reflection | line 4 at 25.20-27.19 |
| 5 | 32.0-41.0 | shot05 arrow volley timing | line 5 at 33.00-35.92; line 6 at 36.80-39.08 |
| 6 | 41.0-50.0 | shot06 ward mark | line 7 at 42.50-44.37; line 8 at 45.00-48.16 |
| 7 | 50.0-59.0 | shot07 strings wand | line 9 at 51.00-54.57 |
| 8 | 59.0-67.0 | shot08 armor/trolley lower-body insert | line 10 at 60.50-63.37 |
| 9 | 67.0-75.0 | shot09 trolley/masked figure | none |
| 10 | 75.0-84.0 | shot10 floor grid/red table | line 11 at 76.50-78.62; line 12 at 79.50-83.63 |
| 11a | 84.0-88.0 | shot11a table/chandelier action | none |
| 11b | 88.0-91.5 | shot11b masked marks | line 13 at 88.30-89.66 |
| 12a | 91.5-95.0 | shot12a Harry marks close | line 14 at 92.00-93.76 |
| 12b | 95.0-100.0 | shot12b Draconia reaction | line 15 at 95.50-99.40 |

## Waveform-derived source line boundaries

1. 0.00-4.27: "Potter, don't turn around. Take my hand and move."
2. 5.04-8.58: "The floor marks anyone who stops. Keep dancing."
3. 9.22-10.63: "Tell me you're not serious."
4. 11.05-13.03: "That reflection is copying us."
5. 13.63-16.55: "The arrows land after the second beat."
6. 17.14-19.42: "Then move on the beat, not after it."
7. 19.96-21.83: "You knew what this was."
8. 22.39-25.55: "It's a Malfoy ward mark. I thought it was dead."
9. 26.34-29.91: "The music is carrying the curse. Cut those strings."
10. 30.58-33.45: "The suits of armor are moving. We need that trolley."
11. 34.05-36.17: "The floor is pulling us into the pattern."
12. 36.77-40.90: "Then we break it. Left side, three beats, red table."
13. 41.38-42.61: "They've marked us both."
14. 43.25-45.01: "You knew more than you said."
15. 45.50-49.40: "I sent you a warning. Someone made sure it never reached you."

## Coverage decisions

- Shot 8 uses a wider lower-body crop from v39 so armor, the trolley, Harry's robe tail, formal shoes and Draconia's gown/shoes are visible without the rejected white-sleeve/no-robe torso.
- Shot 11 is split: 11a supplies the missing table-flip/chandelier causality; 11b supplies the marks and masked figure. This is an explicit coverage change, not a silent action drop.
- Shots 2 and 5 are different crops from the same accepted two-shot source. Treat them as separate action beats and do not restart the dancers' temporal position.
- Shots 11b and 12a are a full-frame to cut-in pair from the same source. Treat 12a as a closer continuation of the same instant, not a new time reset.
- Magic Hour image-to-video takes one start image and an optional end image only. It does not hard-pin intermediate stills; the still sequence is the anchor and QA gate, not a guarantee of every generated mid-frame.
