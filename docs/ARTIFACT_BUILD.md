# Optional document build

The app, tests and evaluation require only requirements.txt. Document authoring is optional.

Report: install requirements-artifacts.txt and run `python -m scripts.build_report`. Markdown is in docs/FINAL_REPORT.md.

Deck: scripts/build_presentation.mjs uses the bundled Codex @oai/artifact-tool and presentation validation utilities (bundle 26.1112.11217). Set `CLIPAGENT_ARTIFACT_RUNTIME` to the dependencies directory, `CLIPAGENT_PRESENTATION_SKILL` to the installed presentations skill directory and `RUNTIME_NODE_MODULES` to the runtime's node/node_modules. Execute using the bundled Node. The deck is rendered to .presentation-build/ and the finalizer validates native tables, fonts, geometry and PPTX import. Choose a new PRESENTATION_NAME when rebuilding an existing final file.

The bundled PDF exporter has a missing standard-font module in this environment. `python -m scripts.build_slide_pdf` creates the PDF from all 10 reviewed slide renders. The PPTX retains editable text, tables and diagram shapes; the companion PDF is a raster presentation copy. No artifact-tool dependency is needed to open the delivered PPTX or PDF.

Final PDFs/PPTX and submission ZIP are in deliverables/. They are local outputs; source, data provenance and results are tracked in Git.
