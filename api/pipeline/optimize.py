"""Build a complete JD-tailored resume using the existing generation stage."""
import logging
import re

from pipeline import demo_polish, ideal_resume, output_coverage, practical_detail
from pipeline.presentation import format_resume
from schemas import ExperienceEntry, Fact, Match, OptimizationStrategy, OptimizeResult, Requirement

log = logging.getLogger(__name__)


def _preserves_structure(original: str, candidate: str) -> bool:
    """Do not trade away resume sections or distinct roles/projects for detail."""
    def headings(markdown: str) -> set[str]:
        return {match.group(1).strip().casefold() for match in
                re.finditer(r"(?m)^##\s+(.+?)\s*$", markdown)}

    def block_count(markdown: str, section: str) -> int:
        match = re.search(rf"(?ims)^##\s+{section}\s*$\n(.*?)(?=^##\s+|\Z)", markdown)
        return len(re.findall(r"(?m)^###\s+", match.group(1))) if match else 0

    original_name = re.search(r"(?m)^#\s+(.+?)\s*$", original)
    candidate_name = re.search(r"(?m)^#\s+(.+?)\s*$", candidate)
    if original_name and (not candidate_name or
                          original_name.group(1).strip() != candidate_name.group(1).strip()):
        return False
    if not headings(original).issubset(headings(candidate)):
        return False
    return all(block_count(candidate, section) >= block_count(original, section)
               for section in (r"(?:Professional|Relevant|Work) Experience",
                               r"(?:Selected|Relevant|Key) Projects"))


def optimize(facts: list[Fact], reqs: list[Requirement], matches: list[Match],
             allowed: set[str], strategy: OptimizationStrategy | None = None,
             debug: dict | None = None, *, jd_text: str = "", resume_text: str = "",
             experience_entries: list[ExperienceEntry] | None = None,
             fictional_template: bool = False,
             fabrication_mode: str = "none",
             allow_unverified: bool = False) -> OptimizeResult:
    generation_mode = "fictional_ideal_resume_demo" if fictional_template or fabrication_mode != "none" else "resume_builder_tailoring"
    requirements = "\n".join(f"- {req.text}" for req in reqs)
    full_jd = jd_text or requirements
    # The complete JD is authoritative. Include only extracted requirements
    # that are not already present verbatim, avoiding duplicate prompt tokens
    # without losing normalized/extracted requirements.
    missing_requirement_lines = [req.text for req in reqs
                                 if req.text.casefold() not in full_jd.casefold()]
    prompt = full_jd
    if missing_requirement_lines:
        prompt += "\n\nADDITIONAL EXTRACTED REQUIREMENTS:\n" + "\n".join(
            f"- {text}" for text in missing_requirement_lines)
    background = resume_text or "\n".join(f.text for f in facts)
    markdown = ideal_resume.generate(prompt, background)
    if not markdown.strip():
        raise ValueError("the model returned an empty resume")
    markdown = ideal_resume.finalize(markdown, full_jd, reqs, experience_entries or [],
                                    fictional_template=fictional_template,
                                    fabrication_mode=fabrication_mode,
                                    allow_unverified=allow_unverified,
                                    resume_text=background)
    coverage = output_coverage.evaluate(markdown, reqs)
    missing = [item.requirement for item in coverage.items
               if item.must_have and not item.present]
    if missing and coverage.required_percent < 95 and (fictional_template or fabrication_mode != "none"):
        try:
            revised = ideal_resume.revise_for_coverage(markdown, full_jd, background, missing)
            if revised.strip():
                candidate = ideal_resume.finalize(revised, full_jd, reqs, experience_entries or [],
                                                  fictional_template=fictional_template,
                                                  fabrication_mode=fabrication_mode,
                                                  allow_unverified=allow_unverified,
                                                  resume_text=background)
                candidate_coverage = output_coverage.evaluate(candidate, reqs)
                if candidate_coverage.required_percent > coverage.required_percent:
                    markdown, coverage = candidate, candidate_coverage
        except Exception:
            log.exception("Optional output-coverage revision failed; retaining original resume")
    if fictional_template or fabrication_mode != "none":
        completed = output_coverage.complete_demo_governance_gaps(markdown, reqs)
        completed = demo_polish.polish(completed, full_jd, background)
        if completed != markdown:
            markdown = completed
            coverage = output_coverage.evaluate(markdown, reqs)
    practical_context = full_jd + "\n" + requirements
    practical = practical_detail.assess(markdown, practical_context)
    practical_attempted = False
    practical_accepted = False
    if practical.needs_revision:
        practical_attempted = True
        try:
            revised = ideal_resume.revise_for_practical(
                markdown, full_jd, background, practical.weak_examples)
            if revised.strip():
                candidate = ideal_resume.finalize(
                    revised, full_jd, reqs, experience_entries or [],
                    fictional_template=fictional_template,
                    fabrication_mode=fabrication_mode,
                    allow_unverified=allow_unverified, resume_text=background)
                if fictional_template or fabrication_mode != "none":
                    candidate = output_coverage.complete_demo_governance_gaps(candidate, reqs)
                    candidate = demo_polish.polish(candidate, full_jd, background)
                candidate_coverage = output_coverage.evaluate(candidate, reqs)
                candidate_practical = practical_detail.assess(candidate, practical_context)
                if (not candidate_practical.critical_defects
                        and candidate_practical.quality > practical.quality
                        and candidate_coverage.required_percent >= coverage.required_percent
                        and _preserves_structure(markdown, candidate)):
                    markdown, coverage = candidate, candidate_coverage
                    practical_accepted = True
                else:
                    reasons = []
                    if candidate_practical.critical_defects:
                        reasons.extend(candidate_practical.critical_defects)
                    if candidate_practical.quality <= practical.quality:
                        reasons.append("practical detail did not improve")
                    if candidate_coverage.required_percent < coverage.required_percent:
                        reasons.append("required JD coverage decreased")
                    if not _preserves_structure(markdown, candidate):
                        reasons.append("resume sections, source roles, or projects were lost")
                    log.warning("practical revision rejected for %s: %s",
                                debug.get("run_id") if debug else "run", "; ".join(reasons))
        except Exception:
            log.exception("Optional practical-detail revision failed; retaining original resume")
    markdown = format_resume(markdown, background, experience_entries or [])
    coverage = output_coverage.evaluate(markdown, reqs)
    if debug is not None:
        debug.update(generation_mode=generation_mode, requirement_count=len(reqs),
                     validation_performed=False, fictional_template=fictional_template,
                     fabrication_mode=fabrication_mode, allow_unverified=allow_unverified,
                     practical_revision_attempted=practical_attempted,
                     practical_revision_accepted=practical_accepted)
    return OptimizeResult(markdown=markdown, output_coverage=coverage, ucr=None,
                          finalizer_version=ideal_resume.FINALIZER_VERSION,
                          generation_mode=generation_mode,
                          fictional_template=fictional_template,
                          fabrication_mode=fabrication_mode,
                          allow_unverified=allow_unverified)
