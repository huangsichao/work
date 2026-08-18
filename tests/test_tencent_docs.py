import unittest

import httpx

from work.domain.models import ProductMapping, ProductStatus
from work.infrastructure.tencent_docs import (
    HttpTencentDocsGateway,
    TencentDocsConfig,
    TencentDocsDataError,
    TencentDocsMappingStore,
)


class FakeGateway:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.writes = []

    def list_rows(self):
        return self.rows

    def upsert_rows(self, rows, *, key_fields):
        self.writes.append((rows, key_fields))


def active_values():
    return {
        "listing_id": "pdd-1",
        "listing_sku": "sku-1",
        "source_product_id": "1688-1",
        "source_sku": "red-m",
        "source_url": "https://detail.1688.com/offer/1.html",
        "purchase_price": "10.5",
        "sale_price": 29.9,
        "supplier_id": "supplier-1",
        "status": "active",
        "source_stock": "12",
    }


class TencentDocsMappingStoreTests(unittest.TestCase):
    def test_list_active_parses_rows_and_filters_status(self):
        paused = active_values() | {"listing_id": "pdd-2", "status": "paused"}
        gateway = FakeGateway([{"values": active_values()}, {"values": paused}])
        mappings = TencentDocsMappingStore(gateway).list_active()
        self.assertEqual(len(mappings), 1)
        self.assertEqual(mappings[0].listing_id, "pdd-1")
        self.assertEqual(mappings[0].purchase_price, 10.5)
        self.assertEqual(mappings[0].source_stock, 12)

    def test_save_upserts_by_listing_and_sku(self):
        gateway = FakeGateway()
        mapping = ProductMapping(
            "pdd-1",
            "sku-1",
            "1688-1",
            "red-m",
            "https://detail.1688.com/offer/1.html",
            11.0,
            29.9,
            "supplier-1",
            ProductStatus.ACTIVE,
            8,
        )
        TencentDocsMappingStore(gateway).save(mapping)
        rows, keys = gateway.writes[0]
        self.assertEqual(keys, ("listing_id", "listing_sku"))
        self.assertEqual(rows[0]["values"]["source_stock"], 8)

    def test_missing_required_field_raises_clear_error(self):
        values = active_values()
        del values["source_sku"]
        gateway = FakeGateway([{"values": values}])
        with self.assertRaises(TencentDocsDataError):
            TencentDocsMappingStore(gateway).list_active()


class HttpTencentDocsGatewayTests(unittest.TestCase):
    def test_reads_all_pages(self):
        requests = []

        def handler(request):
            requests.append(request)
            if request.url.params.get("page_token") == "next":
                return httpx.Response(200, json={"data": {"rows": [{"values": {"id": 2}}]}})
            return httpx.Response(
                200,
                json={"data": {"rows": [{"values": {"id": 1}}], "next_page_token": "next"}},
            )

        client = httpx.Client(
            base_url="https://docs-gateway.example",
            transport=httpx.MockTransport(handler),
        )
        gateway = HttpTencentDocsGateway(
            TencentDocsConfig(
                "https://docs-gateway.example",
                "doc-1",
                "sheet-1",
                "token",
            ),
            client=client,
        )
        rows = gateway.list_rows()
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(requests), 2)

    def test_upsert_sends_keys_and_rows(self):
        captured = {}

        def handler(request):
            captured["payload"] = request.content.decode("utf-8")
            return httpx.Response(200, json={"code": 0})

        client = httpx.Client(
            base_url="https://docs-gateway.example",
            transport=httpx.MockTransport(handler),
        )
        gateway = HttpTencentDocsGateway(
            TencentDocsConfig(
                "https://docs-gateway.example",
                "doc-1",
                "sheet-1",
                "token",
            ),
            client=client,
        )
        gateway.upsert_rows([{"values": {"listing_id": "1"}}], key_fields=("listing_id",))
        self.assertIn("\"key_fields\":[\"listing_id\"]", captured["payload"])


if __name__ == "__main__":
    unittest.main()