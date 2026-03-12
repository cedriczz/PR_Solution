import hashlib
import json
import re
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DB_PATH = "monitor.db"
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            keywords TEXT NOT NULL,
            exclude_keywords TEXT NOT NULL,
            languages TEXT NOT NULL,
            sources TEXT NOT NULL,
            frequency_minutes INTEGER NOT NULL,
            alert_threshold REAL NOT NULL,
            created_at TEXT NOT NULL,
            last_run TEXT
        );

        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            source TEXT,
            title TEXT,
            url TEXT,
            content TEXT,
            language TEXT,
            relevance INTEGER NOT NULL,
            sentiment TEXT NOT NULL,
            sentiment_score REAL NOT NULL,
            is_alert INTEGER NOT NULL,
            dedupe_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(task_id, dedupe_hash)
        );
        """
    )
    conn.commit()
    conn.close()


def render_template(name: str):
    return (TEMPLATES_DIR / name).read_text(encoding="utf-8")


def normalize_text(text: str):
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\u4e00-\u9fff ]", "", text)
    return text.strip()


def calc_hash(title: str, content: str):
    return hashlib.sha256(normalize_text(title + " " + content)[:600].encode("utf-8")).hexdigest()


def detect_language(text: str):
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh"
    return "en"


class LocalModel:
    pos = {"en": ["good", "great", "love", "success"], "zh": ["好", "支持", "成功", "满意"]}
    neg = {"en": ["bad", "risk", "fail", "problem", "complaint"], "zh": ["差", "风险", "失败", "问题", "投诉"]}

    @staticmethod
    def relevance(text, keywords):
        t = normalize_text(text)
        if not keywords:
            return False
        hit = sum(1 for k in keywords if normalize_text(k) in t)
        return hit >= 1

    @classmethod
    def sentiment(cls, text, lang):
        t = text.lower()
        pos = sum(t.count(w) for w in cls.pos.get(lang, cls.pos["en"]))
        neg = sum(t.count(w) for w in cls.neg.get(lang, cls.neg["en"]))
        total = pos + neg
        score = 0.0 if total == 0 else (pos - neg) / total
        label = "neutral"
        if score > 0.2:
            label = "positive"
        elif score < -0.2:
            label = "negative"
        return label, score


def fetch_rss(url):
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = resp.read()
        root = ET.fromstring(data)
        items = []
        for it in root.findall(".//item")[:100]:
            items.append(
                {
                    "title": (it.findtext("title") or "").strip(),
                    "summary": (it.findtext("description") or "").strip(),
                    "link": (it.findtext("link") or "").strip(),
                }
            )
        if not items:
            for it in root.findall(".//{http://www.w3.org/2005/Atom}entry")[:100]:
                link_elem = it.find("{http://www.w3.org/2005/Atom}link")
                items.append(
                    {
                        "title": (it.findtext("{http://www.w3.org/2005/Atom}title") or "").strip(),
                        "summary": (it.findtext("{http://www.w3.org/2005/Atom}summary") or "").strip(),
                        "link": (link_elem.attrib.get("href", "") if link_elem is not None else "").strip(),
                    }
                )
        return items
    except Exception:
        return []


def run_task(task_id: int):
    conn = get_conn()
    task = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not task:
        conn.close()
        return 0

    keywords = json.loads(task["keywords"])
    excludes = [e.lower() for e in json.loads(task["exclude_keywords"])]
    langs = set(json.loads(task["languages"]))
    sources = json.loads(task["sources"])
    inserted = 0

    for src in sources:
        for entry in fetch_rss(src):
            text = f"{entry['title']}\n{entry['summary']}"
            t_lower = text.lower()
            if not any(k.lower() in t_lower for k in keywords):
                continue
            if any(e in t_lower for e in excludes if e):
                continue
            lang = detect_language(text)
            if langs and lang not in langs:
                continue
            if not LocalModel.relevance(text, keywords):
                continue
            sentiment, score = LocalModel.sentiment(text, lang)
            is_alert = 1 if sentiment == "negative" and abs(score) >= float(task["alert_threshold"]) else 0
            h = calc_hash(entry["title"], entry["summary"])
            try:
                conn.execute(
                    """
                    INSERT INTO items(task_id, source, title, url, content, language, relevance,
                                      sentiment, sentiment_score, is_alert, dedupe_hash, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
                    """,
                    (
                        task_id,
                        src,
                        entry["title"],
                        entry["link"],
                        entry["summary"],
                        lang,
                        sentiment,
                        float(score),
                        is_alert,
                        h,
                        datetime.utcnow().isoformat(),
                    ),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                pass

    conn.execute("UPDATE tasks SET last_run=? WHERE id=?", (datetime.utcnow().isoformat(), task_id))
    conn.commit()
    conn.close()
    return inserted


def scheduler_loop():
    while True:
        try:
            conn = get_conn()
            tasks = conn.execute("SELECT id, frequency_minutes, last_run FROM tasks").fetchall()
            conn.close()
            now = datetime.utcnow()
            for t in tasks:
                if not t["last_run"]:
                    run_task(int(t["id"]))
                    continue
                last = datetime.fromisoformat(t["last_run"])
                delta_m = (now - last).total_seconds() / 60
                if delta_m >= max(1, int(t["frequency_minutes"])):
                    run_task(int(t["id"]))
        except Exception:
            pass
        time.sleep(30)


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, status=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _text(self, html, status=200):
        data = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/" or path == "/monitoring":
            return self._text(render_template("monitoring.html"))
        if path == "/results":
            return self._text(render_template("results.html"))
        if path == "/alerts":
            return self._text(render_template("alerts.html"))
        if path.startswith("/static/"):
            p = STATIC_DIR / path.replace("/static/", "")
            if p.exists():
                data = p.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/css; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

        if path == "/api/tasks":
            conn = get_conn()
            rows = conn.execute("SELECT * FROM tasks ORDER BY id DESC").fetchall()
            conn.close()
            out = []
            for r in rows:
                d = dict(r)
                for k in ["keywords", "exclude_keywords", "languages", "sources"]:
                    d[k] = json.loads(d[k])
                out.append(d)
            return self._json(out)

        m = re.fullmatch(r"/api/tasks/(\d+)/(results|alerts)", path)
        if m:
            task_id = int(m.group(1))
            kind = m.group(2)
            where = "task_id=?" if kind == "results" else "task_id=? AND is_alert=1"
            conn = get_conn()
            rows = conn.execute(f"SELECT * FROM items WHERE {where} ORDER BY created_at DESC LIMIT 200", (task_id,)).fetchall()
            conn.close()
            return self._json([dict(r) for r in rows])

        self._json({"error": "not found"}, 404)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")

        if path == "/api/tasks":
            need = ["name", "keywords", "exclude_keywords", "languages", "frequency_minutes", "alert_threshold", "sources"]
            miss = [k for k in need if k not in data]
            if miss:
                return self._json({"error": f"缺少字段 {miss}"}, 400)
            conn = get_conn()
            cur = conn.execute(
                """
                INSERT INTO tasks(name, keywords, exclude_keywords, languages, sources, frequency_minutes, alert_threshold, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["name"],
                    json.dumps(data["keywords"], ensure_ascii=False),
                    json.dumps(data["exclude_keywords"], ensure_ascii=False),
                    json.dumps(data["languages"], ensure_ascii=False),
                    json.dumps(data["sources"], ensure_ascii=False),
                    int(data["frequency_minutes"]),
                    float(data["alert_threshold"]),
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
            task_id = cur.lastrowid
            conn.close()
            return self._json({"task_id": task_id})

        m = re.fullmatch(r"/api/tasks/(\d+)/run", path)
        if m:
            inserted = run_task(int(m.group(1)))
            return self._json({"inserted": inserted})

        self._json({"error": "not found"}, 404)

    def do_PUT(self):
        path = urllib.parse.urlparse(self.path).path
        m = re.fullmatch(r"/api/tasks/(\d+)/keywords", path)
        if not m:
            return self._json({"error": "not found"}, 404)
        length = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        if "keywords" not in data or "exclude_keywords" not in data:
            return self._json({"error": "需要 keywords 和 exclude_keywords"}, 400)
        conn = get_conn()
        conn.execute(
            "UPDATE tasks SET keywords=?, exclude_keywords=? WHERE id=?",
            (
                json.dumps(data["keywords"], ensure_ascii=False),
                json.dumps(data["exclude_keywords"], ensure_ascii=False),
                int(m.group(1)),
            ),
        )
        conn.commit()
        conn.close()
        self._json({"ok": True})


if __name__ == "__main__":
    init_db()
    threading.Thread(target=scheduler_loop, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", 5000), Handler)
    print("服务已启动: http://127.0.0.1:5000")
    server.serve_forever()
