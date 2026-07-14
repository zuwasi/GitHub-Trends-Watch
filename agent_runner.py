"""Run an AI coding agent to analyze GitHub trending repositories."""

import subprocess
import sys
import json
from datetime import datetime

from trending_scraper import format_repos_for_agent
from rating_engine import rate_all_repos


def build_prompt(repos, report_style="detailed", language="en", rated_repos=None):
    """Build the analysis prompt for the agent."""
    repos_text = format_repos_for_agent(repos)
    rating_text = ""
    if rated_repos:
        rating_lines = []
        for repo, rating in rated_repos:
            rating_lines.append(
                f"  {repo['name']}: Score {rating['overall_score']}/100, "
                f"Tier {rating['tier']}, Category {rating['category']}, "
                f"Maturity {rating['maturity']}, "
                f"Innovation {rating['innovation_score']}/100, "
                f"Security {rating['security_score']}/100"
            )
        rating_text = "\n\nPre-computed ratings (use these in your analysis):\n" + "\n".join(rating_lines)

    style_instruction = (
        "Provide a thorough analysis for each repository."
        if report_style == "detailed"
        else "Provide a concise 2-3 sentence summary for each repository."
    )

    lang_instruction = ""
    if language and language != "en":
        lang_map = {
            "es": "Spanish", "fr": "French", "de": "German",
            "he": "Hebrew", "zh": "Chinese", "ja": "Japanese",
            "pt": "Portuguese", "ru": "Russian", "ar": "Arabic",
        }
        lang_name = lang_map.get(language, language)
        lang_instruction = f"\nWrite the entire report in {lang_name}."

    prompt = f"""You are a senior technology analyst. Analyze the following GitHub trending repositories and produce a professional report.

For each repository provide:
1. **What it is** - A clear explanation of what the project does.
2. **Why it is trending** - What problem it solves or why developers are excited about it.
3. **Who is behind it** - The organization or notable contributors, if identifiable from the repo name.
4. **Popularity** - Interpret the star count, growth, and fork numbers.
5. **Security assessment** - License type if known, potential security considerations, code maturity indicators.
6. **Usefulness** - Practical applications and who would benefit from using it.
7. **Notable technical details** - Architecture, language choice, dependencies, or interesting design decisions.

{style_instruction}{lang_instruction}

The report includes pre-computed ratings for each repository. Reference these scores in your analysis and explain why each repo received its tier and category classification.

At the top of your report, include a **Trends Summary** (2-3 paragraphs) highlighting the overall themes and patterns you see across these trending repositories.

Format your response as clean Markdown with a ## heading for each repository.

Here are today's GitHub trending repositories:

{repos_text}
{rating_text}
"""
    return prompt


def run_agent(config, repos):
    """Execute the selected agent with the analysis prompt.

    Returns the agent's text output, or an error message string.
    """
    agent_cfg = config.get("agent", {})
    command = agent_cfg.get("command", "")
    prompt_args = agent_cfg.get("prompt_args", [])
    timeout = agent_cfg.get("timeout", 300)
    rated_repos = rate_all_repos(repos)

    if not command:
        return _fallback_report(repos, rated_repos=rated_repos)

    report_cfg = config.get("report", {})
    report_style = report_cfg.get("report_style", "detailed")
    lang = report_cfg.get("language", "en")

    prompt = build_prompt(repos, report_style, lang, rated_repos)

    # Build the command list
    cmd = [command] + prompt_args + [prompt]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = result.stdout.strip()
        if not output and result.stderr:
            # Some agents output to stderr in some modes
            output = result.stderr.strip()
        if not output:
            return _fallback_report(repos, "Agent produced no output.", rated_repos)
        return output
    except subprocess.TimeoutExpired:
        return _fallback_report(repos, f"Agent timed out after {timeout}s.", rated_repos)
    except FileNotFoundError:
        return _fallback_report(repos, f"Agent not found: {command}", rated_repos)
    except Exception as e:
        return _fallback_report(repos, f"Agent error: {e}", rated_repos)


def _fallback_report(repos, error_msg=None, rated_repos=None):
    """Generate a basic data-only report when no agent is available."""
    lines = []
    if error_msg:
        lines.append(f"> **Note:** Agent analysis unavailable ({error_msg}). Showing data-only report.\n")

    lines.append("## Trends Summary\n")
    lines.append(f"Found {len(repos)} trending repositories. "
                 f"Top languages: "
                 f"{', '.join(sorted(set(r['language'] for r in repos if r['language'])))}.\n")

    if rated_repos:
        lines.append("### Rating Summary\n")
        for repo, rating in rated_repos:
            lines.append(f"- **{repo['name']}** — Score: {rating['overall_score']}/100 | "
                         f"Tier: {rating['tier']} | Category: {rating['category']} | "
                         f"Maturity: {rating['maturity']}\n")

    for r in repos:
        lines.append(f"## {r['name']}\n")
        lines.append(f"**Description:** {r['description']}\n")
        lines.append(f"**Stars:** {r['stars']} (+{r['stars_today']} today) | "
                      f"**Forks:** {r['forks']} | "
                      f"**Language:** {r['language'] or 'N/A'}\n")
        lines.append(f"**URL:** {r['url']}\n")
        if rated_repos:
            for rr, rt in rated_repos:
                if rr["name"] == r["name"]:
                    lines.append(f"**Rating:** {rt['overall_score']}/100 | "
                                 f"Tier: {rt['tier']} | Category: {rt['category']} | "
                                 f"Maturity: {rt['maturity']}\n")
                    break

    return "\n".join(lines)
