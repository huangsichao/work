# 拼多多宠物玩具代发运营框架

这是一个面向“拼多多个人店 + 1688 代发”的模块化项目骨架。第一版坚持“自动监控与建议、人工确认发布和采购”，避免把平台账号密码或支付能力放进程序。

## 当前模块

- domain：商品、SKU、供应商和预警等领域模型。
- application：选品评分、利润计算、库存/价格监控和预警规则。
- infrastructure：腾讯文档、1688、拼多多和通知渠道的适配边界。
- api：供运营后台或定时任务调用的 HTTP 接口。
- tests：不依赖外部平台的规则测试。

## 安全边界

1. 真实平台接入必须使用官方开放接口或已授权 ERP，不能使用模拟登录和高频网页抓取。
2. 密钥只放在环境变量或密钥管理服务，绝不提交到 GitHub。
3. 首次发布、大幅调价、品牌/资质审核和向 1688 付款保留人工确认。

## 本地运行

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -e ".[dev]"
    Copy-Item .env.example .env
    uvicorn work.api:app --reload

默认接口：

- GET /health：健康检查。
- POST /v1/products/evaluate：计算候选商品评分与利润。
- POST /v1/monitor/sync：执行一次商品监控（使用演示适配器）。

详细架构和腾讯文档字段见 docs 目录。

## 腾讯文档读写

已加入可配置的腾讯文档读写适配器：work.infrastructure.tencent_docs。配置授权的 API/ERP 网关后，运行 build_tencent_docs_store_from_env() 即可获得商品映射存储；该实现支持分页读取、429/5xx 重试、字段校验和按商品+SKU 幂等写回。具体环境变量和 HTTP 契约见 docs/tencent-docs-schema.md。
