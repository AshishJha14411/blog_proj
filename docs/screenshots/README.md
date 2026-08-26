# Screenshots — capture checklist

The READMEs already reference these files by name. **Drop a PNG in this folder
with the exact filename and it appears automatically** — no markdown edits needed.
Until then GitHub shows a broken-image icon, which is deliberate: a missing
screenshot is better than a fake placeholder image.

## Captured ✅

| Filename | Shows | Used in |
|---|---|---|
| `home.png` | Story feed, logged out | root, frontend |
| `ai-generate-streaming.png` | AI generation **mid-stream** — the headline shot | root, frontend |
| `notifications.png` | Notification dropdown with unread items | root, frontend |
| `moderation-queue.png` | Moderation queue | root, backend |
| `story-approval.png` | Per-story moderator review | root, backend |

## Still to capture

Not referenced by any README yet — add the markdown once the file exists.

| Filename | What to capture | Notes |
|---|---|---|
| `home.png` (re-shoot) | `/` — the hero plus the **Most loved stories** rail | The current file shows `/userStory`; `/` is now the real landing page |
| `story-detail.png` | A published story with comments, likes and **tag chips** visible | Tags now exist — generated stories take their genre as their tag |
| `analytics.png` | `/admin/analytics` with the daily bar charts populated | Sign in as superadmin; pick the 30d range |
| `api-docs.png` | Swagger UI at `<backend>/docs`, a few groups expanded | — |
| `tests-passing.png` | Terminal showing `394 passed` | — |

## How to capture well

1. **Seed real-looking data first.** Empty states make a project look unfinished.
   Create 4–6 stories with real titles and cover images, a few comments, and at
   least one flagged item so the moderation queue isn't empty.
2. **Log in as `superadmin`** for the admin shots — the mod/analytics routes are
   permission-gated and will 403 otherwise.
3. **Use a consistent viewport.** 1440×900 for full pages; crop tightly for
   component shots (the bell, a card). Avoid capturing your browser chrome,
   bookmarks bar, or other tabs.
4. **Use light or dark consistently** — mixing them across shots looks careless.
5. **Scrub anything personal**: real email addresses, your actual name in test
   accounts, tokens visible in a devtools panel.
6. **Compress before committing.** Run them through TinyPNG or similar; keep each
   under ~300 KB so the README stays fast to load. These are the only large
   binaries in the repo besides `docs/architecture/architecture.gif`.

## Optional extras

Nice to have, referenced nowhere yet — add a markdown link if you use them:

- `mobile-responsive.png` — the feed at ~390px width
- `lighthouse.png` — a Lighthouse score run against the deployed frontend
- `websocket-notification.gif` — a live notification arriving over the socket
  (the WebSocket backplane is a genuine differentiator and hard to convey in a still)
