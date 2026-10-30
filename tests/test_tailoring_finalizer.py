import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "api"))
from pipeline.ideal_resume import (_align_project_period, _source_projects,
                                   clean_export_markdown, finalize, polish_project_titles,
                                   polish_summary_voice)
from schemas import ExperienceEntry, Requirement


def test_finalizer_enforces_targeted_sections_and_moves_new_project():
    draft = """# Pratik Bugade
Target Role: Full Stack Developer
## Profile Summary
Old GenAI summary.
## Projects
### Existing Project
- Existing work
## Technical Skills
- Python, FastAPI
## Education
D. Y. Patil Agriculture and Technical University
D. Y. Patil Agriculture and Technical University
## New Project
### Learning Platform
- React work
Return only the completed resume as valid Markdown.
"""
    requirements = [
        Requirement(req_id="R1", text="Build applications with Node.js and ReactJS",
                    type="responsibility", must_have=True,
                    canonical_skills=["nodejs", "react"]),
        Requirement(req_id="R2", text="Develop scalable REST API endpoints",
                    type="responsibility", must_have=True,
                    canonical_skills=["rest api"]),
        Requirement(req_id="R3", text="Preferred Redux, Nest.js, and Socket.io",
                    type="hard_skill", must_have=False),
    ]
    result = finalize(draft, "As a Full stack Developer at Vidyalai.com", requirements)
    assert result.count("## Professional Summary") == 1
    assert "Old GenAI summary." in result
    skills = result.split("## Technical Skills", 1)[1].split("## ", 1)[0]
    assert all(item in skills for item in ("Node.js", "ReactJS", "REST APIs", "Redux", "Nest.js", "Socket.io"))
    assert result.index("### Learning Platform") < result.index("## Education")
    assert result.index("### Existing Project") < result.index("### Learning Platform")
    assert result.index("### Learning Platform") < result.index(
        "### Real-Time Application Reliability")
    assert "JD-Aligned Project" not in result
    assert "Target Solution" not in result
    assert "## New Project" not in result
    assert "Return only" not in result
    assert "D. Y. Patil Agriculture and Technical University" in result
    assert result.count("D. Y. Patil Agriculture and Technical University") == 1


def test_finalizer_removes_repair_narration_and_qa_blocks():
    draft = """# Candidate
## Professional Summary
Developer
## Technical Skills
Node.js
## Selected Projects
### New JD-Aligned Project
- Built a platform
## Education
College
The new project is missing, so I added it in the Selected Projects section before Education:
# Missing Sections
- None
# New Project Misplaced or Missing
- Yes
"""
    result = finalize(draft, "Full Stack Developer", [])
    assert "The new project is missing" not in result
    assert "Missing Sections" not in result
    assert "New Project Misplaced or Missing" not in result


def test_finalizer_retains_generated_experience_and_source_employment():
    draft = """# Candidate
## Professional Experience
### Full Stack Engineer at Oteemo
- Invented JD responsibilities
## Selected Projects
### Existing Project
- Work
## Education
College
"""
    entries = [ExperienceEntry(
        entry_id="EXP-DATE-01", company="ABC Technologies", role_title="Software Developer",
        start_date="May 2022", end_date="", current=True,
        source_evidence="Software Developer | ABC Technologies | May 2022 – Present",
    )]
    result = finalize(draft, "Full Stack Developer", [], entries)
    assert "**DEMO / FICTIONAL RESUME" not in result
    assert "## Professional Experience" in result
    assert "### Software Developer | ABC Technologies" in result
    assert "Dates: May 2022 - Present" in result
    assert "ABC Technologies" in result
    assert "### Full Stack Engineer at Oteemo" in result
    assert "Invented JD responsibilities" in result


def test_finalizer_keeps_undated_source_employment_visible():
    draft = """# Candidate
## Professional Experience
### Target Company | Full Stack Engineer
- Generated work
## Education
College
"""
    entries = [ExperienceEntry(entry_id="EXP-UNDATED-01", company="ABC Technologies",
                               role_title="Software Developer",
                               source_evidence="ABC Technologies | Software Developer")]
    result = finalize(draft, "Full Stack Developer", [], entries)
    assert "## Professional Experience" in result
    assert "### Software Developer | ABC Technologies" in result
    assert "MM/YYYY" not in result
    assert "ABC Technologies" in result
    assert "### Target Company | Full Stack Engineer" in result


