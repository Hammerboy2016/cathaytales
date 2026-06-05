#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cathay Tales GA4 Data API 查询工具
作者: 旺财
创建: 2026-06-05

用法:
  python3 ga4_query.py                       # 默认拉过去 7 天概览简报
  python3 ga4_query.py --days 30             # 拉过去 30 天
  python3 ga4_query.py --start 2026-06-01 --end 2026-06-05
  python3 ga4_query.py --report toppages     # 单独看 Top pages
  python3 ga4_query.py --report sources      # 单独看流量来源
  python3 ga4_query.py --report countries    # 单独看国家分布
  python3 ga4_query.py --report devices      # 单独看设备分布
  python3 ga4_query.py --report daily        # 每日趋势
  python3 ga4_query.py --report all          # 全部报表

依赖:
  pip install google-analytics-data
  凭据: ~/.config/coze_ga4/cathay-tales-analytics.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    OrderBy,
    RunReportRequest,
)
from google.oauth2 import service_account

# ============ 配置 ============
PROPERTY_ID = "540045995"
CREDENTIALS_PATH = os.environ.get("GA4_SA_PATH", os.path.expanduser("~/.config/coze_ga4/cathay-tales-analytics.json"))


def get_client():
    """加载凭据初始化 GA4 客户端"""
    if not os.path.exists(CREDENTIALS_PATH):
        print(f"❌ 凭据文件不存在: {CREDENTIALS_PATH}", file=sys.stderr)
        sys.exit(1)
    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_PATH,
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )
    return BetaAnalyticsDataClient(credentials=credentials)


def fmt_num(n):
    """数字格式化（千分位）"""
    try:
        return f"{int(n):,}"
    except (ValueError, TypeError):
        return str(n)


def query(client, dimensions, metrics, start, end, limit=20, order_by_metric=None):
    """通用查询封装"""
    dims = [Dimension(name=d) for d in dimensions]
    mets = [Metric(name=m) for m in metrics]
    order_bys = []
    if order_by_metric:
        order_bys = [
            OrderBy(metric=OrderBy.MetricOrderBy(metric_name=order_by_metric), desc=True)
        ]
    req = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        dimensions=dims,
        metrics=mets,
        date_ranges=[DateRange(start_date=start, end_date=end)],
        order_bys=order_bys,
        limit=limit,
    )
    return client.run_report(req)


def report_overview(client, start, end):
    """整体概览：活跃用户、会话、PV、新用户、平均参与时长、跳出率"""
    res = query(
        client,
        dimensions=[],
        metrics=[
            "activeUsers",
            "newUsers",
            "sessions",
            "screenPageViews",
            "userEngagementDuration",
            "bounceRate",
            "engagementRate",
        ],
        start=start,
        end=end,
    )
    print(f"\n📊 概览 ({start} ~ {end})")
    print("-" * 60)
    if not res.rows:
        print("  无数据")
        return
    row = res.rows[0]
    headers = [m.name for m in res.metric_headers]
    vals = [v.value for v in row.metric_values]
    metric_map = dict(zip(headers, vals))
    
    active = int(metric_map.get("activeUsers", 0))
    new = int(metric_map.get("newUsers", 0))
    sessions = int(metric_map.get("sessions", 0))
    pv = int(metric_map.get("screenPageViews", 0))
    engage_sec = float(metric_map.get("userEngagementDuration", 0))
    bounce = float(metric_map.get("bounceRate", 0)) * 100
    engage = float(metric_map.get("engagementRate", 0)) * 100
    
    avg_session_pv = pv / sessions if sessions else 0
    avg_engage_per_user = engage_sec / active if active else 0
    
    print(f"  活跃用户 (Active Users)     : {fmt_num(active)}")
    print(f"  新用户 (New Users)          : {fmt_num(new)}")
    print(f"  会话数 (Sessions)           : {fmt_num(sessions)}")
    print(f"  页面浏览 (Page Views)       : {fmt_num(pv)}")
    print(f"  每会话 PV (Pages/Session)   : {avg_session_pv:.2f}")
    print(f"  人均参与时长                 : {avg_engage_per_user:.1f} 秒 ({avg_engage_per_user/60:.1f} 分)")
    print(f"  参与率 (Engagement Rate)    : {engage:.1f}%")
    print(f"  跳出率 (Bounce Rate)        : {bounce:.1f}%")


def report_daily(client, start, end):
    """每日趋势"""
    res = query(
        client,
        dimensions=["date"],
        metrics=["activeUsers", "newUsers", "sessions", "screenPageViews"],
        start=start,
        end=end,
        limit=100,
    )
    print(f"\n📈 每日趋势 ({start} ~ {end})")
    print("-" * 60)
    print(f"  {'日期':<12} {'活跃':>8} {'新用户':>8} {'会话':>8} {'PV':>8}")
    if not res.rows:
        print("  无数据")
        return
    rows = sorted(res.rows, key=lambda r: r.dimension_values[0].value)
    for r in rows:
        d = r.dimension_values[0].value  # YYYYMMDD
        d_fmt = f"{d[:4]}-{d[4:6]}-{d[6:]}"
        vals = [v.value for v in r.metric_values]
        print(f"  {d_fmt:<12} {fmt_num(vals[0]):>8} {fmt_num(vals[1]):>8} {fmt_num(vals[2]):>8} {fmt_num(vals[3]):>8}")


