"""GitHub Trending Reporter - Entry point.

Usage:
    python main.py              # Launch GUI
    python main.py --gui        # Launch GUI
    python main.py --background # Run scheduler in background (no GUI)
    python main.py --check-now  # Run a single check immediately and exit
"""

import argparse
import logging
import sys
import os

# Ensure local imports work regardless of CWD
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_manager import load_config, ensure_dirs


def setup_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )


def run_gui():
    """Launch the tkinter configuration GUI."""
    from gui import TrendingReporterGUI
    app = TrendingReporterGUI()
    app.run()


def run_background():
    """Run the scheduler in background mode without GUI."""
    from scheduler import TrendingScheduler
    import time

    config = load_config()
    scheduler = TrendingScheduler(config)
    scheduler.start()

    print("GitHub Trending Reporter running in background mode.")
    print("Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\nStopping...")
        scheduler.stop()
        print("Stopped.")


def run_check_now():
    """Run a single check immediately and exit."""
    from scheduler import TrendingScheduler
    import time

    config = load_config()
    scheduler = TrendingScheduler(config)

    # Run check synchronously
    scheduler._do_check()
    result = scheduler.last_result

    if result:
        if result.get("success"):
            print("Check completed: " + result.get("message", ""))
            sys.exit(0)
        else:
            print("Check failed: " + result.get("message", ""))
            sys.exit(1)
    else:
        print("No result returned.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="GitHub Trending Reporter")
    parser.add_argument("--gui", action="store_true", help="Launch the GUI (default)")
    parser.add_argument("--background", action="store_true", help="Run scheduler in background")
    parser.add_argument("--check-now", action="store_true", help="Run a single check and exit")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    setup_logging(args.verbose)
    ensure_dirs()

    if args.check_now:
        run_check_now()
    elif args.background:
        run_background()
    else:
        run_gui()


if __name__ == "__main__":
    main()
