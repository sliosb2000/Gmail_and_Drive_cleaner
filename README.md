# Gmail Triage

A small CLI to summarize your inbox and apply rule-based cleanup (archive,
trash, label) using Gmail search queries.

## 1. Create OAuth credentials (one-time, in your own browser)

This tool authorizes using Google's **device-code flow**, since it runs
headless. That requires an OAuth client of type **"TVs and Limited Input
devices"**:

1. Go to https://console.cloud.google.com/ and create a project (or pick an
   existing one).
2. Enable the **Gmail API**: APIs & Services -> Library -> search "Gmail API"
   -> Enable.
3. Configure the **OAuth consent screen** (APIs & Services -> OAuth consent
   screen): choose "External", fill in the required fields, and add your own
   Gmail address under **Test users**. Leave the app in "Testing" mode — this
   avoids Google's app-verification process and works fine for personal use
   (you'll see an "unverified app" warning when authorizing; that's expected).
4. Create credentials (APIs & Services -> Credentials -> Create Credentials ->
   OAuth client ID) with application type **"TVs and Limited Input devices"**.
5. Download the JSON and save it as `credentials.json` in this directory.
   **Never commit this file** — it's already in `.gitignore`.

## 2. Install dependencies

```
pip install -r requirements.txt
```

## 3. Authorize

```
python auth.py
```

This prints a URL and a short code. Open the URL on any device, sign in, and
enter the code. A `token.json` is saved locally (also gitignored) — this is
what actually grants access to your mailbox, so treat it like a password.

## 4. See what's in your inbox

```
python triage.py report
```

Shows message counts per category (Promotions, Social, Updates, Forums) and
your top senders.

## 5. Review and run triage rules

Rules live in `rules.yaml` — each one is a Gmail search query (same syntax as
the Gmail search box) plus an action (`archive`, `trash`, or
`add_label:SomeName`).

```
python triage.py run           # dry-run: shows what would happen
python triage.py run --apply   # actually applies enabled rules
```

Edit `rules.yaml` to change what gets matched or acted on. Everything is
dry-run by default — nothing touches your mailbox until you pass `--apply`.
