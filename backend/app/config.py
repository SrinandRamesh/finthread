from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite:///./aml.db"
    CORS_ORIGINS: str = "http://localhost:5173"
    LOAD_SAMPLE_ON_STARTUP: bool = True
    SAMPLE_DATA_PATH: str = "data/sample_transactions.csv"
    MAX_UPLOAD_ROWS: int = 50000
    MAX_GRAPH_EDGES: int = 1500

    # detection
    FAN_WINDOW_HOURS: float = 48
    FAN_MIN_COUNTERPARTIES: int = 5
    CYCLE_MAX_LENGTH: int = 6
    CYCLE_MAX_SPAN_HOURS: float = 168
    PASS_THROUGH_MAX_HOURS: float = 24
    PASS_THROUGH_MIN_RATIO: float = 0.8
    PASS_THROUGH_MIN_HOPS: int = 3

    # risk
    REPORTING_THRESHOLD: float = 1_000_000
    STRUCTURING_LOWER_RATIO: float = 0.9
    ALERT_THRESHOLD: int = 40
    HIGH_RISK_THRESHOLD: int = 70

    # baseline
    BASELINE_LARGE_TX: float = 1_000_000
    BASELINE_DAILY_OUT_AMOUNT: float = 2_500_000
    BASELINE_DAILY_OUT_COUNT: int = 10

    LLM_ENABLED: bool = False

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    def grouped(self) -> dict[str, dict[str, float]]:
        d = self.model_dump()
        return {
            "detection": {k: float(v) for k, v in d.items()
                          if k.startswith(("FAN_", "CYCLE_", "PASS_THROUGH_"))},
            "risk": {k: float(d[k]) for k in
                     ("REPORTING_THRESHOLD", "STRUCTURING_LOWER_RATIO", "ALERT_THRESHOLD", "HIGH_RISK_THRESHOLD")},
            "baseline": {k: float(v) for k, v in d.items() if k.startswith("BASELINE_")},
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
