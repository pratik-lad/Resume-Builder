"""Authoritative data contracts. Every stage boundary is one of these."""
from typing import Literal, Optional
from pydantic import BaseModel, Field

FactType = Literal[
    "experience_bullet", "project_bullet", "skill", "education",
    "certification", "summary", "other",
]
ReqType = Literal["hard_skill", "tool", "responsibility", "qualification", "soft_skill"]
Status = Literal["covered", "partial", "missing"]


# ---------- LLM output schemas (kept FLAT and SMALL on purpose) ----------

class ExtractedFact(BaseModel):
    # Local constrained models occasionally return the entity fields first and
    # omit ``text``.  An empty default lets ingestion recover that claim from
    # the lossless source section while retaining the valid entity lists.
    text: str = ""
    context: str = ""          # e.g. "Acme Corp - SDE Intern (Jun 2024 - Dec 2024)"
    tech: list[str] = Field(default_factory=list)
    orgs: list[str] = Field(default_factory=list)
    numbers: list[str] = Field(default_factory=list)
    dates: list[str] = Field(default_factory=list)


class ExtractedFacts(BaseModel):
    facts: list[ExtractedFact] = Field(default_factory=list)


class ExtractedRequirement(BaseModel):
    text: str
    type: ReqType = "hard_skill"
    must_have: bool = True
    min_years: int = 0
    skills: list[str] = Field(default_factory=list)


class ExtractedRequirements(BaseModel):
    role_title: str = ""
    requirements: list[ExtractedRequirement] = Field(default_factory=list)


class RewriteOut(BaseModel):
    # Defaults matter: structured.generate() falls back to schema() (no args) when
    # every retry fails to parse. A required field with no default would raise
    # ValidationError right there, crashing the run instead of degrading gracefully.
    # An empty text + used_evidence=False is a clear generation-failed signal.
    text: str = ""
    used_evidence: bool = False


# ---------- internal contracts ----------

class SourceSpan(BaseModel):
    page: int = 1
    char_start: int = 0
    char_end: int = 0


class Fact(BaseModel):
    fact_id: str
    type: FactType
    parent_id: str = ""
    section_heading: str = ""
    context: str = ""
    text: str
    entities: dict[str, list[str]] = Field(default_factory=dict)
    source: SourceSpan = Field(default_factory=SourceSpan)


class ExperienceEntry(BaseModel):
    """Explicit source employment metadata; projects are never represented here."""
    entry_id: str
    company: str = ""
    role_title: str = ""
    start_date: str = ""
    end_date: str = ""
    current: bool = False
    source_evidence: str


class FactLedger(BaseModel):
    facts: list[Fact] = Field(default_factory=list)
    experience_entries: list[ExperienceEntry] = Field(default_factory=list)
    allowed_entities: list[str] = Field(default_factory=list)
    raw_text: str = ""


class Requirement(BaseModel):
    req_id: str
    text: str
    type: ReqType
    must_have: bool
    min_years: int = 0
    canonical_skills: list[str] = Field(default_factory=list)
    weight: float = 1.0
    # Human review: an OR group remains one requirement; conjunctions use
    # separate atomic rows. Retain this metadata when loading accepted gold.
    logic: Literal['single', 'any'] = 'single'
    source_text: str = ''


class RequirementSet(BaseModel):
    extraction_version: str = "full-jd-tailoring-v4"
    role_title: str = ""
    requirements: list[Requirement] = Field(default_factory=list)
    jd_text: str = ""


class Match(BaseModel):
    req_id: str
    fact_ids: list[str] = Field(default_factory=list)
    score: float = 0.0
    method: Literal["lexical", "fuzzy", "semantic", "none",
                    "qualification:degree", "qualification:years",
                    "qualification:degree+years", "qualification:certification",
                    "qualification:experience_dates"] = "none"
    status: Status = "missing"


class ScoreCard(BaseModel):
    jd_alignment_score: float = 0.0
    hard_skill_coverage: float = 0.0
    responsibility_match: float = 0.0
    qualification_match: float = 0.0
    keyword_surface: float = 0.0
    fit_decision: Literal["match", "partial", "mismatch"] = "partial"
    fit_probability: float = 0.0


