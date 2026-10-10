# RETALLY video production kit (October 10, 2026)

This project turns the owner-approved creative reference into a **testable production specification**, without falsely calling a draft video finished.

- `RETALLY_DIRECTOR_BRIEF.md`: scene-by-scene 29.5-second portrait production plan, pronunciation, exact hypothetical arithmetic, visual direction and acceptance gates.
- `storyboard.json`: machine-readable locked script, timing and brand tokens.
- `check_video.py`: video delivery QC — format, audio coverage, peak/RMS checks, timed video frames, and a JSON acceptance report. **Human visual, music rights, and actual pronunciation checks remain required.**
- `test_check_video.py`: unit tests on math, audio coverage and release gates.

## Validate an export

```bash
python check_video.py RETALLY_candidate.mp4 --out qc_outputs/
```

A `report.json`, `contact_sheet.jpg`, and audio samples are written to the output folder. A technical pass never claims that a generic or poor-looking video has passed creative QA. The report intentionally remains **HOLD** until the actual rendered file has been visually reviewed, the brand pronunciation heard, and rights cleared.

## Important

No video rendering, publication, Meta/YouTube account change, paid ad, billing modification or schedule is performed by this kit. The original presenter/audio in the reference Reel are for editorial analysis only, not assets to copy or impersonate. This preproduction kit does not invent missing presenter footage or claim that a professionally synchronized on-camera speaker has been created.