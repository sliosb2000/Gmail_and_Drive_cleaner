# PRD — Photos Cleaner: a web app to free up Google Photos storage

**Status:** Draft v1
**Author:** Claude (with sliosb2000)
**Date:** 2026-08-02
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
turning photo cleanup into a fast, gamified triage session with smart grouping
(duplicates, themes, time periods) and clear "storage saved" feedback.

## 2. Goals

1. Surface the highest-impact cleanup opportunities first (duplicates, blurry
   shots, screenshots, huge videos, burst series).
2. Let the user triage photos into five buckets — **Delete**, **Print**,
   **Save special**, **Friends**, **Others** — with single-keystroke /
   single-swipe speed.
3. Show a running **storage saved** counter (estimated MB/GB reclaimed) as
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
- No mobile native app; responsive web (PWA-installable) only.

## 4. Users

Single-user personal tool (initially: the repo owner). One Google account at a
time. No multi-tenant concerns in v1, but nothing in the design should
preclude adding them later.

## 5. Hard constraints — Google Photos API reality (design-critical)

These constraints define the architecture. The PRD is written around them
rather than pretending they don't exist:

| Constraint | Consequence |
|---|---|
| The Photos Library API **cannot delete** media items, and since the **March 2025 API changes** third-party apps can no longer even list/read the user's full library (`photoslibrary.readonly` and related scopes were removed; only app-created data scopes remain). | The app cannot silently scan or clean the library server-side. |
| The **Google Photos Picker API** is the sanctioned way to access user photos: the user selects photos/albums in a Google-rendered picker, and the app receives access to the selected items (metadata + download URLs). | Ingestion is user-initiated and batch-based: "pick everything from 2019", "pick the Screenshots search results", etc. |
| Albums created via API can only contain media **uploaded by the app** — the app cannot sort the user's existing photos into new Google Photos albums. | The five buckets are **virtual folders inside our app**, not real Google Photos albums. Acting on them is an assisted-manual flow (see §7.5). |
| A **Google Takeout export** (zip of the full library incl. metadata JSON) has no API restrictions once downloaded. | Offered as the "power mode" ingestion path for full-library analysis, incl. exact file sizes and reliable duplicate detection by hash. |

**Two ingestion modes, one review UX:**

- **Mode A — Picker (default, zero-friction):** user picks batches via the
  Google Photos Picker; app analyzes what was picked. Good for incremental
  cleanup. Limitation: file size is not always exposed → storage-saved figures
  are estimates from resolution/duration heuristics.
- **Mode B — Takeout (power mode):** user uploads/points the app at a Takeout
  export; app indexes everything locally with exact byte sizes and
  content-hash duplicate detection. Best results, more setup.

## 6. User experience principles

- **Speed over completeness at launch.** The app must be usable within ~1
  second on a repeat visit: render the cached index and last session state
  immediately; refresh in the background. First visit shows a guided "pick
  your first batch" flow, never a blank screen.
- **One decision per screen-second.** Triage is a full-screen, one-photo (or
  one-group) at a time flow driven by keyboard (1–5 / arrow keys) and swipe
  gestures. Target sustained pace: ≥ 30 decisions/minute on singles, much
  higher on group actions.
