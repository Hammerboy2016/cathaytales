#!/usr/bin/env python3
"""
GA4 简报邮件发送脚本 v2
- 读取 ga4_report.txt
- 通过 SMTP（163 邮箱）发到 MAIL_TO
- 所有凭据走 GitHub Secrets，自动 strip 空白避免 DNS 报错

环境变量：
  SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS
  MAIL_FROM / MAIL_TO
  REPORT_PATH         可选，默认 ga4_report.txt
  REPORT_TITLE_DATE   可选，邮件标题日期；不传用 UTC+8 today
"""
from __future__ import annotations

import os
import sys
import smtplib
import ssl
import datetime
from email.message import EmailMessage


def env_clean(key: str, default: str | None = None) -> str:
    """读环境变量并 strip 掉前后空白/换行（避免粘贴时带换行导致 DNS/认证报错）"""
    val = os.environ.get(key, default)
    if val is None:
        raise KeyError(f"环境变量 {key} 未设置")
    return val.strip()


def load_report(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"[mailer] 报告文件不存在：{path}\n请检查上一步 ga4_query 是否执行成功。"


def beijing_today() -> str:
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).strftime("%Y-%m-%d")


def main() -> int:
    host = env_clean("SMTP_HOST")
    port = int(env_clean("SMTP_PORT", "465"))
    user = env_clean("SMTP_USER")
    password = env_clean("SMTP_PASS")
    sender = env_clean("MAIL_FROM", user)
    recipient = env_clean("MAIL_TO")

    report_path = env_clean("REPORT_PATH", "ga4_report.txt")
    title_date = os.environ.get("REPORT_TITLE_DATE", "").strip() or beijing_today()

    # 关键调试日志（host/port 不脱敏，secrets 的 *** 由 Actions 自动遮蔽 user/pass）
    print(f"[mailer] host repr: {host!r}  port: {port}")
    print(f"[mailer] from→to: {sender!r} → {recipient!r}")
    print(f"[mailer] report: {report_path}, title_date: {title_date}")

    body = load_report(report_path)

    msg = EmailMessage()
    msg["Subject"] = f"📊 Cathay Tales GA4 日报 · {title_date}"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(body)

    print(f"[mailer] connecting {host}:{port}...")
    ctx = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as smtp:
            smtp.set_debuglevel(0)
            smtp.login(user, password)
            smtp.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        print(f"[mailer] 认证失败: {e!r}", file=sys.stderr)
        print("[mailer] 提示：检查 SMTP_PASS 是否为 163 邮箱授权码（不是登录密码）", file=sys.stderr)
        return 1
    except smtplib.SMTPException as e:
        print(f"[mailer] SMTP error: {e!r}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"[mailer] network error: {e!r}", file=sys.stderr)
        print(f"[mailer] 提示：常见原因为 SMTP_HOST 末尾带换行符。当前 host={host!r}", file=sys.stderr)
        return 1

    print(f"[mailer] ✓ sent ({len(body)} chars) → {recipient}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
