"""Ideal-resume API, with optional legacy matching and analysis endpoints."""
import logging
import hashlib
import json
import os
import shutil
import time
from pathlib import Path

from pipeline.presentation import format_resume
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

import runstore
from config import settings
from llm import client as llm_client
from pipeline import (demo_polish, ideal_resume, ingest, jd as jd_stage, match as match_stage,
                      optimize as optimize_stage, output_coverage,
                      project_bridge as project_stage,
                      render, strategy as strategy_stage)
from review import router as review_router
from schemas import (BuildProjectRequest, FactLedger, GapReport, IdealResumeRequest,
                     IdealResumeResponse, IngestResponse, JDRequest, MatchResponse, MatchResult, OptimizeResponse,
                     OptimizeResult, ProjectBuildPlan, ProjectStatusUpdate,
                     ProposedProject, RenderResponse, RequirementSet, RunRef,
                     ScoreCard, StrategyResponse, TruthSafetyReport)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("resume-optimizer")

app = FastAPI(title="Resume Optimizer", version="1.0.0",
              description="Local resume building and tailoring from the complete job description.")
app.include_router(review_router)


def _require(run_id: str, name: str) -> dict:
    data = runstore.load_json(run_id, name)
    if data is None:
        raise HTTPException(404, f"run {run_id}: '{name}' not found - run the earlier stage first")
    return data


def _cache_path(kind: str, content: bytes) -> Path:
    # The resume ledger includes explicit employment-date entries. Keep stale
    # ledgers out of the cache without changing the active workflow.
    schema_tag = b"source-fidelity-v4" if kind == "resume" else b"full-jd-tailoring-v4"
    identity = b"|".join((settings.cache_version.encode(), schema_tag,
                          settings.model_extract.encode(), settings.llm_revision.encode(), content))
    return settings.cache_dir / kind / f"{hashlib.sha256(identity).hexdigest()}.json"


def _cache_load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _cache_save(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, path)


@app.get("/health")
def health():
    return {"status": "ok", **llm_client.health(),
            "configured": {"extract": settings.model_extract,
                           "rewrite": settings.model_rewrite,
                           "num_ctx": settings.num_ctx,
                           "embeddings": settings.embed_model}}


@app.post("/v1/ideal-resume", response_model=IdealResumeResponse)
def build_ideal_resume(req: IdealResumeRequest):
    """Return a rebuilt, JD-tailored candidate resume using the existing endpoint."""
    if not req.jd_text.strip():
        raise HTTPException(400, "jd_text is empty")
    started = time.perf_counter()
    llm_client.reset_call_stats()
    requirements = jd_stage.extract(req.jd_text)
    try:
        result = optimize_stage.optimize([], requirements.requirements, [], set(),
                                         jd_text=req.jd_text, resume_text=req.resume_text,
                                         fictional_template=req.fictional_template,
                                         fabrication_mode=req.fabrication_mode,
                                         allow_unverified=req.allow_unverified)
    except ValueError as exc:
        raise HTTPException(502, str(exc)) from exc
    log.info("stage ideal_resume completed in %.1fs (%s)",
             time.perf_counter() - started, llm_client.call_stats())
    return IdealResumeResponse(markdown=result.markdown, requirements=requirements,
                               output_coverage=result.output_coverage,
                               fictional_template=result.fictional_template,
                               fabrication_mode=result.fabrication_mode,
                               allow_unverified=result.allow_unverified)


