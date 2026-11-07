# H3Film provenance findings, 2026-10-25

## User-supplied origin

At 2026-10-20 1:56:28 AM IST, the user supplied this exact Drive archive and wrote: "project-owner shared this github repo / check the code now / unzip it and make a folder named li-yunshen-project-owner-13 oct".

- Message ID: `[private-record-reference]`
- Original archive: [private-project-source]
- Name: `h3-film-main.zip`
- Size: 2,373,719,592 bytes
- Uploaded/modified: 2026-10-20 1:54:39/1:55:22 AM IST
- Owner: `account@example.invalid`; current permission: anyone with link can read

At 2026-10-20 2:30:03 AM IST, the user clarified: "It is approach of project-owner / Not project-owner bro / He forked the repo".

- Message ID: `[private-record-reference]`

## Curated source copy

- Source-review ZIP: [private-project-source]
- Size: 2,875,652 bytes
- SHA256: `70b15f46f545744e96d235631f46f0450f74800a58806908fa64d75775794ebc`
- Extracted root: `h3-film-main`
- Extracted files: 879
- No `.git` directory was present in the curated source copy.

## Self-identified upstream and version evidence

Original source `README.md` line 21 says: `[private-project-source] (private) is the repo to build from.`

Original source `docs/history.md` line 11 says the repo was cut from the lab at `5c20bcc`. Original source `docs/lab/notes.md` calls the clean repo status `5755047`. Original source `README.md` line 3000 says changes from `df63897` and `5755047` were deliberately left out of some approved-film behavior and are available in repo history. These are internal source labels, not a verified archive HEAD commit.

The original source `README.md` line 103 says the repo was cut on 2026-10-12. The user's requested folder label was `li-yunshen-project-owner-13 oct`.

## GitHub availability check

A signed-out cloud-browser check on 2026-10-25 confirmed:

- `[private-project-source] exists publicly and shows 19 repositories.
- `[private-project-source] returns GitHub 404 signed out.
- Public repository search on project-owner's profile for `h3` has no matches.

This is consistent with a private repo, but does not prove the private repo's current existence, HEAD commit, or license. GitHub integration is not connected, so no authenticated API check was available.

## License

- No root `LICENSE` file was present in the curated source copy.
- Root `package.json` has `"private": true`.
- The root README has a licensing review section for third-party assets, but no license grant for the h3-film source code itself.
- The supportable status is private reference material shared through project-owner at the user's direction, not public redistributable open source.

## Restored vendor hash comparison against the source-review ZIP

After the bounded correction, these private vendor files are byte-exact to the source-review ZIP:

- `README.md`: `b0484916330f86821b9b216ee6b322392bf91a88fb03f84ef4cc3ec4a0f7d9d4`
- `agent/h3film/check-prompt.mjs`: `bda7f48d5e694cc00f68e8c0bc73bfd21c68e053ef169120cb7a8e0cc997d7e4`
- `agent/h3film/join.mjs`: `68cb16b72374f33735f05ded789c68944920009f4bfbf6faa673dd0ef924832c`
- `agent/h3film/render-all.mjs`: `2a55fe1b77192530a90683b03b21aa013946b17e99a90ae7c50367d1bf1c4d67`
- `research/h3/modal_h3.py`: `842ecc59ce09f6fedf2aebf67f0876b0411c15f63942761084fc2f5aa71792c1`
- `research/h3/runpod/comfy_r2v.py`: `3587ca8a94d95f0e7c9a06045518d93130b77a202e1bacd9c784ef244bfd537e`
- `research/h3/runpod/r2v_v1.json`: `1d927b51d05405fa0d2683593822882c7cf8a6d5f9742817863338e7efe069a3`
- `research/h3/soundtrack.mjs`: `ea609c9f84b0dbfff3fb0d7eb4db4badee93a087a7406928e56458dd46ce17aa`
- `research/h3/tools-film.mjs`: `c3622c146d020541f75a725dfec895248481957d2f4717c09e5912fcf123b376`

The corrective Modal wrapper is preserved separately as `magicdrama/audiofirst/modal_h3_corrective.py`, SHA256 `d8f33de8b267980b1b680ab4ee51bd4ebe81c5ba29cfd3cd3a793fdaf5a35486`. Its differences from the original wrapper are transport, safety and reliability controls: one max container, 1800s timeout, RTX PRO 6000 first, BF16 weight omitted, weight size and hash verification added, SageAttention disabled on all GPUs, original SageAttention build omitted.

## Conclusion

The exact recoverable origin is the user-supplied Drive archive above, identified by the user as project-owner's shared GitHub repo and by its own README as project-owner's private `li-yunshen-project-owner/h3-film` repo. The archive content self-identifies a 2026-10-12 repo cut and internal lab/clean-repo commit labels, but the exact archive HEAD commit and source-code license cannot be verified from the available ZIP or public GitHub route.

The private vendor baseline is now byte-exact to the user-supplied source-review ZIP, with original comments and attribution preserved. The precise claim is: faithful to the user-supplied source archive, not verified upstream HEAD.
