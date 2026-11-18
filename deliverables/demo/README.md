# ClipAgent real-video demonstration

- **ClipAgent-real-demo.mp4**: continuous real browser session with Chinese chapter captions; actual export appended with original audio.
- **NASA-edited.mp4 / NASA-edited.srt**: files downloaded from the application's export buttons.
- **ClipAgent-real-demo.zh.srt / chapters.json**: instructional captions and chapter timing.
- **video-verification.json**: video properties, checksum and full-decoding result.

The input is a real 61-second excerpt from NASA's *#AskNASA – How Can I Be An Astronaut?*, prepared from seconds 113–174 of the official original. Source: [NASA asset collection](https://images-assets.nasa.gov/video/NHQ_2020_0302_AskNASA%20-%20How%20can%20I%20be%20an%20Astronaut/collection.json). Credit: NASA. Educational demonstration; no NASA endorsement implied. See `sample_data/nasa/` for provenance and hashes.

The browser performs real uploads and edits against the running local application. Processing waits remain in the recording. The visible pointer and Chinese captions are instructional annotations. The browser recording section is silent; the appended exported result contains original audio. Automatic subtitles were not manually corrected and can contain recognition errors.

Reproduce with `docs/REAL_VIDEO_DEMO.md`. Test summaries are in `docs/TEST_RESULTS.md` and `evaluation/browser_results/`. This is a curated demonstration, not a general editing-quality benchmark.
