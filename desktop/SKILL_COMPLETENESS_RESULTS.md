# Project Edition 1.6.2 skill-coverage candidate

Project Edition 1.6.3 retains the skill-coverage update and removes the redundant company metadata row when the project heading already shows `Company Name: #Confidential`. When reopening 1.6.2 drafts, only an exact duplicate default row under the confidential heading is removed; other edited text is preserved. Previous 1.6.2 installers remain available for rollback. The benchmark numbers below describe the earlier builds, not a new latency comparison for 1.6.3.

The user requested an installer for this update after reviewing the candidate. The previous installer is retained for rollback. The strict no-slower-median gate did not pass, and project evidence and repetition still need review. No external ATS score has been calculated or promised.

Newly generated resumes retain extracted named mandatory and preferred skills, distinguish exact product names from generic concepts, and assign implementation requirements to the existing project calls. Named-skill presence is checked separately from project evidence. Existing saved drafts and edited export text remain authoritative. New project headings and company metadata show `Company Name: #Confidential`; project metadata uses `Role`. Old drafts retain their previous labels.

## Measurements

On the same Windows laptop with an RTX 3050, three fresh backend-fixture runs of the skill-coverage candidate before the employer-heading update took 86.632, 74.048 and 86.804 seconds (median 86.632), compared with the retained baseline 86.457, 81.283 and 71.618 seconds (median 81.283). All were below five minutes, but the required no-slower-median gate failed. An earlier baseline median was 71.630 seconds; this small sample also shows run-to-run variability. Model calls were 13, 13 and 14, within the existing 27-request ceiling. Peak application/worker RSS was 3.007 GiB and peak device-wide GPU usage was 4,415 MiB; device-wide usage includes other GPU users.

Nine additional fixtures completed in 62.409–74.782 seconds with 13–15 calls. All extracted mandatory and preferred skill names in those fixtures appeared in preview, DOCX and HTML. The backend fixture is reconstructed from the comparison list rather than the exact original JD. These results do not establish complete extraction for every possible JD.

Local mandatory implementation-evidence checks (supported / partial / missing) were: Forward AI 5/18/6; cloud security 11/12/6; full-stack 18/3/1; Salesforce 3/5/0; Java 3/2/0; Databricks 10/10/2; AWS 12/6/5; Azure GenAI 0/2/3; QA 3/1/1. These conservative checks are review aids, not an ATS score or independent proof of claims. Reports also flag metric and technical issues; visual review found repetitive project wording in the Forward AI sample. Generated professional claims remain fictional.

## Validation and artifacts

- After the employer-heading update, a fresh Forward AI sample completed in 86.553 seconds with 15 calls. Its preview, DOCX and HTML were checked for the new labels and absence of generated employer names. Peak worker-tree RSS was about 2.98 GiB; peak device-wide GPU usage was 4,436 MiB. This single run does not establish a new median.
- 203 regression tests passed (five dependency deprecation warnings).
- Twelve earlier samples were checked in preview, DOCX and HTML, including edited exports, date removal, company placeholders and Role labels. The offline bundle's 161 assets passed local integrity checks. Those samples predate the employer-heading update and retain their original headings.
- Editing, undo/redo, preview, autosave recovery and cancellation passed local checks. Cancellation was acknowledged in 0.0098 seconds and owned subprocesses exited.
- Testing used this 16 GB Windows laptop, not a clean 8 GB reference laptop; a fully disconnected installation and upgrade were not verified.
- Samples, per-skill passages and detailed measurements are in `build/skill-coverage/clean-samples/` and `build/skill-coverage/release-measurements.json`. The comparison checklist is `build/skill-coverage/clean-samples/skill-evidence-checklist.csv`.
- Candidate bundle: `dist/projects-skills-clean-final-1.6.2/ResumeOptimizerProjects`. This earlier bundle is a test artifact; the later confidentiality build is packaged separately. The previous installer and saved data are preserved.

The existing model, interface, layout, model-call stages, running memory controls and fictional-generation behavior are unchanged. Further quality and latency work and a new measurement are required before the approved release gates can pass.
