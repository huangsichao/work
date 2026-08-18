# QQ 官方机器人预警

## 接入方式

本项目使用 QQ 官方机器人开放接口，不使用个人 QQ 模拟登录、网页登录自动化或非官方协议。

需要准备：

- QQ 机器人 AppID。
- QQ 机器人 Client Secret。
- 目标群、用户或频道的 OpenID/ID。
- 机器人已获得向目标发送消息的权限。

## 配置

在本地 .env 中设置：

    QQ_ALERT_ENABLED=true
    QQ_BOT_APP_ID=你的AppID
    QQ_BOT_CLIENT_SECRET=你的ClientSecret
    QQ_ALERT_TARGET_TYPE=group
    QQ_ALERT_TARGET_ID=目标群OpenID

支持的目标类型：group、user、channel。默认使用官方生产 API 地址；沙箱或授权网关可覆盖 QQ_BOT_API_BASE_URL 和 QQ_BOT_TOKEN_URL。

令牌由程序自动获取并在有效期内缓存。Client Secret 不得提交到 GitHub 或发送到聊天。

## 消息示例

    [P1] LOW_STOCK 商品 pdd-1001
    货源库存仅剩 3

QQ 机器人发送权限、主动消息频率和目标 ID 由 QQ 开放平台控制；上线前应先用测试群验证。