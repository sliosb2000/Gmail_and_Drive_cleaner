# PRD — Photos Cleaner: a web app to free up Google Photos storage

**Status:** Draft v2 (post over-engineering review: single ingestion mode, single architecture)
**Author:** Claude (with sliosb2000)
**Date:** 2026-08-03
**Related:** Gmail triage CLI (this repo) — same "review fast, act in bulk" philosophy.

---

## 1. Problem

Google account storage (15 GB shared across Gmail, Drive, and Photos) fills up,
and Photos is usually the biggest consumer. Cleaning it manually in the Google
Photos UI is painfully slow: duplicates are hard to spot, there's no way to
sort by "what's eating the most space", and triage decisions (keep / delete /
print / archive) must be made one photo at a time with no memory of past
decisions.

**Goal:** let the user reclaim the maximum storage in the minimum time, by
turning photo cleanup into a fast triage session with smart grouping
(duplicates, themes, time periods) and clear "storage saved" feedback.

## 2. Goals

1. Surface the highest-impact cleanup opportunities first (duplicates, blurry
   shots, screenshots, huge videos, burst series).
2. Let the user triage photos into five buckets — **Delete**, **Print**,
   **Save special**, **Friends**, **Others** — with single-keystroke /
   single-swipe speed.
3. Show a running **storage saved** counter (exact bytes reclaimed) as
   motivation and progress feedback.
4. Make app launch feel instant (< 1 s to interactive on repeat visits).
5. Persist all triage decisions so a session can be interrupted and resumed
   without re-reviewing anything.

## 3. Non-goals

- Not a photo editor, backup tool, or gallery replacement.
- No automatic deletion of anything, ever. The user always performs the final
  destructive action themselves (see §5, Constraints).
- No face recognition / ML identity features in v1 ("Friends" is a manual
  bucket, not auto-detected people).
- No mobile native app; responsive web page served by the local app.
- No Google API integration in v1. The Photos Library API cannot delete media
  and (since the March 2025 changes) cannot even read the user's library; the
  Picker API would add OAuth + a second ingestion pipeline that yields worse
  data (no exact sizes, no content hashes) than a Takeout export. Revisit only
  if Takeout friction proves real.

## 4. Users

Single-user personal tool (the repo owner). One Google account.

## 5. Hard constraints

- **The API cannot delete photos or sort existing photos into albums** — so
  the five buckets are virtual folders inside the app, and the final delete is
  always performed manually by the user on their phone (§7.5).
- **Ingestion = Google Takeout.** The user downloads a Takeout export of their
  Photos library (zip + per-photo JSON metadata); the app indexes it locally.
  No API restrictions, exact byte sizes, content-hash duplicate detection.
  Cost: a Takeout export takes Google minutes-to-hours to prepare — the app's
  onboarding screen explains the wait once.

## 6. User experience principles

- **Speed over completeness at launch.** Usable within ~1 second on a repeat
  visit: render the cached index and last session state immediately. First
  visit shows a guided "ingest your Takeout" flow, never a blank screen.
- **One decision per screen-second.** Triage is a full-screen, one-photo (or
  one-group) at a time flow driven by keyboard (1–5 / arrow keys) and swipe
  gestures. Target sustained pace: ≥ 30 decisions/minute on singles, much
  higher on group actions.
