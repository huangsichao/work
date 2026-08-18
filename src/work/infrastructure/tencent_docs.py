from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
import os
import time
from typing import Any, Protocol

import httpx

from work.domain.models import ProductMapping, ProductStatus


class TencentDocsError(RuntimeError):
    """腾讯文档请求或响应错误。"""


class TencentDocsDataError(TencentDocsError):
    """腾讯文档行数据不符合商品映射结构。"""


class TencentDocsGateway(Protocol):
    def list_rows(self) -> list[dict[str, Any]]: ...

    def upsert_rows(
        self,
        rows: list[dict[str, Any]],
        *,
        key_fields: tuple[str, ...],
    ) -> None: ...


@dataclass(frozen=True)
class TencentDocsConfig:
    base_url: str
    document_id: str
    sheet_id: str
    access_token: str
    read_path: str = "/documents/{document_id}/sheets/{sheet_id}/rows"
    write_path: str = "/documents/{document_id}/sheets/{sheet_id}/rows:upsert"
    page_size: int = 200
    timeout_seconds: float = 10.0
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> TencentDocsConfig:
        values = {
            "base_url": os.getenv("TENCENT_DOCS_BASE_URL", ""),
            "document_id": os.getenv("TENCENT_DOCS_DOCUMENT_ID", ""),
            "sheet_id": os.getenv("TENCENT_DOCS_SHEET_ID", ""),
            "access_token": os.getenv("TENCENT_DOCS_ACCESS_TOKEN", ""),
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise TencentDocsError(
                "缺少腾讯文档配置: " + ", ".join(sorted(missing))
            )
        return cls(
            **values,
            read_path=os.getenv("TENCENT_DOCS_READ_PATH", cls.read_path),
            write_path=os.getenv("TENCENT_DOCS_WRITE_PATH", cls.write_path),
            page_size=int(os.getenv("TENCENT_DOCS_PAGE_SIZE", "200")),
            timeout_seconds=float(os.getenv("TENCENT_DOCS_TIMEOUT_SECONDS", "10")),
            max_retries=int(os.getenv("TENCENT_DOCS_MAX_RETRIES", "3")),
        )


class HttpTencentDocsGateway:
    """调用腾讯文档开放接口或授权网关的 HTTP 实现。"""

    def __init__(
        self,
        config: TencentDocsConfig,
        *,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.config = config
        self._sleep = sleep
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=config.base_url.rstrip("/"),
            timeout=config.timeout_seconds,
            headers={
                "Authorization": f"Bearer {config.access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> HttpTencentDocsGateway:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def list_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        page_token: str | None = None
        path = self.config.read_path.format(
            document_id=self.config.document_id,
            sheet_id=self.config.sheet_id,
        )
        while True:
            params: dict[str, Any] = {"page_size": self.config.page_size}
            if page_token:
                params["page_token"] = page_token
            payload = self._request("GET", path, params=params)
            data = _unwrap_data(payload)
            page_rows = data.get("rows", [])
            if not isinstance(page_rows, list):
                raise TencentDocsDataError("腾讯文档响应中的 rows 必须是数组")
            rows.extend(_require_row(row) for row in page_rows)
            page_token = _next_page_token(data)
            if not page_token:
                return rows

    def upsert_rows(
        self,
        rows: list[dict[str, Any]],
        *,
        key_fields: tuple[str, ...],
    ) -> None:
        if not rows:
            return
        path = self.config.write_path.format(
            document_id=self.config.document_id,
            sheet_id=self.config.sheet_id,
        )
        self._request(
            "POST",
            path,
            json_body={
                "document_id": self.config.document_id,
                "sheet_id": self.config.sheet_id,
                "key_fields": list(key_fields),
                "rows": rows,
            },
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            try:
                response = self._client.request(
                    method,
                    path,
                    params=params,
                    json=json_body,
                )
            except httpx.RequestError as exc:
                last_error = exc
                if attempt >= self.config.max_retries:
                    raise TencentDocsError(f"腾讯文档网络请求失败: {exc}") from exc
                self._sleep(2**attempt)
                continue

            if response.status_code == 429 or response.status_code >= 500:
                if attempt >= self.config.max_retries:
                    raise TencentDocsError(
                        f"腾讯文档请求失败: HTTP {response.status_code}"
                    )
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                self._sleep(delay)
                continue

            if response.status_code >= 400:
                raise TencentDocsError(
                    f"腾讯文档请求失败: HTTP {response.status_code} {response.text[:300]}"
                )
            try:
                payload = response.json()
            except ValueError as exc:
                raise TencentDocsError("腾讯文档返回了非 JSON 响应") from exc
            if not isinstance(payload, dict):
                raise TencentDocsError("腾讯文档响应必须是 JSON 对象")
            code = payload.get("code")
            if code not in (None, 0, "0"):
                message = payload.get("message") or payload.get("msg") or "未知错误"
                raise TencentDocsError(f"腾讯文档业务错误 {code}: {message}")
            return payload

        raise TencentDocsError(f"腾讯文档请求失败: {last_error}")


class TencentDocsMappingStore:
    """将腾讯文档行转换为商品映射，并按商品+SKU幂等写回。"""

    KEY_FIELDS = ("listing_id", "listing_sku")

    def __init__(self, gateway: TencentDocsGateway):
        self.gateway = gateway

    def list_active(self) -> list[ProductMapping]:
        mappings: list[ProductMapping] = []
        for row in self.gateway.list_rows():
            values = _row_values(row)
            status = _status(values.get("status", ProductStatus.CANDIDATE))
            if status != ProductStatus.ACTIVE:
                continue
            mappings.append(_mapping_from_values(values, status))
        return mappings

    def save(self, mapping: ProductMapping) -> None:
        values: dict[str, Any] = {
            "listing_id": mapping.listing_id,
            "listing_sku": mapping.listing_sku,
            "source_product_id": mapping.source_product_id,
            "source_sku": mapping.source_sku,
            "source_url": mapping.source_url,
            "purchase_price": mapping.purchase_price,
            "sale_price": mapping.sale_price,
            "supplier_id": mapping.supplier_id,
            "status": mapping.status.value,
            "source_stock": mapping.source_stock,
            "last_synced_at": (
                mapping.last_synced_at.isoformat()
                if mapping.last_synced_at
                else None
            ),
        }
        self.gateway.upsert_rows(
            [{"values": values}],
            key_fields=self.KEY_FIELDS,
        )


def build_tencent_docs_store_from_env() -> TencentDocsMappingStore:
    return TencentDocsMappingStore(
        HttpTencentDocsGateway(TencentDocsConfig.from_env())
    )


def _unwrap_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data", payload)
    if not isinstance(data, dict):
        raise TencentDocsDataError("腾讯文档响应中的 data 必须是对象")
    return data


def _next_page_token(data: dict[str, Any]) -> str | None:
    token = data.get("next_page_token") or data.get("nextPageToken")
    return str(token) if token else None


def _require_row(row: Any) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise TencentDocsDataError("腾讯文档中的每一行必须是对象")
    return row


def _row_values(row: dict[str, Any]) -> dict[str, Any]:
    values = row.get("values") or row.get("fields") or row
    if not isinstance(values, dict):
        raise TencentDocsDataError("腾讯文档行 values/fields 必须是对象")
    return values


def _mapping_from_values(
    values: dict[str, Any],
    status: ProductStatus,
) -> ProductMapping:
    required = (
        "listing_id",
        "listing_sku",
        "source_product_id",
        "source_sku",
        "source_url",
        "purchase_price",
        "sale_price",
        "supplier_id",
    )
    missing = [name for name in required if values.get(name) in (None, "")]
    if missing:
        raise TencentDocsDataError(
            "商品映射缺少字段: " + ", ".join(missing)
        )
    return ProductMapping(
        listing_id=str(values["listing_id"]),
        listing_sku=str(values["listing_sku"]),
        source_product_id=str(values["source_product_id"]),
        source_sku=str(values["source_sku"]),
        source_url=str(values["source_url"]),
        purchase_price=_float_value(values["purchase_price"], "purchase_price"),
        sale_price=_float_value(values["sale_price"], "sale_price"),
        supplier_id=str(values["supplier_id"]),
        status=status,
        source_stock=_int_value(values.get("source_stock", 0), "source_stock"),
        last_synced_at=_datetime_value(values.get("last_synced_at")),
    )


def _status(value: Any) -> ProductStatus:
    try:
        return ProductStatus(str(value).strip().lower())
    except ValueError as exc:
        raise TencentDocsDataError(f"未知商品状态: {value}") from exc


def _float_value(value: Any, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise TencentDocsDataError(f"{field_name} 不是有效数字: {value}") from exc


def _int_value(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise TencentDocsDataError(f"{field_name} 不是有效整数: {value}") from exc


def _datetime_value(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise TencentDocsDataError(f"last_synced_at 不是 ISO 时间: {value}") from exc