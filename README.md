# GitHub Trends Watch

A cross-platform desktop app that monitors GitHub trending repositories on a schedule, uses your installed AI coding agent to analyze them, and emails you a professional HTML report with charts.

## Features

- **Scheduled checks**: daily, weekly, or custom intervals (every N days/weeks up to 30)
- **Agent-powered analysis**: detects installed AI coding agents (Amp, Claude Code, Gemini CLI, Codex, Aider, etc.) and uses one to write intelligent repo analysis
- **Beautiful HTML email**: gradient header, repo cards, stats bar, embedded charts
- **Charts**: top repos by stars, language distribution pie, stars-gained-today bar
- **Email providers**: Gmail, Outlook, Yahoo, iCloud, Zoho, GMX, Yandex, ProtonMail Bridge, or custom SMTP
- **Filters**: min stars, min stars today, max repos, keyword include/exclude
- **GitHub trending options**: daily/weekly/monthly, programming language filter, spoken language filter
- **Report history**: all past reports saved locally with auto-cleanup
- **Background mode**: runs silently with minimal resources after configuration
- **Cross-platform**: Windows, Linux, macOS

## Rating & Classification System

Each trending repository is evaluated using a consistent rating and classification system:

- **Overall Score (0-100)**: Calculated with a weighted formula:
  - Popularity (stars): 30%
  - Growth velocity (stars today): 25%
  - Maturity: 20%
  - Security signals: 15%
  - Community (forks + contributors): 10%
- **Tier Classification**:
  - **S (85-100)**: Exceptional — top-tier project with massive adoption and rapid growth
  - **A (70-84)**: Excellent — strong momentum and established presence
  - **B (50-69)**: Good — notable project with steady growth
  - **C (30-49)**: Emerging — early-stage with potential
  - **D (0-29)**: Experimental — just starting to gain traction
- **Category Classification**: Auto-detected from the repository description and name as AI/ML, Security, DevOps, Web, Data, Mobile, Systems, Tools, or Other.
- **Maturity Level**: Based on total star count:
  - Experimental: fewer than 100 stars
  - Early-Stage: 100-999 stars
  - Growing: 1,000-9,999 stars
  - Mature: 10,000-49,999 stars
  - Established: 50,000+ stars
- **Innovation Score (0-100)**: Based on the growth velocity ratio (stars today / total stars). A project gaining 10% or more of its total stars in one day scores very high.
- **Security Score (0-100)**: A heuristic based on maturity, fork scrutiny, and contributor diversity.

## Installation

```bash
cd GitHubTrendingReporter
pip install -r requirements.txt
```

## Usage

### GUI mode (first run / configuration)
```bash
python main.py
```
or
```bash
python main.py --gui
```

### Background mode (after config is saved)
```bash
python main.py --background
```

### One-time immediate check
```bash
python main.py --check-now
```

## Configuration

1. Launch the GUI with `python main.py`
2. **Schedule tab**: choose interval type, time, and day of week
3. **Agent tab**: click "Refresh Detection" to find installed agents, select one
4. **Email tab**: choose provider, enter credentials, add recipients
5. **Filters tab**: set star thresholds, keyword filters, report options
6. Click "Save Config", then "Start Scheduler" or "Check Now"

### Gmail App Password

For Gmail, you need an App Password (not your regular password):
1. Enable 2-Step Verification at myaccount.google.com
2. Generate an App Password at myaccount.google.com/apppasswords
3. Use that 16-character password in the Email tab

## How It Works

1. Scrapes the GitHub trending page (configurable time range, language)
2. Applies your filters (min stars, keywords, max repos)
3. Rates and classifies each repository by overall score, tier, category, maturity, innovation, and security
4. Sends the trending data and ratings to your selected AI agent with an analysis prompt
5. The agent produces a structured report with:
   - What each repo does and why it's trending
   - Who is behind it
   - Popularity metrics and security assessment
   - Usefulness and technical details
6. Generates matplotlib charts (stars, languages, growth)
7. Packs everything into a styled HTML email
8. Sends via your configured SMTP server
9. Saves a copy to the history folder

## File Structure

| File | Purpose |
|------|---------|
| `main.py` | Entry point (GUI, background, or check-now) |
| `gui.py` | Tkinter configuration GUI with 5 tabs |
| `config_manager.py` | Load/save/validate config JSON |
| `agent_detector.py` | Detect installed AI coding agents |
| `trending_scraper.py` | Scrape GitHub trending page |
| `rating_engine.py` | Rate and classify trending repositories |
| `agent_runner.py` | Run agent with analysis prompt |
| `chart_maker.py` | Generate matplotlib charts |
| `email_handler.py` | Build HTML email and send via SMTP |
| `scheduler.py` | Background scheduling engine |

Config is stored at `~/.github_trending_reporter/config.json`.
Report history is saved at `~/.github_trending_reporter/history/`.

## Requirements

- Python 3.9+
- See `requirements.txt` for dependencies

## License

MIT — Daniel Liezrowice-Zuwasi / ESL
