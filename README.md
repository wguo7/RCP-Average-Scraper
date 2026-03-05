# RCP-Average-Scraper

A Python scraper that extracts historical presidential approval/disapproval polling averages from [RealClearPolling](https://www.realclearpolling.com/polls/approval/donald-trump/approval-rating).

## Overview

RealClearPolling does not expose a public API for its polling average time series. This tool uses Playwright to load the interactive chart, intercept JSON API responses, and extract daily approve/disapprove values into a clean CSV for downstream analysis.

## Requirements

- Python 3.9+
- Playwright

```bash
pip install playwright
playwright install chromium
```

## Usage

```bash
python rcp_scraper.py
```

Outputs `rcp_trump_approval.csv` with columns:

| date | approve | disapprove |
|------|---------|------------|
| 27-Jan-25 | 47.10% | 49.80% |
| 28-Jan-25 | 47.20% | 49.70% |
| ... | ... | ... |

## How It Works

1. Launches a headless Chromium browser via Playwright
2. Navigates to the RealClearPolling approval rating page
3. Intercepts JSON network responses containing polling data
4. Falls back to DOM extraction from the chart's JavaScript data stores if API interception fails
5. Deduplicates by date and writes results to CSV

## Use Case

Built to support research on prediction market efficiency, specifically comparing Kalshi approval rating contract prices against RCP polling averages using difference-in-differences and jump detection methods.
