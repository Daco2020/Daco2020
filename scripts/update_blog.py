#!/usr/bin/env python3
"""티스토리 최신 글의 og:image를 내려받아 README의 4열 그리드를 갱신한다.

티스토리 og:image URL은 서명과 만료(약 한 달)가 붙어 있어 그대로 쓰면 곧 깨진다.
그래서 이미지를 저장소로 복사하고 상대 경로로 참조한다.
"""
import html, os, re, subprocess, sys
from pathlib import Path

FEED  = "https://daco2020.tistory.com/rss"
COUNT = 8          # 4열 x 2줄
OUT   = Path("assets/blog")
START, END = "<!-- BLOG-POST-LIST:START -->", "<!-- BLOG-POST-LIST:END -->"


def fetch(url, binary=False):
    r = subprocess.run(["curl", "-sL", "--max-time", "30", url],
                       capture_output=True)
    if r.returncode != 0:
        return None
    return r.stdout if binary else r.stdout.decode("utf8", "replace")


def unescape_all(s):
    prev = None
    while prev != s:                 # 티스토리 제목은 이중 인코딩이다
        prev, s = s, html.unescape(s)
    return s


def posts():
    xml = fetch(FEED)
    if not xml:
        sys.exit("RSS를 가져오지 못했다")
    items = []
    for chunk in re.findall(r"<item>(.*?)</item>", xml, re.S)[:COUNT]:
        t = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", chunk, re.S)
        l = re.search(r"<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>", chunk, re.S)
        if t and l:
            items.append((unescape_all(t.group(1).strip()), l.group(1).strip()))
    return items


def og_image(page_url):
    doc = fetch(page_url)
    if not doc:
        return None
    m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]*>', doc)
    if not m:
        return None
    c = re.search(r'content=["\']([^"\']+)["\']', m.group(0))
    return html.unescape(c.group(1)) if c else None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.png"):
        old.unlink()

    cells = []
    for title, link in posts():
        pid = link.rstrip("/").rsplit("/", 1)[-1] or "post"
        src = og_image(link)
        if not src:
            continue
        data = fetch(src, binary=True)
        if not data or len(data) < 1000:
            continue
        (OUT / f"{pid}.png").write_bytes(data)
        alt = title.replace('"', "&quot;")
        cells.append(f'<a href="{link}"><img src="assets/blog/{pid}.png" '
                     f'width="200" alt="{alt}" title="{alt}"></a>')

    rows = []
    for i in range(0, len(cells), 4):
        row = "".join(f"\n<td>{c}</td>" for c in cells[i:i+4])
        rows.append(f"<tr>{row}\n</tr>")
    table = "<table>\n" + "\n".join(rows) + "\n</table>" if rows else ""

    p = Path("README.md")
    t = p.read_text(encoding="utf8")
    t = re.sub(re.escape(START) + r".*?" + re.escape(END),
               f"{START}\n{table}\n{END}", t, flags=re.S)
    p.write_text(t, encoding="utf8")
    print(f"{len(cells)}개 갱신")


if __name__ == "__main__":
    main()
