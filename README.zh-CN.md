# Subscription Leak Radar

[English](README.md) | 中文

Subscription Leak Radar 是一个本地优先的订阅漏费审计工具，帮助用户从银行或信用卡流水里找出忘记取消的订阅、重复服务、涨价项目和即将续费的扣款。

- 从银行/信用卡 CSV 或粘贴的交易文本中识别 recurring charges，不要求用户手动列出所有订阅。
- 估算年化支出、续费时间、涨价幅度、重复类别和取消优先级。
- 生成本地 Markdown / JSON 报告，方便用户在取消或降级服务前先做私密审计。

上线前补充截图或 GIF。

快速体验：

```bash
python server.py
```

打开 `http://127.0.0.1:8786`，点击 **Load sample**，再点击 **Run analysis**。

## Problem

订阅扣费很容易被忽略，因为金额通常不大、自动发生，而且分散在银行卡、信用卡、App Store、PayPal、免费试用和不同服务商里。用户往往记得几个明显的订阅，但会漏掉重复的流媒体服务、应用商店续费、年度扣款、只用过一次的 AI 工具，或者悄悄涨价的套餐。

真正麻烦的不是简单加总金额，而是打开流水、找重复商户、识别奇怪的扣款名、估算年度影响、判断哪些马上续费，然后决定先取消哪一个。

## Why Existing Approaches Are Not Enough

表格可以记账，但前提是用户已经把每个订阅都找出来并手动填进去。预算软件功能很强，但很多需要绑定账户、云同步或付费后才能得到清晰的订阅审计。手动订阅 tracker 通常要求用户逐项输入商户、日期和价格，而这正是产品应该帮用户减少的工作。

Subscription Leak Radar 只聚焦一个更轻、更私密的本地工作流：导入流水，推断 recurring charges，排出最值得检查的项目，并导出决策报告。

## What This Project Does

`流水 CSV 或粘贴交易文本 -> 订阅识别 -> 续费和成本分析 -> 取消优先级队列 -> Markdown/JSON 报告`

应用会解析交易、规范化商户名、聚合同一商户的重复扣款、推断扣款周期、估算年化成本、标记涨价和重复类别，然后告诉用户哪些项目最应该先检查。

## Key Features

- 灵活 CSV 字段映射，支持常见银行/信用卡导出字段，例如 `date`、`posted_date`、`description`、`merchant`、`amount`、`debit`、`charge`。
- 粘贴交易文本解析，适合从 PDF、邮件或网银页面复制出来的流水。
- 手动补录订阅，覆盖导入窗口之外的年度订阅或特殊服务。
- 周、月、季度、年度和不规则扣款的周期推断。
- 检测最近扣款是否明显高于最早观察到的扣款。
- 标记同类别重复服务，例如多个 AI 工具、流媒体、云存储或应用商店订阅。
- 续费时间线、类别支出面板、取消优先级队列和节省情景分析。
- 本地 Markdown / JSON 导出。

## 为什么有用

它把杂乱的银行卡或信用卡流水变成一张订阅漏费地图：重复扣款商户、预计扣款周期、涨价项目、重复类别、续费时间，以及最应该先检查的取消优先级队列。

## Demo / Screenshots

上线前补充截图或 GIF。

内置 demo 数据包含 40 多条真实感流水，覆盖流媒体、AI 工具、云存储、应用商店扣款、健身房会员、年度会员和一次性非订阅消费。

## Quick Start

```bash
cd products/product-020/repo
python server.py
```

然后打开：

```text
http://127.0.0.1:8786
```

不需要联网，不需要绑定银行账户，不需要 API key，也不会把数据发送到外部服务。

## Example Input / Output

示例 CSV：

```csv
Date,Description,Amount,Currency,Account
2026-03-05,NETFLIX.COM 866-579-7172,-17.99,USD,Checking
2026-04-04,NETFLIX.COM 866-579-7172,-17.99,USD,Checking
2026-03-15,OPENAI CHATGPT SUBSCRIPTION,-20.00,USD,Credit Card
2026-04-15,OPENAI CHATGPT SUBSCRIPTION,-20.00,USD,Credit Card
```

输出文件：

```text
outputs/subscription-leak-report.md
outputs/subscription-leak-report.json
```

示例输出摘要：

```text
Detected subscriptions: 11
Estimated annualized cost: $2,800+
Priority queue: Adobe, gym membership, AI-tool duplicates, Netflix price increase
Savings scenarios: cancel top 1, cancel top 3, cancel duplicate/price-increase items, cut 20%
```

## Use Cases

- 每季度用信用卡导出流水做一次订阅审计。
- 找出曾经有用、现在已经不值得继续付费的 AI 或软件工具。
- 在做预算前发现同类别重复服务。
- 在年度或月度续费前检查即将扣款项目。
- 不分享银行登录信息，也能生成本地取消清单。

## How It Works

分析器使用确定性的本地逻辑。它先把不同 CSV 字段映射到统一交易模型，再用保守的日期/金额模式解析粘贴文本，然后规范化商户名、按商户分组、计算扣款间隔、推断周期并估算年化成本。取消优先级会综合成本、续费时间、涨价、重复类别、置信度和需要人工复核的标记。

输出强调决策，而不只是罗列订阅：它会说明哪些项目值得先看、为什么值得先看。

## Project Structure

```text
subscription_leak_radar/analyzer.py  核心解析、订阅识别、评分和导出
server.py                           本地 HTTP 服务
web/                                浏览器界面
samples/                            真实感流水样例
examples/                           粘贴交易文本样例
tests/                              单元测试
scripts/smoke_test.py               用户视角 smoke test
```

## Roadmap

- PayPal、Apple、Google Play、银行和信用卡导出的 source-specific preset。
- PDF 流水文本提取辅助功能。
- 可编辑商户目录和取消链接表。
- 即将续费项目的日历导出。
- 可选的加密本地历史，用于月度对比审计。

## Limitations

Subscription Leak Radar 不连接银行账户，不自动取消服务，不发送邮件，也不提供财务建议。订阅识别依赖用户导入的流水数据；如果日期范围太短、商户改名、年度订阅只出现一次，或 App Store 合并扣款，可能需要人工复核。当前不实现 PDF/图片 OCR；用户可以粘贴已经提取出的流水文本。

## License

MIT

## Language

English version: [README.md](README.md)
