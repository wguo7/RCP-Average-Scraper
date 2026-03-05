"""
RCP Trump Approval Rating Scraper (v5)
---------------------------------------
The chart has ONE tooltip that moves and updates text as you hover.
We use a MutationObserver to capture every text change in real-time
as we sweep the mouse across the chart.

Requirements:
    pip install playwright
    playwright install chromium

Usage:
    python rcp_scraper.py
"""

from playwright.sync_api import sync_playwright
import csv
import time


URL = "https://www.realclearpolling.com/polls/approval/donald-trump/approval-rating"
OUTPUT_FILE = "rcp_trump_approval.csv"


def scrape_approval_data():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        print(f"Loading {URL}...")
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_selector("#screenshot_line_chart", timeout=15000)
        time.sleep(3)

        # scroll chart into view
        page.evaluate("""
        () => {
            const chart = document.querySelector('#screenshot_line_chart');
            if (chart) chart.scrollIntoView({ block: 'center' });
        }
        """)
        time.sleep(1)

        # click MAX
        print("Clicking MAX...")
        page.evaluate("""
        () => {
            const all = document.querySelectorAll('button, span, div, a');
            for (const el of all) {
                if (el.textContent.trim() === 'MAX') { el.click(); return; }
            }
        }
        """)
        time.sleep(5)

        # re-scroll after reload
        page.evaluate("""
        () => {
            const chart = document.querySelector('#screenshot_line_chart');
            if (chart) chart.scrollIntoView({ block: 'center' });
        }
        """)
        time.sleep(1)

        # get chart bounding box (largest svg)
        chart_box = page.evaluate("""
        () => {
            const svgs = document.querySelectorAll('#screenshot_line_chart svg');
            let best = null;
            let bestArea = 0;
            for (const svg of svgs) {
                const rect = svg.getBoundingClientRect();
                if (rect.width * rect.height > bestArea && rect.width > 200) {
                    bestArea = rect.width * rect.height;
                    best = { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
                }
            }
            return best;
        }
        """)
        print(f"Chart: {chart_box['width']:.0f}x{chart_box['height']:.0f} at ({chart_box['x']:.0f}, {chart_box['y']:.0f})")

        # ---------- set up MutationObserver to capture tooltip changes ----------
        print("Setting up MutationObserver...")
        page.evaluate("""
        () => {
            // global array to store captured data points
            window.__rcp_captured = [];

            const container = document.querySelector('#screenshot_line_chart');
            if (!container) return;

            // watch for ANY text/attribute changes inside the chart
            const observer = new MutationObserver((mutations) => {
                // read current tooltip state
                const dateEl = container.querySelector('.tooltip-top-date-object');
                const approveEl = container.querySelector('.circle_tooltip[class*="approve"]:not([class*="disapprove"]) .candidate-vote-value');
                const disapproveEl = container.querySelector('.circle_tooltip[class*="disapprove"] .candidate-vote-value');

                const date = dateEl ? dateEl.textContent.trim() : null;
                const approve = approveEl ? approveEl.textContent.trim() : null;
                const disapprove = disapproveEl ? disapproveEl.textContent.trim() : null;

                if (date && approve) {
                    const last = window.__rcp_captured[window.__rcp_captured.length - 1];
                    // only add if different from last captured
                    if (!last || last.date !== date || last.approve !== approve) {
                        window.__rcp_captured.push({ date, approve, disapprove });
                    }
                }
            });

            observer.observe(container, {
                childList: true,
                subtree: true,
                characterData: true,
                attributes: true,
                attributeFilter: ['transform', 'opacity', 'style']
            });

            window.__rcp_observer = observer;
        }
        """)

        # ---------- sweep mouse across chart ----------
        start_x = int(chart_box['x']) + 5
        end_x = int(chart_box['x'] + chart_box['width']) - 5
        hover_y = int(chart_box['y'] + chart_box['height'] * 0.4)
        step = 1  # every single pixel for max granularity

        total_steps = (end_x - start_x) // step
        print(f"Sweeping mouse across {total_steps} pixels (x={start_x} to x={end_x})...")
        print("This may take a minute...")

        for i, x in enumerate(range(start_x, end_x, step)):
            page.mouse.move(x, hover_y)
            # tiny pause every few pixels to let JS update
            if i % 3 == 0:
                time.sleep(0.01)
            if i % 200 == 0:
                count = page.evaluate("() => window.__rcp_captured ? window.__rcp_captured.length : 0")
                pct = (i / max(total_steps, 1)) * 100
                print(f"  {pct:.0f}% — {count} points captured", end='\r')

        # final pause
        time.sleep(0.5)

        # ---------- collect results ----------
        results = page.evaluate("() => window.__rcp_captured || []")

        # stop observer
        page.evaluate("""
        () => {
            if (window.__rcp_observer) window.__rcp_observer.disconnect();
        }
        """)

        print(f"\n  Done! Captured {len(results)} data points.")

        # deduplicate by date
        seen = set()
        deduped = []
        for r in results:
            if r['date'] not in seen:
                seen.add(r['date'])
                deduped.append(r)

        print(f"  After dedup: {len(deduped)} unique dates.")

        # ---------- save csv ----------
        if deduped:
            with open(OUTPUT_FILE, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['date', 'approve', 'disapprove'])
                writer.writeheader()
                writer.writerows(deduped)
            print(f"\nSaved to {OUTPUT_FILE}")
            print("\nFirst 10:")
            for r in deduped[:10]:
                print(f"  {r['date']:>15}  Approve: {str(r['approve']):>6}  Disapprove: {str(r['disapprove']):>6}")
            print(f"\nLast 5:")
            for r in deduped[-5:]:
                print(f"  {r['date']:>15}  Approve: {str(r['approve']):>6}  Disapprove: {str(r['disapprove']):>6}")

            # quick sanity check: are values actually varying?
            unique_approves = set(r['approve'] for r in deduped if r['approve'])
            print(f"\nUnique approve values: {len(unique_approves)}")
            if len(unique_approves) <= 5:
                print(f"  Values: {unique_approves}")
            else:
                print(f"  Sample: {list(unique_approves)[:10]}")
        else:
            print("\nNo data captured.")

        input("\nPress Enter to close browser...")
        browser.close()

    return deduped


if __name__ == "__main__":
    scrape_approval_data()