# Guideline compliance matrix

Based on the supplied COMP7608B Final Project Student Guideline. Deadline: 25 November 2026, 23:59 Hong Kong time. Demo sessions: 1 or 8 December, assigned by the course. Report/code and presentation weights: 50% and 30%; proposal: 20%.

| Guideline item | Evidence supplied | Status / qualification |
| --- | --- | --- |
| Identifiable users and needs | Report sections 1–2 | Students/presenters editing English spoken recaps |
| Complete autonomous system | Architecture and service controller | Working deterministic controller with ASR; course approval of proposal scope reduction remains unconfirmed |
| Decisions, tools, observations, stopping | Code map, traces, three-render bound | Implemented within declared limited scope |
| Proposal continuity | Report scope table | Explicitly discloses unimplemented LLM, vision, memory and original dataset |
| Model/version, prompts, tools, data/state | README, architecture, public provenance, AI record | Runtime has no generative planner prompts |
| At least two failures | System tests and traces | Render/decode/queue fault injection, impossible duration, corrupt input, missing evidence |
| Non-functional checks | Report, measured latency, local storage design | Full workload, human usability, energy and network audit not measured |
| Baseline and evaluation | 18 cases × 3 methods, CSV/JSON and traces | Synthetic developer-authored component cases; no human ratings |
| Real media execution | Public WAV wrapper and system results | One public speech sample; not original video benchmark |
| Runnable standalone app | app.py, README, pinned dependencies | No notebook needed |
| Ordinary/changed/failure inputs | sample_data README, cases, demo guide | Supplied |
| Code snapshot and exact version | Submission ZIP, SHA256 manifest, Git history | ZIP includes source even when GitHub is provided |
| AI declaration and prompts | AI_USE_DECLARATION and prompts record | Partial retained history disclosed |
| Contributions and attribution | CONTRIBUTIONS, WORK_LOG, licenses | Individual division deferred until team confirmation |
| Report PDF | deliverables/Group59-ClipAgent-Final-Report.pdf | Review copy pending contribution confirmation |
| Live pitch/demo/Q&A | PPTX/PDF and DEMO_GUIDE | Live demo still required; deck does not replace it |

Submission is a report PDF plus a source ZIP. Keep the original proposal containing student IDs/emails outside the public repository. Names are included as required. Do not present the remaining course or human confirmations as completed.
