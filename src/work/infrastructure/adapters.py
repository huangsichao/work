from work.domain.models import Alert, ProductMapping, ProductSnapshot, ProductStatus
from work.infrastructure.tencent_docs import TencentDocsMappingStore

__all__ = [
    "ConsoleNotifier",
    "Demo1688Provider",
    "MemoryMappingStore",
    "PddMarketplaceAdapter",
    "TencentDocsMappingStore",
]


class MemoryMappingStore:
    """开发演示存储；生产环境替换为腾讯文档适配器。"""

    def __init__(self, mappings: list[ProductMapping] | None = None):
        self.items = {
            item.listing_id + ":" + item.listing_sku: item
            for item in (mappings or [])
        }

    def list_active(self) -> list[ProductMapping]:
        return [
            mapping
            for mapping in self.items.values()
            if mapping.status == ProductStatus.ACTIVE
        ]

    def save(self, mapping: ProductMapping) -> None:
        self.items[mapping.listing_id + ":" + mapping.listing_sku] = mapping


class Demo1688Provider:
    def get_snapshot(self, mapping: ProductMapping) -> ProductSnapshot:
        """占位实现，禁止用于真实店铺；接入官方/授权接口后替换。"""
        return ProductSnapshot(
            mapping.source_product_id,
            mapping.source_sku,
            mapping.purchase_price,
            mapping.source_stock,
        )


class ConsoleNotifier:
    def notify(self, alert: Alert) -> None:
        print(f"[{alert.level}] {alert.code} {alert.listing_id or ''} {alert.message}")


class PddMarketplaceAdapter:
    """拼多多官方/授权 ERP 接口边界。"""

    def create_listing_draft(self, mapping: ProductMapping) -> str:
        raise NotImplementedError("请配置拼多多官方 API 或授权 ERP")

    def pause_sku(self, listing_id: str, listing_sku: str) -> None:
        raise NotImplementedError("请配置拼多多官方 API 或授权 ERP")