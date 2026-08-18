from work.domain.models import Alert, AlertLevel
from work.infrastructure.qq_alerts import build_qq_notifier_from_env


def main() -> None:
    notifier = build_qq_notifier_from_env()
    try:
        notifier.notify(
            Alert(
                AlertLevel.P3,
                "QQ_CONNECTION_TEST",
                "QQ 预警通道连接成功",
                "test-listing",
            )
        )
        print("QQ test alert sent")
    finally:
        notifier.close()


if __name__ == "__main__":
    main()