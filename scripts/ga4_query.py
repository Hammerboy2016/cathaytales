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


def report_source_country(client, start, end, limit=20):
    """来源 × 国家二维交叉（用于识别 medium referral 真粉丝来自哪国）"""
    res = query(
        client,
        dimensions=["sessionSource", "country"],
        metrics=["sessions", "activeUsers", "engagedSessions", "userEngagementDuration"],
        start=start,
        end=end,
        limit=limit,
        order_by_metric="sessions",
    )
    print(f"\n🔍 来源 × 国家交叉 (Top {limit}, {start} ~ {end})")
    print("-" * 70)
    if not res.rows:
        print("  无数据")
        return
    print(f"  {'来源':<20} {'国家':<20} {'会话':>6} {'用户':>6} {'参与':>6} {'人均时长':>10}")
    for r in res.rows:
        src = (r.dimension_values[0].value or "(direct)")[:19]
        cty = (r.dimension_values[1].value or "(unknown)")[:19]
        s = int(r.metric_values[0].value or 0)
        u = int(r.metric_values[1].value or 0)
        es = int(r.metric_values[2].value or 0)
        dur = float(r.metric_values[3].value or 0)
        avg = (dur / u) if u else 0
        print(f"  {src:<20} {cty:<20} {s:>6} {u:>6} {es:>6} {avg:>8.1f}s")


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


def report_landing(client, start, end, limit=15):
    """着陆页排行 = SEO/外链入口"""
    res = query(
        client,
        dimensions=["landingPage"],
        metrics=["sessions", "activeUsers", "engagedSessions", "bounceRate", "userEngagementDuration"],
        start=start,
        end=end,
        limit=limit,
        order_by_metric="sessions",
    )
    print(f"\n🛬 Top {limit} 着陆页（用户进站第一页 = SEO/外链入口）")
    print("-" * 70)
    if not res.rows:
        print("  无数据")
        return
    print(f"  {'路径':<45} {'会话':>6} {'用户':>6} {'参与率':>8} {'人均':>8}")
    for r in res.rows:
        path = (r.dimension_values[0].value or "(unknown)")[:44]
        s = int(r.metric_values[0].value or 0)
        u = int(r.metric_values[1].value or 0)
        es = int(r.metric_values[2].value or 0)
        eng_rate = (es / s * 100) if s else 0
        dur = float(r.metric_values[4].value or 0)
        avg = (dur / u) if u else 0
        print(f"  {path:<45} {s:>6} {u:>6} {eng_rate:>6.1f}% {avg:>6.1f}s")


def report_pages_engagement(client, start, end, limit=20):
    """每页详细参与度（识别哪些文章值得放大）"""
    res = query(
        client,
        dimensions=["pagePath"],
        metrics=["screenPageViews", "activeUsers", "userEngagementDuration", "bounceRate"],
        start=start,
        end=end,
        limit=limit,
        order_by_metric="userEngagementDuration",
    )
    print(f"\n⭐ Top {limit} 页面参与度（按总停留时长排）")
    print("-" * 70)
    if not res.rows:
        print("  无数据")
        return
    print(f"  {'路径':<45} {'PV':>4} {'UV':>4} {'人均':>8} {'跳出率':>8} {'质量分':>8}")
    for r in res.rows:
        path = (r.dimension_values[0].value or "(unknown)")[:44]
        pv = int(r.metric_values[0].value or 0)
        uv = int(r.metric_values[1].value or 0)
        dur = float(r.metric_values[2].value or 0)
        bounce = float(r.metric_values[3].value or 0) * 100
        avg = (dur / uv) if uv else 0
        # 质量分 = 人均停留 / 60 * 5 + (100 - 跳出率) / 10  → 0-15 区间
        score = (avg / 60.0) * 5 + (100 - bounce) / 10
        flag = "🔥" if score >= 10 else ("✓ " if score >= 5 else "🔻")
        print(f"  {path:<45} {pv:>4} {uv:>4} {avg:>6.1f}s {bounce:>6.1f}% {flag}{score:>5.1f}")


def report_new_vs_return(client, start, end):
    """新 vs 老用户对比（内容粘性指标）"""
    res = query(
        client,
        dimensions=["newVsReturning"],
        metrics=["activeUsers", "sessions", "userEngagementDuration", "screenPageViews"],
        start=start,
        end=end,
        limit=10,
    )
    print(f"\n👥 新 vs 老用户对比（粘性指标）")
    print("-" * 70)
    if not res.rows:
        print("  无数据")
        return
    print(f"  {'类型':<15} {'用户':>6} {'会话':>6} {'PV':>5} {'人均时长':>10} {'人均PV':>8}")
    for r in res.rows:
        t = (r.dimension_values[0].value or "(unknown)")
        u = int(r.metric_values[0].value or 0)
        s = int(r.metric_values[1].value or 0)
        dur = float(r.metric_values[2].value or 0)
        pv = int(r.metric_values[3].value or 0)
        avg_dur = (dur / u) if u else 0
        avg_pv = (pv / u) if u else 0
        print(f"  {t:<15} {u:>6} {s:>6} {pv:>5} {avg_dur:>8.1f}s {avg_pv:>8.2f}")


