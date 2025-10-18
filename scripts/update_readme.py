#!/usr/bin/env python3
import os
import re
import json
import sys
import time
import math
import datetime as dt
import urllib.request
import urllib.error
import ssl
import xml.etree.ElementTree as ET

STATE_DIR = ".github/.state"
STATE_PATH = os.path.join(STATE_DIR, "state.json")
DEFAULT_RSS = os.environ.get("BLOG_RSS_URL", "https://www.erinmikailstaples.com/rss/")
GH_API_GRAPHQL = "https://api.github.com/graphql"
GH_LOGIN = os.environ.get("GH_LOGIN") or os.environ.get("GITHUB_REPOSITORY_OWNER") or ""
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
TZ = dt.timezone.utc

# Marker constants
BLOG_START = "<!-- DYNAMIC:START:blog -->"
BLOG_END = "<!-- DYNAMIC:END:blog -->"
STATS_START = "<!-- DYNAMIC:START:stats -->"
STATS_END = "<!-- DYNAMIC:END:stats -->"

def load_config():
    cfg_path = ".github/readme.config.json"
    if not os.path.isfile(cfg_path):
        return {}
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def ensure_state():
    os.makedirs(STATE_DIR, exist_ok=True)
    if not os.path.isfile(STATE_PATH):
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f)
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def save_state(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)

def http_get(url, headers=None, timeout=15):
    headers = headers or {}
    req = urllib.request.Request(url, headers=headers, method="GET")
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            body = resp.read()
            return resp.getcode(), body, dict(resp.getheaders())
    except urllib.error.HTTPError as e:
        return e.code, e.read() if e.fp else b"", dict(e.headers or {})
    except Exception as e:
        raise

def http_post(url, data_dict, headers=None, timeout=20):
    headers = headers or {}
    data = json.dumps(data_dict).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        body = resp.read()
        return resp.getcode(), body, dict(resp.getheaders())

def parse_rss_or_atom(xml_bytes):
    # Attempt to parse both RSS and Atom
    root = ET.fromstring(xml_bytes)
    ns = {}
    if root.tag.endswith("rss") or "rss" in root.tag:
        channel = root.find("channel")
        items = []
        if channel is None:
            return items
        for item in channel.findall("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub = (item.findtext("pubDate") or "").strip()
            items.append({"title": title, "link": link, "published": pub})
        return items
    # Atom
    if root.tag.endswith("feed"):
        # populate namespace if any
        if root.tag[0] == "{":
            ns_uri = root.tag[root.tag.find("{")+1:root.tag.find("}")]
            ns = {"a": ns_uri}
        entries = root.findall("a:entry", ns) if ns else root.findall("entry")
        items = []
        for e in entries:
            title_el = e.find("a:title", ns) if ns else e.find("title")
            title = (title_el.text if title_el is not None else "").strip()
            link_el = e.find("a:link", ns) if ns else e.find("link")
            link = ""
            if link_el is not None:
                link = link_el.get("href", "").strip() or (link_el.text or "").strip()
            pub_el = e.find("a:updated", ns) if ns else e.find("updated")
            if pub_el is None:
                pub_el = e.find("a:published", ns) if ns else e.find("published")
            pub = (pub_el.text if pub_el is not None else "").strip()
            items.append({"title": title, "link": link, "published": pub})
        return items
    # Unknown format
    return []

def fmt_date(s, fallback_fmt="%b %d, %Y"):
    # Try a few common formats, then fallback to raw string
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            d = dt.datetime.strptime(s, fmt)
            return d.strftime(fallback_fmt)
        except Exception:
            continue
    # If there's a timezone-less RFC822-like date, try without %z
    for fmt in ("%a, %d %b %Y %H:%M:%S",):
        try:
            d = dt.datetime.strptime(s, fmt)
            return d.strftime(fallback_fmt)
        except Exception:
            continue
    return s

def fetch_blog_posts(rss_url, max_items, state):
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; GitHubActionsBot; +https://github.com/erinmikailstaples/erinmikailstaples)",
        "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.8"
    }
    etag = state.get("rss_etag")
    last_mod = state.get("rss_last_modified")
    if etag:
        headers["If-None-Match"] = etag
    if last_mod:
        headers["If-Modified-Since"] = last_mod

    code, body, resp_headers = http_get(rss_url, headers=headers, timeout=15)
    if code == 304:
        return {"unchanged": True, "posts": []}
    if code != 200:
        raise RuntimeError(f"RSS fetch failed: HTTP {code}")

    # Update conditional headers in state
    if "ETag" in resp_headers:
        state["rss_etag"] = resp_headers["ETag"]
    if "Last-Modified" in resp_headers:
        state["rss_last_modified"] = resp_headers["Last-Modified"]

    items = parse_rss_or_atom(body)
    # Filter invalid entries
    items = [i for i in items if i.get("title") and i.get("link")]
    posts = items[:max_items]
    return {"unchanged": False, "posts": posts}