@app.post("/v1/ingest", response_model=IngestResponse)
async def ingest_resume(file: UploadFile = File(...)):
    run_id = runstore.new_run_id()
    t0 = time.perf_counter()
    llm_client.reset_call_stats()

    dest = runstore.run_dir(run_id) / f"source{Path(file.filename or 'resume.pdf').suffix.lower()}"
    with dest.open("wb") as fh:
        shutil.copyfileobj(file.file, fh)

    cache_path = _cache_path("resume", dest.read_bytes())
    cached = _cache_load(cache_path)
    if cached:
        ledger = FactLedger(**cached["ledger"])
        sections = cached["sections"]
        warnings = cached.get("warnings", [])
        cache_hit = True
    else:
        try:
            doc = ingest.parse_file(str(dest))
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        ledger, sections = ingest.build_ledger(doc)
        warnings = doc.warnings
        cache_hit = False
        _cache_save(cache_path, {"ledger": ledger.model_dump(), "sections": sections,
                                 "warnings": warnings})
    runstore.save_json(run_id, "facts", ledger)
    runstore.save_json(run_id, "sections", sections)
    runstore.save_json(run_id, "meta", {"filename": file.filename, "cache_hit": cache_hit,
                                        "ingest_seconds": round(time.perf_counter() - t0, 2)})
    log.info("run %s ingested: %s facts in %.1fs (cache_hit=%s, %s)",
             run_id, len(ledger.facts), time.perf_counter() - t0, cache_hit,
             llm_client.call_stats())
    return IngestResponse(run_id=run_id, sections=sections,
                          fact_count=len(ledger.facts), warnings=warnings)


@app.post("/v1/jd/extract")
def extract_jd(req: JDRequest):
    if not req.jd_text.strip():
        raise HTTPException(400, "jd_text is empty")
    started = time.perf_counter()
    llm_client.reset_call_stats()
    normalized = req.jd_text.strip()
    cache_path = _cache_path("jd", normalized.encode("utf-8"))
    cached = _cache_load(cache_path)
    if cached:
        req_set = RequirementSet(**cached, jd_text=normalized)
    else:
        req_set = jd_stage.extract(normalized)
        payload = req_set.model_dump(exclude={"jd_text"})
        _cache_save(cache_path, payload)
    runstore.save_json(req.run_id, "requirements", req_set)
    log.info("run %s JD extracted: %s requirements in %.1fs (cache_hit=%s, %s)",
             req.run_id, len(req_set.requirements), time.perf_counter() - started,
             bool(cached), llm_client.call_stats())
    return req_set


@app.post("/v1/match", response_model=MatchResponse)
def run_match(ref: RunRef):
    ledger = FactLedger(**_require(ref.run_id, "facts"))
    req_set = RequirementSet(**_require(ref.run_id, "requirements"))

    matches, card, gap = match_stage.run(
        req_set, ledger.facts, ledger.raw_text, ledger.experience_entries,
        allow_unverified=ref.allow_unverified)
    runstore.save_json(ref.run_id, "match",
                       MatchResult(matches=matches, score_card=card, gap_report=gap))
    coverage = strategy_stage.coverage_analysis(req_set.requirements, matches, ledger.facts,
                                              allow_unverified=getattr(ref, "allow_unverified", False))
    return MatchResponse(run_id=ref.run_id, score_before=card,
                         gap_report=gap, match_table=matches, coverage=coverage)


def _strategy_for(run_id: str, ledger: FactLedger, req_set: RequirementSet,
                  mr: MatchResult):
    cached = runstore.load_json(run_id, "strategy")
    if cached:
        from schemas import OptimizationStrategy
        strategy = OptimizationStrategy(**cached)
    else:
        strategy = strategy_stage.build(req_set, ledger.facts, mr.matches,
                                        mr.score_card, ledger.raw_text,
                                        ledger.experience_entries,
                                        allow_unverified=getattr(ref, "allow_unverified", False))
        runstore.save_json(run_id, "strategy", strategy)
    bridge_data = runstore.load_json(run_id, "project_bridge")
    bridge = ProposedProject(**bridge_data) if bridge_data else project_stage.recommend(req_set, strategy)
    if bridge and not bridge_data:
        runstore.save_json(run_id, "project_bridge", bridge)
    return strategy, bridge


@app.post("/v1/strategy", response_model=StrategyResponse)
def build_strategy(ref: RunRef):
    ledger = FactLedger(**_require(ref.run_id, "facts"))
    req_set = RequirementSet(**_require(ref.run_id, "requirements"))
    mr = MatchResult(**_require(ref.run_id, "match"))
    strategy, bridge = _strategy_for(ref.run_id, ledger, req_set, mr)
    return StrategyResponse(run_id=ref.run_id, strategy=strategy, project_bridge=bridge)


