"""Auditoria read-only por endereço, sem Gemini/Telegram nem estado de produção."""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import feedparser
from web_access import bounded_get, editorial_source, extract_public_body, FetchError

URLS = [
    "https://www.nexojornal.com.br/rss.xml",
    "https://www.nexojornal.com.br/feed/",
    "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
    "https://feeds.content.dowjones.io/public/rss/RSSWorldNews",
    "https://www.ft.com/rss/home/international",
    "https://www.ft.com/rss/world",
]


def main():
    rows = []
    for url in URLS:
        row = dict(url=url, checked_at=datetime.now(timezone.utc).isoformat())
        try:
            data, final, mime = bounded_get(url, feed=True)
            parsed = feedparser.parse(data)
            links = [e.get("link", "") for e in parsed.entries]
            dates = []
            for e in parsed.entries:
                stamp = e.get("published_parsed") or e.get("updated_parsed")
                if stamp:
                    dates.append(datetime(*stamp[:6], tzinfo=timezone.utc))
            row.update(result="HTTP 200", final_url=final, content_type=mime,
                       entries=len(links), editorial_entries=sum(bool(editorial_source(x)) for x in links),
                       sample_links=links[:2],
                       newest_entry=max(dates).isoformat() if dates else None,
                       oldest_entry=min(dates).isoformat() if dates else None,
                       dated_last_24h=sum(datetime.now(timezone.utc)-timedelta(hours=24) <= d <= datetime.now(timezone.utc) for d in dates))
            if links and editorial_source(links[0]):
                probe = dict(url=links[0])
                try:
                    body_bytes, body_final, body_mime = bounded_get(links[0])
                    body, access = extract_public_body(body_bytes.decode("utf-8", errors="replace"), requested_url=links[0])
                    probe.update(result="HTTP 200", final_url=body_final,
                                 content_type=body_mime, extracted_chars=len(body), access=access)
                except Exception as exc:
                    probe["result"] = str(exc) if isinstance(exc, FetchError) else type(exc).__name__
                row["article_probe"] = probe
        except Exception as exc:
            row["result"] = str(exc) if isinstance(exc, FetchError) else type(exc).__name__
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    Path("docs/feed-checks.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