class OutputCoverageItem(BaseModel):
    req_id: str
    requirement: str
    must_have: bool
    present: bool
    status: Status = "missing"
    coverage: float = 0.0
    missing_components: list[str] = Field(default_factory=list)
    excerpt: str = ""


class OutputCoverage(BaseModel):
    """Text coverage in generated output, not verified candidate eligibility."""
    required_percent: float = 0.0
    preferred_percent: float = 0.0
    items: list[OutputCoverageItem] = Field(default_factory=list)


class GapItem(BaseModel):
    req_id: str
    requirement: str
    must_have: bool
    score: float
    evidence: str = ""
    suggestion: str = ""


class GapReport(BaseModel):
    missing_required: list[GapItem] = Field(default_factory=list)
    missing_optional: list[GapItem] = Field(default_factory=list)
    partial: list[GapItem] = Field(default_factory=list)


class RequirementCoverage(BaseModel):
    req_id: str
    requirement: str
    type: ReqType
    must_have: bool
    importance: Literal["critical", "high", "medium"]
    status: Status
    confidence: float = 0.0
    evidence_fact_ids: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    improvement_opportunity: str = ""


class OptimizationAction(BaseModel):
    action: Literal["rewrite", "reorder", "highlight", "gap_only"]
    target: Literal["summary", "skills", "experience", "projects", "certifications", "sections"]
    fact_ids: list[str] = Field(default_factory=list)
    requirement_ids: list[str] = Field(default_factory=list)
    reason: str


class ExperienceGap(BaseModel):
    """An explicitly reported years gap; never an instruction to rewrite years."""
    req_id: str
    requirement: str
    required_years: int
    candidate_years: float | None = None
    gap_years: float | None = None
    source_supported: bool = False
    qualification_result: Literal["satisfied", "partial", "unmet", "unverifiable"] = "unverifiable"
    verified_relevant_months: int | None = None
    evidence_entry_ids: list[str] = Field(default_factory=list)


class OptimizationStrategy(BaseModel):
    current_score: float
    potential_score_existing_evidence: float
    project_bridged_projected_alignment: float = 0.0
    must_have_coverage: float
    coverage: list[RequirementCoverage] = Field(default_factory=list)
    prioritized_gap_ids: list[str] = Field(default_factory=list)
    actions: list[OptimizationAction] = Field(default_factory=list)
    section_order: list[str] = Field(default_factory=list)
    fact_order: list[str] = Field(default_factory=list)
    transferable_evidence_fact_ids: list[str] = Field(default_factory=list)
    transferable_skills: list[str] = Field(default_factory=list)
    experience_gaps: list[ExperienceGap] = Field(default_factory=list)
    keyword_priorities: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


ProjectStatus = Literal["proposed", "in_progress", "completed", "verified"]


class ProposedProject(BaseModel):
    project_id: str
    title: str
    status: ProjectStatus = "proposed"
    eligible_as_resume_evidence: bool = False
    problem_statement: str
    why_it_matches_jd: str
    technologies: list[str] = Field(default_factory=list)
    architecture: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)
    requirements_covered: list[str] = Field(default_factory=list)
    skills_demonstrated: list[str] = Field(default_factory=list)
    expected_resume_bullets: list[str] = Field(default_factory=list)
    implementation_roadmap: list[str] = Field(default_factory=list)
    testing_plan: list[str] = Field(default_factory=list)
    deployment_plan: list[str] = Field(default_factory=list)
    github_structure: list[str] = Field(default_factory=list)
    estimated_difficulty: Literal["beginner", "intermediate", "advanced"] = "intermediate"
    portfolio_value: str
    verification_evidence: list[str] = Field(default_factory=list)


class TruthSafetyReport(BaseModel):
    ucr: float = 0.0
    current_resume_claims_source_supported: bool = True
    proposed_project_separated: bool = True
    proposed_project_status: ProjectStatus | None = None
    proposed_project_used_as_evidence: bool = False
    immutable_fields_preserved: bool = True
    immutable_field_violations: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ProjectBuildPlan(BaseModel):
    project_id: str
    status: ProjectStatus = "proposed"
    folder_structure: list[str] = Field(default_factory=list)
    readme: str
    implementation_plan: list[str] = Field(default_factory=list)
    files: dict[str, str] = Field(default_factory=dict)
    setup_instructions: list[str] = Field(default_factory=list)
    tests: list[str] = Field(default_factory=list)
    resume_evidence_warning: str