@app.post("/v1/optimize", response_model=OptimizeResponse)
def run_optimize(ref: RunRef):
    started = time.perf_counter()
    llm_client.reset_call_stats()
    ledger = FactLedger(**_require(ref.run_id, "facts"))
    req_set = RequirementSet(**_require(ref.run_id, "requirements"))
    signature = hashlib.sha256((ledger.raw_text + req_set.model_dump_json()
                                + settings.model_rewrite
                                + settings.llm_revision
                                + ideal_resume.PROMPT_VERSION
                                + str(ref.fictional_template)
                                + ref.fabrication_mode
                                + str(ref.allow_unverified)).encode()).hexdigest()
    cached = runstore.load_json(ref.run_id, "rewrites")
    if cached and cached.get("markdown") and cached.get("input_signature") == signature:
        result = OptimizeResult(**cached)
        if result.finalizer_version != ideal_resume.FINALIZER_VERSION:
            if result.finalizer_version in {"resume-finalizer-v26", "resume-finalizer-v27"}:
                if result.finalizer_version == "resume-finalizer-v26":
                    result.markdown = ideal_resume.polish_summary_voice(result.markdown)
                result.markdown = ideal_resume.polish_project_titles(result.markdown,
                                                                      ledger.raw_text)
            else:
                result.markdown = ideal_resume.finalize(result.markdown, req_set.jd_text,
                                                        req_set.requirements, ledger.experience_entries,
                                                        fictional_template=ref.fictional_template,
                                                        fabrication_mode=ref.fabrication_mode,
                                                        allow_unverified=ref.allow_unverified,
                                                        resume_text=ledger.raw_text)
            result.finalizer_version = ideal_resume.FINALIZER_VERSION
            result.fictional_template = ref.fictional_template
            result.fabrication_mode = ref.fabrication_mode
            result.allow_unverified = ref.allow_unverified
            result.output_coverage = output_coverage.evaluate(result.markdown, req_set.requirements)
            runstore.save_json(ref.run_id, "rewrites", result)
            runstore.save_text(ref.run_id, "ideal_resume.md", result.markdown)
        current_coverage = output_coverage.evaluate(result.markdown, req_set.requirements)
        content_changed = False
        if ref.fictional_template or ref.fabrication_mode != "none":
            completed = output_coverage.strip_demo_coverage_appendix(result.markdown)
            completed = output_coverage.complete_demo_governance_gaps(
                completed, req_set.requirements)
            completed = demo_polish.polish(completed, req_set.jd_text, ledger.raw_text)
            if completed != result.markdown:
                result.markdown = completed
                content_changed = True
                current_coverage = output_coverage.evaluate(completed, req_set.requirements)
                runstore.save_text(ref.run_id, "ideal_resume.md", completed)
        if content_changed or result.output_coverage != current_coverage:
            result.output_coverage = current_coverage
            runstore.save_json(ref.run_id, "rewrites", result)
    else:
        ledger = FactLedger(**_require(ref.run_id, "facts"))
        req_set = RequirementSet(**_require(ref.run_id, "requirements"))
        debug = {"run_id": ref.run_id}
        try:
            result = optimize_stage.optimize(
                ledger.facts, req_set.requirements, [], set(), debug=debug,
                jd_text=req_set.jd_text, resume_text=ledger.raw_text,
                experience_entries=ledger.experience_entries,
                fictional_template=ref.fictional_template,
                fabrication_mode=ref.fabrication_mode,
                allow_unverified=ref.allow_unverified)
        except ValueError as exc:
            raise HTTPException(502, str(exc)) from exc
        result.input_signature = signature
        result.fictional_template = ref.fictional_template
        result.fabrication_mode = ref.fabrication_mode
        result.allow_unverified = ref.allow_unverified
        runstore.save_json(ref.run_id, "rewrite_debug", debug)
        runstore.save_json(ref.run_id, "rewrites", result)
        runstore.save_text(ref.run_id, "ideal_resume.md", result.markdown)
    displayed = format_resume(result.markdown, ledger.raw_text, ledger.experience_entries)
    if displayed != result.markdown:
        result.markdown = displayed
        result.output_coverage = output_coverage.evaluate(displayed, req_set.requirements)
        runstore.save_json(ref.run_id, "rewrites", result)
        runstore.save_text(ref.run_id, "ideal_resume.md", displayed)
    log.info("run %s optimized in %.1fs (%s)", ref.run_id,
             time.perf_counter() - started, llm_client.call_stats())
    return OptimizeResponse(run_id=ref.run_id,
                            **result.model_dump(exclude={"input_signature", "finalizer_version"}))


