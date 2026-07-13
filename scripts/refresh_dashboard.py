#!/usr/bin/env python3
"""
Daily CEE dashboard refresh.

Reads index.html, asks Claude (with web search enabled) to update it with the
latest CEE economic and political news, and writes the result back to index.html.

Requires the ANTHROPIC_API_KEY environment variable (set as a GitHub secret).
"""

import os
import re
import sys
import json
import datetime
import requests

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-opus-4-8"
DASHBOARD_PATH = "index.html"

# How hard Claude is allowed to work: web search rounds and output size.
MAX_SEARCHES = 25
MAX_TOKENS = 32000

TODAY = datetime.date.today().isoformat()

# The standing instruction — the accumulated "house style" for this dashboard.
INSTRUCTIONS = f"""You maintain a single-file HTML dashboard called "CEE Pulse" that tracks
economic and political news for six Central/Eastern European countries: Czechia, Hungary,
Poland, Romania, Bulgaria, and Slovakia. Today is {TODAY}.

I will give you the CURRENT contents of index.html. Your job: return the COMPLETE, updated
index.html and nothing else.

Update rules — follow all of them:

1. SEARCH FIRST. Use web search to find genuinely new developments since the dates already
   on the page: policy-rate decisions, inflation prints, GDP/retail/industrial/construction/
   housing data, fiscal news, FX moves, and political events with economic impact. Prefer
   primary sources (central banks, statistics offices) and local-language press; you may cite
   an English source alongside an original-language one.

2. PRESERVE STRUCTURE EXACTLY. Keep the existing HTML structure, CSS, filter buttons, and
   JavaScript intact. Only change content inside the news cards, the rate ticker, the
   quickstats lines, the regional themes, the political section, and the fact-check.

3. EACH news item is a <div class="story" data-cat="..." data-date="YYYY-MM-DD" data-age="N">.
   - data-cat must be one of: rates, inflation, growth, fiscal, fx, retail, industry,
     construction, housing, political.
   - data-date is the item's source date. data-age is (today − data-date) in whole days.
   - RECOMPUTE data-age for EVERY item relative to today ({TODAY}), so the week/month time
     filter stays accurate. This is important — stale ages break the filter.

4. NEWEST FIRST. Within each country card, order items newest-first by data-date.

5. POLITICAL SECTION = last 30 days. Keep the six country political items focused on
   developments within the last ~30 days; replace anything that has aged out with something current.

6. FACT-CHECK = conflicting accounts. Keep the fact-check section focused on events where
   sources genuinely disagree (competing versions side by side, each sourced, with a dated
   "where it stands"). Refresh it if the conflicts have moved. Keep the separate
   "Corrections made to this dashboard" list, adding any correction you make this run.

7. VERIFY, DON'T INVENT. Never fabricate a figure or a source. If you cannot confirm a
   specific number against a real source, use a cautious phrasing rather than false precision.
   Update the header date to {TODAY} and add a one-paragraph refresh-log entry (dated {TODAY})
   at the top of the log in the footer describing what changed.

8. OUTPUT. Return ONLY the full updated HTML document, starting with <!DOCTYPE html> and
   ending with </html>. Do not wrap it in markdown fences. Do not add commentary before or
   after it."""


def read_dashboard():
    if not os.path.exists(DASHBOARD_PATH):
        sys.exit(f"ERROR: {DASHBOARD_PATH} not found in repository root.")
    with open(DASHBOARD_PATH, "r", encoding="utf-8") as f:
        return f.read()


def call_claude(current_html):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ERROR: ANTHROPIC_API_KEY is not set. Add it as a repository secret.")

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": INSTRUCTIONS,
        "tools": [
            {"type": "web_search_20250305", "name": "web_search", "max_uses": MAX_SEARCHES}
        ],
        "messages": [
            {
                "role": "user",
                "content": (
                    "Here is the current index.html. Refresh it per your instructions and "
                    "return the complete updated file:\n\n" + current_html
                ),
            }
        ],
    }

    resp = requests.post(API_URL, headers=headers, json=payload, timeout=1200)
    if resp.status_code != 200:
        sys.exit(f"ERROR: API returned {resp.status_code}: {resp.text[:2000]}")

    data = resp.json()
    # Concatenate all text blocks (skip web_search tool blocks).
    text = "".join(
        block.get("text", "")
        for block in data.get("content", [])
        if block.get("type") == "text"
    )
    return text.strip()


def extract_html(text):
    """Pull the HTML document out of the model's reply, tolerating stray fences/preamble."""
    # Strip markdown fences if the model added them despite instructions.
    text = re.sub(r"^```(?:html)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text.strip())
    start = text.find("<!DOCTYPE html>")
    end = text.rfind("</html>")
    if start == -1 or end == -1:
        sys.exit("ERROR: Model reply did not contain a complete HTML document; leaving file unchanged.")
    return text[start : end + len("</html>")]


def sanity_check(html):
    """Cheap guardrails so a malformed reply can't overwrite a good dashboard."""
    problems = []
    if len(html) < 10000:
        problems.append(f"suspiciously short ({len(html)} chars)")
    if html.count("<div") != html.count("</div>"):
        problems.append(f"unbalanced divs ({html.count('<div')} open / {html.count('</div>')} close)")
    for needle in ('id="filterBar"', 'class="news-card"', "</html>"):
        if needle not in html:
            problems.append(f"missing expected marker: {needle}")
    if problems:
        sys.exit("ERROR: refreshed HTML failed sanity checks: " + "; ".join(problems))


def main():
    current = read_dashboard()
    print(f"Read {len(current)} chars from {DASHBOARD_PATH}. Asking Claude to refresh…")
    reply = call_claude(current)
    html = extract_html(reply)
    sanity_check(html)
    with open(DASHBOARD_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {len(html)} chars back to {DASHBOARD_PATH}. Done.")


if __name__ == "__main__":
    main()
