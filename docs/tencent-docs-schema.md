# 腾讯文档读写接入

## 前置条件

腾讯文档个人网页登录状态不能直接作为程序凭据。请通过腾讯文档开放平台、企业授权应用或经过授权的 ERP/API 网关取得以下信息：

- API 基础地址
- 文档 ID 和工作表 ID
- 可读取和更新该工作表的访问令牌
- 行读取路径和按键更新路径

程序不会保存腾讯账号密码、验证码或买家隐私数据。

## 环境变量

复制 .env.example 并配置 TENCENT_DOCS_BASE_URL、TENCENT_DOCS_DOCUMENT_ID、TENCENT_DOCS_SHEET_ID 和 TENCENT_DOCS_ACCESS_TOKEN。

不同开放平台或 ERP 网关的路径可以通过 TENCENT_DOCS_READ_PATH 与 TENCENT_DOCS_WRITE_PATH 覆盖。路径支持 document_id 和 sheet_id 占位符。

## HTTP 契约

读取接口返回：

    {"data": {"rows": [{"values": {"listing_id": "..."}}], "next_page_token": "..."}}

写入接口接收：

    {"document_id": "...", "sheet_id": "...", "key_fields": ["listing_id", "listing_sku"], "rows": [{"values": {...}}]}

程序自动处理分页、429/5xx 重试、HTTP 错误和业务错误码。写入使用 listing_id 与 listing_sku 作为幂等键。

## 商品映射字段

| 字段 | 说明 |
| --- | --- |
| listing_id | 拼多多商品 ID |
| listing_sku | 拼多多 SKU ID |
| source_product_id | 1688 商品 ID |
| source_sku | 1688 规格 ID/编码 |
| source_url | 合法授权的货源链接 |
| purchase_price | 最新采购价 |
| sale_price | 当前销售价 |
| supplier_id | 供应商 ID |
| status | candidate/pending_review/active/paused/replaced |
| source_stock | 最新货源库存 |
| last_synced_at | 最近同步时间，ISO 8601 格式 |

不要在腾讯文档填写 API 密钥、买家完整地址、手机号、支付密码或验证码。