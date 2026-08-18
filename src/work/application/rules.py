from dataclasses import dataclass

from work.domain.models import Alert, AlertLevel, ProductMapping, ProductSnapshot


@dataclass(frozen=True)
class Evaluation:
    gross_margin: float
    estimated_net_profit: float
    score: float
    eligible: bool
    reasons: tuple[str, ...] = ()


def evaluate_product(
    purchase_price: float,
    sale_price: float,
    *,
    shipping_cost: float = 0.0,
    platform_cost: float = 0.0,
    promotion_cost: float = 0.0,
    aftersale_reserve: float = 0.0,
    demand_score: float = 0.5,
    competition_score: float = 0.5,
    supply_score: float = 0.5,
    min_gross_margin: float = 0.30,
    min_net_profit: float = 5.0,
) -> Evaluation:
    if sale_price <= 0:
        return Evaluation(0.0, -1.0, 0.0, False, ("销售价必须大于0",))
    total_cost = (
        purchase_price
        + shipping_cost
        + platform_cost
        + promotion_cost
        + aftersale_reserve
    )
    net_profit = sale_price - total_cost
    gross_margin = (sale_price - purchase_price) / sale_price
    score = max(
        0.0,
        min(
            100.0,
            demand_score * 35
            + competition_score * 20
            + supply_score * 30
            + gross_margin * 15,
        ),
    )
    reasons: list[str] = []
    if gross_margin < min_gross_margin:
        reasons.append("毛利率低于阈值")
    if net_profit < min_net_profit:
        reasons.append("预计净利润低于阈值")
    return Evaluation(gross_margin, net_profit, score, not reasons, tuple(reasons))


def inspect_snapshot(
    mapping: ProductMapping,
    snapshot: ProductSnapshot,
    *,
    low_stock_threshold: int = 5,
    min_net_profit: float = 5.0,
) -> list[Alert]:
    alerts: list[Alert] = []
    if not snapshot.is_available:
        alerts.append(
            Alert(
                AlertLevel.P0,
                "SOURCE_UNAVAILABLE",
                "1688货源商品不可售",
                mapping.listing_id,
            )
        )
    if snapshot.stock <= low_stock_threshold:
        alerts.append(
            Alert(
                AlertLevel.P1,
                "LOW_STOCK",
                f"货源库存仅剩 {snapshot.stock}",
                mapping.listing_id,
            )
        )
    estimated_profit = mapping.sale_price - snapshot.purchase_price
    if estimated_profit < min_net_profit:
        alerts.append(
            Alert(
                AlertLevel.P1,
                "MARGIN_DROP",
                f"预计单笔利润降至 {estimated_profit:.2f}",
                mapping.listing_id,
            )
        )
    return alerts