def report_referrer_detail(client, start, end, limit=15):
    """referral 子来源细分（剔除 direct/google/not set 后真渠道）"""
    res = query(
        client,
        dimensions=["sessionSource", "sessionMedium", "landingPage"],
        metrics=["sessions", "activeUsers", "userEngagementDuration"],
        start=start,
        end=end,
        limit=50,
        order_by_metric="sessions",
    )
    print(f"\n🔗 真渠道细分（剔除 direct/google/(not set)）")
    print("-" * 70)
    if not res.rows:
        print("  无数据")
        return
    SKIP = {"(direct)", "(not set)", "google"}
    rows = [r for r in res.rows if r.dimension_values[0].value not in SKIP]
    if not rows:
        print("  暂无真渠道流量（除 direct/google 外都是空）")
        return
    print(f"  {'来源':<18} {'媒介':<10} {'落地页':<30} {'会话':>4} {'用户':>4} {'人均':>8}")
    for r in rows[:limit]:
        src = (r.dimension_values[0].value or "")[:17]
        med = (r.dimension_values[1].value or "")[:9]
        lp = (r.dimension_values[2].value or "")[:29]
        s = int(r.metric_values[0].value or 0)
        u = int(r.metric_values[1].value or 0)
        dur = float(r.metric_values[2].value or 0)
        avg = (dur / u) if u else 0
        print(f"  {src:<18} {med:<10} {lp:<30} {s:>4} {u:>4} {avg:>6.1f}s")


def report_hourly(client, start, end):
    """24 小时流量分布（看流量峰值时段）"""
    res = query(
        client,
        dimensions=["hour"],
        metrics=["activeUsers", "sessions", "screenPageViews"],
        start=start,
        end=end,
        limit=24,
    )
    print(f"\n🕐 24 小时流量分布（UTC，北京时间 +8）")
    print("-" * 70)
    if not res.rows:
        print("  无数据")
        return
    # 按小时排
    buckets = {int(r.dimension_values[0].value or 0): r for r in res.rows}
    max_pv = max((int(r.metric_values[2].value or 0) for r in res.rows), default=1)
    print(f"  {'UTC':>4} {'北京':>5} {'用户':>5} {'会话':>5} {'PV':>4}  柱状(PV)")
    for h in range(24):
        r = buckets.get(h)
        if not r:
            continue
        bj = (h + 8) % 24
        u = int(r.metric_values[0].value or 0)
        s = int(r.metric_values[1].value or 0)
        pv = int(r.metric_values[2].value or 0)
        bar = "█" * int(pv / max_pv * 30) if max_pv else ""
        print(f"  {h:>4} {bj:>4}:00 {u:>5} {s:>5} {pv:>4}  {bar}")


def report_weekday(client, start, end):
    """周几流量分布"""
    res = query(
        client,
        dimensions=["dayOfWeek"],
        metrics=["activeUsers", "sessions", "screenPageViews", "userEngagementDuration"],
        start=start,
        end=end,
        limit=7,
    )
    print(f"\n📅 周几流量分布（0=周日, 6=周六）")
    print("-" * 70)
    if not res.rows:
        print("  无数据")
        return
    DAYS = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
    buckets = {int(r.dimension_values[0].value or 0): r for r in res.rows}
    max_pv = max((int(r.metric_values[2].value or 0) for r in res.rows), default=1)
    print(f"  {'星期':<6} {'用户':>5} {'会话':>5} {'PV':>5} {'人均时长':>10}  柱状(PV)")
    for d in range(7):
        r = buckets.get(d)
        if not r:
            continue
        u = int(r.metric_values[0].value or 0)
        s = int(r.metric_values[1].value or 0)
        pv = int(r.metric_values[2].value or 0)
        dur = float(r.metric_values[3].value or 0)
        avg = (dur / u) if u else 0
        bar = "█" * int(pv / max_pv * 25) if max_pv else ""
        print(f"  {DAYS[d]:<6} {u:>5} {s:>5} {pv:>5} {avg:>8.1f}s  {bar}")


