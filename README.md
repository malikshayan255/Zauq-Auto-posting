# ZAUQ Auto-Posting

A scheduled GitHub Action that automatically publishes posts to the ZAUQ **Facebook Page** and **Instagram Business account** on a daily schedule, using Meta's Graph API. No manual click required once it's set up — it runs, posts the next item in the queue, and marks it done.

## How it works

1. `content/queue.json` holds an ordered list of posts (image + captions). Each has `posted: false` until it goes out.
2. Every day, the GitHub Action (`.github/workflows/post-to-social.yml`) runs `scripts/post_to_social.py`.
3. The script finds the first unposted entry, publishes it to Facebook and Instagram via the Graph API, flips `posted` to `true` with a timestamp, and commits that change back to the repo.
4. When the queue runs out, the job logs a notice and does nothing (no error) — add more entries to `content/queue.json` to keep it going.

## One-time setup

### 1. Get your Meta credentials

You need three values from Meta's side. These go into **GitHub repo secrets**, never into this README or any committed file.

- **`META_PAGE_ACCESS_TOKEN`** — a long-lived Page access token for the ZAUQ Facebook Page.
  1. Go to [Meta for Developers](https://developers.facebook.com/) → create/select an app → add the **Facebook Login** and **Instagram Graph API** products.
  2. Use the [Graph API Explorer](https://developers.facebook.com/tools/explorer/) to generate a **User** access token with these permissions: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `instagram_basic`, `instagram_content_publish`.
  3. Exchange it for a long-lived user token (60 days): `GET /oauth/access_token?grant_type=fb_exchange_token&client_id=<APP_ID>&client_secret=<APP_SECRET>&fb_exchange_token=<SHORT_LIVED_TOKEN>`.
  4. Get the Page token from that: `GET /me/accounts` (with the long-lived user token) — find ZAUQ's page in the list, grab its `access_token`. **Page tokens from a long-lived user token don't expire** as long as the user token stays valid and the user stays an admin of the page — this is the value that goes into the secret.

- **`META_PAGE_ID`** — the ZAUQ Facebook Page's numeric ID (same `/me/accounts` response gives you this, as `id`).

- **`META_IG_USER_ID`** — the Instagram **Business/Creator account ID** linked to that Facebook Page: `GET /{page-id}?fields=instagram_business_account&access_token=<PAGE_TOKEN>`.

### 2. Add the secrets to this repo

GitHub → this repo → **Settings → Secrets and variables → Actions → New repository secret**. Add all three:
- `META_PAGE_ACCESS_TOKEN`
- `META_PAGE_ID`
- `META_IG_USER_ID`

### 3. Add your content

Drop image files into `content/images/` (JPEG or PNG, square 1080×1080 recommended for IG) and add an entry to `content/queue.json` for each:

```json
{
  "id": "2026-11-16-brand-lifestyle",
  "image": "content/images/2026-11-16-brand-lifestyle.png",
  "caption_instagram": "Home, wherever work takes you.\n\nFully furnished serviced living with fiber Wi-Fi • 100% power backup • personalized concierge — across Islamabad, Rawalpindi, Lahore, Karachi and Murree.\n\nDM us to book your stay.\n\n#ZAUQ #ServicedLiving #ShortTermRentals #IslamabadStays #LahoreStays #KarachiStays #VerifiedHospitality #PakistanTravel #BusinessTravel #BoutiqueStays",
  "caption_facebook": "Home, wherever work takes you. ZAUQ's fully furnished serviced apartments come with fiber Wi-Fi, 100% power backup, and a concierge who's actually there when you need one — across Islamabad, Rawalpindi, Lahore, Karachi and Murree.\n\nDM us to book your stay.\n\n#ZAUQ #ServicedLiving #VerifiedHospitality",
  "posted": false
}
```

The Instagram API requires the image to be reachable at a **public URL** — the script builds this automatically from `raw.githubusercontent.com/<owner>/<repo>/<branch>/<image path>`, which only works because this repo is public. Keep it public, or switch to an external image host if you make the repo private later.

### 4. Set the schedule

Edit the `cron` line in `.github/workflows/post-to-social.yml` (currently daily at 09:00 UTC = 14:00 Asia/Tashkent). You can also trigger a run manually from the **Actions** tab ("Run workflow") to test before trusting the schedule.

## Testing without posting live

Run the script locally with `DRY_RUN=true` to print what it *would* post without calling the Graph API:

```bash
pip install requests
DRY_RUN=true META_PAGE_ACCESS_TOKEN=x META_PAGE_ID=x META_IG_USER_ID=x python scripts/post_to_social.py
```

## Safety notes

- Tokens live only in GitHub Secrets — never commit them.
- The script only ever posts the **next unposted** queue entry per run, so a schedule misfire (e.g. two runs close together) can't double-post past what's in the queue — it just finds nothing new and exits quietly if the single unposted item was already claimed by a concurrent run (see `posted` flag commit race note in the script).