def gh_graphql(query, variables, token):
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "GitHubActionsBot",
        "Authorization": f"bearer {token}"
    }
    code, body, _ = http_post(GH_API_GRAPHQL, {"query": query, "variables": variables}, headers=headers, timeout=25)
    if code != 200:
        raise RuntimeError(f"GraphQL HTTP {code}: {body.decode('utf-8', errors='ignore')}")
    data = json.loads(body.decode("utf-8"))
    if "errors" in data and data["errors"]:
        raise RuntimeError(f"GraphQL errors: {data['errors']}")
    return data["data"]

def start_of_year(now):
    return dt.datetime(now.year, 1, 1, tzinfo=TZ)

def isoformat(d):
    return d.astimezone(TZ).isoformat()

def fetch_github_stats(login, token, recent_days_window=90):
    now = dt.datetime.now(TZ)
    from_year = start_of_year(now)
    from_recent = now - dt.timedelta(days=recent_days_window)

    query = """
    query($login:String!, $fromYear:DateTime!, $to:DateTime!, $fromRecent:DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $fromYear, to: $to) {
          totalCommitContributions
          restrictedContributionsCount
          commitContributionsByRepository(maxRepositories: 100) {
            repository {
              nameWithOwner
              isPrivate
              isFork
              stargazerCount
              primaryLanguage { name }
              languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
                edges { size node { name } }
              }
              repositoryTopics(first: 30) {
                nodes { topic { name } }
              }
              pushedAt
            }
            contributions {
              totalCount
            }
          }
        }
      }
    }
    """

    variables = {
        "login": login,
        "fromYear": isoformat(from_year),
        "to": isoformat(now),
        "fromRecent": isoformat(from_recent)
    }
    data = gh_graphql(query, variables, token)
    cc = data["user"]["contributionsCollection"]
    total_commits = cc.get("totalCommitContributions", 0)
    restricted = cc.get("restrictedContributionsCount", 0)

    # Aggregate languages and frameworks for repos with recent contributions
    langs_weight = {}
    frameworks_weight = {}

    # Simple framework keyword map (topics to display names)
    FRAME_KEYS = {
        "react": "React",
        "nextjs": "Next.js",
        "next-js": "Next.js",
        "astro": "Astro",
        "svelte": "Svelte",
        "vue": "Vue",
        "nuxt": "Nuxt",
        "angular": "Angular",
        "express": "Express",
        "nodejs": "Node.js",
        "django": "Django",
        "flask": "Flask",
        "fastapi": "FastAPI",
        "rails": "Rails",
        "laravel": "Laravel",
        "spring": "Spring",
        "tensorflow": "TensorFlow",
        "pytorch": "PyTorch",
        "tailwind": "Tailwind CSS",
        "bootstrap": "Bootstrap"
    }

    for item in cc.get("commitContributionsByRepository", []):
        repo = item.get("repository") or {}
        contribs = (item.get("contributions") or {}).get("totalCount", 0)
        if contribs <= 0:
            continue

        # Filter to recently active repos (pushedAt within window)
        pushed_at = repo.get("pushedAt")
        is_recent = True
        try:
            if pushed_at:
                # 2025-10-18T16:58:12Z
                pushed_dt = dt.datetime.strptime(pushed_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=TZ)
                is_recent = pushed_dt >= dt.datetime.now(TZ) - dt.timedelta(days=90)
        except Exception:
            pass
        if not is_recent:
            continue

        langs = (repo.get("languages") or {}).get("edges", [])
        total_size = sum(edge.get("size", 0) for edge in langs) or 1
        for edge in langs:
            name = ((edge.get("node") or {}).get("name") or "").strip()
            size = edge.get("size", 0)
            if not name:
                continue
            # Weight language by both repo composition and your commits in that repo
            weight = (size / total_size) * contribs
            langs_weight[name] = langs_weight.get(name, 0.0) + weight

        topics = [(n.get("topic") or {}).get("name", "") for n in (repo.get("repositoryTopics") or {}).get("nodes", [])]
        for t in topics:
            key = t.lower().strip()
            if key in FRAME_KEYS:
                disp = FRAME_KEYS[key]
                frameworks_weight[disp] = frameworks_weight.get(disp, 0.0) + contribs

    # Normalize to percentages for languages
    total_lang_weight = sum(langs_weight.values()) or 1.0
    langs_sorted = sorted(langs_weight.items(), key=lambda x: x[1], reverse=True)
    langs_pct = [(name, round((w / total_lang_weight) * 100)) for name, w in langs_sorted]

    frameworks_sorted = sorted(frameworks_weight.items(), key=lambda x: x[1], reverse=True)

    return {
        "total_commits_year": total_commits,
        "restricted_commits_year": restricted,
        "languages": langs_pct,
        "frameworks": [name for name, _ in frameworks_sorted]
    }

