#!/usr/bin/env python3
"""
Trigger a comprehensive multi-city, multi-market scraping session.
This wrapper avoids shell quoting issues.
"""

import os
import sys

from scraper.comprehensive_multi_city_scraper import scrape_comprehensive_multi_city


def main() -> None:
    # Force UTF-8 to avoid Windows console encoding issues
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"

    scrape_comprehensive_multi_city()


if __name__ == "__main__":
    main()


