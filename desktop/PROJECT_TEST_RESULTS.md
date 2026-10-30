# Project Edition 1.1.0 - local verification

Resumed and verified 22 October 2026. Full fictional professional generation remains enabled.

## What was interrupted

Most implementation was already present, with 66 earlier regression passes. The final model run, release selection, checksum, comparison samples and release records were incomplete. The old manifest still identified 1.0.0. This resume completed those local steps and fixed real-model findings: repeated bullets, mixed accuracy/precision comparisons, prose returned as skills, and recruiter fragments counted as technologies.

## Implemented behavior

- Three distinct employer/project blocks under Relevant Project Experience; six scoped responsibilities per project.
- Confidential client masking, visible employers and preserved identity/contact/education. Employment and project dates removed.
- JD-led outlines and project-specific writing prompts; named data-flow, implementation, integration, security, evaluation and delivery fields.
- Known required technology names are completed in skills; location/proficiency/requirement fragments are excluded. Preferred JD sections are classified separately.
- Versioned planning, quality and evidence; affected cache keys change. Full fabrication is preserved.
- At most three malformed-response retries and two single-shot quality calls, targeting different projects. Hard submission guard: 27.
- DOCX and HTML use edited section text; report evidence is recalculated on export. Old drafts remain readable.
- Build stages the installer, retains its predecessor and writes the actual release version/checksum.

## Final model and UI measurement

- Fresh isolated profile, supplied nine-page candidate PDF and 684-word Databricks JD; final frozen worker, CPU only.
- Generation: 392.310 seconds (22 model submissions).
- Peak GUI/worker/model RSS: 2.149 GiB.
- Edit handler: 1.0 ms; preview/autosave: 12.5 ms; maximum Qt heartbeat gap: 104.6 ms.
- Active cancellation acknowledgement: 10.0 ms; no owned processes remained after 500 ms.
- Host: Windows 11 x64 build 26200, approximately 16 GB RAM, 10 physical CPU cores; model limited to four threads. Installer compilation and developer activity overlapped the run. This is an observed local result, not the 8 GB reference-laptop benchmark.

## Same-rule comparison with the saved Databricks draft

| Local measure | Saved draft | New draft |
| --- | ---: | ---: |
| Named required-technology keyword coverage | 88.0% | 100.0% |
| Required-technology project text evidence | 56.0% | 64.0% |
| Capability rows supported | 9 | 10 |
| Capability rows partial | 21 | 21 |
| Capability rows missing | 2 | 1 |
| Known technical/repetition warnings | 9 | 2 |

Both drafts were evaluated with the same current rules. Keyword checks use named required technologies, not raw recruiter fragments. Capability rows use action/mechanism passages and explicit facets. These are conservative text heuristics, not external ATS scores, semantic proof of implementation, or verification of fictional claims. No overall ATS percentage is promised.

## Remaining required capability gaps

- Collibra metadata synchronization [partial]: glossary|steward|business term, from Unity Catalog|Unity Catalog to Collibra, from Collibra|Collibra to Unity Catalog
- Commercial analytics domains [partial]: activity|activities, market, performance
- Authenticated stateful context serving [partial]: Redis|DynamoDB|PostgreSQL|Delta table|database
- This engagement is explicitly Databricks-centric: the ontology, knowledge graph, and semantic layer being built on AWS must integrate with the client's existing Databricks Unity Catalog, Databricks Genie, and Collibra environment rather than operate as a disconnected AWS-only island. [partial]: collibra\ platform, databricks\ genie
- Partner with the client's Databricks platform team during onboarding and discovery to align the Knowledge Layer implementation architecture with the client's existing Databricks-centric data estate (Unity Catalog, Collibra, and a medallion Bronze/Silver/Gold lakehouse). [partial]: collibra\ platform
- Configure Databricks Genie (metric views, certified tables, and grounding logic) so brand/commercial insights business users can query the Knowledge Layer in natural language and receive accurate, cited, reproducible answers. [partial]: databricks\ genie
- Design and build the bi-directional metadata synchronization between Collibra and Databricks Unity Catalog, supporting governed metadata capture across both systems. [partial]: collibra\ platform
- Support deployment of the stateful context-serving agent and serving layer so it is accessible via Databricks and governed API interfaces, coordinating with Databricks Vector Search / AI Search where the context store spans both Databricks and AWS (S3 Tables, Amazon Neptune, Amazon Bedrock Knowledge Bases). [partial]: amazon\ bedrock, amazon\ bedrock\ knowledge\ bases, amazon\ neptune, aws\ s3\ tables, databricks\ vector\ search
- Apply Unity Catalog access controls (row/column-level security, masking) consistent with the client's data governance and stewardship model. [partial]: security
- Collaborate with the GenAI Engineering and Data/Knowledge Engineering tracks to keep the Databricks-side catalog and serving layer consistent with the AWS-side ontology, knowledge graph, and semantic store. [partial]: llm, the\ genai\ engineering
- Produce technical documentation for the Unity Catalog/Collibra integration and Genie configuration, and package reusable Databricks-side assets so future use cases can onboard without rebuilding context from scratch. [partial]: collibra\ platform, databricks\ genie
- Strong, hands-on Databricks Unity Catalog experience: catalog/schema/table administration, external locations and storage credentials, lineage APIs, and access control (row- and column-level security). [partial]: security
- Hands-on experience configuring Databricks Genie — metric views, certified tables, and grounding query responses in approved definitions, business rules, and source lineage. [partial]: databricks\ genie
- Proficiency in PySpark, Spark SQL, and Delta Lake at production scale (partitioning, Z-ordering, schema evolution). [partial]: z\-ordering
- Experience integrating Databricks with AWS services (S3, IAM roles/instance profiles); exposure to Amazon Neptune and/or Amazon Bedrock Knowledge Bases is a strong plus. [partial]: amazon\ bedrock, aws\ services\ s3, iam\ roles
- Demonstrated experience building or maintaining a metadata synchronization between Databricks Unity Catalog and an enterprise data catalog such as Collibra. [partial]: collibra\ platform
- Strong Python programming skills for data pipeline and API automation. [partial]: etl

