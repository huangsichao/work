from dataclasses import dataclass
import os


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "dev")
    min_gross_margin: float = _float("MIN_GROSS_MARGIN", 0.30)
    min_net_profit: float = _float("MIN_NET_PROFIT", 5.0)
    low_stock_threshold: int = _int("LOW_STOCK_THRESHOLD", 5)
    source_stale_minutes: int = _int("SOURCE_STALE_MINUTES", 60)


settings = Settings()
