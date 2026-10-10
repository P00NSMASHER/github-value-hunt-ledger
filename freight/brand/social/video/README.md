# RETALLY | Presenter-led video production acceptance contract

This directory contains the source-controlled creative direction for RETALLY video production, established after reviewing the owner-supplied 27.1-second reference Reel.

- [RETALLY_DIRECTOR_BRIEF.md](RETALLY_DIRECTOR_BRIEF.md): production brief, screen-by-screen timing, narrative, source-media rules, exact brand language, spoken pronunciation, and fail-closed release gates.
- [storyboard.json](storyboard.json): machine-readable editor storyboard, illustrative detention arithmetic and required human acceptance checks.

## Companion offline QA package

The owner-facing **RETALLY_VIDEO_PRODUCTION_KIT_2026-10-10.zip** produced in ChatGPT contains this brief plus `check_video.py`, `test_check_video.py`, and a matching local `storyboard.json`. Those scripts are part of the delivered downloadable package, **not** tracked in this repository directory. Extract the ZIP and run:

```bash
python -m unittest discover -v
python check_video.py ACTUAL_FINISHED_VIDEO.mp4 --out qc_outputs/
```

The inspector checks the **rendered MP4**, audio continuity, dimensions, framerate, runtime and frame samples. Sound measured in an audio stream is not proof that narration is actually intelligible. A passing technical report never changes publication status to GO; a human must approve the actual video, correctly hear **re-tally**, inspect captions/evidence and verify rights.

## Hard limits

No paid generation, unrelated changes, new scheduled tasks or publication are authorized by this document. The original Facebook Reel is a **style reference only**; do not reuse the source presenter's face, footage, voice, music, brand or captions. No fictional buyer data or hypothetical discrepancy may be presented as a real recovered amount.
