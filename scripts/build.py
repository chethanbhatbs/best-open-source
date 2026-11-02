#!/usr/bin/env python3
"""Pull live stats for every project in repos.txt and rebuild README.md.

Requires the GitHub CLI (https://cli.github.com/), logged in with `gh auth login`.
Usage: python3 scripts/build.py
"""
import datetime, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_URL = "https://github.com/chethanbhatbs/best-open-source"


def fetch(repo):
    r = subprocess.run(["gh", "api", f"repos/{repo}"], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return json.loads(r.stdout)


def short(n):
    return f"{n/1000:.1f}k".replace(".0k", "k") if n >= 1000 else str(n)


def cell(s):
    return (s or "").replace("|", "\\|").replace("\n", " ").strip()


def main():
    sections, current = [], None
    for raw in open(os.path.join(ROOT, "repos.txt")):
        line = raw.strip()
        if not line or (line.startswith("#") and not line.startswith("## ")):
            continue
        if line.startswith("## "):
            current = (line[3:].strip(), [])
            sections.append(current)
            continue
        name, _, note = (p.strip() for p in line.partition("|"))
        if current is None:
            sys.exit(f"'{name}' is above the first '## ' section heading")
        current[1].append((name, note))

    today = datetime.date.today().isoformat()
    rows, missing, total, out = [], [], 0, []
    for title, items in sections:
        body = []
        for name, note in items:
            d = fetch(name)
            if d is None:
                missing.append(name)
                print(f"WARN: could not fetch {name} (deleted, renamed or private)")
                continue
            total += 1
            rows.append([d["full_name"], d["stargazers_count"], (d.get("license") or {}).get("spdx_id") or "none",
                         d["pushed_at"][:10], d.get("language") or "-", "yes" if d.get("archived") else "no"])
            what = cell(note or d.get("description") or "-")
            lic = (d.get("license") or {}).get("spdx_id") or "none"
            flag = " (archived)" if d.get("archived") else ""
            body.append(f"| [{d['full_name']}]({d['html_url']}){flag} | {what} | {short(d['stargazers_count'])} | {lic} | {d['pushed_at'][:10]} |")
        out.append((title, f"## {title}\n\n| Project | What it is | Stars | Licence | Last update |\n|---|---|---|---|---|\n" + "\n".join(body) + "\n"))

    anchors = "\n".join(f"- [{t}](#{t.lower().replace(' ', '-')})" for t, _ in out)
    readme = f"""# Best Open Source

A hand-picked list of open-source projects worth knowing, in one place.

**{total} projects.** Stars, licence and last-update dates are pulled live from the GitHub API by `scripts/build.py`. Last pulled: **{today}**.

## Contents

{anchors}
- [Add a project](#add-a-project)

---

""" + "\n".join(md for _, md in out) + f"""
---

## Add a project

1. Add a line to [`repos.txt`](repos.txt) under the right `## ` heading: `owner/name`, optionally `| one-line note`.
2. Run `python3 scripts/build.py` (needs the [GitHub CLI](https://cli.github.com/), logged in).
3. Open a pull request.

Without a note, the project's own GitHub description is used.

**Licence `none`** means GitHub found no licence file. You can read the code, but you may not have the right to reuse it.

## Licence

This list is [CC0](LICENSE): public domain. Each project keeps its own licence.
"""
    open(os.path.join(ROOT, "README.md"), "w").write(readme)
    with open(os.path.join(ROOT, "data", "stats.tsv"), "w") as f:
        f.write("repo\tstars\tlicense\tpushed\tlang\tarchived\n")
        for r in rows:
            f.write("\t".join(map(str, r)) + "\n")
    print(f"Built README.md: {total} projects, {len(missing)} missing, pulled {today}")
    if missing:
        sys.exit(1)


if __name__ == "__main__":
    main()
