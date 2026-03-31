"""Stage 4: Render HTML email and send digest."""

import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

load_dotenv()

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
OUTPUT_DIR = Path(__file__).parent.parent / "output"


def render_html(items: list[dict]) -> str:
    """Render the email HTML from the Jinja2 template."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
    template = env.get_template("email.html.j2")
    return template.render(
        items=items,
        date=datetime.now().strftime("%A, %B %d, %Y"),
    )


def render_markdown(items: list[dict]) -> str:
    """Render a plain text markdown version of the digest."""
    lines = [
        f"# Daily Intel — {datetime.now().strftime('%Y-%m-%d')}",
        "",
    ]

    if not items:
        lines.append("Quiet day — nothing scored high enough to send.")
        return "\n".join(lines)

    for i, item in enumerate(items, 1):
        icon = "forward" if item.get("forward_only") else "connected"
        lines.append(f"## {i}. [{item.get('score', '?')}/10] {item.get('headline', item.get('title', 'N/A'))}")
        lines.append("")

        if not item.get("forward_only") and item.get("built_connection"):
            lines.append(f"- **You built this manually:** {item['built_connection']}")
            if item.get("time_saved"):
                lines.append(f"- **Could have saved:** {item['time_saved']}")
            if item.get("what_next"):
                lines.append(f"- **With that time:** {item['what_next']}")
            lines.append("")
        elif item.get("forward_only"):
            lines.append("*Forward recommendation — no direct match to your repos*")
            lines.append("")

        lines.append(f"**Action:** [{item.get('action_label', 'Read')}]({item.get('action', item.get('url', ''))})")
        lines.append(f"*Source: {item.get('source', 'unknown')}*")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def write_markdown(items: list[dict]) -> Path:
    """Write the DAILY-INTEL.md file."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    md_path = OUTPUT_DIR / "DAILY-INTEL.md"
    md_path.write_text(render_markdown(items))
    logger.info("  Wrote %s", md_path)
    return md_path


def send_smtp(html: str, subject: str) -> None:
    """Send email via SMTP."""
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASS", "")
    email_to = os.getenv("EMAIL_TO", "")

    if not all([user, password, email_to]):
        logger.error("  SMTP credentials not fully configured (SMTP_USER, SMTP_PASS, EMAIL_TO)")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = email_to
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.sendmail(user, [email_to], msg.as_string())

    logger.info("  Email sent via SMTP to %s", email_to)


def send_sendgrid(html: str, subject: str) -> None:
    """Send email via SendGrid."""
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Content, Email, Mail, To

    api_key = os.getenv("SENDGRID_API_KEY", "")
    from_email = os.getenv("SMTP_USER", "")
    to_email = os.getenv("EMAIL_TO", "")

    if not all([api_key, from_email, to_email]):
        logger.error("  SendGrid not fully configured (SENDGRID_API_KEY, SMTP_USER, EMAIL_TO)")
        return

    message = Mail(
        from_email=Email(from_email),
        to_emails=To(to_email),
        subject=subject,
        html_content=Content("text/html", html),
    )

    sg = SendGridAPIClient(api_key)
    response = sg.send(message)
    logger.info("  Email sent via SendGrid (status %s) to %s", response.status_code, to_email)


def deliver(synthesised_items: list[dict], dry_run: bool = True) -> None:
    """Render and deliver the digest email."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    subject = f"AI Research Digest — {date_str}"

    html = render_html(synthesised_items)
    write_markdown(synthesised_items)

    if dry_run:
        logger.info("  [DRY RUN] Printing HTML to stdout (%d chars)", len(html))
        print("\n" + "=" * 60)
        print("EMAIL HTML OUTPUT (dry run)")
        print("=" * 60)
        print(html)
        print("=" * 60)
        return

    # Send for real
    if os.getenv("SENDGRID_API_KEY"):
        try:
            send_sendgrid(html, subject)
        except Exception as e:
            logger.error("  SendGrid failed: %s — falling back to SMTP", e)
            send_smtp(html, subject)
    else:
        send_smtp(html, subject)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    deliver([], dry_run=True)
