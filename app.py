import os, sqlite3, hashlib
from datetime import datetime, timezone
from flask import Flask, render_template, request, abort, send_from_directory, Response

app = Flask(__name__)

# ---- Config (override with env vars on the host) ----
DB_PATH = os.environ.get("DB_PATH", "scans.db")
ADMIN_KEY = os.environ.get("ADMIN_KEY", "change-me")
BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")
PROFILE = {
    "name": "Nitya Dhagat",
    "linkedin": os.environ.get("LINKEDIN_URL", "https://www.linkedin.com/in/nitya-dhagat"),
    "github": os.environ.get("GITHUB_URL", "https://github.com/Nitya-Dhagat"),
    "email": os.environ.get("CONTACT_EMAIL", "nityaddhagat@gmail.com"),
    "scholar": "https://scholar.google.com/citations?user=dpTNCPMAAAAJ&hl=en",
}
# Campaign slugs -> label. Any slug listed here works as /<slug>
CAMPAIGNS = {"careerfair": "Career Fair", "meetup": "Meetup", "linkedin": "LinkedIn", "nitya": "Direct"}


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, campaign TEXT, device TEXT, country TEXT, referrer TEXT, visitor TEXT)""")
        con.execute("""CREATE TABLE IF NOT EXISTS clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, campaign TEXT, target TEXT)""")


init_db()


def device_type(ua):
    ua = (ua or "").lower()
    if any(k in ua for k in ("iphone", "android", "mobile")):
        return "mobile"
    if "ipad" in ua or "tablet" in ua:
        return "tablet"
    return "desktop"


def log_scan(campaign):
    ua = request.headers.get("User-Agent", "")
    if any(b in ua.lower() for b in ("bot", "crawl", "spider", "preview")):
        return
    ip = (request.headers.get("X-Forwarded-For", request.remote_addr) or "").split(",")[0].strip()
    # anonymous visitor hash (for return-visit counting); IP itself is never stored
    visitor = hashlib.sha256((ip + ua).encode()).hexdigest()[:16]
    country = request.headers.get("CF-IPCountry") or request.headers.get("X-Country") or "unknown"
    with db() as con:
        con.execute(
            "INSERT INTO scans (ts, campaign, device, country, referrer, visitor) VALUES (?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), campaign, device_type(ua), country,
             request.referrer or "direct", visitor))


def page(campaign):
    log_scan(campaign)
    return render_template("index.html", p=PROFILE, campaign=campaign)


@app.route("/")
def home():
    return page("direct")


@app.route("/go/<target>")
def go(target):
    """Tracked outbound links: /go/linkedin?c=careerfair"""
    urls = {"linkedin": PROFILE["linkedin"], "github": PROFILE["github"],
            "email": "mailto:" + PROFILE["email"], "resume": "/resume.pdf",
            "scholar": PROFILE["scholar"],
            "hidenet": "https://ieeexplore.ieee.org/document/11429958",
            "flood": "https://doi.org/10.31223/X59Z2M",
            "voice": "https://arxiv.org/abs/2606.28779",
            "site": "https://nityadhagat.vercel.app"}
    if target not in urls:
        abort(404)
    with db() as con:
        con.execute("INSERT INTO clicks (ts, campaign, target) VALUES (?,?,?)",
                    (datetime.now(timezone.utc).isoformat(), request.args.get("c", "direct"), target))
    return Response(status=302, headers={"Location": urls[target]})


@app.route("/resume.pdf")
def resume():
    return send_from_directory("static", "resume.pdf")


@app.route("/admin")
def admin():
    if request.args.get("key") != ADMIN_KEY:
        abort(403)
    with db() as con:
        total = con.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
        unique = con.execute("SELECT COUNT(DISTINCT visitor) FROM scans").fetchone()[0]
        by_campaign = con.execute("SELECT campaign, COUNT(*) n FROM scans GROUP BY campaign ORDER BY n DESC").fetchall()
        by_device = con.execute("SELECT device, COUNT(*) n FROM scans GROUP BY device ORDER BY n DESC").fetchall()
        by_country = con.execute("SELECT country, COUNT(*) n FROM scans GROUP BY country ORDER BY n DESC LIMIT 10").fetchall()
        by_hour = con.execute("SELECT substr(ts,1,13) h, COUNT(*) n FROM scans GROUP BY h ORDER BY n DESC LIMIT 5").fetchall()
        clicks = con.execute("SELECT target, COUNT(*) n FROM clicks GROUP BY target ORDER BY n DESC").fetchall()
        recent = con.execute("SELECT * FROM scans ORDER BY id DESC LIMIT 15").fetchall()
    return render_template("dashboard.html", total=total, unique=unique, returning=total - unique,
                           by_campaign=by_campaign, by_device=by_device, by_country=by_country,
                           by_hour=by_hour, clicks=clicks, recent=recent)


@app.route("/<slug>")
def campaign(slug):
    if slug not in CAMPAIGNS:
        abort(404)
    return page(slug)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