class MatchResult(BaseModel):
    matches: list[Match] = Field(default_factory=list)
    score_card: ScoreCard = Field(default_factory=ScoreCard)
    gap_report: GapReport = Field(default_factory=GapReport)


class Violation(BaseModel):
    layer: str
    detail: str


class Rewrite(BaseModel):
    fact_id: str
    target_req: str = ""
    original: str
    final: str
    # accepted  = passed validation AND the text genuinely changed
    # unchanged = passed validation but the model returned the same text verbatim
    #             (legitimate -- it decided no rewrite was warranted -- but should
    #             not be counted as a real improvement in reporting/eval)
    # reverted  = failed validation after all repair attempts; fell back to original
    status: Literal["accepted", "unchanged", "reverted"] = "unchanged"
    attempts: int = 0
    violations_fixed: list[str] = Field(default_factory=list)


class OptimizeResult(BaseModel):
    input_signature: str = ""
    finalizer_version: str = ""
    generation_mode: str = "resume_builder_tailoring"
    markdown: str = ""
    output_coverage: OutputCoverage | None = None
    rewrites: list[Rewrite] = Field(default_factory=list)
    ucr: float | None = None
    accepted: int = 0
    unchanged: int = 0
    reverted: int = 0
    strategy: Optional[OptimizationStrategy] = None
    project_bridge: Optional[ProposedProject] = None
    truth_report: Optional[TruthSafetyReport] = None
    fictional_template: bool = False
    fabrication_mode: Literal["none", "demo", "fictional", "synthetic"] = "none"
    allow_unverified: bool = False


# ---------- API request/response ----------

class RunRef(BaseModel):
    run_id: str
    fictional_template: bool = True
    fabrication_mode: Literal["none", "demo", "fictional", "synthetic"] = "demo"
    allow_unverified: bool = True


class JDRequest(BaseModel):
    run_id: str
    jd_text: str


class IdealResumeRequest(BaseModel):
    jd_text: str
    resume_text: str = ""
    fictional_template: bool = True
    fabrication_mode: Literal["none", "demo", "fictional", "synthetic"] = "demo"
    allow_unverified: bool = True


class IdealResumeResponse(BaseModel):
    markdown: str
    output_coverage: OutputCoverage | None = None
    requirements: RequirementSet | None = None
    fictional_template: bool = False
    fabrication_mode: Literal["none", "demo", "fictional", "synthetic"] = "none"
    allow_unverified: bool = False


class IngestResponse(BaseModel):
    run_id: str
    sections: dict[str, int]
    fact_count: int
    warnings: list[str] = Field(default_factory=list)


class MatchResponse(BaseModel):
    run_id: str
    score_before: ScoreCard
    gap_report: GapReport
    match_table: list[Match]
    coverage: list[RequirementCoverage] = Field(default_factory=list)


class StrategyResponse(BaseModel):
    run_id: str
    strategy: OptimizationStrategy
    project_bridge: Optional[ProposedProject] = None


class OptimizeResponse(BaseModel):
    generation_mode: str = "resume_builder_tailoring"
    markdown: str = ""
    output_coverage: OutputCoverage | None = None
    run_id: str
    ucr: float | None = None
    accepted: int
    unchanged: int = 0
    reverted: int
    rewrites: list[Rewrite]
    strategy: Optional[OptimizationStrategy] = None
    project_bridge: Optional[ProposedProject] = None
    truth_report: Optional[TruthSafetyReport] = None
    fictional_template: bool = False
    fabrication_mode: Literal["none", "demo", "fictional", "synthetic"] = "none"
    allow_unverified: bool = False


class BuildProjectRequest(BaseModel):
    run_id: str


class ProjectStatusUpdate(BaseModel):
    run_id: str
    status: ProjectStatus
    verification_evidence: list[str] = Field(default_factory=list)


class RenderResponse(BaseModel):
    run_id: str
    docx_path: str
    download_url: str
    report_url: str
    score_after: ScoreCard | None = None
