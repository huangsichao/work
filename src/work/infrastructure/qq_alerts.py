from __future__ import annotations

from dataclasses import dataclass
import os
import time
from typing import Any, Callable

import httpx

from work.domain.models import Alert


class QQAlertError(RuntimeError):
    """QQ 官方机器人预警发送失败。"""


@dataclass(frozen=True)
class QQBotConfig:
    app_id: str
    client_secret: str
    target_id: str
    target_type: str = "group"
    api_base_url: str = "https://api.sgroup.qq.com"
    token_url: str = "https://bots.qq.com/app/getAppAccessToken"
    timeout_seconds: float = 10.0
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> QQBotConfig:
        values = {
            "app_id": os.getenv("QQ_BOT_APP_ID", ""),
            "client_secret": os.getenv("QQ_BOT_CLIENT_SECRET", ""),
            "target_id": os.getenv("QQ_ALERT_TARGET_ID", ""),
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise QQAlertError(
                "缺少 QQ 机器人配置: " + ", ".join(sorted(missing))
            )
        target_type = os.getenv("QQ_ALERT_TARGET_TYPE", "group").lower()
        if target_type not in {"group", "user", "channel"}:
            raise QQAlertError("QQ_ALERT_TARGET_TYPE 必须是 group、user 或 channel")
        return cls(
            **values,
            target_type=target_type,
            api_base_url=os.getenv("QQ_BOT_API_BASE_URL", cls.api_base_url),
            token_url=os.getenv("QQ_BOT_TOKEN_URL", cls.token_url),
            timeout_seconds=float(os.getenv("QQ_BOT_TIMEOUT_SECONDS", "10")),
            max_retries=int(os.getenv("QQ_BOT_MAX_RETRIES", "3")),
        )

    @property
    def message_path(self) -> str:
        if self.target_type == "group":
            return f"/v2/groups/{self.target_id}/messages"
        if self.target_type == "user":
            return f"/v2/users/{self.target_id}/messages"
        return f"/channels/{self.target_id}/messages"


class QQBotNotifier:
    def __init__(
        self,
        config: QQBotConfig,
        *,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.config = config
        self._sleep = sleep
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=config.timeout_seconds)
        self._access_token: str | None = None
        self._token_expires_at = 0.0

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> QQBotNotifier:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def notify(self, alert: Alert) -> None:
        token = self._get_access_token()
        self._request(
            "POST",
            self.config.api_base_url.rstrip("/") + self.config.message_path,
            headers={
                "Authorization": f"QQBot {token}",
                "X-Union-Appid": self.config.app_id,
                "Content-Type": "application/json",
            },
            json_body={"content": format_alert(alert), "msg_type": 0},
        )

    def _get_access_token(self) -> str:
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        payload = self._request(
            "POST",
            self.config.token_url,
            headers={"Content-Type": "application/json"},
            json_body={
                "appId": self.config.app_id,
                "clientSecret": self.config.client_secret,
            },
        )
        token = payload.get("access_token")
        expires_in = payload.get("expires_in", 7200)
        if not token:
            raise QQAlertError("QQ 令牌响应缺少 access_token")
        try:
            ttl = max(60.0, float(expires_in) - 60.0)
        except (TypeError, ValueError):
            ttl = 7140.0
        self._access_token = str(token)
        self._token_expires_at = time.time() + ttl
        return self._access_token

    def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json_body: dict[str, Any],
    ) -> dict[str, Any]:
        for attempt in range(self.config.max_retries + 1):
            try:
                response = self._client.request(
                    method,
                    url,
                    headers=headers,
                    json=json_body,
                )
            except httpx.RequestError as exc:
                if attempt >= self.config.max_retries:
                    raise QQAlertError(f"QQ 请求失败: {exc}") from exc
                self._sleep(2**attempt)
                continue
            if response.status_code == 429 or response.status_code >= 500:
                if attempt >= self.config.max_retries:
                    raise QQAlertError(
                        f"QQ 请求失败: HTTP {response.status_code}"
                    )
                retry_after = response.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after else float(2**attempt)
                except ValueError:
                    delay = float(2**attempt)
                self._sleep(delay)
                continue
            if response.status_code >= 400:
                raise QQAlertError(
                    f"QQ 请求失败: HTTP {response.status_code} {response.text[:300]}"
                )
            if response.status_code == 204 or not response.content:
                return {}
            try:
                payload = response.json()
            except ValueError as exc:
                raise QQAlertError("QQ 返回了非 JSON 响应") from exc
            if not isinstance(payload, dict):
                raise QQAlertError("QQ 响应必须是 JSON 对象")
            return payload
        raise QQAlertError("QQ 请求失败")


def format_alert(alert: Alert) -> str:
    listing = f" 商品 {alert.listing_id}" if alert.listing_id else ""
    return f"[{alert.level}] {alert.code}{listing}\n{alert.message}"


def build_qq_notifier_from_env() -> QQBotNotifier:
    return QQBotNotifier(QQBotConfig.from_env())