import unittest

from work.application.rules import evaluate_product, inspect_snapshot
from work.domain.models import ProductMapping, ProductSnapshot, ProductStatus


class RulesTests(unittest.TestCase):
    def test_profitable_product_is_eligible(self):
        result = evaluate_product(
            10,
            30,
            shipping_cost=2,
            platform_cost=1,
            aftersale_reserve=1,
        )
        self.assertTrue(result.eligible)
        self.assertGreater(result.estimated_net_profit, 5)

    def test_low_margin_product_is_rejected(self):
        result = evaluate_product(20, 22, min_gross_margin=0.3)
        self.assertFalse(result.eligible)
        self.assertIn("毛利率低于阈值", result.reasons)

    def test_source_unavailable_emits_alert(self):
        mapping = ProductMapping(
            "listing-1",
            "sku-1",
            "source-1",
            "red-m",
            "https://example.com",
            10,
            20,
            "supplier-1",
            ProductStatus.ACTIVE,
            10,
        )
        snapshot = ProductSnapshot("source-1", "red-m", 10, 0, False)
        codes = {alert.code for alert in inspect_snapshot(mapping, snapshot)}
        self.assertIn("SOURCE_UNAVAILABLE", codes)


if __name__ == "__main__":
    unittest.main()
