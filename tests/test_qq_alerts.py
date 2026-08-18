import json
import os
import unittest
from unittest.mock import patch

import httpx

from work.domain.models import Alert, AlertLevel
from work.infrastructure.qq_alerts import (
    QQAlertError,
    QQBotConfig,
    QQBotNotifier,
    format_alert,
)


class QQBotNotifierTests(unittest.TestCase):
    def test_token_is_cached_and_group_message_is_sent(self):
        calls = []

        def handler(request):
            calls.append(request)
            if request.url.path == "/token":
                return httpx.Response(200, json={"access_token": "token-1", "expires_in": 7200})
            self.assertEqual(request.url.path, "/v2/groups/group-1/messages")
            self.assertEqual(request.headers["Authorization"], "QQBot token-1")
            payload = json.loads(request.content)
            self.assertEqual(payload["msg_type"], 0)
            self.assertIn("LOW_STOCK", payload["content"])
            return httpx.Response(200, json={})

        client = httpx.Client(transport=httpx.MockTransport(handler))
        notifier = QQBotNotifier(
            QQBotConfig(
                "app-1",
                "secret-1",
                "group-1",
                token_url="https://bot.example/token",
            ),
            client=client,
        )
        alert = Alert(AlertLevel.P1, "LOW_STOCK", "库存不足", "listing-1")
        notifier.notify(alert)
        notifier.notify(alert)
        self.assertEqual(sum(request.url.path == "/token" for request in calls), 1)
        self.assertEqual(sum(request.url.path.endswith("/messages") for request in calls), 2)

    def test_target_path_for_user_and_channel(self):
        user = QQBotConfig(
            "app",
            "secret",
            "user-1",
            target_type="user",
        )
        channel = QQBotConfig(
            "app",
            "secret",
            "channel-1",
            target_type="channel",
        )
        self.assertEqual(user.message_path, "/v2/users/user-1/messages")
        self.assertEqual(channel.message_path, "/channels/channel-1/messages")

    def test_invalid_target_type_is_rejected(self):
        env = {
            "QQ_BOT_APP_ID": "app",
            "QQ_BOT_CLIENT_SECRET": "secret",
            "QQ_ALERT_TARGET_ID": "target",
            "QQ_ALERT_TARGET_TYPE": "invalid",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(QQAlertError):
                QQBotConfig.from_env()


class QQAlertFormattingTests(unittest.TestCase):
    def test_format_includes_level_code_listing_and_message(self):
        text = format_alert(
            Alert(AlertLevel.P0, "SOURCE_UNAVAILABLE", "货源下架", "pdd-1")
        )
        self.assertIn("P0", text)
        self.assertIn("SOURCE_UNAVAILABLE", text)
        self.assertIn("pdd-1", text)
        self.assertIn("货源下架", text)


if __name__ == "__main__":
    unittest.main()