# CEE Dashboard — daily auto-refresh setup

This makes GitHub call Claude once a day to refresh your dashboard automatically, then
publish it. After a one-time setup (~15 minutes, no coding), you don't have to do anything.

## What you'll end up with

- Every morning, GitHub runs a job on its own servers.
- The job asks Claude (via the Anthropic API, with web search) to update `index.html`.
- If anything changed, GitHub commits the new file and your site updates itself.
- You can also trigger it any time with a "Run workflow" button.

## What you need

- Your existing GitHub repo with `index.html` in it.
- An Anthropic API key (a few clicks — see step 2). This is the only thing that costs money,
  and a once-daily refresh is small (typically well under a euro a month, often just cents,
  depending on how much searching each run does).

---

## Step 1 — Add these files to your repo

Put these three files into your repository, keeping the exact folder paths:

```
.github/workflows/daily-refresh.yml
scripts/refresh_dashboard.py
```

(Your `index.html` stays where it already is, in the repo root.)

The easiest no-terminal way: on GitHub, click **Add file → Create new file**, type the full
path including the slashes (e.g. `.github/workflows/daily-refresh.yml`) into the name box —
GitHub turns the slashes into folders automatically — paste the contents, and commit. Repeat
for the script.

## Step 2 — Get an Anthropic API key

1. Go to https://console.anthropic.com and sign in (or create an account).
2. Add a small amount of credit (billing settings) — a few dollars lasts a long time here.
3. Create an API key and copy it. You'll paste it once in the next step and never need it again.

## Step 3 — Store the key in your repo (as a secret, not in the code)

1. In your repo, go to **Settings → Secrets and variables → Actions**.
2. Click **New repository secret**.
3. Name it exactly: `ANTHROPIC_API_KEY`
4. Paste your key into the value box and save.

The key is stored encrypted and is never visible in the code or the logs.

## Step 4 — Turn it on and test it

1. Go to the **Actions** tab of your repo. If prompted, enable Actions.
2. Pick **Daily CEE dashboard refresh** on the left.
3. Click **Run workflow** (the manual button) to test it right now instead of waiting for tomorrow.
4. Watch it run. When it finishes green, check `index.html` — it should have today's date and
   a fresh refresh-log entry. Your published site updates within a minute or two.

That's it. From now on it runs by itself once a day.

---

## Adjusting things

- **Change the time:** edit the `cron:` line in `daily-refresh.yml`. It's in UTC.
  `"15 6 * * *"` means 06:15 UTC. For example, 07:00 Central European Time in winter is `0 6 * * *`.
- **Change how much it searches / how long it can get:** edit `MAX_SEARCHES` and `MAX_TOKENS`
  near the top of `refresh_dashboard.py`.
- **Change what it focuses on:** edit the `INSTRUCTIONS` text in `refresh_dashboard.py`. That
  block is the standing prompt — the dashboard's "house style." Adjust it the way you'd ask
  in chat.

## Safety built in

The script won't overwrite your dashboard with a broken file: before saving, it checks the
result is a complete HTML document of reasonable size, has balanced tags, and still contains
the filter bar and news cards. If Claude's reply fails those checks, the run stops and your
existing `index.html` is left untouched.

## If a run fails

- **Red run in the Actions tab:** click it to read the error. The most common causes are a
  missing or mistyped `ANTHROPIC_API_KEY` secret, or no credit on the Anthropic account.
- **It ran but committed nothing:** that's normal on a slow news day — it only commits when
  something actually changed.
- **Scheduled runs are late:** GitHub's free cron can be delayed from a few minutes up to about
  an hour at busy times. Use the manual **Run workflow** button if you need it immediately.

## A note on trust

This automation removes the human review step you've been doing. The dashboard's own
fact-check and verification-log discipline becomes more important, not less, when nobody is
eyeballing each refresh. It's worth opening the site every few days to spot-check — especially
the numbers for Romania and Bulgaria, where sourcing is thinnest.
