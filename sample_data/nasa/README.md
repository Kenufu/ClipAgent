# Real NASA video example

Credit: NASA, **#AskNASA – How Can I Be An Astronaut?** (2020).

This folder contains a 61-second excerpt from the official 233.28-second video. Preparation takes source seconds 113–174, keeps the original moving images and audio, and re-encodes at the native 640×360 resolution. The selection was made by the demo author before upload; it is not an example of automatic visual scene selection. The excerpt discusses astronaut training and spacewalks.

The exact official download URL, preparation interval, SHA256 hashes, and media properties are in `provenance.json`. Reproduce it with `python -m scripts.prepare_nasa_demo`. The complete upstream download is kept in ignored local `data/recording-source/`, not bundled in Git.

Source: [NASA official asset collection](https://images-assets.nasa.gov/video/NHQ_2020_0302_AskNASA%20-%20How%20can%20I%20be%20an%20Astronaut/collection.json). Usage follows [NASA Images and Media Usage Guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/): this is an attributed educational software demonstration, with no NASA endorsement implied. NASA identifiers are not adopted as ClipAgent branding. No third-party rights are claimed.

The example is curated and the author inspected an earlier full-video transcription before choosing supported topics. The recorded browser run uploads the excerpt and performs its own real transcription, planning, rendering, and validation. There are no supplied transcripts, substituted outputs, or simulated backend states. It is not a held-out benchmark. ASR and lexical selection can still be incorrect.
