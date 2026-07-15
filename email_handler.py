"""Build and send HTML email reports with embedded charts."""

import smtplib
import base64
import json
from datetime import datetime
from html import escape as html_escape
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.utils import formataddr

try:
    import markdown as md
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False

from config_manager import get_history_dir


# SMTP server presets for popular providers
SMTP_PRESETS = {
    "gmail":       {"server": "smtp.gmail.com",       "port": 587, "tls": True},
    "outlook":     {"server": "smtp.office365.com",    "port": 587, "tls": True},
    "yahoo":       {"server": "smtp.mail.yahoo.com",   "port": 587, "tls": True},
    "icloud":      {"server": "smtp.mail.me.com",      "port": 587, "tls": True},
    "zoho":        {"server": "smtp.zoho.com",         "port": 587, "tls": True},
    "mailcom":     {"server": "smtp.mail.com",         "port": 587, "tls": True},
    "gmx":         {"server": "mail.gmx.com",          "port": 587, "tls": True},
    "protonmail":  {"server": "127.0.0.1",             "port": 1025, "tls": False},  # requires ProtonMail Bridge
    "yandex":      {"server": "smtp.yandex.com",       "port": 465, "tls": False},
    "custom":      {"server": "",                      "port": 587, "tls": True},
}


def get_smtp_preset(provider):
    """Return SMTP settings for a known provider."""
    return SMTP_PRESETS.get(provider, SMTP_PRESETS["custom"])