def test_finalizer_cleans_template_artifacts_and_preserves_source_identity():
    source = """Alex Example
Summary
Example Health (Mar 2024 - Current):
Designation: Senior DevOps Engineer
Relevant Project Experience
Whisper (ASR Platform)
Title:
Project Description:
Healthcare transcription.
"""
    draft = """# Alex Example
GPU Engineer
Contact details: invented@example.com, (123) 456-7890
## Professional Summary
GPU infrastructure engineer.
## Professional Experience
### GPU Engineer | Example Health (Mar 2024 - Current)
- Built GPU infrastructure.
### Senior DevOps Engineer | Example Health (Feb 2023 - Mar 2024)
- Duplicated role artifact.
## Selected Projects
### Existing Project Name: Whisper (ASR Platform)
- Improved transcription.
### Project Name GPU Telemetry Platform
- Built telemetry collectors.
## Additional Skills & Experience
- 10+ years preferred.
"""
    result = finalize(draft, "*Job Title: GPU Engineer*", [], resume_text=source)
    assert "### Senior DevOps Engineer | Example Health" in result
    assert "Dates: Mar 2024 - Current" in result
    assert "- Built GPU infrastructure." in result
    assert result.count("### Senior DevOps Engineer | Example Health") == 1
    assert "### Whisper (ASR Platform)" in result
    assert "### GPU Telemetry Platform" in result
    assert "Existing Project Name" not in result
    assert "Project Name" not in result
    assert "invented@example.com" not in result
    assert "10+ years preferred" not in result


def test_finalizer_adds_two_detailed_projects_and_two_certifications():
    source = """Asha Rao
Relevant Project Experience
Source Platform
Title:
Project Description:
Existing production system.
Certifications:
•
Cloud Foundations Certificate
Extra-Curricular Activities:
"""
    draft = """# Asha Rao
## Professional Summary
Infrastructure engineer focused on reliable systems.
## Technical Skills
- Systems: Linux, Python
## Selected Projects
### Source Platform
Description: Existing production system.
- Improved reliability.
### GPU Telemetry Platform
Description: Collected telemetry from benchmark workloads.
Technologies: Linux, Python, NVML
- Built collectors for GPU telemetry.
## Education
Engineering degree
## Certifications
- Cloud Foundations Certificate
"""
    jd = """*Job Title: GPU Infrastructure Engineer*
Key Technical Areas
GPU Telemetry: NVML, DCGM
Systems: Linux, Python
Candidate Profile
"""
    result = finalize(draft, jd, [], resume_text=source)
    projects = result.split("## Selected Projects\n", 1)[1].split("## Education", 1)[0]
    assert projects.count("### ") == 3
    assert projects.index("### Source Platform") < projects.index("### GPU Telemetry Platform")
    assert "### Multi-GPU Workload Orchestration Platform" in projects
    for field in ("Title:", "Client:", "Operating System:", "Tools:", "Team Size:",
                  "Period:", "Project Description:", "Technical:", "Functional:"):
        assert projects.count(field) >= 2
    certifications = result.split("## Certifications\n", 1)[1]
    assert "Cloud Foundations Certificate" in certifications
    assert len([line for line in certifications.splitlines() if line.startswith("- ")]) == 3
    summary = result.split("## Professional Summary\n", 1)[1].split("## ", 1)[0]
    assert "Infrastructure engineer focused on reliable systems." in summary
    assert "Source Platform" in summary
    assert "Brings together implementation" not in summary


def test_finalizer_keeps_source_project_order_when_model_mixes_projects():
    source = """Asha Rao
Relevant Project Experience
Whisper Platform
Title:
Project Description:
Speech transcription system.
Payment Platform
Title:
Project Description:
Payment processing system.
"""
    draft = """# Asha Rao
## Selected Projects
### Payment Platform
Title: Unrelated Chatbot
- Built a chatbot.
### Whisper Platform
Description: Improved transcription.
- Improved throughput.
### Project 1
Title: GPU Benchmarking Suite
- Built benchmarks.
## Education
College
"""
    result = finalize(draft, "GPU Infrastructure Engineer", [], resume_text=source)
    projects = result.split("## Selected Projects\n", 1)[1].split("## Education", 1)[0]
    assert projects.index("### Whisper Platform") < projects.index("### Payment Platform")
    assert "Payment processing system" in projects
    assert "Unrelated Chatbot" not in projects
    assert "### GPU Benchmarking Suite" in projects
    assert "### Project 1" not in projects


def test_finalizer_drops_duplicate_projects_outside_project_section():
    draft = """# Asha Rao
## Selected Projects
### GPU Benchmark Platform
- Ran benchmarks.
### Multi-GPU Workload Platform
- Ran workloads.
## Education
College
## Achievements
- Team Award
### New Project: Duplicate Benchmark Suite
- Duplicate project text.
"""
    result = finalize(draft, "GPU Infrastructure Engineer", [])
    assert "Duplicate Benchmark Suite" not in result
    assert "Team Award" in result


