"""Shared fetcher: cache, checkpoints, politeness. Used by both spiders.

Design rules:
- every fetched page is cached to raw/ BEFORE parsing — debugging parsers
  never re-hits the site;
- checkpoints make every script resumable after Ctrl-C or a crash;
- delays + backoff keep us polite; 5 consecutive failures = stop and tell
  the human instead of hammering.
"""
import hashlib
import json
import random
import sys
import time
from pathlib import Path

import httpx

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.6",
}


class Fetcher:
    def __init__(self, cache_dir="raw", min_delay=1.5, max_delay=3.5):
        self.cache = Path(cache_dir)
        self.cache.mkdir(exist_ok=True)
        self.client = httpx.Client(headers=HEADERS, timeout=25, follow_redirects=True)
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.consecutive_fails = 0
        self.fetched = 0
        self.from_cache = 0

    def get(self, url, use_cache=True):
        key = self.cache / (hashlib.md5(url.encode()).hexdigest() + ".html")
        if use_cache and key.exists():
            self.from_cache += 1
            return key.read_text(encoding="utf-8")

        for attempt in range(4):
            try:
                r = self.client.get(url)
            except httpx.HTTPError as e:
                print(f"  network error {type(e).__name__}, retry {attempt + 1}/4")
                time.sleep(10 * (attempt + 1))
                continue

            if r.status_code == 200:
                key.write_text(r.text, encoding="utf-8")
                self.consecutive_fails = 0
                self.fetched += 1
                time.sleep(random.uniform(self.min_delay, self.max_delay))
                return r.text
            if r.status_code in (403, 429):
                wait = 60 * (attempt + 1)
                print(f"  HTTP {r.status_code} — похоже на анти-бот, ждём {wait}s")
                time.sleep(wait)
            elif r.status_code == 404:
                return None
            else:
                print(f"  HTTP {r.status_code}, retry")
                time.sleep(15)

        self.consecutive_fails += 1
        if self.consecutive_fails >= 5:
            sys.exit(
                "\n5 URL подряд не скачались — вероятно, блокировка. "
                "Остановитесь на час и перезапустите скрипт: он продолжит "
                "с чекпоинта, ничего не потеряется."
            )
        return None

    def stats(self):
        return f"fetched={self.fetched} from_cache={self.from_cache}"


def load_checkpoint(path, default):
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return default


def save_checkpoint(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def append_jsonl(path, obj):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def read_jsonl(path):
    p = Path(path)
    if not p.exists():
        return []
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out