- **Bulk first.** Duplicates and burst series are triaged as *groups* ("keep
  best, mark rest for deletion" is one action, not N).
- **Everything undoable inside the app.** Decisions are app-side labels until
  the user executes them (§7.5); an Undo stack and a per-bucket review grid
  let the user reverse anything before acting.

## 7. Features

### 7.1 Ingestion & indexing
- Google OAuth sign-in (reusing this repo's manual-loopback flow patterns
  where applicable).
- Mode A: launch Google Photos Picker, receive selected items, fetch metadata
  + thumbnails, store in local index (IndexedDB in-browser; optional SQLite if
  we add a small local backend).
- Mode B: ingest a Takeout archive (drag-and-drop the zip or point at an
  unzipped folder), parse the per-photo JSON sidecars, compute content hashes.
- Index stores: media id, filename, timestamp, dimensions, duration, mime
  type, exact or estimated size, thumbnail (cached blob), hash (Mode B),
  triage state.

### 7.2 Smart grouping & filters (the "find the fat" layer)
Priority-ordered cleanup lanes shown on the home dashboard, each with an
estimated reclaimable size:

1. **Exact duplicates** — identical content hash (Mode B) or same
   name+timestamp+dimensions heuristic (Mode A).
2. **Near-duplicates / bursts** — perceptual-hash clusters and < 3 s timestamp
   bursts; UI proposes "best of group" (sharpest/largest) automatically.
3. **Videos by size** — largest first; video is where the gigabytes are.
4. **Screenshots & WhatsApp/downloaded images** — detected via
   filename/path/dimensions patterns.
5. **Temporal filters** — by year, month, or auto-detected "event" clusters
   (gaps in timestamps), oldest-first or largest-first.
6. **Thematic filters (v1 = heuristic, not ML):** screenshots, memes/images
   with no EXIF camera data, very short videos, very old photos. (ML topic
   clustering is a v2 candidate, on-device only.)

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
- Session stats bar: photos triaged, decisions/min, **storage staged for
  deletion** live counter.

### 7.4 Dashboard
- Total indexed, total triaged, per-bucket counts and sizes.
- **Storage saved to date** (executed deletions) and **storage staged**
  (pending in Delete bucket) — the headline numbers.
- Cleanup lanes (§7.2) with per-lane progress and estimated remaining gain.
- Resume button → drops straight into the next undecided item (< 1 s).

### 7.5 Acting on buckets (assisted-manual execution)
Because the API cannot delete or re-album existing photos (§5):

- **Delete bucket → guided deletion:** the app opens each staged item directly
  in Google Photos (deep link) in sequence — user presses the app's "next"
  after deleting, or uses a split-screen checklist view. For Takeout-sourced
  cleanups, the app also exports a filename/date manifest to search-and-delete
  in batches. Deleted items are confirmed in-app → move to "saved" tally.
  *(Explicitly assisted-manual: this is the price of Google's API policy, and
  the UX goal is to make it as close to one-tap-per-item as possible.)*
- **Print bucket:** export a zip (Mode B) or a manifest + open-in-Photos links
  (Mode A) suitable for sending to a print service.
- **Save special / Friends / Others:** exported as manifests; optionally the
  app *re-uploads* copies into real app-created Google Photos albums named
  "Save special" etc. — allowed by the API since the app uploaded them —
  presented as an opt-in ("creates copies, uses storage until originals are
  deleted").

### 7.6 Fast-launch engineering requirements
- PWA with service worker: app shell cached, offline-capable review of the
  local index.
- Index + thumbnails in IndexedDB; virtualized grids (no 10k-DOM-node lists).
- Skeleton UI < 200 ms, interactive < 1 s (repeat visit), background refresh.
- All heavy work (hashing, perceptual hashing, EXIF parse) in Web Workers —
  the UI thread never blocks during ingestion.

## 8. Architecture (proposed)

- **Frontend-only by default:** static SPA (React or Svelte + TypeScript),
  IndexedDB storage, Web Workers for hashing/analysis, Google Identity
  Services for OAuth, Photos Picker API for Mode A. Deployable as static
  hosting; nothing sensitive server-side.
- **Optional tiny local backend (Mode B comfort):** a small Python/Node local
  server to stream-parse multi-GB Takeout zips and serve thumbnails —
  mirrors how the Gmail CLI in this repo runs locally with user-held
  credentials.
- **Secrets:** same policy as the Gmail tool — OAuth client config and tokens
  live only on the user's machine, gitignored, never committed.

## 9. Success metrics

| Metric | Target |
|---|---|
| Time from launch (repeat visit) to first triage decision | < 3 s |
| Sustained triage pace, single photos | ≥ 30 decisions/min |
| Duplicate-lane precision (staged pairs that are truly duplicates) | ≥ 99% (Mode B), ≥ 95% (Mode A) |
| Storage reclaimed in first full session | user-visible GB counter; qualitative "felt worth it" |
| Re-review rate (items triaged twice) | ~0 — decisions must persist |

## 10. Risks & open questions

1. **Google API policy drift** — the Picker API contract may change again;
   Mode B (Takeout) is the hedge since it's policy-proof.
2. **Deletion friction** — the assisted-manual delete loop is the weakest UX
   point; needs prototyping early (deep-link behavior differs between Photos
   web and mobile). *Prototype in milestone 1.*
3. **Estimated vs. actual sizes (Mode A)** — storage-saved figures are
   estimates; label them as such to keep trust.
4. **Thumbnail cache size** — a full-library index can itself take real disk
   space in the browser; needs cache-eviction policy.
5. Open: should "Friends" support per-friend sub-buckets in v1? (Proposed: no
   — keep the loop to 5 buckets for speed.)

## 11. Milestones

1. **M1 — Spike (1–2 days):** Picker API ingestion + deep-link deletion loop
   prototype. Validates the two riskiest assumptions before any UI polish.
2. **M2 — Core loop:** index, triage screen with keyboard/swipe, buckets,
   persistence, dashboard with storage counters.
3. **M3 — Smart lanes:** duplicates (hash + perceptual), bursts, size-sorted
   videos, screenshots, temporal clusters.
4. **M4 — Execution flows:** guided delete, print/export manifests, opt-in
   re-upload albums; PWA/perf hardening to hit launch-speed targets.
