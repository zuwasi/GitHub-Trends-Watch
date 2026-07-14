"""Scheduler engine for background trending checks."""

import threading
import logging
from datetime import datetime, timedelta

from config_manager import load_config
from trending_scraper import scrape_trending, apply_filters
from agent_runner import run_agent
from chart_maker import generate_charts
from email_handler import build_html_email, build_text_fallback, send_email, save_report_to_history
from rating_engine import rate_all_repos, get_category_summary, get_tier_distribution

logger = logging.getLogger(__name__)


class TrendingScheduler:
    """Runs the trending check on a schedule in a background thread."""

    def __init__(self, config=None, status_callback=None):
        self.config = config or load_config()
        self.status_callback = status_callback
        self._thread = None
        self._stop_event = threading.Event()
        self._next_check = None
        self._last_result = None
        self._lock = threading.Lock()

    @property
    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    @property
    def next_check_time(self):
        return self._next_check

    @property
    def last_result(self):
        with self._lock:
            return self._last_result

    def start(self):
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def check_now(self):
        t = threading.Thread(target=self._do_check, daemon=True)
        t.start()

    def _run_loop(self):
        self._set_next_check_time()
        while not self._stop_event.is_set():
            now = datetime.now()
            if self._next_check and now >= self._next_check:
                self._do_check()
                self._set_next_check_time()
            self._stop_event.wait(timeout=30)

    def _set_next_check_time(self):
        sched = self.config.get("schedule", {})
        interval_type = sched.get("interval_type", "daily")
        interval_value = sched.get("interval_value", 1)
        check_time = sched.get("check_time", "09:00")
        day_of_week = int(sched.get("check_day_of_week", "1"))

        now = datetime.now()
        try:
            hour, minute = map(int, check_time.split(":"))
        except ValueError:
            hour, minute = 9, 0

        base_today = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if interval_type == "daily":
            next_time = base_today
            if next_time <= now:
                next_time += timedelta(days=1)
        elif interval_type == "weekly":
            days_ahead = (day_of_week - now.weekday()) % 7
            next_time = base_today + timedelta(days=days_ahead)
            if next_time <= now:
                next_time += timedelta(days=7)
        elif interval_type == "custom_days":
            next_time = base_today + timedelta(days=interval_value)
            if next_time <= now:
                next_time += timedelta(days=interval_value)
        elif interval_type == "custom_weeks":
            next_time = base_today + timedelta(weeks=interval_value)
            if next_time <= now:
                next_time += timedelta(weeks=interval_value)
        else:
            next_time = base_today + timedelta(days=1)

        self._next_check = next_time
        self._notify_status("Next check: " + next_time.strftime("%Y-%m-%d %H:%M"))

    def _do_check(self):
        self._notify_status("Checking GitHub trending...")
        try:
            trending_cfg = self.config.get("trending", {})
            repos = scrape_trending(
                time_range=trending_cfg.get("time_range", "daily"),
                language=trending_cfg.get("language", ""),
                spoken_language=trending_cfg.get("spoken_language", ""),
            )
            self._notify_status("Found " + str(len(repos)) + " repos. Filtering...")

            filters = self.config.get("filters", {})
            repos = apply_filters(repos, filters)
            self._notify_status(str(len(repos)) + " repos after filters. Running agent...")

            # Rate and classify repos
            self._notify_status("Rating and classifying repos...")
            rated_repos = rate_all_repos(repos)
            category_summary = get_category_summary(rated_repos)
            tier_distribution = get_tier_distribution(rated_repos)

            report_cfg = self.config.get("report", {})
            if report_cfg.get("include_agent_analysis", True):
                agent_output = run_agent(self.config, repos)
            else:
                agent_output = ""

            charts = {}
            if report_cfg.get("include_charts", True):
                self._notify_status("Generating charts...")
                charts = generate_charts(repos)

            self._notify_status("Building email...")
            html_body = build_html_email(repos, agent_output, charts, self.config,
                                         rated_repos=rated_repos,
                                         category_summary=category_summary,
                                         tier_distribution=tier_distribution)
            text_body = build_text_fallback(repos, agent_output, rated_repos=rated_repos)

            now = datetime.now()
            subject = "GitHub Trending Report - " + now.strftime("%b %d, %Y")

            save_report_to_history(html_body, repos, self.config)

            self._notify_status("Sending email...")
            success, message = send_email(html_body, text_body, subject, self.config)

            if success:
                self._notify_status("Done! " + message)
                with self._lock:
                    self._last_result = {"success": True, "message": message,
                                         "timestamp": now.isoformat(),
                                         "repo_count": len(repos)}
            else:
                self._notify_status("Failed: " + message)
                with self._lock:
                    self._last_result = {"success": False, "message": message,
                                         "timestamp": now.isoformat()}

        except Exception as e:
            error_msg = "Check failed: " + str(e)
            logger.exception("Trending check failed")
            self._notify_status(error_msg)
            with self._lock:
                self._last_result = {"success": False, "message": error_msg,
                                     "timestamp": datetime.now().isoformat()}

    def _notify_status(self, message):
        logger.info(message)
        if self.status_callback:
            try:
                self.status_callback(message)
            except Exception:
                pass

    def reload_config(self):
        self.config = load_config()
        self._set_next_check_time()
