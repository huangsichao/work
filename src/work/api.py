from dataclasses import asdict

from fastapi import FastAPI
from pydantic import BaseModel, Field

from work.application.rules import evaluate_product
from work.application.services import MonitoringService
from work.infrastructure.adapters import (
    ConsoleNotifier,
    Demo1688Provider,
    MemoryMappingStore,
)
from work.settings import settings

app = FastAPI(title="拼多多宠物玩具代发运营框架", version="0.1.0")
store = MemoryMappingStore()


class EvaluationRequest(BaseModel):
    purchase_price: float = Field(gt=0)
    sale_price: float = Field(gt=0)
    shipping_cost: float = Field(default=0, ge=0)
    platform_cost: float = Field(default=0, ge=0)
    promotion_cost: float = Field(default=0, ge=0)
    aftersale_reserve: float = Field(default=0, ge=0)
    demand_score: float = Field(default=0.5, ge=0, le=1)
    competition_score: float = Field(default=0.5, ge=0, le=1)
    supply_score: float = Field(default=0.5, ge=0, le=1)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "pdd-pet-resale"}


@app.post("/v1/products/evaluate")
def evaluate(request: EvaluationRequest) -> dict:
    result = evaluate_product(
        **request.model_dump(),
        min_gross_margin=settings.min_gross_margin,
        min_net_profit=settings.min_net_profit,
    )
    return asdict(result)


@app.post("/v1/monitor/sync")
def monitor_sync() -> dict:
    service = MonitoringService(
        store,
        Demo1688Provider(),
        ConsoleNotifier(),
        low_stock_threshold=settings.low_stock_threshold,
        min_net_profit=settings.min_net_profit,
    )
    alerts = service.sync_once()
    return {"alerts": [asdict(alert) for alert in alerts], "count": len(alerts)}
