"""Every tunable number in the system lives here. Nothing is hardcoded downstream."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Ollama ---
    ollama_host: str = "http://host.docker.internal:11434"
    model_extract: str = "dolphin-llama3"
    model_rewrite: str = "dolphin-llama3"
    num_ctx: int = 6144           # Enough for a normal JD + resume, with lower local inference latency.
    max_resume_tokens: int = 1800 # A concise, two-page resume; prevents runaway generation.
    temp_extract: float = 0.0
    temp_rewrite: float = 0.15
    top_p: float = 0.9
    stop_sequences: str = "User:,Assistant:,Note:,Warning:"
    seed: int = 42
    llm_timeout: float = 180.0
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
    cache_version: str = "jd-builder-v2"
    column_gap_ratio: float = 0.15

    # --- paths ---
    runs_dir: Path = Path("/data/runs")
    datasets_dir: Path = Path("/data/datasets")
    evaluation_dir: Path = Path("/data/evaluation")
    evaluation_source_dir: Path = Path("/external/jds")
    cache_dir: Path = Path("/data/cache")

    @property
    def resources(self) -> Path:
        return Path(__file__).parent / "resources"

    @property
    def prompts(self) -> Path:
        return Path(__file__).parent / "prompts"


settings = Settings()
settings.runs_dir.mkdir(parents=True, exist_ok=True)
settings.datasets_dir.mkdir(parents=True, exist_ok=True)
settings.cache_dir.mkdir(parents=True, exist_ok=True)