def test_repair_echo_is_removed_and_source_activities_are_grouped():
    draft = """# Kavya Iyer
## Professional Summary
Full stack developer.
## Other Skills and Interests
- Organizer of ChennaiJS monthly meetup.
- Maintainer of an open-source React accessibility hooks library with 900+ GitHub stars.
- Achieved Product Impact Award at LearnLoop EdTech for the Assessment Engine launch.
- Runner-up at Smart India Hackathon (software edition).
Rebuild and tailor this candidate resume to the complete job description. Keep distinct jobs and projects structurally separate.
**MISSING JD SKILLS:** data visualization, etl, kafka
**MISSING SECTIONS:** selected projects
**NEW PROJECT MISPLACED OR MISSING:** yes
Return a complete replacement resume. Correct every listed omission.
"""
    cleaned = clean_export_markdown(draft)
    result = finalize(draft, "Full Stack Developer", [])
    for output in (cleaned, result):
        assert "Rebuild and tailor" not in output
        assert "MISSING JD SKILLS" not in output
        assert "Return a complete replacement" not in output
        assert "## Other Skills and Interests" not in output
        assert "## Extracurricular Activities" in output
        assert "Organizer of ChennaiJS" in output
        assert "## Achievements" in output
        assert "Product Impact Award" in output
        assert "Runner-up at Smart India Hackathon" in output


def test_all_required_jd_skills_are_added_even_with_key_technical_areas():
    draft = """# Asha Rao
## Professional Summary
ML platform engineer.
## Technical Skills
- Languages: Python
## Education
Engineering degree
"""
    jd = """Job Title: Data Engineer
Key Technical Areas
Programming: Python
Candidate Profile
Required experience with Kafka, Spark, Pandas, ETL, machine learning, time series, and data visualization.
Experience with Ray Serve and Kubeflow Pipelines.
Knowledge of Slurm and FeatureStoreX.
Required Skills
- CustomScheduler9

"""
    result = finalize(draft, jd, [])
    skills = result.split("## Technical Skills\n", 1)[1].split("## ", 1)[0].casefold()
    for term in ("python", "kafka", "spark", "pandas", "etl", "machine learning",
                 "time series", "data visualization", "ray serve", "kubeflow pipelines",
                 "slurm", "featurestorex", "customscheduler9"):
        assert term in skills


def test_source_project_metadata_and_generated_projects_remain_distinct():
    source = """Asha Rao
Alpha Corp (Jan 2023 - Current):
Designation: ML Engineer
Relevant Project Experience
Source Platform
Title:
Source Platform
Client: Product
Operating System: Ubuntu
Tools: Python, Kubernetes
Team size: 7
Period: 2023 - Current
Project Description:
Production ML service.
Role and Responsibilities:
Technical:
â€¢ Built deployment automation.
Functional:
â€¢ Coordinated release reviews.
"""
    draft = """# Asha Rao
## Professional Experience
### ML Engineer | Alpha Corp
Dates: Jan 2023 - Current
- Led systems work.
## Selected Projects
### Source Platform
- Improved deployment.
## Education
Engineering degree
"""
    result = finalize(draft, "GPU infrastructure engineer with telemetry and multi-GPU inference", [],
                      resume_text=source)
    projects = result.split("## Selected Projects\n", 1)[1].split("## Education", 1)[0]
    assert projects.count("Employer: Alpha Corp") == 3
    assert "### Source Platform" in projects
    assert "Operating System: Ubuntu" in projects
    assert "Tools: Python, Kubernetes" in projects
    assert "Built deployment automation" in projects
    assert "### GPU Benchmarking and Telemetry Platform" in projects
    assert "### Multi-GPU Workload Orchestration Platform" in projects
    first = projects.split("### GPU Benchmarking and Telemetry Platform", 1)[1].split("### Multi-GPU", 1)[0]
    second = projects.split("### Multi-GPU Workload Orchestration Platform", 1)[1]
    assert "stress testing" in first
    assert "inference and training" in second
    assert first != second


def test_generated_project_period_stays_within_associated_role():
    role = ExperienceEntry(entry_id="EXP-1", company="Alpha Corp", role_title="Engineer",
                           start_date="Jan 2021", end_date="Dec 2023", source_evidence="Role dates")
    assert "Period: Jan 2021 - Dec 2023" in _align_project_period(
        "Tools: Python\nPeriod: 2024 - Present", role)
    assert "Period: 2022 - 2023" in _align_project_period(
        "Period: 2022 - 2023", role)


