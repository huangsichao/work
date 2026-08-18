from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProductStatus(StrEnum):
    CANDIDATE = "candidate"
    PENDING_REVIEW = "pending_review"
    ACTIVE = "active"
    PAUSED = "paused"
    REPLACED = "replaced"


class AlertLevel(StrEnum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


@dataclass(frozen=True)
class Supplier:
    supplier_id: str
    name: str
    product_url: str
    authorized_distribution: bool
    dispatch_hours: int = 48


@dataclass
class ProductMapping:
    listing_id: str
    listing_sku: str
    source_product_id: str
    source_sku: str
    source_url: str
    purchase_price: float
    sale_price: float
    supplier_id: str
    status: ProductStatus = ProductStatus.CANDIDATE
    source_stock: int = 0
    last_synced_at: datetime | None = None


@dataclass(frozen=True)
class ProductSnapshot:
    source_product_id: str
    source_sku: str
    purchase_price: float
    stock: int
    is_available: bool = True
    captured_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class Alert:
    level: AlertLevel
    code: str
    message: str
    listing_id: str | None = None
    created_at: datetime = field(default_factory=utc_now)
