# Images

Put each post's image here (PNG or JPEG, square 1080×1080 recommended for Instagram) and reference it by path in `content/queue.json`.

The repo must stay **public** for the posting script's default public-URL method (`raw.githubusercontent.com`) to work, since Instagram's Graph API requires a publicly reachable image URL.

## Pending: first queued post's image

`content/queue.json` already has an entry (`2026-11-16-brand-lifestyle`) pointing at `content/images/2026-11-16-brand-lifestyle.png`, which doesn't exist yet. Export/download the matching visual from the ZAUQ Brand Post design artifact and add it here with that exact filename before the next scheduled run, or the script will skip that entry and log a missing-image warning.
