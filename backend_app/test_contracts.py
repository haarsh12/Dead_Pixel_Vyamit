"""Offline contract checks for the Flutter-to-FastAPI integration.

These checks never open a database connection or call an AI provider. They
protect the endpoints and response shapes the application relies on.
"""

import unittest

from core.rate_limit import SlidingWindowRateLimiter
from core.shop_categories import SHOP_CATEGORIES, normalise_category
from db.models import Bill, SaleItem
from db.schemas import OTPRequest, VerifyOTPRequest
from services.voice_inventory_service import VoiceInventoryService
from services.voice_service import VoiceService


class _StubPipeline:
    def invoke(self, prompt: str):
        return (
            {
                "type": "BILL",
                "customer_name": "Asha",
                "items": [{"name": "Rice", "quantity": 2, "price": 60, "unit": "kg"}],
                "msg": "Rice add kar diya.",
                "should_stop": False,
            },
            0.012,
            "stub",
        )


class FrontendContractTests(unittest.TestCase):
    def test_phone_input_is_normalised_consistently(self):
        self.assertEqual(OTPRequest(phone_number="98765 43210").phone_number, "+919876543210")
        self.assertEqual(
            VerifyOTPRequest(phone_number="+91-9876543210", otp_code="112233").phone_number,
            "+919876543210",
        )

    def test_voice_service_returns_flutter_bill_shape(self):
        response = VoiceService(_StubPipeline()).process(
            "two kilo rice",
            [{"names": ["Rice"], "price": 60, "unit": "kg", "category": "Grains"}],
            "Kirana",
        )
        self.assertEqual(response["type"], "BILL")
        self.assertEqual(response["customer_name"], "Asha")
        self.assertEqual(response["items"][0]["qty_display"], "2kg")
        self.assertEqual(response["items"][0]["total"], 120.0)
        self.assertEqual(response["metadata"]["model_used"], "stub")

    def test_voice_inventory_fallback_marks_existing_item(self):
        service = VoiceInventoryService()
        parsed = service._normalise_result(
            service._fallback_parse("rice 55 rs kg"),
            "rice 55 rs kg",
            [{"id": "rice", "names": ["Rice"], "price": 50, "unit": "kg", "category": "Grains"}],
            ["Grains"],
        )
        item = parsed["categories"][0]["items"][0]
        self.assertTrue(item["is_existing"])
        self.assertEqual(item["old_price"], 50.0)

    def test_rate_limit_rejects_the_next_request(self):
        limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=60)
        limiter.check("127.0.0.1", "+919876543210")
        with self.assertRaises(Exception) as context:
            limiter.check("127.0.0.1", "+919876543210")
        self.assertEqual(context.exception.status_code, 429)

    def test_all_business_categories_have_one_canonical_scope(self):
        self.assertEqual(len(SHOP_CATEGORIES), 10)
        self.assertEqual(normalise_category("stationary"), "Stationery")
        self.assertEqual(normalise_category("fast-food"), "Fast Food")
        self.assertEqual(normalise_category("Doctor Prescription"), "Doctor Prescription")
        self.assertIsNone(normalise_category("unlisted-business"))

    def test_bill_and_sale_capture_the_active_category_snapshot(self):
        bill = Bill(
            owner_id=1,
            shop_category="Hardware",
            total_amount=100,
            total_items=1,
            items_json="[]",
        )
        sale = SaleItem(
            owner_id=1,
            bill_id=1,
            shop_category="Hardware",
            item_name="Hammer",
            item_category="Tools",
            quantity=1,
            unit="piece",
            price_per_unit=100,
            total_price=100,
            hour_of_day=12,
        )
        self.assertEqual(bill.shop_category, "Hardware")
        self.assertEqual(sale.shop_category, "Hardware")

    def test_registered_routes_cover_every_frontend_api(self):
        from main import app

        paths = {route.path for route in app.routes if hasattr(route, "path")}
        self.assertTrue(
            {
                "/auth/send-otp",
                "/auth/verify-otp",
                "/auth/update-profile",
                "/items/",
                "/items/{item_id}/",
                "/analytics/bills",
                "/analytics/dashboard",
                "/inventory/voice-parse",
                "/voice/process",
                "/voice/ws/stream",
            }.issubset(paths)
        )


if __name__ == "__main__":
    unittest.main()
