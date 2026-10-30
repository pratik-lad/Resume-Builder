"""Every tunable number in the system lives here. Nothing is hardcoded downstream."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


def _local_data_path(*parts: str) -> Path:
    root = Path(__file__).resolve().parents[1]
    return root.joinpath("data", *parts)


def _normalize_data_path(value: Path | str) -> Path:
    text = str(value).replace("\\", "/")
    if text.startswith("/data/") or text.startswith("data/") or text.startswith("//data/"):
        suffix = text.split("/data/", 1)[1] if "/data/" in text else text.split("data/", 1)[1]
        return _local_data_path(*[part for part in suffix.split("/") if part])
    if text == "/data" or text == "data":
        return _local_data_path()
    return Path(value)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Native GGUF server on the Windows host ---
    llm_host: str = "http://host.docker.internal:18081"
    llm_api_key: str = ""
    llm_revision: str = "unsloth-qwen3.5-4b-q4_k_m-e87f1764"
    model_extract: str = "qwen3.5:4b"
    model_rewrite: str = "qwen3.5:4b"
    catalog_enabled: bool = True  # Local, bounded JD terminology lookup; no model change.
    num_ctx: int = 8192           # Keep the current project setting across the runtime change.
    max_resume_tokens: int = 3500 # Room for distinct jobs, projects, and a complete education section.
    temp_extract: float = 0.0
    max_extract_tokens: int = 1200
    max_jd_extract_tokens: int = 900
    temp_rewrite: float = 0.15
    top_p: float = 0.9
    top_k: int = 20
    presence_penalty: float = 1.5
    repeat_penalty: float = 1.05
    stop_sequences: str = "User:,Assistant:,Note:,Warning:"
    seed: int = 42
    llm_timeout: float = 600.0
    think: bool = False   # disable chain-of-thought on hybrid-reasoning models; see llm/client.py

    # --- embeddings ---
    embed_model: str = "BAAI/bge-small-en-v1.5"
    embed_enabled: bool = True    # falls back to lexical-only matching if unavailable

    # --- matching / scoring ---
    sem_cal_min: float = 0.45     # BGE cosines live in a narrow band; calibrate to [0,1]
    sem_cal_max: float = 0.85
    covered_threshold: float = 0.75
    partial_threshold: float = 0.40
    # 0.88 was too permissive -- it let e.g. "risk assessment" fuzzy-match
    # "data assessment" purely on the shared word "assessment", inflating scores
    # for genuinely unrelated resume/JD pairs. Tightened as an interim measure;
    # full calibration (README Part 4, Step 4) still needs real labelled pairs.
    fuzzy_threshold: float = 0.92

    w_hard: float = 0.40
    w_resp: float = 0.25
    w_qual: float = 0.20
    w_keyword: float = 0.15
    weight_must_have: float = 3.0
    weight_nice_to_have: float = 1.0

    # --- validation ---
    drift_threshold: float = 0.70
    entity_fuzzy_threshold: float = 0.90
    max_repair_attempts: int = 2

    # --- pipeline limits ---
    max_bullets: int = 14
    low_fit_score: float = 25.0
    ocr_min_chars: int = 200
    ocr_alnum_ratio: float = 0.5
    extraction_workers: int = 2
    cache_version: str = "jd-builder-v4"
    column_gap_ratio: float = 0.15

    # --- paths ---
    runs_dir: Path = _local_data_path("runs")
    datasets_dir: Path = _local_data_path("datasets")
    evaluation_dir: Path = _local_data_path("evaluation")
    evaluation_source_dir: Path = Path("/external/jds")
    cache_dir: Path = _local_data_path("cache")

    @property
    def resources(self) -> Path:
        return Path(__file__).parent / "resources"

    @property
    def prompts(self) -> Path:
        return Path(__file__).parent / "prompts"


settings = Settings()
for attr in ("runs_dir", "datasets_dir", "cache_dir", "evaluation_dir"):
    value = getattr(settings, attr)
    normalized = _normalize_data_path(value)
    if normalized != value:
        setattr(settings, attr, normalized)
    normalized.mkdir(parents=True, exist_ok=True)
