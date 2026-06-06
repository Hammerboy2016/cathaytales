#!/usr/bin/env python3
"""
GA4 简报邮件发送脚本
- 读取 ga4_report.txt
- 通过 SMTP（163 邮箱）发到 MAIL_TO
- 在 GitHub Actions 中调用，所有凭据走 secrets

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


def load_report(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"[mailer] 报告文件不存在：{path}\n请检查上一步 ga4_query 是否执行成功。"


def beijing_today() -> str:
    return (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime("%Y-%m-%d")


def main() -> int:
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASS"]
    sender = os.environ.get("MAIL_FROM", user)
    recipient = os.environ["MAIL_TO"]

    report_path = os.environ.get("REPORT_PATH", "ga4_report.txt")
    title_date = os.environ.get("REPORT_TITLE_DATE") or beijing_today()

    body = load_report(report_path)

    msg = EmailMessage()
    msg["Subject"] = f"📊 Cathay Tales GA4 日报 · {title_date}"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(body)

    print(f"[mailer] connecting {host}:{port} as {user} → {recipient}")
    ctx = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as smtp:
            smtp.login(user, password)
            smtp.send_message(msg)
    except smtplib.SMTPException as e:
        print(f"[mailer] SMTP error: {e!r}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"[mailer] network error: {e!r}", file=sys.stderr)
        return 1

    print(f"[mailer] ✓ sent ({len(body)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
