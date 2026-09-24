"""Build a complete JD-tailored resume using the existing generation stage."""
from pipeline import ideal_resume
from schemas import ExperienceEntry, Fact, Match, OptimizationStrategy, OptimizeResult, Requirement


def optimize(facts: list[Fact], reqs: list[Requirement], matches: list[Match],
             allowed: set[str], strategy: OptimizationStrategy | None = None,
             debug: dict | None = None, *, jd_text: str = "", resume_text: str = "",
             experience_entries: list[ExperienceEntry] | None = None) -> OptimizeResult:
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
    markdown = ideal_resume.finalize(markdown, full_jd, reqs, experience_entries or [])
    if debug is not None:
        debug.update(generation_mode="resume_builder_tailoring", requirement_count=len(reqs),
                     validation_performed=False)
    return OptimizeResult(markdown=markdown, ucr=None,
                          finalizer_version=ideal_resume.FINALIZER_VERSION)

