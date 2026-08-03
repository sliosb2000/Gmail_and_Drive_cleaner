"""M1 spike: generate a phone deletion checklist from Google Photos URLs.

Input: urls.txt (one https://photos.google.com/... URL per line — from
Takeout metadata JSON's "url" field, or copied from the Photos web app).
Output: checklist.html — open it on your phone; each row deep-links into
Google Photos. Ticks persist in localStorage (survives closing the page).

Usage: python m1_checklist.py [urls.txt] [checklist.html]
"""
import html
import sys

urls_file = sys.argv[1] if len(sys.argv) > 1 else "urls.txt"
out_file = sys.argv[2] if len(sys.argv) > 2 else "checklist.html"

with open(urls_file) as f:
    urls = [u.strip() for u in f if u.strip() and not u.startswith("#")]

rows = "\n".join(
    f'<li><input type="checkbox" id="c{i}"> '
    f'<a href="{html.escape(u)}" target="_blank">photo {i + 1}</a></li>'
    for i, u in enumerate(urls)
)

page = f"""<!doctype html>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Delete checklist ({len(urls)})</title>
<style>
  body {{ font-family: sans-serif; margin: 1rem; }}
  li {{ font-size: 1.4rem; padding: .6rem 0; list-style: none; }}
  input {{ width: 1.4rem; height: 1.4rem; margin-right: .8rem; }}
  :checked + a {{ text-decoration: line-through; color: #999; }}
  #done {{ font-weight: bold; }}
</style>
<p><span id="done">0</span> / {len(urls)} deleted</p>
<ul>{rows}</ul>
<script>
  const boxes = document.querySelectorAll("input");
  const done = document.getElementById("done");
  const update = () => done.textContent =
    [...boxes].filter(b => b.checked).length;
  boxes.forEach(b => {{
    b.checked = localStorage.getItem(b.id) === "1";
    b.onchange = () => {{ localStorage.setItem(b.id, b.checked ? "1" : "0"); update(); }};
  }});
  update();
</script>
"""

with open(out_file, "w") as f:
    f.write(page)
print(f"{out_file}: {len(urls)} links")
