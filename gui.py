"""Tkinter configuration GUI for GitHub Trending Reporter."""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import json
from datetime import datetime

from config_manager import load_config, save_config, validate_config, ensure_dirs, get_history_dir
from agent_detector import detect_agents
from email_handler import SMTP_PRESETS
from scheduler import TrendingScheduler

import os
import sys

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _create_tray_icon_image():
    """Create a simple tray icon image."""
    img = Image.new("RGB", (64, 64), "#1a1a2e")
    draw = ImageDraw.Draw(img)
    draw.ellipse([12, 12, 52, 52], fill="#58a6ff")
    draw.text((22, 18), "GT", fill="white")
    return img


class TrendingReporterGUI:
    """Main configuration GUI."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GitHub Trending Reporter")
        self.root.geometry("750x680")
        self.root.minsize(650, 600)

        self.config = load_config()
        self.scheduler = TrendingScheduler(self.config, status_callback=self._on_status)
        self.detected_agents = []
        self._tray_icon = None
        self._in_tray = False

        self._build_ui()
        self._load_config_into_ui()

        if self.config.get("app", {}).get("check_on_startup", False):
            self._start_scheduler()

    def _build_ui(self):
        """Build the tabbed interface."""
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tabs
        self.tab_schedule = ttk.Frame(notebook)
        self.tab_agent = ttk.Frame(notebook)
        self.tab_email = ttk.Frame(notebook)
        self.tab_filters = ttk.Frame(notebook)
        self.tab_status = ttk.Frame(notebook)

        notebook.add(self.tab_schedule, text="Schedule")
        notebook.add(self.tab_agent, text="Agent")
        notebook.add(self.tab_email, text="Email")
        notebook.add(self.tab_filters, text="Filters")
        notebook.add(self.tab_status, text="Status")

        self._build_schedule_tab()
        self._build_agent_tab()
        self._build_email_tab()
        self._build_filters_tab()
        self._build_status_tab()

        # Bottom buttons
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Button(btn_frame, text="Save Config", command=self._save_config).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Check Now", command=self._check_now).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Start Scheduler", command=self._start_scheduler).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Stop Scheduler", command=self._stop_scheduler).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Test Email", command=self._test_email).pack(side="right", padx=5)

    def _build_schedule_tab(self):
        tab = self.tab_schedule
        frame = ttk.LabelFrame(tab, text="Check Interval", padding=15)
        frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(frame, text="Interval type:").grid(row=0, column=0, sticky="w", pady=5)
        self.interval_var = tk.StringVar(value="daily")
        interval_combo = ttk.Combobox(frame, textvariable=self.interval_var, state="readonly",
                                       values=["daily", "weekly", "custom_days", "custom_weeks"], width=20)
        interval_combo.grid(row=0, column=1, pady=5, padx=10)
        interval_combo.bind("<<ComboboxSelected>>", self._on_interval_change)

        self.every_label = ttk.Label(frame, text="Every:")
        self.every_label.grid(row=1, column=0, sticky="w", pady=5)
        self.interval_value_var = tk.IntVar(value=1)
        self.every_spin = ttk.Spinbox(frame, from_=1, to=30, textvariable=self.interval_value_var, width=10)
        self.every_spin.grid(row=1, column=1, pady=5, padx=10, sticky="w")

        self.interval_label = ttk.Label(frame, text="day(s)")
        self.interval_label.grid(row=1, column=2, sticky="w")

        ttk.Label(frame, text="Check time (HH:MM):").grid(row=2, column=0, sticky="w", pady=5)
        self.time_var = tk.StringVar(value="09:00")
        ttk.Entry(frame, textvariable=self.time_var, width=10).grid(row=2, column=1, pady=5, padx=10, sticky="w")

        self.dow_label = ttk.Label(frame, text="Day of week:")
        self.dow_label.grid(row=3, column=0, sticky="w", pady=5)
        self.dow_var = tk.StringVar(value="Monday")
        self.dow_combo = ttk.Combobox(frame, textvariable=self.dow_var, state="readonly",
                     values=DAYS_OF_WEEK, width=15)
        self.dow_combo.grid(row=3, column=1, pady=5, padx=10, sticky="w")

        # Trending options
        frame2 = ttk.LabelFrame(tab, text="GitHub Trending Options", padding=15)
        frame2.pack(fill="x", padx=10, pady=10)

        ttk.Label(frame2, text="Time range:").grid(row=0, column=0, sticky="w", pady=5)
        self.range_var = tk.StringVar(value="daily")
        ttk.Combobox(frame2, textvariable=self.range_var, state="readonly",
                     values=["daily", "weekly", "monthly"], width=15).grid(row=0, column=1, pady=5, padx=10)

        ttk.Label(frame2, text="Programming language:").grid(row=1, column=0, sticky="w", pady=5)
        self.lang_var = tk.StringVar(value="")
        ttk.Entry(frame2, textvariable=self.lang_var, width=20).grid(row=1, column=1, pady=5, padx=10, sticky="w")
        ttk.Label(frame2, text="(empty = all languages)").grid(row=1, column=2, sticky="w")

        ttk.Label(frame2, text="Spoken language code:").grid(row=2, column=0, sticky="w", pady=5)
        self.spoken_var = tk.StringVar(value="")
        ttk.Entry(frame2, textvariable=self.spoken_var, width=10).grid(row=2, column=1, pady=5, padx=10, sticky="w")
        ttk.Label(frame2, text="(e.g. en, zh, es; empty = all)").grid(row=2, column=2, sticky="w")

    def _build_agent_tab(self):
        tab = self.tab_agent
        frame = ttk.LabelFrame(tab, text="Detected AI Agents", padding=15)
        frame.pack(fill="x", padx=10, pady=10)

        ttk.Button(frame, text="Refresh Detection", command=self._refresh_agents).grid(row=0, column=0, pady=5)

        self.agent_listbox = tk.Listbox(frame, height=8, width=60)
        self.agent_listbox.grid(row=1, column=0, pady=10, sticky="ew")
        self.agent_listbox.bind("<<ListboxSelect>>", self._on_agent_select)

        ttk.Label(frame, text="Selected agent command:").grid(row=2, column=0, sticky="w")
        self.agent_cmd_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.agent_cmd_var, width=50, state="readonly").grid(row=3, column=0, sticky="w")

        ttk.Label(frame, text="Prompt args (comma-separated):").grid(row=4, column=0, sticky="w", pady=(10, 0))
        self.agent_args_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.agent_args_var, width=50).grid(row=5, column=0, sticky="w")

        ttk.Label(frame, text="Agent timeout (seconds):").grid(row=6, column=0, sticky="w", pady=(10, 0))
        self.agent_timeout_var = tk.IntVar(value=300)
        ttk.Spinbox(frame, from_=60, to=900, textvariable=self.agent_timeout_var, width=10).grid(row=7, column=0, sticky="w")

    def _build_email_tab(self):
        tab = self.tab_email
        frame = ttk.LabelFrame(tab, text="Email Provider", padding=15)
        frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(frame, text="Provider:").grid(row=0, column=0, sticky="w", pady=5)
        self.provider_var = tk.StringVar(value="gmail")
        provider_combo = ttk.Combobox(frame, textvariable=self.provider_var, state="readonly",
                                       values=list(SMTP_PRESETS.keys()), width=15)
        provider_combo.grid(row=0, column=1, pady=5, padx=10)
        provider_combo.bind("<<ComboboxSelected>>", self._on_provider_change)

        ttk.Label(frame, text="SMTP Server:").grid(row=1, column=0, sticky="w", pady=5)
        self.smtp_server_var = tk.StringVar(value="smtp.gmail.com")
        ttk.Entry(frame, textvariable=self.smtp_server_var, width=30).grid(row=1, column=1, pady=5, padx=10)

        ttk.Label(frame, text="SMTP Port:").grid(row=2, column=0, sticky="w", pady=5)
        self.smtp_port_var = tk.IntVar(value=587)
        ttk.Spinbox(frame, from_=1, to=65535, textvariable=self.smtp_port_var, width=10).grid(row=2, column=1, pady=5, padx=10, sticky="w")

        self.tls_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="Use TLS", variable=self.tls_var).grid(row=3, column=1, sticky="w", pady=5)

        ttk.Label(frame, text="Username (email):").grid(row=4, column=0, sticky="w", pady=5)
        self.email_user_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.email_user_var, width=40).grid(row=4, column=1, pady=5, padx=10)

        ttk.Label(frame, text="Password / App password:").grid(row=5, column=0, sticky="w", pady=5)
        self.email_pass_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.email_pass_var, width=40, show="*").grid(row=5, column=1, pady=5, padx=10)

        ttk.Label(frame, text="Sender name:").grid(row=6, column=0, sticky="w", pady=5)
        self.sender_name_var = tk.StringVar(value="GitHub Trending Reporter")
        ttk.Entry(frame, textvariable=self.sender_name_var, width=30).grid(row=6, column=1, pady=5, padx=10)

        # Recipients
        frame2 = ttk.LabelFrame(tab, text="Recipients", padding=15)
        frame2.pack(fill="x", padx=10, pady=10)

        self.recipients_text = tk.Text(frame2, height=4, width=50)
        self.recipients_text.grid(row=0, column=0, pady=5)
        ttk.Label(frame2, text="(one email per line)").grid(row=1, column=0, sticky="w")

        ttk.Label(frame2, text="Note: For Gmail, use an App Password (not your regular password).\nEnable 2FA, then generate one at myaccount.google.com/apppasswords").grid(row=2, column=0, sticky="w", pady=(10, 0))

    def _build_filters_tab(self):
        tab = self.tab_filters
        frame = ttk.LabelFrame(tab, text="Repository Filters", padding=15)
        frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(frame, text="Minimum total stars:").grid(row=0, column=0, sticky="w", pady=5)
        self.min_stars_var = tk.IntVar(value=0)
        ttk.Spinbox(frame, from_=0, to=1000000, increment=100, textvariable=self.min_stars_var, width=15).grid(row=0, column=1, pady=5, padx=10, sticky="w")

        ttk.Label(frame, text="Minimum stars today:").grid(row=1, column=0, sticky="w", pady=5)
        self.min_today_var = tk.IntVar(value=0)
        ttk.Spinbox(frame, from_=0, to=100000, increment=10, textvariable=self.min_today_var, width=15).grid(row=1, column=1, pady=5, padx=10, sticky="w")

        ttk.Label(frame, text="Max repos in report:").grid(row=2, column=0, sticky="w", pady=5)
        self.max_repos_var = tk.IntVar(value=25)
        ttk.Spinbox(frame, from_=1, to=100, textvariable=self.max_repos_var, width=10).grid(row=2, column=1, pady=5, padx=10, sticky="w")

        ttk.Label(frame, text="Exclude keywords (comma-sep):").grid(row=3, column=0, sticky="w", pady=5)
        self.exclude_kw_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.exclude_kw_var, width=40).grid(row=3, column=1, pady=5, padx=10)

        ttk.Label(frame, text="Include keywords (comma-sep):").grid(row=4, column=0, sticky="w", pady=5)
        self.include_kw_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.include_kw_var, width=40).grid(row=4, column=1, pady=5, padx=10)
        ttk.Label(frame, text="(empty = include all)").grid(row=4, column=2, sticky="w")

        # Report options
        frame2 = ttk.LabelFrame(tab, text="Report Options", padding=15)
        frame2.pack(fill="x", padx=10, pady=10)

        self.include_charts_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame2, text="Include charts in report", variable=self.include_charts_var).grid(row=0, column=0, sticky="w", pady=2)

        self.include_analysis_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame2, text="Include agent analysis", variable=self.include_analysis_var).grid(row=1, column=0, sticky="w", pady=2)

        ttk.Label(frame2, text="Report style:").grid(row=2, column=0, sticky="w", pady=5)
        self.style_var = tk.StringVar(value="detailed")
        ttk.Combobox(frame2, textvariable=self.style_var, state="readonly",
                     values=["detailed", "summary"], width=15).grid(row=2, column=1, pady=5, padx=10, sticky="w")

        ttk.Label(frame2, text="Report language:").grid(row=3, column=0, sticky="w", pady=5)
        self.report_lang_var = tk.StringVar(value="en")
        ttk.Combobox(frame2, textvariable=self.report_lang_var, state="readonly",
                     values=["en", "es", "fr", "de", "he", "zh", "ja", "pt", "ru", "ar"], width=10).grid(row=3, column=1, pady=5, padx=10, sticky="w")

        # App options
        self.run_bg_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame2, text="Run in background when GUI is closed",
                        variable=self.run_bg_var).grid(row=4, column=0, sticky="w", pady=2)

        self.check_startup_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame2, text="Start scheduler on app launch", variable=self.check_startup_var).grid(row=5, column=0, sticky="w", pady=2)

        ttk.Label(frame2, text="Keep history (days):").grid(row=6, column=0, sticky="w", pady=5)
        self.history_days_var = tk.IntVar(value=90)
        ttk.Spinbox(frame2, from_=7, to=365, textvariable=self.history_days_var, width=10).grid(row=6, column=1, pady=5, padx=10, sticky="w")

    def _build_status_tab(self):
        tab = self.tab_status
        frame = ttk.LabelFrame(tab, text="Status & Log", padding=15)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.scheduler_status_label = ttk.Label(frame, text="Scheduler: Stopped", font=("", 11, "bold"))
        self.scheduler_status_label.pack(anchor="w", pady=(0, 10))

        self.next_check_label = ttk.Label(frame, text="Next check: -")
        self.next_check_label.pack(anchor="w", pady=(0, 10))

        self.log_text = scrolledtext.ScrolledText(frame, height=20, width=80, state="disabled")
        self.log_text.pack(fill="both", expand=True, pady=5)

        # History
        frame2 = ttk.LabelFrame(tab, text="Report History", padding=10)
        frame2.pack(fill="x", padx=10, pady=5)

        ttk.Button(frame2, text="Open History Folder", command=self._open_history).pack(side="left", padx=5)
        self.history_label = ttk.Label(frame2, text="0 reports saved")
        self.history_label.pack(side="left", padx=10)

    # --- Event handlers ---

    def _on_interval_change(self, event=None):
        itype = self.interval_var.get()
        # Show/hide "Every N" spinbox — only for custom intervals
        if itype in ("custom_days", "custom_weeks"):
            self.every_label.grid()
            self.every_spin.grid()
            self.interval_label.grid()
        else:
            self.every_label.grid_remove()
            self.every_spin.grid_remove()
            self.interval_label.grid_remove()
        # Update unit label
        if itype in ("daily", "custom_days"):
            self.interval_label.config(text="day(s)")
        elif itype in ("weekly", "custom_weeks"):
            self.interval_label.config(text="week(s)")
        # Show/hide "Day of week" — only for weekly
        if itype == "weekly":
            self.dow_label.grid()
            self.dow_combo.grid()
        else:
            self.dow_label.grid_remove()
            self.dow_combo.grid_remove()

    def _on_provider_change(self, event=None):
        provider = self.provider_var.get()
        preset = SMTP_PRESETS.get(provider, {})
        if preset.get("server"):
            self.smtp_server_var.set(preset["server"])
        self.smtp_port_var.set(preset.get("port", 587))
        self.tls_var.set(preset.get("tls", True))

    def _refresh_agents(self):
        self.agent_listbox.delete(0, tk.END)
        self.detected_agents = detect_agents()
        if not self.detected_agents:
            self.agent_listbox.insert(tk.END, "No agents detected. Install amp, claude, gemini, etc.")
            return
        for a in self.detected_agents:
            self.agent_listbox.insert(tk.END, a["display_name"] + " (" + a["path"] + ")")

    def _on_agent_select(self, event=None):
        sel = self.agent_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < len(self.detected_agents):
            agent = self.detected_agents[idx]
            self.agent_cmd_var.set(agent["command"])
            self.agent_args_var.set(", ".join(agent["prompt_args"]))

    def _check_now(self):
        self._save_config(silent=True)
        self.scheduler.reload_config()
        self.scheduler.check_now()
        self._log("Check triggered manually.")

    def _start_scheduler(self):
        self._save_config(silent=True)
        self.scheduler.reload_config()
        self.scheduler.start()
        self._update_scheduler_status()

    def _stop_scheduler(self):
        self.scheduler.stop()
        self._update_scheduler_status()

    def _test_email(self):
        self._save_config(silent=True)
        threading.Thread(target=self._send_test_email, daemon=True).start()

    def _send_test_email(self):
        self._log("Sending test email...")
        from email_handler import send_email
        html = "<html><body><h1>Test Email</h1><p>GitHub Trending Reporter is working!</p></body></html>"
        text = "Test Email - GitHub Trending Reporter is working!"
        success, msg = send_email(html, text, "Test - GitHub Trending Reporter", self.config)
        if success:
            self._log("Test email sent successfully!")
        else:
            self._log("Test email failed: " + msg)

    def _save_config(self, silent=False):
        # Gather all values from UI
        self.config["schedule"]["interval_type"] = self.interval_var.get()
        self.config["schedule"]["interval_value"] = self.interval_value_var.get()
        self.config["schedule"]["check_time"] = self.time_var.get()
        self.config["schedule"]["check_day_of_week"] = str(DAYS_OF_WEEK.index(self.dow_var.get()))

        self.config["agent"]["command"] = self.agent_cmd_var.get()
        args_str = self.agent_args_var.get().strip()
        self.config["agent"]["prompt_args"] = [a.strip() for a in args_str.split(",") if a.strip()] if args_str else []
        self.config["agent"]["timeout"] = self.agent_timeout_var.get()

        # Set agent name from detected
        for a in self.detected_agents:
            if a["command"] == self.agent_cmd_var.get():
                self.config["agent"]["name"] = a["display_name"]
                break

        self.config["email"]["provider"] = self.provider_var.get()
        self.config["email"]["smtp_server"] = self.smtp_server_var.get()
        self.config["email"]["smtp_port"] = self.smtp_port_var.get()
        self.config["email"]["use_tls"] = self.tls_var.get()
        self.config["email"]["username"] = self.email_user_var.get()
        self.config["email"]["password"] = self.email_pass_var.get()
        self.config["email"]["sender_name"] = self.sender_name_var.get()

        recipients_raw = self.recipients_text.get("1.0", tk.END).strip()
        self.config["email"]["recipients"] = [r.strip() for r in recipients_raw.split("\n") if r.strip()]

        self.config["trending"]["time_range"] = self.range_var.get()
        self.config["trending"]["language"] = self.lang_var.get().strip()
        self.config["trending"]["spoken_language"] = self.spoken_var.get().strip()

        self.config["filters"]["min_stars"] = self.min_stars_var.get()
        self.config["filters"]["min_stars_today"] = self.min_today_var.get()
        self.config["filters"]["max_repos"] = self.max_repos_var.get()
        self.config["filters"]["exclude_keywords"] = [k.strip() for k in self.exclude_kw_var.get().split(",") if k.strip()]
        self.config["filters"]["include_keywords"] = [k.strip() for k in self.include_kw_var.get().split(",") if k.strip()]

        self.config["report"]["include_charts"] = self.include_charts_var.get()
        self.config["report"]["include_agent_analysis"] = self.include_analysis_var.get()
        self.config["report"]["report_style"] = self.style_var.get()
        self.config["report"]["language"] = self.report_lang_var.get()

        self.config["app"]["run_in_background"] = self.run_bg_var.get()
        self.config["app"]["check_on_startup"] = self.check_startup_var.get()
        self.config["app"]["history_keep_days"] = self.history_days_var.get()

        errors = validate_config(self.config)
        if errors:
            if not silent:
                messagebox.showwarning("Validation", "Issues:\n" + "\n".join(errors))
            return False

        save_config(self.config)
        if not silent:
            messagebox.showinfo("Saved", "Configuration saved successfully.")
        self._log("Configuration saved.")
        return True

    def _load_config_into_ui(self):
        c = self.config
        s = c.get("schedule", {})
        self.interval_var.set(s.get("interval_type", "daily"))
        self.interval_value_var.set(s.get("interval_value", 1))
        self.time_var.set(s.get("check_time", "09:00"))
        dow_idx = int(s.get("check_day_of_week", "1"))
        self.dow_var.set(DAYS_OF_WEEK[dow_idx] if 0 <= dow_idx < 7 else "Monday")
        self._on_interval_change()

        a = c.get("agent", {})
        self.agent_cmd_var.set(a.get("command", ""))
        self.agent_args_var.set(", ".join(a.get("prompt_args", [])))
        self.agent_timeout_var.set(a.get("timeout", 300))

        e = c.get("email", {})
        self.provider_var.set(e.get("provider", "gmail"))
        self.smtp_server_var.set(e.get("smtp_server", "smtp.gmail.com"))
        self.smtp_port_var.set(e.get("smtp_port", 587))
        self.tls_var.set(e.get("use_tls", True))
        self.email_user_var.set(e.get("username", ""))
        self.email_pass_var.set(e.get("password", ""))
        self.sender_name_var.set(e.get("sender_name", "GitHub Trending Reporter"))
        self.recipients_text.delete("1.0", tk.END)
        self.recipients_text.insert("1.0", "\n".join(e.get("recipients", [])))

        t = c.get("trending", {})
        self.range_var.set(t.get("time_range", "daily"))
        self.lang_var.set(t.get("language", ""))
        self.spoken_var.set(t.get("spoken_language", ""))

        f = c.get("filters", {})
        self.min_stars_var.set(f.get("min_stars", 0))
        self.min_today_var.set(f.get("min_stars_today", 0))
        self.max_repos_var.set(f.get("max_repos", 25))
        self.exclude_kw_var.set(", ".join(f.get("exclude_keywords", [])))
        self.include_kw_var.set(", ".join(f.get("include_keywords", [])))

        r = c.get("report", {})
        self.include_charts_var.set(r.get("include_charts", True))
        self.include_analysis_var.set(r.get("include_agent_analysis", True))
        self.style_var.set(r.get("report_style", "detailed"))
        self.report_lang_var.set(r.get("language", "en"))

        app = c.get("app", {})
        self.run_bg_var.set(app.get("run_in_background", True))
        self.check_startup_var.set(app.get("check_on_startup", False))
        self.history_days_var.set(app.get("history_keep_days", 90))

        # Auto-detect agents
        self._refresh_agents()
        self._update_history_count()

    def _on_status(self, message):
        self.root.after(0, lambda: self._log(message))

    def _log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, "[" + timestamp + "] " + message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def _update_scheduler_status(self):
        if self.scheduler.is_running:
            self.scheduler_status_label.config(text="Scheduler: Running", foreground="green")
        else:
            self.scheduler_status_label.config(text="Scheduler: Stopped", foreground="red")
        nct = self.scheduler.next_check_time
        if nct:
            self.next_check_label.config(text="Next check: " + nct.strftime("%Y-%m-%d %H:%M"))
        else:
            self.next_check_label.config(text="Next check: -")

    def _open_history(self):
        import subprocess
        import sys
        hist = str(get_history_dir())
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", hist])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", hist])
            else:
                subprocess.Popen(["xdg-open", hist])
        except Exception:
            pass

    def _update_history_count(self):
        try:
            count = len(list(get_history_dir().glob("report_*.html")))
            self.history_label.config(text=str(count) + " reports saved")
        except Exception:
            pass

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()
        # Clean up tray icon if still active when mainloop exits
        self._destroy_tray()

    def _on_close(self):
        run_in_background = self.run_bg_var.get()
        if run_in_background and HAS_TRAY:
            # Save config before going to tray
            self._save_config(silent=True)
            # Start scheduler if not already running
            if not self.scheduler.is_running:
                self.scheduler.reload_config()
                self.scheduler.start()
            # Hide window, show tray icon
            self.root.withdraw()
            self._create_tray()
        else:
            # Full quit
            self._quit_app()

    def _create_tray(self):
        """Create the system tray icon."""
        if self._tray_icon is not None:
            return

        def on_show(icon, item):
            self.root.after(0, self._restore_from_tray)

        def on_check_now(icon, item):
            self.root.after(0, lambda: self.scheduler.check_now())

        def on_quit(icon, item):
            self.root.after(0, self._quit_app)

        menu = pystray.Menu(
            pystray.MenuItem("Show GUI", on_show, default=True),
            pystray.MenuItem("Check Now", on_check_now),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", on_quit),
        )

        self._tray_icon = pystray.Icon(
            "GitHubTrendsWatch",
            _create_tray_icon_image(),
            "GitHub Trends Watch",
            menu,
        )
        self._in_tray = True

        # Run tray icon in a separate thread
        threading.Thread(target=self._tray_icon.run, daemon=True).start()

    def _restore_from_tray(self):
        """Restore the GUI window from the system tray."""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self._destroy_tray()

    def _destroy_tray(self):
        """Remove the system tray icon."""
        if self._tray_icon is not None:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
            self._tray_icon = None
        self._in_tray = False

    def _quit_app(self):
        """Fully quit the application."""
        self._destroy_tray()
        if self.scheduler.is_running:
            self.scheduler.stop()
        self.root.destroy()