## Remaining technical review notes

- Multiple percentage claims need separate metric baselines/results or an explicit consistent change calculation: - The evaluation workload involves a controlled population of 5,000 synthetic brand campaign records to test entity resolution and metric tracking accuracy. The
- Quantified outcome needs its metric, workload, baseline and final result: - Reusable deployment is achieved through Terraform-managed Asset Bundles that automate the promotion and rollback of Spark SQL pipelines, ensuring documented r

## Manual review of the acceptance sample

- Authentication passages name Databricks Service Mesh. Verify the actual API identity mechanism and use precise service-principal/OAuth terminology where appropriate.
- The lakehouse passage says partitioned by Z.order. Distinguish table partitioning from Z-ordering/data layout and specify the actual optimization.
- One metadata evaluation compares baseline accuracy with final consistency. Define a single metric and evaluation rubric before using that claim.

These manual observations are additional to the known-pattern warning counts above. The small model can still invent inaccurate component names or measurements. The sample remains editable and these issues are explicitly reported rather than declared technically verified.

## Checks completed

- 67 regression cases passed, including all 46 legacy cases and Databricks/AWS/Azure JD fixtures. Only existing PyMuPDF SWIG deprecation warnings were emitted.
- Final fresh generation completed; distinct titles/employers, stable role IDs, six bullets, preserved source fields, client labels and date rules checked.
- Clean and edited DOCX/HTML exports passed through the final frozen worker; manual client/date edits were sanitized and edited wording remained.
- Editing, undo/redo, autosave/recovery, queue/cancellation, missing/corrupt assets, insufficient memory, idle unloading and owned-listener behavior covered by regression checks.
- Local model/assets available without downloads; offline flags used. A worker/model TCP sample used loopback only. This is not a physically disconnected clean-machine test.
- GUI identity and coexistence verified alongside the old edition. Final installer lifecycle used isolated registry identity and data, with compression disabled for that test; payload and installation logic match production.
- Install 22.64 s; upgrade 8.6 s; uninstall 1.33 s. Saved data survived, and both existing application registrations were unchanged.
- Final installer compiled successfully and SHA-256 recorded. The previous 1.0.0 installer and the interrupted 1.1.0 installer are retained.

## Use and manual checklist

1. Close Project Edition and run ResumeOptimizerProjectsSetup.exe. Use the Resume Optimizer Project Edition shortcut.
2. Choose a text PDF/DOCX, paste the JD and Generate; review any remaining report gaps.
3. Edit a section, undo/redo, restart to check autosave, then export DOCX and HTML.
4. Try Cancel during generation and confirm another application's model/app remains unaffected.
5. Before broad distribution, complete the actual 8 GB/four-core reference-laptop benchmark and physically disconnected clean Windows installation/use test.

## Changed source files

- desktop/project_generation.py
- desktop/project_rules.py
- desktop/project_document.py
- desktop/generation.py
- desktop/quality.py
- desktop/draft.py
- desktop/project_installer.nsi
- desktop/build_projects.ps1
- desktop/install_smoke.py
- desktop/test_project_quality.py
- desktop/test_project_edition.py
- desktop/fixtures/databricks-jd.txt
- desktop/fixtures/aws-jd.txt
- desktop/fixtures/azure-genai-jd.txt
- desktop/PROJECT_EDITION.md
- desktop/PROJECT_TEST_RESULTS.md

## Artifact integrity

Installer SHA-256: ec32a09fc767992be9b2567fdcac6db26f2968d751b5f91e856974ba64b1df06
Installer size: 1,402,802,430 bytes.