def test_docx_style_source_without_title_lines_and_copied_resume_are_cleaned():
    source = """Marcus D'Souza
Principal Data Engineer
SUMMARY
Built analytics platforms using SQL, Python, and Power BI.
TECHNICAL SKILLS
Languages | Python, SQL
BI | Power BI, Tableau
EDUCATION
M.Tech | National Institute | 8.9/10
RELEVANT PROJECT EXPERIENCE
GridPulse Analytics (Sep 2021 - Current)
Designation: Principal Data Engineer
Smart Meter Lakehouse
Client: Product
Tools: Spark, Kafka, Python
Project Description: Processes meter readings for reporting.
Technical:
Built data pipelines.
Created quality checks.
Network Analytics
Client: Product
Tools: SQL, Power BI
Project Description: Builds operational reports.
Functional:
Presented findings to stakeholders.
CERTIFICATIONS
Databricks Certified Data Engineer Professional
"""
    draft = """# Marcus D'Souza
## Professional Summary
Principal Data Engineer targeting experienced Senior Data Analyst roles. Experience across relevant technology platforms; delivers infrastructure and automation.
## Professional Experience
### Principal Data Engineer | GridPulse Analytics
Dates: Sep 2021 - Current
## Principal Data Engineer
### Professional Summary
Copied source summary.
### Technical Skills
Copied source skills.
### Relevant Project Experience
Copied source projects.
### Education
Copied source education.
## Education
M.Tech | National Institute | 8.9/10
"""
    jd = """http://localhost:8000/v1/download/abc# Job Title: Senior Data Analyst
## Required Technical Environment
**Programming & Analysis:** SQL, Python, Excel
**BI & Visualization:** Power BI, Tableau
"""
    result = finalize(draft, jd, [], resume_text=source)
    assert result.splitlines()[1] == "Senior Data Analyst"
    assert result.count("## Professional Summary") == 1
    assert "\n## Principal Data Engineer\n" not in result
    assert "Copied source" not in result
    assert "Experience across relevant technology platforms" not in result
    assert result.count("### Smart Meter Lakehouse") == 1
    assert result.count("### Network Analytics") == 1
    assert "Employer: GridPulse Analytics" in result
    assert "Built data pipelines" in result
    assert "### Business KPI and Self-Service Analytics" in result
    assert "### Forecasting and Data Quality Insights" in result
    assert "GPU telemetry" not in result
    skills = result.split("## Technical Skills\n", 1)[1].split("## ", 1)[0]
    assert all(line.startswith("- **") and ":** " in line for line in skills.splitlines() if line)
    assert "|" not in skills
    assert all(term in skills for term in ("SQL", "Python", "Excel", "Power BI", "Tableau"))


def test_finalizer_compacts_malformed_experience_metadata_and_education_spillover():
    draft = """# Candidate
## Professional Summary
Security engineer with platform and incident-response experience.
## Professional Experience
### Security Operations
Dates: 2020 - Present
### Period: | broken metadata copied from a table
Dates: 2020 - Present
## Selected Projects
### Security Platform
Client: Product
Tools: Python, AWS
Project Description: A production security platform. Extra detail that should not be needed.
- Built monitoring automation.
- Built monitoring automation.
- Added incident diagnostics.
- Added operational reporting.
## Education
B.Tech | Example University | 8.0
Relevant Experience
This must not appear in education.
## Certifications
- Security Certificate
"""
    result = finalize(draft, "Cybersecurity Engineer", [], resume_text="Candidate")
    experience = result.split("## Professional Experience\n", 1)[1].split("## Selected Projects", 1)[0]
    education = result.split("## Education\n", 1)[1].split("## Certifications", 1)[0]
    projects = result.split("## Selected Projects\n", 1)[1].split("## Education", 1)[0]
    assert "### Period:" not in experience
    assert "This must not appear" not in education
    assert projects.count("- Built monitoring automation.") == 1


def test_template_echo_summary_and_project_fields_are_replaced_without_cutting_education():
    source = """Candidate
Summary
Senior engineer delivering data platforms with Python and Spark.
Built production analytics and deployment workflows.
Technical Skills
Python, Spark
Education
MSc
First University
8.0/10
BCA
Second College
7.5/10
Relevant Project Experience
"""
    draft = """# Candidate
## Professional Summary
Three or four substantive sentences specific to this candidate and JD, covering technical depth.
Use third-person resume voice, never address the candidate as you or your.
## Selected Projects
### Specific Project Name
Title: specific name
Client: product or customer context
Tools: concise technology list
Team Size: number
Project Description: two or three detailed sentences on architecture and purpose.
## Education
MSc
"""
    result = finalize(draft, "Data Engineer", [], resume_text=source)
    assert "Senior engineer delivering data platforms" in result
    assert "substantive sentences" not in result
    assert "resume voice" not in result
    assert "Specific Project Name" not in result
    assert "Team Size: number" not in result
    assert "concise technology list" not in result
    assert "Second College" in result and "7.5/10" in result


