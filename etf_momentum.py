# -*- coding: utf-8 -*-
"""
ETF 动量轮动策略 —— GitHub Actions 云端版
==========================================
每天由 GitHub Actions 自动运行，计算四只 ETF 的动量信号，
把结果追加到 data/信号历史.json，供 GitHub Pages 网页展示。

数据源：腾讯行情（web.ifzq.gtimg.cn），前复权日线 + 实时价。
"""

import json
import math
import os
import sys
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd

# 统一 UTF-8 输出（GitHub 服务器是 Linux）
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
DATA_FILE = os.path.join(DATA_DIR, "信号历史.json")

M_DAYS = 25
TZ_CN = timezone(timedelta(hours=8))  # 北京时间

ETF_POOL = {
    "518880.SH": ("518880", "黄金ETF", "大宗商品"),
    "513100.SH": ("513100", "纳指100", "海外资产"),
    "159915.SZ": ("159915", "创业板100", "成长/科技"),
    "510180.SH": ("510180", "上证180", "价值/蓝筹"),
}


def calc_rank_score(close_series):
    y = np.log(close_series.values.astype(float))
    x = np.arange(len(y))
    if len(y) < 2:
        return float("nan")
    slope, intercept = np.polyfit(x, y, 1)
    annual = math.pow(math.exp(slope), 250) - 1
    y_fit = slope * x + intercept
    ss_res = np.sum((y - y_fit) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot != 0 else 0.0
    return annual * r2


def _tencent_code(ak_code):
    return ("sh" + ak_code) if ak_code.startswith(("5", "6")) else ("sz" + ak_code)


def fetch_close(ak_code):
    """腾讯前复权日线，返回收盘价 Series。"""
    import requests
    code = _tencent_code(ak_code)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    url = (f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
           f"?param={code},day,,,360,qfq")
    for _ in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=15)
            d = json.loads(r.text)
            node = d["data"][code]
            klines = node.get("qfqday") or node.get("day")
            if klines:
                dates = [k[0] for k in klines]
                closes = [float(k[2]) for k in klines]
                return pd.Series(closes, index=pd.to_datetime(dates))
        except Exception:
            continue
    return pd.Series(dtype=float)


def fetch_price(ak_code):
    """腾讯实时价。"""
    import requests
    code = _tencent_code(ak_code)
    try:
        r = requests.get(f"http://qt.gtimg.cn/q={code}", timeout=10)
        r.encoding = "gbk"
        parts = r.text.split("~")
        if len(parts) > 3:
            return round(float(parts[3]), 3)
    except Exception:
        pass
    return None


def get_ranks():
    rows = []
    for jq, (ak_code, name, attr) in ETF_POOL.items():
        try:
            close = fetch_close(ak_code).tail(M_DAYS)
            score = calc_rank_score(close)
            y = np.log(close.values.astype(float))
            slope = np.polyfit(np.arange(len(y)), y, 1)[0]
            annual = math.pow(math.exp(slope), 250) - 1
            r2 = np.corrcoef(np.arange(len(y)), y)[0, 1] ** 2
            price = fetch_price(ak_code)
            rows.append({
                "代码": jq, "名称": name, "资产属性": attr,
                "价格": price,
                "年化收益": round(annual, 4),
                "R2": round(r2, 4),
                "动量得分": round(score, 4),
            })
        except Exception as e:
            print(f"[错误] {name} 失败: {type(e).__name__}: {e}")
            rows.append({"代码": jq, "名称": name, "资产属性": attr,
                         "价格": None, "年化收益": None, "R2": None,
                         "动量得分": None})
    df = pd.DataFrame(rows).sort_values("动量得分", ascending=False)
    return df


def main():
    now = datetime.now(TZ_CN)
    date_str = now.strftime("%Y-%m-%d")
    ts = now.strftime("%Y-%m-%d %H:%M")

    df = get_ranks()

    # 判断操作（对比上次持仓）
    history = []
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)

    prev_hold = None
    if history:
        prev_hold = history[-1].get("持仓")

    top_code = None
    top_name = None
    top_price = None
    top_score = None
    if not df.empty and df["动量得分"].notna().any():
        top = df.iloc[0]
        top_code = top["代码"]
        top_name = top["名称"]
        top_price = top["价格"]
        top_score = top["动量得分"]

    if top_code is None:
        action = "无信号"
    elif prev_hold is None:
        action = "买入"
    elif prev_hold != top_code:
        action = "换仓"
    else:
        action = "持有"

    record = {
        "日期": date_str,
        "时间": ts,
        "操作": action,
        "持仓": top_code,
        "持仓名称": top_name,
        "价格": top_price,
        "动量得分": top_score,
        "排名": df.to_dict("records"),
    }

    # 同一天重复运行则覆盖最后一条
    if history and history[-1].get("日期") == date_str:
        history[-1] = record
    else:
        history.append(record)

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    print(f"[{ts}] 信号已记录：{action} {top_name or '-'} @ {top_price}")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
