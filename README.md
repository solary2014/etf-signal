# ETF 动量轮动信号

每天自动计算黄金、纳指、创业板、上证180 四只 ETF 的动量得分（年化收益 × R²），
选出动量最强的一只，结果通过 GitHub Pages 网页展示。

## 网页地址

部署后访问：`https://<你的用户名>.github.io/<仓库名>/`

## 工作原理

```
每天 13:59（北京时间，周一到周五）
  └─ GitHub Actions 自动运行 etf_momentum.py
       ├─ 腾讯行情源拉取四只 ETF 前复权日线 + 实时价
       ├─ 计算动量得分 = 年化收益 × R²
       ├─ 对比上次持仓，判断「买入/持有/换仓」
       └─ 结果写入 data/信号历史.json 并提交回仓库
            └─ GitHub Pages 网页读取 JSON 展示
```

## 部署步骤

1. 在 GitHub 新建一个 **public** 仓库，把本目录所有文件推送上去；
2. 仓库 **Settings → Pages → Source 选 `main` 分支根目录** → Save；
3. 等约 1 分钟，访问生成的网址即可看到页面；
4. **手动触发一次测试**：仓库 **Actions → 每日ETF信号 → Run workflow**；
5. 之后每天 13:59 自动运行（GitHub Actions 的定时任务允许有几分钟延迟）。

## 注意事项

- 仓库必须 **public**（免费版 Pages 不支持 private 仓库）；
- 数据源用腾讯行情（`web.ifzq.gtimg.cn`），云端通常可直连；
- 首次运行后，`data/信号历史.json` 会积累历史数据，网页自动更新；
- 工作日（周一到周五）运行，周末和节假日跳过（A股休市）。

## 文件说明

| 文件 | 作用 |
|---|---|
| `etf_momentum.py` | 信号计算脚本（云端版） |
| `.github/workflows/daily-signal.yml` | 定时任务配置 |
| `index.html` | 展示网页 |
| `data/信号历史.json` | 历史数据（自动累积） |
| `requirements.txt` | Python 依赖 |
