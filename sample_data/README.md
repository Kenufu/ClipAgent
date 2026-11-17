# Public sample and reproducible demonstration

The included 23.315-second WAV is LibriSpeech test-clean utterance 6930-75918-0003, downloaded from NVIDIA's TensorRT-Model-Connect test fixtures. See provenance.json for its source URL, authors, SHA256 and CC BY 4.0 attribution. The license text and the supplier's attribution are retained in evidence/.

The author attribution is Vassil Panayotov, Guoguo Chen, Daniel Povey and Sanjeev Khudanpur, with the original LibriVox readers. Original corpus: https://www.openslr.org/12/ . Fixture attribution: https://github.com/NVIDIA/TensorRT-Model-Connect/blob/main/ASSET_LICENSES.md . License: https://creativecommons.org/licenses/by/4.0/ . No endorsement is implied.

Run `.venv/bin/python scripts/run_public_sample.py` after downloading the model as described in the root README. This creates static_audio_wrapper.mp4 with a visibly labelled synthetic title card, transcribes actual speech, plans and renders an output, checks the result and writes evaluation/public_results/. The WAV is existing public data; the generated title card is not original video content. No independent human score or WER is claimed without an independently retrieved reference.

Ordinary task: upload static_audio_wrapper.mp4, set target to 23 seconds, choose landscape and leave required topics blank. Changed request: request portrait orientation. Failure task: require quantum teleportation, which is absent. For a three-source demonstration, run scripts.make_demo on macOS, or use user-owned English MP4s.

Three pre-generated project demo MP4s are included in demo/. They use project-written narration from scripts/make_demo.py and synthetic title cards, not participant data. Upload these directly on any supported platform; local speech synthesis is not required to use the included files. They can also be copied to data/demo/ to enable the one-click demo button.