- **Bulk first.** Duplicates and burst series are triaged as *groups* ("keep
  best, mark rest for deletion" is one action, not N).
- **Everything undoable inside the app.** Decisions are app-side labels until
  the user executes them (§7.5); an Undo stack and a per-bucket review grid
  let the user reverse anything before acting.
- **No decision is ever lost.** Every triage action is durably persisted the
  instant it's made (§7.6). Closing the tab, a browser crash, a phone dying
  mid-swipe — none of it loses more than the single in-flight decision, and
  the app resumes exactly where the user left off.

## 7. Features

### 7.1 Ingestion & indexing
- Ingest a Takeout archive: drag-and-drop the zip(s) or point at an unzipped
  folder; the local server stream-parses it (multi-GB safe), reads the
  per-photo JSON sidecars, computes content hashes, generates thumbnails.
- Index stores: media id, filename, timestamp, dimensions, duration, mime
  type, exact size, thumbnail, hash, triage state.

### 7.2 Smart grouping & filters (the "find the fat" layer)
Priority-ordered cleanup lanes shown on the home dashboard, each with its
exact reclaimable size:

1. **Exact duplicates** — identical content hash; "keep one, stage the rest"
   proposed automatically.
2. **Near-duplicates / bursts** — perceptual-hash clusters and < 3 s timestamp
   bursts; UI proposes "best of group" (sharpest/largest) automatically.
3. **Videos by size** — largest first; video is where the gigabytes are.
4. **Screenshots & no-camera-EXIF images** — screenshots, WhatsApp/downloaded
   images, memes; detected via filename/path/dimensions/EXIF patterns.
5. **By date** — year, month, or auto-detected "event" clusters (gaps in
   timestamps), oldest-first or largest-first.

### 7.3 Triage flow (the core loop)
- Full-screen card: photo/video preview, size, date, group context
  ("duplicate 2 of 5").
- Five buckets + skip:
  - **1 · Delete** — stage for removal
  - **2 · Print** — shortlist for physical printing
  - **3 · Save special** — the precious ones
  - **4 · Friends** — to share/send to friends
  - **5 · Others** — everything that needs a later look
  - **Space/→ · Skip** — decide later, resurfaces at end of lane
- Keyboard, click, and swipe (mobile) mappings for all six actions.
- Group cards for duplicate/burst clusters: one action applies to the whole
  group with the auto-picked "best" exempted (overridable).
- Session stats bar: photos triaged and **storage staged for deletion** live
  counter.

### 7.4 Dashboard
- Total indexed, total triaged, per-bucket counts and sizes.
- **Storage saved to date** (executed deletions) and **storage staged**
  (pending in Delete bucket) — the headline numbers.
- Cleanup lanes (§7.2) with per-lane progress and remaining gain.
- Resume button → drops straight into the next undecided item (< 1 s).

### 7.5 Acting on buckets (assisted-manual execution)
The final destructive step is always performed **by the user, manually, on
their phone** in the Google Photos app (§5). The web app's job is to make
that phone session as short and mechanical as possible:

- **Delete bucket → phone deletion checklist:** the app renders the staged
  items as a mobile-friendly checklist (thumbnail, date, filename), ordered to
  match Google Photos' own timeline so the user can walk both apps in
  parallel. Each item has a **deep link that opens it directly in the Google
  Photos app** on the phone — tap link, tap delete, back, check it off, next.
  Checked-off items move to the "saved" tally. The checklist survives
  interruption (§7.6): the user can delete 40 photos on the bus, close
  everything, and pick up at item 41 that evening.
- A filename/date manifest export is also available for batch
  search-and-delete on desktop.
- **Print / Save special / Friends / Others:** export as a zip (files are
  local from the Takeout) and/or a manifest — e.g. the Print zip goes straight
  to a print service.

### 7.6 Crash-safe decision persistence (durability requirements)

Triage sessions will be interrupted constantly — tab closed, browser killed,
phone locked mid-swipe, battery dies. The design treats interruption as the
normal case, not the exception:

- **Write-per-decision, not write-per-session.** Each triage action (bucket
  assignment, skip, undo, checklist tick) is committed to IndexedDB in its own
  transaction *before* the UI advances to the next card. No batching, no
  "save on exit", no debounce longer than the decision itself.
- **At most one in-flight decision at risk.** If the app dies between the
  user's tap and the commit, only that single decision is lost; on relaunch
  the same card is shown again. Nothing already committed is ever re-asked.
- **Deterministic resume.** Session state (current lane, position, filters,
  undo stack) is persisted alongside decisions; relaunch restores the exact
  card the user was on.
- **Storage resilience:** request `navigator.storage.persist()` so the browser
  won't evict the index under storage pressure; detect eviction on launch
  (index version marker) and fail loud with a re-ingest prompt rather than
  silently starting over.
- **Export/import of the decision ledger** (single JSON file) as a
  user-controlled backup and a migration path between browsers/devices.
- **Execution ticks are decisions too:** the phone deletion checklist (§7.5)
  uses the same per-action commit path, so progress through a 500-item delete
  session is never lost.

### 7.7 Fast-launch engineering requirements
- Index + decisions in IndexedDB; virtualized grids (no 10k-DOM-node lists).
- Skeleton UI < 200 ms, interactive < 1 s (repeat visit).
- Heavy work (hashing, perceptual hashing, EXIF parse) happens in the local
  server during ingestion — the browser UI never blocks on it.

## 8. Architecture

One local app, mirroring how the Gmail CLI in this repo runs:

- **Local Python server** (reuse this repo's patterns): stream-parses Takeout
  zips, computes hashes, serves thumbnails and one web page.
- **One web page** (plain TS/JS, IndexedDB for decisions): the triage UI,
  also opened from the phone over the LAN for the deletion checklist.
- **No accounts, no OAuth, no deploy** — everything stays on the user's
  machine; the Takeout folder itself is gitignored.

## 9. Success metrics

| Metric | Target |
|---|---|
| Time from launch (repeat visit) to first triage decision | < 3 s |
| Sustained triage pace, single photos | ≥ 30 decisions/min |
| Duplicate-lane precision (staged pairs that are truly duplicates) | ≥ 99% |
| Storage reclaimed in first full session | user-visible GB counter; qualitative "felt worth it" |
| Re-review rate (items triaged twice) | ~0 — decisions must persist |
| Decisions lost on unexpected app stop (crash/tab-kill/battery) | ≤ 1 (only the in-flight one) |

## 10. Risks & open questions

1. **Deletion friction** — the phone deletion checklist is the weakest UX
   point; needs prototyping early. Deep-link behavior differs across
   Android/iOS and Photos app versions (per-item links may open the app but
   not always the exact photo), so the checklist must degrade gracefully to
   timeline-ordered manual lookup. *Prototype on a real phone in milestone 1.*
2. **Takeout friction** — the export takes Google minutes-to-hours to prepare
   and re-ingesting is the only way to refresh. Acceptable for a periodic
   cleanup tool; revisit (Picker API) only if it proves not to be.
3. **Thumbnail/index disk size** — a full-library index takes real disk
   space; thumbnails live on the server's disk, only decisions in the browser.
4. Open: should "Friends" support per-friend sub-buckets in v1? (Proposed: no
   — keep the loop to 5 buckets for speed.)

## 11. Milestones

1. **M1 — Spike (a day):** deep-link deletion loop prototyped on a real
   phone. Validates the single riskiest assumption before any UI is built.
2. **M2 — Core loop:** Takeout ingest + index, triage screen with
   keyboard/swipe, buckets, persistence, dashboard with storage counters.
3. **M3 — Smart lanes:** duplicates (hash + perceptual), bursts, size-sorted
   videos, screenshots, date clusters.
4. **M4 — Execution flows:** phone deletion checklist, print/export zips and
   manifests; perf hardening to hit launch-speed targets.
