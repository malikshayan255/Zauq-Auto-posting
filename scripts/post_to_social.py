#!/usr/bin/env python3
"""
Posts the next unposted item in content/queue.json to the ZAUQ Facebook Page
and Instagram Business account via Meta's Graph API, then marks it posted.

Required environment variables (set as GitHub Actions secrets):
  META_PAGE_ACCESS_TOKEN  - long-lived Page access token (see README.md)
  META_PAGE_ID            - Facebook Page numeric ID
  META_IG_USER_ID         - linked Instagram Business account ID

Optional:
  DRY_RUN=true            - print what would be posted, make no API calls
  GRAPH_API_VERSION       - defaults to v21.0
  GITHUB_REPOSITORY       - "owner/repo", provided automatically in Actions
  GIT_BRANCH              - defaults to "main"; used to build the public image URL
"""

import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

import requests

ROOT = Path(__file__).resolve().parent.parent
QUEUE_PATH = ROOT / "content" / "queue.json"

GRAPH_VERSION = os.environ.get("GRAPH_API_VERSION", "v21.0")
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"

DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"


def log(msg: str) -> None:
    print(f"[post_to_social] {msg}", flush=True)


def load_queue() -> list:
    if not QUEUE_PATH.exists():
        log(f"No queue file at {QUEUE_PATH}")
        return []
    return json.loads(QUEUE_PATH.read_text())


def save_queue(queue: list) -> None:
    QUEUE_PATH.write_text(json.dumps(queue, indent=2, ensure_ascii=False) + "\n")


def public_image_url(image_rel_path: str) -> str:
    repo = os.environ.get("GITHUB_REPOSITORY")
    branch = os.environ.get("GIT_BRANCH", "main")
    if not repo:
        raise RuntimeError(
            "GITHUB_REPOSITORY is not set. Running outside GitHub Actions? "
            "Set it manually as 'owner/repo' to build the public image URL."
        )
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{image_rel_path}"


def post_to_facebook(page_id: str, page_token: str, image_url: str, caption: str) -> str:
    resp = requests.post(
        f"{GRAPH_BASE}/{page_id}/photos",
        data={
            "url": image_url,
            "caption": caption,
            "published": "true",
            "access_token": page_token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    log(f"Facebook post published: id={data.get('post_id') or data.get('id')}")
    return data.get("post_id") or data.get("id")


def post_to_instagram(ig_user_id: str, page_token: str, image_url: str, caption: str) -> str:
    # Step 1: create a media container
    container_resp = requests.post(
        f"{GRAPH_BASE}/{ig_user_id}/media",
        data={
            "image_url": image_url,
            "caption": caption,
            "access_token": page_token,
        },
        timeout=30,
    )
    container_resp.raise_for_status()
    creation_id = container_resp.json()["id"]
    log(f"Instagram media container created: {creation_id}")

    # IG sometimes needs a moment to fetch/process the image before publish succeeds.
    time.sleep(5)

    # Step 2: publish the container
    publish_resp = requests.post(
        f"{GRAPH_BASE}/{ig_user_id}/media_publish",
        data={
            "creation_id": creation_id,
            "access_token": page_token,
        },
        timeout=30,
    )
    publish_resp.raise_for_status()
    media_id = publish_resp.json()["id"]
    log(f"Instagram post published: id={media_id}")
    return media_id


def main() -> int:
    queue = load_queue()
    next_item = next((item for item in queue if not item.get("posted")), None)

    if next_item is None:
        log("No unposted items in queue. Nothing to do.")
        return 0

    image_rel_path = next_item["image"]
    image_abs_path = ROOT / image_rel_path
    if not image_abs_path.exists():
        log(
            f"WARNING: queued item '{next_item['id']}' points at a missing image "
            f"({image_rel_path}). Add the file and re-run. Skipping for now — "
            "this item is NOT marked posted."
        )
        return 0

    image_url = public_image_url(image_rel_path)
    caption_fb = next_item.get("caption_facebook", "")
    caption_ig = next_item.get("caption_instagram", "")

    log(f"Next queued item: {next_item['id']}")
    log(f"Image URL: {image_url}")

    if DRY_RUN:
        log("DRY_RUN=true — not calling the Graph API. Would post:")
        log(f"  Facebook caption:\n{caption_fb}\n")
        log(f"  Instagram caption:\n{caption_ig}\n")
        return 0

    page_token = os.environ["META_PAGE_ACCESS_TOKEN"]
    page_id = os.environ["META_PAGE_ID"]
    ig_user_id = os.environ["META_IG_USER_ID"]

    fb_post_id = None
    ig_media_id = None
    try:
        fb_post_id = post_to_facebook(page_id, page_token, image_url, caption_fb)
        ig_media_id = post_to_instagram(ig_user_id, page_token, image_url, caption_ig)
    except requests.HTTPError as e:
        log(f"ERROR posting to Graph API: {e.response.text if e.response else e}")
        log(
            f"Partial result — facebook_post_id={fb_post_id}, instagram_media_id={ig_media_id}. "
            "Item NOT marked posted; fix the issue and re-run (may double-post to whichever "
            "platform already succeeded above — check before re-running)."
        )
        return 1

    next_item["posted"] = True
    next_item["posted_at"] = datetime.now(timezone.utc).isoformat()
    next_item["facebook_post_id"] = fb_post_id
    next_item["instagram_media_id"] = ig_media_id
    save_queue(queue)
    log(f"Marked '{next_item['id']}' as posted and saved queue.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