def test_project_parser_does_not_treat_metadata_values_as_project_names():
    source = """Relevant Project Experience
Whisper Platform
Title:
Whisper Platform
Client:
Product
Operating System:
Ubuntu
Tools:
Python, Kubernetes
Period:
March 2024 - Current
Project Description:
Speech platform.
Summary Generator
Client: Product
Tools: Python, SQL
Project Description: Summary platform.
"""
    assert [name for name, _ in _source_projects(source)] == [
        "Whisper Platform", "Summary Generator"]


def test_finalizer_uses_professional_summary_voice_without_changing_other_sections():
    draft = """# Akhilesh Sharma
Senior Full Stack Engineer
## Professional Summary
Akhilesh is a Senior Full Stack Engineer with 10 years of React and Python delivery. He possesses deep experience in cloud architecture. He thrives in Agile environments, leading cross-functional teams. His recent work includes API modernization and scalable platforms. Akhilesh's expertise includes cloud migrations. As a senior engineer, Akhilesh leads platform modernization.
## Professional Experience
### Senior Engineer | Example Company
Dates: 2020 - Present
- Led React and Python delivery.
## Selected Projects
### Modern API Platform
Client: Enterprise customer
Tools: Python, React
Project Description: Built a scalable platform.
## Education
B.Tech | Example University
"""
    result = finalize(draft, "Senior Full Stack Engineer with React and Python", [],
                      fictional_template=True, fabrication_mode="demo",
                      allow_unverified=True, resume_text="Akhilesh")
    summary = result.split("## Professional Summary\n", 1)[1].split("## Technical Skills", 1)[0]
    assert "Senior Full Stack Engineer with 10 years" in summary
    assert "Experience in cloud architecture" in summary
    assert "Leads cross-functional teams in Agile environments" in summary
    assert "Recent work includes API modernization" in summary
    assert "Expertise includes cloud migrations" in summary
    assert "Senior engineer, leading platform modernization" in summary
    assert not any(phrase in summary for phrase in (
        "Akhilesh is", "He possesses", "He thrives", "His recent"))
    assert "- Led React and Python delivery." in result
    assert "### Modern API Platform" in result


def test_cached_summary_polish_leaves_experience_and_projects_identical():
    original = """# Akhilesh Sharma
## Professional Summary
Akhilesh is a Senior Full Stack Engineer. He possesses deep experience in Python.

## Professional Experience
### Engineer | Example Company
- Built React and Python services.

## Selected Projects
### API Platform
- Modernized production APIs.
"""
    result = polish_summary_voice(original)
    assert "Senior Full Stack Engineer. Experience in Python." in result
    assert result.split("## Professional Experience", 1)[1] == original.split(
        "## Professional Experience", 1)[1]


def test_source_project_title_replaces_duplicate_experience_heading_only():
    source = """Candidate Name
PROFESSIONAL EXPERIENCE
Title: | Enterprise SaaS Modernization to .NET 8 & React
Client: | Internal platform
Project Description: Modernized a legacy application with .NET 8 and React.
"""
    draft = """# Candidate Name
## Professional Summary
Senior engineer with cloud delivery experience.
## Professional Experience
### Senior Engineer | Example Company
- Built production systems.
## Selected Projects
### PROFESSIONAL EXPERIENCE
Client: Internal platform
Project Description: Modernized a legacy application with .NET 8 and React.
- Designed scalable APIs.
## Education
B.Tech | Example University
"""
    expected = draft.replace("### PROFESSIONAL EXPERIENCE",
                             "### Enterprise SaaS Modernization to .NET 8 & React")
    assert polish_project_titles(draft, source) == expected
    result = finalize(draft, "Senior Full Stack Engineer", [], resume_text=source,
                      fictional_template=True, fabrication_mode="demo", allow_unverified=True)
    assert result.count("## Professional Experience") == 1
    assert "### PROFESSIONAL EXPERIENCE" not in result
    assert "### Enterprise SaaS Modernization to .NET 8 & React" in result
    assert "Modernized a legacy application with .NET 8 and React" in result