@app.post("/v1/project/build", response_model=ProjectBuildPlan)
def build_project(req: BuildProjectRequest):
    project = ProposedProject(**_require(req.run_id, "project_bridge"))
    plan = project_stage.build_plan(project)
    runstore.save_json(req.run_id, "project_build", plan)
    return plan


@app.post("/v1/project/status", response_model=ProposedProject)
def update_project_status(req: ProjectStatusUpdate):
    project = ProposedProject(**_require(req.run_id, "project_bridge"))
    try:
        project = project_stage.with_status(project, req.status, req.verification_evidence)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    runstore.save_json(req.run_id, "project_bridge", project)
    return project


@app.post("/v1/render", response_model=RenderResponse)
def run_render(ref: RunRef):
    req_set = RequirementSet(**_require(ref.run_id, "requirements"))
    result = OptimizeResult(**_require(ref.run_id, "rewrites"))
    if not result.markdown:
        raise HTTPException(409, "run /v1/optimize to generate the ideal resume first")
    ledger = FactLedger(**_require(ref.run_id, "facts"))
    cleaned = format_resume(output_coverage.strip_demo_coverage_appendix(result.markdown),
                            ledger.raw_text, ledger.experience_entries)
    if cleaned != result.markdown:
        result.markdown = cleaned
        result.output_coverage = output_coverage.evaluate(cleaned, req_set.requirements)
        runstore.save_json(ref.run_id, "rewrites", result)
        runstore.save_text(ref.run_id, "ideal_resume.md", cleaned)
    docx_path = render.build_ideal_docx(
        result.markdown, runstore.run_dir(ref.run_id) / "optimized.docx")
    html = render.build_ideal_report(result.markdown, req_set)
    runstore.save_text(ref.run_id, "report.html", html)
    return RenderResponse(run_id=ref.run_id, docx_path=str(docx_path),
                          download_url=f"/v1/download/{ref.run_id}",
                          report_url=f"/v1/report/{ref.run_id}")


@app.get("/v1/report/{run_id}", response_class=HTMLResponse)
def report(run_id: str):
    path = runstore.run_dir(run_id) / "report.html"
    if not path.exists():
        raise HTTPException(404, "no report - run /v1/render first")
    return HTMLResponse(path.read_text(encoding="utf-8"))


@app.get("/v1/download/{run_id}")
def download(run_id: str):
    path = runstore.run_dir(run_id) / "optimized.docx"
    if not path.exists():
        raise HTTPException(404, "no document - run /v1/render first")
    return FileResponse(path, filename="optimized_resume.docx",
                        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@app.get("/v1/dataset/export")
def dataset_export():
    """Export tailored-resume examples with their complete job descriptions."""
    rows = []
    for run_dir in sorted(settings.runs_dir.iterdir()):
        rw = run_dir / "rewrites.json"
        req = run_dir / "requirements.json"
        if not rw.exists() or not req.exists():
            continue
        result = json.loads(rw.read_text(encoding="utf-8"))
        if not result.get("markdown"):
            continue
        requirements = json.loads(req.read_text(encoding="utf-8"))
        rows.append({"messages": [
            {"role": "system", "content": ideal_resume.SYSTEM_PROMPT},
            {"role": "user", "content": requirements.get("jd_text", "")},
            {"role": "assistant", "content": result["markdown"]},
        ]})
    return {"count": len(rows), "rows": rows}
