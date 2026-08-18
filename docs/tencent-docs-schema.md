# 腾讯文档表结构

第一版使用独立工作表，字段名保持稳定，避免程序依赖人工填写的列序号。

## 商品映射

| 字段 | 说明 |
| --- | --- |
| listing_id | 拼多多商品 ID |
| listing_sku | 拼多多 SKU ID |
| merchant_code | 内部商家编码，如 1688ID-颜色-规格 |
| source_product_id | 1688 商品 ID |
| source_sku | 1688 规格 ID/编码 |
| source_url | 合法授权的货源链接 |
| purchase_price | 最新采购价 |
| supplier_shipping_cost | 供应商运费 |
| sale_price | 当前销售价 |
| supplier_id | 供应商 ID |
| status | candidate/pending_review/active/paused/replaced |
| source_stock | 最新货源库存 |
| last_synced_at | 最近同步时间 |

## 其他工作表

- 供应商：授权状态、发货时效、退换货约定和风险评级。
- 候选池：需求、竞争、供货、利润、合规评分及审核结论。
- 运营数据：曝光、点击、成交、退款、推广费和实际利润。
- 预警记录：等级、代码、商品、通知状态、负责人和处理结果。

不要填写 API 密钥、买家完整地址、手机号、支付密码或验证码。