def report_toppages(client, start, end, limit=10):
    """Top 页面"""
    res = query(
        client,
        dimensions=["pagePath", "pageTitle"],
        metrics=["screenPageViews", "activeUsers", "userEngagementDuration"],
        start=start,
        end=end,
        limit=limit,
        order_by_metric="screenPageViews",
    )
    print(f"\n📄 Top {limit} 页面 ({start} ~ {end})")
    print("-" * 60)
    if not res.rows:
        print("  无数据")
        return
    for i, r in enumerate(res.rows, 1):
        path = r.dimension_values[0].value
        title = r.dimension_values[1].value[:40]
        pv = r.metric_values[0].value
        users = r.metric_values[1].value
        engage = float(r.metric_values[2].value)
        avg = engage / int(users) if int(users) else 0
        print(f"  {i:>2}. {path}")
        print(f"      {title}")
        print(f"      PV={fmt_num(pv)}  独立访客={fmt_num(users)}  人均停留={avg:.0f}s")


def report_sources(client, start, end, limit=10):
    """流量来源"""
    res = query(
        client,
        dimensions=["sessionSource", "sessionMedium"],
        metrics=["sessions", "activeUsers", "engagedSessions"],
        start=start,
        end=end,
        limit=limit,
        order_by_metric="sessions",
    )
    print(f"\n🚀 Top {limit} 流量来源 ({start} ~ {end})")
    print("-" * 60)
    if not res.rows:
        print("  无数据")
        return
    print(f"  {'来源 / 媒介':<35} {'会话':>8} {'用户':>8} {'参与会话':>10}")
    for r in res.rows:
        src = r.dimension_values[0].value
        med = r.dimension_values[1].value
        combo = f"{src} / {med}"[:34]
        s = r.metric_values[0].value
        u = r.metric_values[1].value
        es = r.metric_values[2].value
        print(f"  {combo:<35} {fmt_num(s):>8} {fmt_num(u):>8} {fmt_num(es):>10}")


def report_countries(client, start, end, limit=10):
    """国家分布"""
    res = query(
        client,
        dimensions=["country"],
        metrics=["activeUsers", "sessions"],
        start=start,
        end=end,
        limit=limit,
        order_by_metric="activeUsers",
    )
    print(f"\n🌏 Top {limit} 国家 ({start} ~ {end})")
    print("-" * 60)
    if not res.rows:
        print("  无数据")
        return
    for i, r in enumerate(res.rows, 1):
        country = r.dimension_values[0].value
        u = r.metric_values[0].value
        s = r.metric_values[1].value
        print(f"  {i:>2}. {country:<25} 用户={fmt_num(u):>6}  会话={fmt_num(s):>6}")


def report_devices(client, start, end):
    """设备分布"""
    res = query(
        client,
        dimensions=["deviceCategory"],
        metrics=["activeUsers", "sessions"],
        start=start,
        end=end,
        limit=10,
        order_by_metric="activeUsers",
    )
    print(f"\n📱 设备分布 ({start} ~ {end})")
    print("-" * 60)
    if not res.rows:
        print("  无数据")
        return
    total_u = sum(int(r.metric_values[0].value) for r in res.rows)
    for r in res.rows:
        d = r.dimension_values[0].value
        u = int(r.metric_values[0].value)
        s = r.metric_values[1].value
        pct = u / total_u * 100 if total_u else 0
        print(f"  {d:<12} 用户={fmt_num(u):>6} ({pct:.1f}%)  会话={fmt_num(s):>6}")


def main():
    ap = argparse.ArgumentParser(description="Cathay Tales GA4 查询工具")
    ap.add_argument("--days", type=int, default=7, help="过去 N 天，默认 7")
    ap.add_argument("--start", type=str, help="开始日期 YYYY-MM-DD（与 --days 互斥）")
    ap.add_argument("--end", type=str, help="结束日期 YYYY-MM-DD，默认今天")
    ap.add_argument(
        "--report",
        type=str,
        default="brief",
        choices=["brief", "overview", "daily", "toppages", "sources", "countries", "devices", "all"],
        help="报表类型，默认 brief（概览+top10+来源）",
    )
    args = ap.parse_args()

    today = datetime.now().date()
    if args.start:
        start = args.start
        end = args.end or today.strftime("%Y-%m-%d")
    else:
        end = args.end or today.strftime("%Y-%m-%d")
        start = (today - timedelta(days=args.days - 1)).strftime("%Y-%m-%d")

    print(f"=" * 60)
    print(f"  Cathay Tales GA4 数据简报")
    print(f"  Property ID: {PROPERTY_ID}")
    print(f"  日期范围: {start} ~ {end}")
    print(f"=" * 60)

    client = get_client()

    if args.report in ("brief", "overview", "all"):
        report_overview(client, start, end)
    if args.report in ("brief", "daily", "all"):
        report_daily(client, start, end)
    if args.report in ("brief", "toppages", "all"):
        report_toppages(client, start, end)
    if args.report in ("brief", "sources", "all"):
        report_sources(client, start, end)
    if args.report in ("countries", "all"):
        report_countries(client, start, end)
    if args.report in ("brief", "devices", "all"):
        report_devices(client, start, end)

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
