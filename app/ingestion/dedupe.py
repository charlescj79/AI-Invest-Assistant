import hashlib


def news_dedupe_hash(title: str, url: str) -> str:
    canonical = f"{title.strip().lower()}|{url.strip().lower()}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