def _markdown_to_html(text):
    """Convert markdown text to HTML."""
    if HAS_MARKDOWN:
        # Use "tables" and "fenced_code" but NOT "extra" (which allows inline HTML)
        return md.markdown(text, extensions=["tables", "fenced_code"], output_format="html5")
    # Fallback: basic conversion
    html = text
    html = html.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html = html.replace("\n\n", "</p><p>")
    html = html.replace("\n", "<br>")
    # Bold
    import re
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    # Headers
    html = re.sub(r"^## (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    return f"<p>{html}</p>"


def build_html_email(repos, agent_analysis, charts, config, rated_repos=None, category_summary=None, tier_distribution=None):
    """Build the full HTML email body.

    Args:
        repos: list of repo dicts
        agent_analysis: markdown text from the agent
        charts: dict of {name: base64_png}
        config: app config dict

    Returns:
        HTML string for the email body.
    """
    now = datetime.now()
    date_str = now.strftime("%B %d, %Y")
    time_range = config.get("trending", {}).get("time_range", "daily")
    agent_name = config.get("agent", {}).get("name", "Data-only")
    report_style = config.get("report", {}).get("report_style", "detailed")

    # Convert agent analysis to HTML
    analysis_html = _markdown_to_html(agent_analysis)

    # Build rating lookup if available
    rating_map = {}
    if rated_repos:
        for repo, rating in rated_repos:
            rating_map[repo["name"]] = rating

    # Build repo cards
    repo_cards = ""
    for r in repos:
        # Escape all scraped data to prevent HTML injection (F-002)
        repo_name = html_escape(r["name"])
        repo_url = html_escape(r["url"], quote=True)
        repo_desc = html_escape(r["description"] or "No description available.")
        repo_lang = html_escape(r["language"]) if r["language"] else ""

        lang_badge = ""
        if r["language"]:
            lang_badge = '<span class="badge lang">' + repo_lang + "</span>"

        # Rating badges
        rating_badges = ""
        rating = rating_map.get(r["name"])
        if rating:
            tier_class = "tier-" + rating["tier"].lower()
            rating_badges = (
                '<span class="badge ' + tier_class + '">Tier ' + html_escape(rating["tier"]) + "</span>"
                '<span class="badge score">' + str(rating["overall_score"]) + "/100</span>"
                '<span class="badge cat">' + html_escape(rating["category"]) + "</span>"
                '<span class="badge maturity">' + html_escape(rating["maturity"]) + "</span>"
            )

        contribs = ""
        if r["contributors"]:
            contribs_html = "".join(
                '<span class="contrib">' + html_escape(c) + "</span>" for c in r["contributors"][:5]
            )
            contribs = '<div class="contributors"><span>Built by:</span> ' + contribs_html + "</div>"

        repo_cards += f"""
        <div class="repo-card">
            <div class="repo-header">
                <h3><a href="{repo_url}">{repo_name}</a></h3>
                <span class="rank">#{r['rank']}</span>
            </div>
            <p class="repo-desc">{repo_desc}</p>
            <div class="repo-meta">
                {lang_badge}
                <span class="badge stars">&#9733; {r['stars']:,}</span>
                <span class="badge today">+{r['stars_today']} today</span>
                <span class="badge forks">&#42780; {r['forks']:,}</span>
                {rating_badges}
            </div>
            {contribs}
        </div>
        """

    # Build chart images
    charts_html = ""
    if charts:
        chart_titles = {
            "top_stars": "Top Repositories by Total Stars",
            "language_pie": "Programming Language Distribution",
            "stars_today": "Stars Gained Today",
        }
        for key, b64 in charts.items():
            title = chart_titles.get(key, key.replace("_", " ").title())
            charts_html += f"""
            <div class="chart-container">
                <h3>{title}</h3>
                <img src="data:image/png;base64,{b64}" alt="{title}" style="max-width:100%;border-radius:8px;" />
            </div>
            """

    # Stats summary
    total_stars_today = sum(r["stars_today"] for r in repos)
    total_stars = sum(r["stars"] for r in repos)
    languages = sorted(set(r["language"] for r in repos if r["language"]))

    # Rating summary HTML
    rating_summary_html = ""
    if tier_distribution:
        tier_order = ["S", "A", "B", "C", "D"]
        tier_colors = {"S": "#e91e63", "A": "#4caf50", "B": "#2196f3", "C": "#ff9800", "D": "#9e9e9e"}
        tier_badges = ""
        for tier in tier_order:
            if tier in tier_distribution:
                color = tier_colors.get(tier, "#999")
                tier_badges += '<span class="tier-badge" style="background:' + color + '">' + tier + ": " + str(tier_distribution[tier]) + "</span>"

        cat_badges = ""
        if category_summary:
            for cat, count in sorted(category_summary.items(), key=lambda x: x[1], reverse=True):
                cat_badges += '<span class="cat-badge">' + cat + ": " + str(count) + "</span>"

        rating_summary_html = """
    <div class="section-title">Rating Overview</div>
    <div class="rating-summary">
      <div class="tier-distribution">""" + tier_badges + """</div>
      <div class="category-distribution">""" + cat_badges + """</div>
    </div>
    """

    html = f"""
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{
    font-family: 'Segoe UI', -apple-system, Arial, sans-serif;
    background: #f0f2f5;
    margin: 0; padding: 0;
    color: #1a1a2e;
  }}
  .container {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
  .header {{
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white; padding: 30px 25px; border-radius: 12px 12px 0 0;
    text-align: center;
  }}
  .header h1 {{ margin: 0; font-size: 28px; font-weight: 700; }}
  .header p {{ margin: 8px 0 0; opacity: 0.9; font-size: 14px; }}
  .body {{ background: white; padding: 25px; border-radius: 0 0 12px 12px;
           box-shadow: 0 2px 10px rgba(0,0,0,0.08); }}
  .stats-bar {{
    display: flex; justify-content: space-around;
    background: #f8f9fa; border-radius: 8px; padding: 15px; margin: 20px 0;
  }}
  .stat {{ text-align: center; }}
  .stat .num {{ font-size: 24px; font-weight: 700; color: #667eea; }}
  .stat .label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
  .analysis {{ margin: 20px 0; line-height: 1.7; }}
  .analysis h2 {{ color: #667eea; border-bottom: 2px solid #eee; padding-bottom: 8px; }}
  .analysis h3 {{ color: #555; margin-top: 20px; }}
  .chart-container {{ margin: 25px 0; text-align: center; }}
  .chart-container h3 {{ color: #333; font-size: 15px; }}
  .repo-card {{
    border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px;
    margin: 12px 0; transition: box-shadow 0.2s;
  }}
  .repo-card:hover {{ box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
  .repo-header {{ display: flex; justify-content: space-between; align-items: center; }}
  .repo-header h3 {{ margin: 0; font-size: 16px; }}
  .repo-header h3 a {{ color: #667eea; text-decoration: none; }}
  .repo-header .rank {{ color: #aaa; font-size: 14px; font-weight: 600; }}
  .repo-desc {{ color: #555; font-size: 14px; margin: 8px 0; }}
  .repo-meta {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .badge {{
    font-size: 12px; padding: 3px 10px; border-radius: 12px;
    background: #f0f0f0; color: #555;
  }}
  .badge.lang {{ background: #e8f5e9; color: #2e7d32; }}
  .badge.stars {{ background: #fff3e0; color: #e65100; }}
  .badge.today {{ background: #e3f2fd; color: #1565c0; }}
  .badge.forks {{ background: #f3e5f5; color: #7b1fa2; }}
  .contributors {{ margin-top: 8px; font-size: 12px; color: #888; }}
  .contributors span.contrib {{
    display: inline-block; background: #f5f5f5; padding: 2px 8px;
    border-radius: 10px; margin: 0 2px; font-size: 11px;
  }}
  .section-title {{
    font-size: 20px; font-weight: 700; color: #333;
    margin: 30px 0 15px; border-left: 4px solid #667eea; padding-left: 12px;
  }}
  .footer {{
    text-align: center; padding: 20px; color: #999;
    font-size: 12px;
  }}
  .badge.tier-s {{ background: #fce4ec; color: #c2185b; font-weight: bold; }}
  .badge.tier-a {{ background: #e8f5e9; color: #2e7d32; font-weight: bold; }}
  .badge.tier-b {{ background: #e3f2fd; color: #1565c0; font-weight: bold; }}
  .badge.tier-c {{ background: #fff3e0; color: #e65100; }}
  .badge.tier-d {{ background: #f5f5f5; color: #757575; }}
  .badge.score {{ background: #f3e5f5; color: #7b1fa2; font-weight: bold; }}
  .badge.cat {{ background: #e0f7fa; color: #006064; }}
  .badge.maturity {{ background: #f1f8e9; color: #558b2f; }}
  .rating-summary {{ margin: 20px 0; }}
  .tier-distribution {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 10px; }}
  .tier-badge {{ color: white; padding: 4px 12px; border-radius: 12px; font-size: 13px; font-weight: bold; }}
  .category-distribution {{ display: flex; gap: 8px; flex-wrap: wrap; }}
  .cat-badge {{ background: #f0f4c3; color: #558b2f; padding: 3px 10px; border-radius: 12px; font-size: 12px; }}
  @media (max-width: 600px) {{
    .stats-bar {{ flex-direction: column; gap: 10px; }}
    .repo-meta {{ flex-direction: column; gap: 4px; }}
  }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>&#128640; GitHub Trending Report</h1>
    <p>{date_str} | Time range: {time_range.capitalize()} | Agent: {agent_name} | Style: {report_style.capitalize()}</p>
  </div>
  <div class="body">
    <div class="stats-bar">
      <div class="stat"><div class="num">{len(repos)}</div><div class="label">Repos Found</div></div>
      <div class="stat"><div class="num">{total_stars:,}</div><div class="label">Total Stars</div></div>
      <div class="stat"><div class="num">+{total_stars_today:,}</div><div class="label">Stars Today</div></div>
      <div class="stat"><div class="num">{len(languages)}</div><div class="label">Languages</div></div>
    </div>

    {rating_summary_html}

    <div class="section-title">Agent Analysis</div>
    <div class="analysis">{analysis_html}</div>

    <div class="section-title">Visual Overview</div>
    {charts_html}

    <div class="section-title">Repository Details</div>
    {repo_cards}
  </div>
  <div class="footer">
    Generated by GitHub Trending Reporter on {now.strftime("%Y-%m-%d %H:%M")} |
    Powered by {agent_name}
  </div>
</div>
</body>
</html>
"""
    return html


def build_text_fallback(repos, agent_analysis, rated_repos=None):
    """Build a plain-text version of the report for email clients that need it."""
    lines = [f"GitHub Trending Report - {datetime.now().strftime('%Y-%m-%d')}", "=" * 50, ""]
    lines.append(agent_analysis)
    if rated_repos:
        lines.append("\n" + "-" * 40)
        lines.append("Rating Summary:")
        lines.append("-" * 40)
        for repo, rating in rated_repos:
            lines.append("  " + repo["name"] + " | Score: " + str(rating["overall_score"]) +
                         "/100 | Tier: " + rating["tier"] + " | Category: " + rating["category"] +
                         " | Maturity: " + rating["maturity"])
        lines.append("")

    lines.append("\n" + "=" * 50)
    lines.append("Repository Details:\n")
    for r in repos:
        lines.append(f"  #{r['rank']} {r['name']} - {r['description']}")
        lines.append(f"      Stars: {r['stars']:,} (+{r['stars_today']} today) | "
                      f"Forks: {r['forks']:,} | Language: {r['language'] or 'N/A'}")
        lines.append(f"      URL: {r['url']}\n")
    return "\n".join(lines)


def send_email(html_body, text_body, subject, config):
    """Send the email via SMTP using config settings.

    Returns (success: bool, message: str).
    """
    email_cfg = config.get("email", {})
    smtp_server = email_cfg.get("smtp_server", "smtp.gmail.com")
    smtp_port = email_cfg.get("smtp_port", 587)
    username = email_cfg.get("username", "")
    password = email_cfg.get("password", "")
    use_tls = email_cfg.get("use_tls", True)
    recipients = email_cfg.get("recipients", [])
    sender_name = email_cfg.get("sender_name", "GitHub Trending Reporter")

    if not recipients:
        return False, "No recipients configured."

    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = formataddr((sender_name, username))
    msg["To"] = ", ".join(recipients)

    # Alternative part for text + HTML
    alt_part = MIMEMultipart("alternative")
    alt_part.attach(MIMEText(text_body, "plain", "utf-8"))
    alt_part.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(alt_part)

    try:
        if use_tls:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)

        server.login(username, password)
        server.sendmail(username, recipients, msg.as_string())
        server.quit()
        return True, f"Email sent to {', '.join(recipients)}"
    except Exception as e:
        return False, f"Email send failed: {e}"


def save_report_to_history(html_body, repos, config):
    """Save the report HTML to the history directory."""
    history_dir = get_history_dir()
    history_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    filename = f"report_{now.strftime('%Y%m%d_%H%M%S')}.html"
    filepath = history_dir / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_body)

    # Also save a JSON summary
    summary = {
        "timestamp": now.isoformat(),
        "repo_count": len(repos),
        "repos": [{"name": r["name"], "stars": r["stars"],
                    "stars_today": r["stars_today"], "language": r["language"]}
                   for r in repos],
    }
    json_path = history_dir / filename.replace(".html", ".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Clean old reports
    keep_days = config.get("app", {}).get("history_keep_days", 90)
    _clean_history(history_dir, keep_days)

    return filepath


def _clean_history(history_dir, keep_days):
    """Delete report files older than keep_days."""
    import os
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=keep_days)
    for f in history_dir.glob("report_*"):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                f.unlink()
        except Exception:
            pass
