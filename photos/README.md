# Photos Cleaner — M1 spike

Tests the PRD's riskiest assumption (docs/PRD-photos-cleaner.md §10.1):
can a web checklist deep-link into the Google Photos app on a phone,
landing on the exact photo, so deleting is ~one tap per item?

## Test protocol

1. Put a few `https://photos.google.com/photo/...` URLs in `urls.txt`
   (one per line). Get them by opening any photo at photos.google.com
   and copying the address — or later, from Takeout metadata's `url` field.
2. `python m1_checklist.py` → writes `checklist.html`.
3. Open `checklist.html` on the phone (any way you like — email it to
   yourself, host it, airdrop it).
4. Tap each link. Record what happens:
   - Opens the Google Photos **app on the exact photo** → best case, PRD holds.
   - Opens photos.google.com **in the browser** on the photo → acceptable
     (browser has a delete button too).
   - Opens the app/site but **not** the photo → checklist must fall back to
     timeline-ordered manual lookup; PRD §7.5 degrades.
5. Ticks persist in localStorage — close the page mid-list and reopen to
   verify resume works.

## Verdict

_Record test results here._
