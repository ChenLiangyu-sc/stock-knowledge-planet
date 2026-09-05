# 星球抓取方法备忘（2026-09-05 实战）

## 通道对比

| 通道 | 优点 | 现状 |
|------|------|------|
| ZsxqCrawler（`~/workspace/web-search-hub/ZsxqCrawler`） | 稳定分页、入库、去重 | cookie 已过期（401），需在 Web UI 重新贴 cookie |
| opencli 浏览器会话 | 复用 Chrome 登录态，无需 cookie | 可用，但页面内 fetch 频繁触发 1059 风控 |

## opencli 通道要点

```bash
# 验证登录态
opencli zsxq whoami
# 单页接口（在已登录页面上下文里 fetch，cookie 自动携带）
# https://api.zsxq.com/v2/groups/15522441485522/topics?scope=all|digests&count=30[&end_time=ISO8601]
# end_time = 上一页最老话题的 create_time，逐页向前翻
```

- `count=30` 是实际可用上限（`count=100` 返回 14001）
- 触发 1059 = 风控限频：退避 90-120s 即可恢复；连续请求 3-5 次就会触发，请保持 ≥6s 间隔并降低预期
- `scope=digests`（精华）是低请求量、高信号的历史补抓通道
- 驱动脚本思路：`while oldest > 目标日期: eval(fetch一页) -> 去重入库 -> sleep(6~9s)`，每 10 页落盘一次

## 数据文件

- `data/raw/all_topics.json`：近端全量话题（2026-08-28 → 09-05，1143 条）
- `data/raw/digests.json`：全期精华帖（2026-06-22 → 09-05，523 条）
- `data/raw/combined.json`：个股信号合并（精华×2 + 全量×1 + 券商×2 + 推荐类）
- `scripts/extract.py`：股票名/券商标签提取（A 股名单需先由 akshare 导出）
