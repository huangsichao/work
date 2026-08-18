from dataclasses import replace
from typing import Protocol

from work.application.rules import inspect_snapshot
from work.domain.models import Alert, ProductMapping, ProductSnapshot


class SourceProductProvider(Protocol):
    def get_snapshot(self, mapping: ProductMapping) -> ProductSnapshot: ...


class MappingStore(Protocol):
    def list_active(self) -> list[ProductMapping]: ...

    def save(self, mapping: ProductMapping) -> None: ...


class AlertNotifier(Protocol):
    def notify(self, alert: Alert) -> None: ...


class MonitoringService:
    def __init__(
        self,
        store: MappingStore,
        source: SourceProductProvider,
        notifier: AlertNotifier,
        *,
        low_stock_threshold: int = 5,
        min_net_profit: float = 5.0,
    ):
        self.store = store
        self.source = source
        self.notifier = notifier
        self.low_stock_threshold = low_stock_threshold
        self.min_net_profit = min_net_profit

    def sync_once(self) -> list[Alert]:
        emitted: list[Alert] = []
        for mapping in self.store.list_active():
            snapshot = self.source.get_snapshot(mapping)
            updated = replace(
                mapping,
                purchase_price=snapshot.purchase_price,
                source_stock=snapshot.stock,
                last_synced_at=snapshot.captured_at,
            )
            self.store.save(updated)
            for alert in inspect_snapshot(
                updated,
                snapshot,
                low_stock_threshold=self.low_stock_threshold,
                min_net_profit=self.min_net_profit,
            ):
                self.notifier.notify(alert)
                emitted.append(alert)
        return emitted