def render_blog_block(posts, date_format="%b %d, %Y"):
    lines = []
    lines.append("### Latest from my blog")
    if not posts:
        lines.append("_No recent posts found._")
    else:
        for p in posts:
            d = p.get("published") or ""
            if d:
                d = fmt_date(d, fallback_fmt=date_format)
                lines.append(f"- [{p['title']}]({p['link']}) — {d}")
            else:
                lines.append(f"- [{p['title']}]({p['link']})")
    lines.append(f"Last updated: {dt.datetime.now(TZ).strftime('%Y-%m-%d %H:%M UTC')}")
    return "\n".join(lines) + "\n"

def render_stats_block(stats, max_languages=6, max_frameworks=6):
    lines = []
    lines.append("### GitHub activity")
    commits_line = f"- Commits this year: {stats.get('total_commits_year', 0)}"
    rc = stats.get("restricted_commits_year", 0) or 0
    if rc > 0:
        commits_line += f" (+{rc} private)"
    lines.append(commits_line)

    langs = stats.get("languages", [])
    if langs:
        top = langs[:max_languages]
        lang_text = ", ".join([f"{name} ({pct}%)" for name, pct in top])
        lines.append(f"- Recently used languages: {lang_text}")

    frames = stats.get("frameworks", [])
    if frames:
        frames = frames[:max_frameworks]
        lines.append(f"- Recently used frameworks: {', '.join(frames)}")

    return "\n".join(lines) + "\n"

def replace_block(content, start_marker, end_marker, new_block):
    pattern = re.compile(
        rf"({re.escape(start_marker)})(.*?){re.escape(end_marker)}",
        re.DOTALL | re.IGNORECASE,
    )
    if re.search(pattern, content):
        return re.sub(pattern, rf"\1\n{new_block}{end_marker}", content)
    # If markers missing, append at the end
    return content.rstrip() + f"\n\n{start_marker}\n{new_block}{end_marker}\n"

def main():
    cfg = load_config()
    state = ensure_state()

    rss_url = (cfg.get("blog") or {}).get("rss_url") or DEFAULT_RSS
    max_items = int((cfg.get("blog") or {}).get("max_items", 5))
    date_fmt = (cfg.get("blog") or {}).get("date_format", "%b %d, %Y")

    stats_cfg = (cfg.get("stats") or {})
    recent_days = int(stats_cfg.get("recent_days_window", 90))
    max_langs = int(stats_cfg.get("max_languages", 6))
    max_frames = int(stats_cfg.get("max_frameworks", 6))

    blog_block = None
    stats_block = None

    # Fetch blog posts
    try:
        blog_result = fetch_blog_posts(rss_url, max_items, state)
        if not blog_result.get("unchanged", False):
            blog_block = render_blog_block(blog_result.get("posts", []), date_fmt)
    except Exception as e:
        print(f"[warn] Blog fetch failed: {e}", file=sys.stderr)

    # Fetch GitHub stats
    token = GITHUB_TOKEN
    if not token:
        print("[error] GITHUB_TOKEN is not set", file=sys.stderr)
    else:
        try:
            login = GH_LOGIN.strip()
            if not login:
                raise RuntimeError("GH_LOGIN not set")
            stats = fetch_github_stats(login, token, recent_days_window=recent_days)
            stats_block = render_stats_block(stats, max_languages=max_langs, max_frameworks=max_frames)
        except Exception as e:
            print(f"[warn] GitHub stats fetch failed: {e}", file=sys.stderr)

    # Load README
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content

    if blog_block is not None:
        content = replace_block(content, BLOG_START, BLOG_END, blog_block)
    if stats_block is not None:
        content = replace_block(content, STATS_START, STATS_END, stats_block)

    # Save state snapshot hash to skip no-op commits
    state["last_hash"] = str(hash((blog_block or "",))) + ":" + str(hash((stats_block or "",)))
    save_state(state)

    if content != original_content:
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(content)
        print("README updated.")
    else:
        print("No updates to README.")

if __name__ == "__main__":
    main()