def report_growth_signal(client, start, end):
    """旺财增长信号分析（自动找放大点 + 哑火点）"""
    print(f"\n🎯 增长信号分析（旺财自动总结）")
    print("-" * 70)
    res = query(
        client,
        dimensions=["pagePath"],
        metrics=["screenPageViews", "activeUsers", "userEngagementDuration", "bounceRate"],
        start=start,
        end=end,
        limit=50,
    )
    if not res.rows:
        print("  无数据")
        return

    posts = []
    hubs = []
    for r in res.rows:
        path = r.dimension_values[0].value or ""
        pv = int(r.metric_values[0].value or 0)
        uv = int(r.metric_values[1].value or 0)
        dur = float(r.metric_values[2].value or 0)
        bounce = float(r.metric_values[3].value or 0) * 100
        avg = (dur / uv) if uv else 0
        score = (avg / 60.0) * 5 + (100 - bounce) / 10
        item = {"path": path, "pv": pv, "uv": uv, "avg": avg, "bounce": bounce, "score": score}
        if path.startswith("/posts/"):
            posts.append(item)
        elif path.startswith("/hubs/"):
            hubs.append(item)

    # 🔥 应该放大：质量高 + 流量可观
    amplify = sorted([p for p in posts if p["score"] >= 10 and p["pv"] >= 2],
                     key=lambda x: -x["score"])[:5]
    print(f"\n  🔥 应该放大（高质量+有流量，质量分≥10）：")
    if not amplify:
        print("    暂无")
    for p in amplify:
        print(f"    {p['path'][:50]:<50} 质量{p['score']:.1f} 停留{p['avg']:.0f}s PV{p['pv']}")

    # 🔻 哑火警告：流量有 + 质量低
    dud = sorted([p for p in posts if p["score"] < 5 and p["pv"] >= 2],
                 key=lambda x: -x["pv"])[:5]
    print(f"\n  🔻 哑火警告（流量有但质量低，需复盘标题/开篇/选材）：")
    if not dud:
        print("    暂无")
    for p in dud:
        print(f"    {p['path'][:50]:<50} 质量{p['score']:.1f} 停留{p['avg']:.0f}s PV{p['pv']}")

    # 💎 潜力股：质量高但流量低 → 需要外推（Medium/Reddit）
    gem = sorted([p for p in posts if p["score"] >= 10 and p["pv"] < 5],
                 key=lambda x: -x["score"])[:5]
    print(f"\n  💎 潜力股（质量高但流量低，应外推到 Medium/Reddit）：")
    if not gem:
        print("    暂无")
    for p in gem:
        print(f"    {p['path'][:50]:<50} 质量{p['score']:.1f} 停留{p['avg']:.0f}s PV{p['pv']}")

    # Hub 健康度
    print(f"\n  🗂️  Hub 引流健康度：")
    if not hubs:
        print("    暂无 hub 流量")
    for h in sorted(hubs, key=lambda x: -x["pv"]):
        print(f"    {h['path']:<50} PV{h['pv']} UV{h['uv']} 停留{h['avg']:.0f}s")


def main():
    ap = argparse.ArgumentParser(description="Cathay Tales GA4 查询工具")
    ap.add_argument("--days", type=int, default=7, help="过去 N 天，默认 7")
    ap.add_argument("--start", type=str, help="开始日期 YYYY-MM-DD（与 --days 互斥）")
    ap.add_argument("--end", type=str, help="结束日期 YYYY-MM-DD，默认今天")
    ap.add_argument(
        "--report",
        type=str,
        default="brief",
        choices=["brief", "overview", "daily", "toppages", "sources", "countries", "devices",
                 "crosstab", "landing", "engagement", "newvsreturn", "referrer", "hourly",
                 "weekday", "signal", "all"],
        help="报表类型，默认 brief（概览+top10+来源+增长信号）",
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
    if args.report in ("brief", "engagement", "all"):
        report_pages_engagement(client, start, end)
    if args.report in ("landing", "all"):
        report_landing(client, start, end)
    if args.report in ("brief", "sources", "all"):
        report_sources(client, start, end)
    if args.report in ("referrer", "all"):
        report_referrer_detail(client, start, end)
    if args.report in ("crosstab", "all"):
        report_source_country(client, start, end)
    if args.report in ("countries", "all"):
        report_countries(client, start, end)
    if args.report in ("newvsreturn", "all"):
        report_new_vs_return(client, start, end)
    if args.report in ("brief", "devices", "all"):
        report_devices(client, start, end)
    if args.report in ("hourly", "all"):
        report_hourly(client, start, end)
    if args.report in ("weekday", "all"):
        report_weekday(client, start, end)
    if args.report in ("brief", "signal", "all"):
        report_growth_signal(client, start, end)

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
