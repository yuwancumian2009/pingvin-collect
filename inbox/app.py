#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件收件箱 —— 只读展示通过 Pingvin Share X「反向分享」收到的上传。

设计原则：绝不写 Pingvin 的数据（数据库以 mode=ro 打开，上传目录只读挂载）。
所有写操作只发生在自己的 /state 与 /cache 目录。
"""
import base64
import hmac
import html
import json
import os
import re
import sqlite3
import time
import shutil
import threading
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from email.utils import formatdate
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DB_PATH = os.environ.get("DB_PATH", "/pingvin/pingvin-share.db")
UPLOADS = os.environ.get("UPLOADS", "/pingvin/uploads/shares")
STATE = os.environ.get("STATE", "/state/state.json")
CACHE = os.environ.get("CACHE", "/cache")
BASE_PATH = os.environ.get("BASE_PATH", "").rstrip("/")   # 例如 /inbox
PINGVIN_API = os.environ.get("PINGVIN_API", "http://127.0.0.1:3010")
PORT = int(os.environ.get("PORT", "8080"))

# ---- 收集链接的保存目录配置（全在自己的 /state 里，绝不写主站数据）----
TARGETS = os.environ.get("TARGETS", "/state/targets.json")     # token -> 保存配置
COPIED = os.environ.get("COPIED", "/state/copied.json")        # fileId -> 已归档信息
ROOTS_FILE = os.environ.get("ROOTS_FILE", "/state/dirs.json")  # 手动追加的可选目录
SYNC_INTERVAL = int(os.environ.get("SYNC_INTERVAL", "20"))     # 自动归档轮询秒数

# 这些挂载点不算「可选的保存目录」（容器自身的系统路径）
INTERNAL_MOUNTS = ("/", "/pingvin", "/state", "/cache", "/app")
SYS_PREFIX = ("/proc", "/sys", "/dev", "/etc")
# 主站自己的目录不能当保存位置：单镜像里数据目录也是挂载点，会被 /proc/mounts
# 扫出来，选中它等于把收到的文件又写回主站数据里。
APP_PREFIX = ("/opt/app", "/pingvin", "/state", "/cache", "/app")

# 表单体积上限（收件箱自己的表单都很小；超了就断开连接而不是读进内存）
MAX_BODY = 2 * 1024 * 1024

IMG_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".avif", ".heic", ".heif"}
VID_EXT = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv", ".3gp"}

MIME = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
    ".avif": "image/avif", ".heic": "image/heic", ".heif": "image/heif",
    ".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm",
    ".m4v": "video/x-m4v", ".mkv": "video/x-matroska", ".3gp": "video/3gpp",
    ".pdf": "application/pdf", ".txt": "text/plain; charset=utf-8",
    ".zip": "application/zip", ".mp3": "audio/mpeg", ".m4a": "audio/mp4",
}

try:
    from PIL import Image, ImageOps  # noqa
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
    except Exception:
        pass
    HAVE_PIL = True
except Exception:
    HAVE_PIL = False


# --------------------------------------------------------------------------- 工具

def human(n):
    try:
        n = float(n)
    except Exception:
        return "-"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return ("%.0f %s" % (n, unit)) if unit == "B" else ("%.1f %s" % (n, unit))
        n /= 1024.0
    return "%.1f PB" % n


def parse_ts(v):
    """Prisma/SQLite 里时间可能是 int 毫秒、float 秒或 ISO 字符串。"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        x = float(v)
        if x > 1e11:      # 毫秒
            x /= 1000.0
        return x
    try:
        s = str(v).replace("Z", "+00:00")
        import datetime
        dt = datetime.datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.timestamp()
    except Exception:
        return None


def fmt_ts(ts):
    if not ts:
        return "未知时间"
    lt = time.localtime(ts)
    now = time.time()
    d = time.strftime("%Y-%m-%d", lt)
    hm = time.strftime("%H:%M", lt)
    if d == time.strftime("%Y-%m-%d", time.localtime(now)):
        return "今天 " + hm
    if d == time.strftime("%Y-%m-%d", time.localtime(now - 86400)):
        return "昨天 " + hm
    return d + " " + hm


def ext_of(name):
    return os.path.splitext(name or "")[1].lower()


def load_state():
    try:
        with open(STATE, "r", encoding="utf-8") as f:
            st = json.load(f)
            if isinstance(st, dict) and isinstance(st.get("seen"), list):
                return st
    except Exception:
        pass
    return {"seen": []}


def save_state(st):
    try:
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        tmp = STATE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(st, f)
        os.replace(tmp, STATE)
    except Exception as e:
        print("save_state failed:", e, flush=True)


# --------------------------------------------------------------------------- 收集目标

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            v = json.load(f)
        return v if isinstance(v, type(default)) else default
    except Exception:
        return default


def save_json(path, obj):
    try:
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
        return True
    except Exception as e:
        print("save_json(%s) failed: %r" % (path, e), flush=True)
        return False


def available_roots():
    """可作为保存目录的挂载点 = 管理员挂进容器的目录（可写、非系统路径）。"""
    roots = []
    try:
        with open("/proc/mounts", "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                p = line.split()
                if len(p) < 2:
                    continue
                point = p[1].replace("\\040", " ").replace("\\011", "\t")
                if point in INTERNAL_MOUNTS or point.startswith(SYS_PREFIX) \
                        or point.startswith(APP_PREFIX):
                    continue
                if not os.path.isdir(point) or not os.access(point, os.W_OK):
                    continue
                roots.append(point)
    except Exception as e:
        print("mounts scan failed: %r" % e, flush=True)
    for extra in load_json(ROOTS_FILE, []):
        if isinstance(extra, str) and os.path.isdir(extra) and os.access(extra, os.W_OK):
            roots.append(extra)
    return sorted(set(roots))


def pingvin_config(name):
    """读主站配置（只读），name 形如 share.maxSize。"""
    if "." not in name:
        return None
    cat, key = name.split(".", 1)
    try:
        con = sqlite3.connect("file:%s?mode=ro" % DB_PATH, uri=True, timeout=10)
        try:
            row = con.execute("SELECT value FROM Config WHERE category = ? AND name = ?",
                              (cat, key)).fetchone()
        finally:
            con.close()
        return row[0] if row else None
    except Exception:
        return None


def safe_component(name, fallback="未命名"):
    """把任意字符串变成安全的单层路径片段（挡掉 ../ 和路径分隔符）。"""
    s = (name or "").strip().replace("\\", "_").replace("/", "_")
    s = re.sub(r'[\x00-\x1f<>:"|?*]', "_", s)
    s = s.strip(". ")
    if not s or s in (".", ".."):
        return fallback
    return s[:120]


def resolve_dest(cfg):
    """按配置算出存放目录。返回 (绝对路径, 错误信息)。"""
    root = (cfg.get("root") or "").rstrip("/") or "/"
    allowed = available_roots()
    real_root = os.path.realpath(root)
    if not any(os.path.realpath(r) == real_root or real_root.startswith(os.path.realpath(r) + os.sep)
               for r in allowed):
        return None, "保存目录不在允许范围内：%s" % root
    if not os.path.isdir(root) or not os.access(root, os.W_OK):
        return None, "保存目录不可写：%s" % root
    mode = cfg.get("mode") or "root"
    sub = ""
    if mode == "folder":
        sub = safe_component(cfg.get("folder"), "")
    elif mode == "auto":
        sub = safe_component(cfg.get("task"), "")
    dest = os.path.join(root, sub) if sub else root
    return dest, None


def unique_path(p):
    if not os.path.exists(p):
        return p
    base, ext = os.path.splitext(p)
    for i in range(2, 1000):
        cand = "%s (%d)%s" % (base, i, ext)
        if not os.path.exists(cand):
            return cand
    return "%s (%d)%s" % (base, int(time.time()), ext)


def describe_target(cfg):
    """给人看的保存位置说明。"""
    root = cfg.get("root") or "-"
    mode = cfg.get("mode") or "root"
    if mode == "auto":
        return "%s / 自动以任务名建文件夹「%s」" % (root, cfg.get("task") or "未命名")
    if mode == "folder":
        return "%s / %s" % (root, cfg.get("folder") or "未命名")
    return "%s /（直接放根目录）" % root


def sync_targets():
    """把已配置保存目录的收集链接收到的文件复制过去。返回本次复制的文件数。"""
    cfg = load_json(TARGETS, {})
    if not cfg:
        return 0
    copied = load_json(COPIED, {})
    n = 0
    dirty_cfg = False
    con = sqlite3.connect("file:%s?mode=ro" % DB_PATH, uri=True, timeout=10)
    con.row_factory = sqlite3.Row
    try:
        for token, c in list(cfg.items()):
            if not isinstance(c, dict):
                continue
            rs = con.execute("SELECT id FROM ReverseShare WHERE token = ?", (token,)).fetchone()
            if not rs:
                continue
            dest, err = resolve_dest(c)
            if err:
                if c.get("lastError") != err:
                    c["lastError"] = err
                    dirty_cfg = True
                continue
            try:
                os.makedirs(dest, exist_ok=True)
            except Exception as e:
                c["lastError"] = "无法创建目录：%r" % e
                dirty_cfg = True
                continue
            shares = con.execute("SELECT id FROM Share WHERE reverseShareId = ?",
                                 (rs["id"],)).fetchall()
            for s in shares:
                files = con.execute(
                    "SELECT id, name, size FROM File WHERE shareId = ? ORDER BY createdAt",
                    (s["id"],)).fetchall()
                for f in files:
                    if f["id"] in copied:
                        continue
                    src = file_path(s["id"], f["id"])
                    if not src or not os.path.isfile(src):
                        continue
                    dst = unique_path(os.path.join(dest, safe_component(f["name"], "file")))
                    try:
                        shutil.copy2(src, dst)
                    except Exception as e:
                        c["lastError"] = "复制失败：%r" % e
                        dirty_cfg = True
                        continue
                    copied[f["id"]] = {"path": dst, "ts": time.time(), "share": s["id"]}
                    n += 1
            if c.get("lastError"):
                c["lastError"] = ""
                dirty_cfg = True
            c["lastSync"] = time.time()
    finally:
        con.close()
    if n:
        save_json(COPIED, copied)
    if dirty_cfg:
        save_json(TARGETS, cfg)
    return n


def fetch_links():
    """列出所有收集链接 + 我配的保存目录 + 归档进度。"""
    cfg = load_json(TARGETS, {})
    copied = load_json(COPIED, {})
    con = sqlite3.connect("file:%s?mode=ro" % DB_PATH, uri=True, timeout=10)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "SELECT id, token, createdAt, shareExpiration, remainingUses, maxShareSize, "
            "simplified, publicAccess FROM ReverseShare ORDER BY createdAt DESC").fetchall()
        out = []
        for r in rows:
            sids = [x["id"] for x in con.execute(
                "SELECT id FROM Share WHERE reverseShareId = ?", (r["id"],)).fetchall()]
            nf = nb = 0
            for sid in sids:
                for f in con.execute("SELECT id, size FROM File WHERE shareId = ?", (sid,)).fetchall():
                    nf += 1
                    try:
                        nb += int(f["size"])
                    except Exception:
                        pass
            c = cfg.get(r["token"]) or {}
            arch = sum(1 for k, v in copied.items() if v.get("share") in set(sids))
            out.append({
                "id": r["id"], "token": r["token"],
                "ts": parse_ts(r["createdAt"]),
                "expiration": parse_ts(r["shareExpiration"]),
                "remaining": r["remainingUses"],
                "maxsize": r["maxShareSize"],
                "cfg": c, "target": describe_target(c) if c.get("root") else "",
                "lastError": c.get("lastError") or "",
                "nfiles": nf, "nbytes": nb, "narch": arch,
            })
        return out
    finally:
        con.close()


def pingvin_api(method, path, body=None, cookie=None):
    """带着管理员的 cookie 调主站接口（用他的身份，不自己造令牌）。"""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(PINGVIN_API + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if cookie:
        req.add_header("Cookie", cookie)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, repr(e)


def sync_worker():
    while True:
        try:
            time.sleep(SYNC_INTERVAL)
            n = sync_targets()
            if n:
                print("auto-archive: copied %d file(s)" % n, flush=True)
        except Exception as e:
            print("sync_worker error: %r" % e, flush=True)


# --------------------------------------------------------------------------- 数据

def fetch_uploads():
    """返回所有来自反向分享的上传（新到旧）。"""
    con = sqlite3.connect("file:%s?mode=ro" % DB_PATH, uri=True, timeout=10)
    con.row_factory = sqlite3.Row
    try:
        shares = con.execute(
            "SELECT s.id, s.name, s.createdAt, s.expiration, s.isZipReady, "
            "       s.storageProvider, s.description, r.token AS rsToken "
            "FROM Share s LEFT JOIN ReverseShare r ON r.id = s.reverseShareId "
            "WHERE s.reverseShareId IS NOT NULL "
            "ORDER BY s.createdAt DESC"
        ).fetchall()
        out = []
        for s in shares:
            files = con.execute(
                "SELECT id, name, size, createdAt FROM File WHERE shareId = ? "
                "ORDER BY createdAt, name",
                (s["id"],),
            ).fetchall()
            items = []
            total = 0
            n_img = n_vid = 0
            for f in files:
                try:
                    sz = int(f["size"])
                except Exception:
                    sz = 0
                total += sz
                e = ext_of(f["name"])
                kind = "img" if e in IMG_EXT else ("vid" if e in VID_EXT else "file")
                if kind == "img":
                    n_img += 1
                elif kind == "vid":
                    n_vid += 1
                items.append({
                    "id": f["id"], "name": f["name"] or "未命名",
                    "size": sz, "kind": kind, "ext": e,
                    "ts": parse_ts(f["createdAt"]),
                })
            out.append({
                "id": s["id"],
                "name": s["name"] or "",
                "ts": parse_ts(s["createdAt"]),
                "expiration": parse_ts(s["expiration"]),
                "storage": s["storageProvider"],
                "note": (s["description"] or "").strip(),
                "rsToken": s["rsToken"] or "",
                "files": items,
                "count": len(items),
                "total": total,
                "n_img": n_img,
                "n_vid": n_vid,
            })
        return out
    finally:
        con.close()


def file_path(share_id, file_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", share_id or ""):
        return None
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", file_id or ""):
        return None
    return os.path.join(UPLOADS, share_id, file_id)


def share_dir(share_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", share_id or ""):
        return None
    return os.path.join(UPLOADS, share_id)


def fresh_archive_zip(share_id, files):
    """Pingvin 自己生成的 archive.zip，比所有文件新就用它（省 CPU）。"""
    d = share_dir(share_id)
    if not d:
        return None
    zp = os.path.join(d, "archive.zip")
    try:
        zmt = os.path.getmtime(zp)
    except OSError:
        return None
    for f in files:
        p = file_path(share_id, f["id"])
        try:
            if os.path.getmtime(p) > zmt:
                return None
        except OSError:
            return None
    return zp


def build_zip(share_id, files):
    """自己打包（STORED，照片视频本来已压缩，省 CPU）。"""
    os.makedirs(CACHE, exist_ok=True)
    tmp = os.path.join(CACHE, "zip-%s-%d.zip" % (share_id, int(time.time())))
    used = set()
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_STORED) as z:
        for f in files:
            p = file_path(share_id, f["id"])
            if not p or not os.path.exists(p):
                continue
            arc = f["name"] or f["id"]
            if arc in used:
                base, ext = os.path.splitext(arc)
                i = 2
                while "%s (%d)%s" % (base, i, ext) in used:
                    i += 1
                arc = "%s (%d)%s" % (base, i, ext)
            used.add(arc)
            z.write(p, arcname=arc)
    return tmp


def thumb_path(share_id, f):
    """生成/复用缩略图；失败返回 None（前端回退到原图）。"""
    if not HAVE_PIL or f["kind"] != "img":
        return None
    src = file_path(share_id, f["id"])
    if not src or not os.path.exists(src):
        return None
    d = os.path.join(CACHE, "thumb", share_id)
    dst = os.path.join(d, f["id"] + ".jpg")
    try:
        if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            return dst
        os.makedirs(d, exist_ok=True)
        im = Image.open(src)
        im = ImageOps.exif_transpose(im)
        im.thumbnail((520, 520))
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        im.save(dst, "JPEG", quality=82, optimize=True)
        return dst
    except Exception:
        return None


SHELL_CSS = """
:root{
  --bg:#1A1B1E;            /* 页面底色 = Mantine dark[7] */
  --paper:#25262B;         /* 卡片 = dark[6] */
  --paper2:#2C2E33;        /* 输入框/次级块 = dark[5] */
  --line:#373A40;          /* 边框 = dark[4] */
  --div:#2C2E33;           /* 分割线 */
  --fg:#C1C2C5;            /* 正文 = dark[0] */
  --fg-strong:#F8F9FA;
  --dim:#909296;           /* 次要文字 = dark[2] */
  --pri:#544AF4;           /* 主色 = victoria[4] */
  --pri-deep:#4239C8;      /* victoria[6] */
  --pri-bg:rgba(71,66,142,.22);
  --ok:#37b24d;  --ok-fg:#8ce99a;  --ok-bg:rgba(55,178,77,.14);
  --warn-fg:#ffd43b; --warn-bg:rgba(245,159,0,.14);
  --danger:#fa5252; --danger-fg:#ffa8a8; --danger-bg:rgba(250,82,82,.12);
  --r:4px;                 /* 控件圆角 = 主题 defaultRadius(sm) */
  --r-card:8px;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
  font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,
    "PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;
  -webkit-text-size-adjust:100%}
a{color:var(--pri);text-decoration:none}
a:hover{text-decoration:underline}

/* ---------- 顶栏：对齐主站（56px / logo / 站点名 / 细分割线）---------- */
header.top{position:sticky;top:0;z-index:9;height:56px;display:flex;align-items:center;
  gap:10px;padding:0 16px;background:var(--bg);border-bottom:1px solid var(--div)}
header.top img{width:34px;height:34px;border-radius:8px;object-fit:contain;display:block}
header.top .name{font-size:17px;font-weight:600;color:var(--fg-strong);min-width:0;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
header.top .sp{flex:1}
header.top .out{font-size:13px;color:var(--dim);white-space:nowrap}

main{max-width:900px;margin:0 auto;padding:8px 16px 60px}
h1{font-size:22px;line-height:1.35;margin:16px 0 6px;font-weight:700;color:var(--fg-strong);
  display:flex;align-items:center;gap:8px;flex-wrap:wrap}
h2{font-size:16px;margin:0 0 12px;font-weight:600;color:var(--fg-strong)}
.sub{color:var(--dim);font-size:13.5px;margin-bottom:18px}
.pill{background:var(--ok-bg);color:var(--ok-fg);border-radius:999px;font-size:12px;
  padding:2px 10px;font-weight:700}

/* ---------- 卡片 ---------- */
.card{background:var(--paper);border:1px solid var(--line);border-radius:var(--r-card);
  padding:16px;margin-bottom:14px}
.card.new{border-color:rgba(55,178,77,.55)}
.note{background:var(--pri-bg);border-left:3px solid var(--pri);border-radius:var(--r);
  padding:9px 12px;margin:12px 0 0;font-size:13.5px;color:var(--fg);word-break:break-all}
.chead{display:flex;justify-content:space-between;gap:10px;align-items:flex-start;flex-wrap:wrap}
.title{font-weight:600;font-size:16px;color:var(--fg-strong);word-break:break-all}
.meta{color:var(--dim);font-size:12.5px;margin-top:4px}

/* ---------- 缩略图网格 ---------- */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(96px,1fr));gap:8px;margin:14px 0}
.th{position:relative;aspect-ratio:1;border-radius:var(--r-card);overflow:hidden;
  background:var(--paper2);display:block}
.th img{width:100%;height:100%;object-fit:cover;display:block}
.th .ph{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  font-size:26px;color:var(--dim)}
.th .tag{position:absolute;left:5px;bottom:5px;background:rgba(0,0,0,.7);
  border-radius:var(--r);padding:1px 6px;font-size:11px;color:#fff;margin:0}

/* ---------- 文件列表 ---------- */
ul.fl{list-style:none;margin:8px 0 0;padding:0}
ul.fl li{display:flex;justify-content:space-between;gap:10px;align-items:center;
  padding:9px 0;border-top:1px solid var(--div);font-size:13.5px}
ul.fl li:first-child{border-top:0}
.fn{word-break:break-all;flex:1;min-width:0}
.fs{color:var(--dim);font-size:12px;white-space:nowrap}
a.dl{color:var(--pri);font-weight:600;white-space:nowrap}

/* ---------- 按钮：主按钮用实心，次按钮用 light 变体 ---------- */
.btn{display:inline-block;background:var(--pri-deep);color:#fff;font-weight:600;
  padding:9px 16px;border-radius:var(--r);font-size:14px;border:0;cursor:pointer;
  font-family:inherit;line-height:1.4}
.btn:hover{filter:brightness(1.12);text-decoration:none}
.btn.ghost{background:var(--pri-bg);color:var(--pri)}
.btn.danger{background:var(--danger-bg);color:var(--danger-fg)}
.bar{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin-top:12px}

/* ---------- 表单 ---------- */
.fld{margin:14px 0}
.fld>label{display:block;color:var(--dim);font-size:12.5px;margin-bottom:6px}
input[type=text],input[type=number],select{width:100%;background:var(--paper2);color:var(--fg);
  border:1px solid var(--line);border-radius:var(--r);padding:9px 12px;font-size:14px;
  font-family:inherit;min-height:38px}
input[type=text]:focus,input[type=number]:focus,select:focus{outline:none;border-color:var(--pri)}
.rad{display:flex;align-items:center;gap:8px;margin:9px 0;font-size:14px}
.rad input[type=text]{flex:1;min-width:80px}
.rad input[type=radio],.rad input[type=checkbox]{width:16px;height:16px;min-height:0;
  accent-color:var(--pri);flex:0 0 auto}

/* ---------- 提示条 ---------- */
.msg{background:var(--ok-bg);border:1px solid rgba(55,178,77,.45);color:var(--ok-fg);
  padding:10px 14px;border-radius:var(--r);margin-bottom:14px;font-size:13.5px;
  word-break:break-all}
.msg.err{background:var(--danger-bg);border-color:rgba(250,82,82,.45);color:var(--danger-fg)}
.msg.note{background:var(--paper2);border-color:var(--line);color:var(--dim)}

/* ---------- 表格 / 标签 ---------- */
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:10px 8px;border-bottom:1px solid var(--div);vertical-align:top}
th{color:var(--dim);font-weight:600;font-size:12px;white-space:nowrap}
.mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11.5px;word-break:break-all}
.tag{display:inline-block;background:var(--paper2);border-radius:var(--r);padding:2px 8px;
  font-size:11.5px;color:var(--dim);margin:1px 3px 1px 0}
.tag.ok{background:var(--ok-bg);color:var(--ok-fg)}
.tag.warn{background:var(--warn-bg);color:var(--warn-fg)}

details summary{cursor:pointer;color:var(--dim);font-size:13px;margin-top:9px}
details summary:hover{color:var(--fg)}
.empty{text-align:center;color:var(--dim);padding:48px 12px;font-size:14px}
footer{color:var(--dim);font-size:12px;text-align:center;margin-top:28px;line-height:1.9;
  border-top:1px solid var(--div);padding-top:16px}
"""


def shell_head():
    """顶栏：与主站一致。链接用绝对路径，插进页面后不要再做前缀替换。"""
    name = pingvin_config("general.appName") or "文件收集站"
    return ('<header class="top">'
            '<img src="/img/logo.png" alt="" '
            'onerror="this.style.visibility=\'hidden\'">'
            '<div class="name">%s</div><div class="sp"></div>'
            '<a class="out" href="/account/reverseShares">主站后台</a>'
            '</header>' % html.escape(name))

COLLECT_PAGE = """<!doctype html>
<html lang="zh-CN"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#1A1B1E">
<title>文件收集</title>
<style>__CSS__</style></head><body>
__HEAD__
<main>
<h1>文件收集</h1>
<div class="sub">创建收集链接，并指定这个链接收到的文件保存到哪个目录</div>
__MSG__
<div class="card">
<h2>创建收集链接</h2>
<form method="post" action="/collect/create">
  <div class="fld"><label>任务名称（勾选「自动建文件夹」时用它做文件夹名）</label>
    <input type="text" name="task" value="__TASK__" placeholder="例如：2026国庆家庭照片"></div>
  <div class="fld"><label>保存位置</label><select name="root">__ROOTS__</select></div>
  <div class="fld"><label>存放方式</label>
    <label class="rad"><input type="radio" name="mode" value="root" checked> 直接放在所选目录的根目录</label>
    <label class="rad"><input type="radio" name="mode" value="folder"> 在所选目录下新建文件夹：
      <input type="text" name="folder" placeholder="文件夹名"></label>
    <label class="rad"><input type="checkbox" name="auto_folder" value="1">
      <b>自动以任务名新建文件夹</b>（勾选后忽略上面的选择）</label>
  </div>
  <div class="fld"><label>备注</label>
    <label class="rad"><input type="checkbox" name="needNote" value="1">
      <b>要求上传者填写备注</b>（开启后对方每次上传都必须填一次，方便知道是谁传的）</label>
  </div>
  <div class="fld"><label>可使用次数（对方每上传一次扣一次）</label>
    <input type="number" name="maxUseCount" value="1000" min="1" max="1000"></div>
  <div class="fld"><label>有效期（到期后对方不能再上传；<b>已收到的文件不会丢</b>）</label><select name="expiration">
    <option value="7-days">7 天</option>
    <option value="30-days">30 天</option>
    <option value="90-days">90 天</option>
    <option value="365-days" selected>1 年（推荐）</option>
    <option value="3650-days">10 年</option>
  </select></div>
  <div class="msg note">
    提示：删除链接只会让链接失效，<b>已经收到的文件会保留</b>在「收件箱」里，也会保留在保存目录中。
  </div>
  <button class="btn" type="submit">创建收集链接</button>
</form>
</div>
<div class="card">
<h2>已有收集链接</h2>
__LIST__
<form method="post" action="/collect/sync" style="margin-top:14px">
  <button class="btn ghost" type="submit">立即归档一次</button>
</form>
</div>
<footer><a href="/">← 收件箱</a><br>生成于 __NOW__</footer>
</main>
</body></html>"""


# --------------------------------------------------------------------------- 页面

PAGE = """<!doctype html>
<html lang="zh-CN"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#1A1B1E">
<title>收件箱</title>
<style>__CSS__</style></head><body>
__HEAD__
<main>
<h1>收件箱__PILL__</h1>
<div class="sub">__SUB__</div>
__BODY__
<footer>只读视图 · 删除链接、改有效期请到 <a href="/account/reverseShares">主站后台</a><br>生成于 __NOW__</footer>
</main>
</body></html>"""


def prefix_links(body, B):
    if not B:
        return body
    b = B.lstrip("/")          # 注意：替换串本身已含前导斜杠，B 不能再带
    for a in ('href="/', 'src="/', 'action="/'):
        body = body.replace(a, '%s%s/' % (a, b))
    return body


def app_base_url():
    """主站对外地址：读主站配置的 general.appUrl。

    不要在这里写死域名——换台机器部署（比如 NAS）就会显示成别人的地址。
    读不到就返回空串，链接退化成相对路径，在浏览器里点仍然是对的。
    """
    try:
        con = sqlite3.connect("file:%s?mode=ro" % DB_PATH, uri=True, timeout=5)
        row = con.execute("select value from Config where category='general' and name='appUrl'"
                          ).fetchone()
        con.close()
        v = (row[0] if row else "") or ""
        if v.startswith("http"):
            return v.rstrip("/")
    except Exception:
        pass
    return ""


def render_collect(links, msg=None, is_err=False):
    B = BASE_PATH
    base = app_base_url()
    roots = available_roots()
    opts = "".join('<option value="%s">%s</option>' % (html.escape(r, quote=True), html.escape(r))
                   for r in roots)
    if not roots:
        opts = '<option value="">（没有可用的挂载目录）</option>'

    rows = []
    for l in links:
        tok = html.escape(l["token"], quote=True)
        url = base + "/upload/" + tok
        if l["expiration"]:
            days = int((l["expiration"] - time.time()) // 86400)
            exp = ("剩余 %d 天" % days) if days >= 0 else "已过期"
        else:
            exp = "永久"
        if l["cfg"].get("root"):
            if l["lastError"]:
                tgt = '<span class="tag warn">%s</span>' % html.escape(l["lastError"])
            else:
                tgt = '<span class="tag ok">%s</span>' % html.escape(l["target"])
            tgt += '<div class="tag">已归档 %d/%d 个文件</div>' % (l["narch"], l["nfiles"])
        else:
            tgt = '<span class="tag warn">未设置保存位置（不会归档）</span>'
        cur = l["cfg"].get("root") or ""
        sel = "".join('<option value="%s"%s>%s</option>' %
                      (html.escape(r, quote=True), " selected" if r == cur else "", html.escape(r))
                      for r in roots)
        mode = l["cfg"].get("mode") or "root"
        rows.append(
            '<tr><td>'
            '<div style="font-weight:600">%s</div>'
            '<div class="mono">%s</div>'
            '<div style="margin-top:5px">'
            '<a href="%s" target="_blank">打开上传页</a> · '
            '<span class="tag">剩余 %s 次</span><span class="tag">%s</span>'
            '<span class="tag%s">%s</span>'
            '</div></td>'
            '<td>%s'
            '<details><summary>修改保存位置</summary>'
            '<form method="post" action="/collect/target">'
            '<input type="hidden" name="token" value="%s">'
            '<div class="fld"><label>保存位置</label><select name="root">%s</select></div>'
            '<div class="fld"><label>存放方式</label>'
            '<label class="rad"><input type="radio" name="mode" value="root"%s> 根目录</label>'
            '<label class="rad"><input type="radio" name="mode" value="folder"%s> 新建文件夹'
            '<input type="text" name="folder" value="%s"></label>'
            '<label class="rad"><input type="checkbox" name="auto_folder" value="1"%s> 自动以任务名建文件夹</label>'
            '</div>'
            '<div class="fld"><label>任务名称</label>'
            '<input type="text" name="task" value="%s"></div>'
            '<div class="fld"><label>备注</label>'
            '<label class="rad"><input type="checkbox" name="needNote" value="1"%s>'
            ' 要求上传者填写备注</label></div>'
            '<button class="btn" type="submit">保存</button>'
            '</form></details></td>'
            '<td><form method="post" action="/collect/delete" '
            'onsubmit="return confirm(&quot;删除这个收集链接？对方将无法再上传；已经收到的文件会保留，不会丢。&quot;)">'
            '<input type="hidden" name="token" value="%s">'
            '<button class="btn danger" type="submit">删除</button></form></td></tr>'
            % (html.escape(l["cfg"].get("task") or "（未命名任务）"),
               html.escape(url),
               html.escape(url, quote=True),
               html.escape(str(l["remaining"])), html.escape(exp),
               " ok" if l["cfg"].get("needNote") else "",
               "要填备注" if l["cfg"].get("needNote") else "不填备注",
               tgt, tok, sel,
               " checked" if mode == "root" else "",
               " checked" if mode == "folder" else "",
               html.escape(l["cfg"].get("folder") or "", quote=True),
               " checked" if mode == "auto" else "",
               html.escape(l["cfg"].get("task") or "", quote=True),
               " checked" if l["cfg"].get("needNote") else "",
               tok)
        )
    if rows:
        listing = ('<table><thead><tr><th>任务 / 链接</th><th>保存位置</th><th></th></tr></thead>'
                   '<tbody>%s</tbody></table>' % "".join(rows))
    else:
        listing = '<div class="empty">还没有收集链接。上面填一下就能创建。</div>'

    m = ""
    if msg:
        m = '<div class="msg%s">%s</div>' % (" err" if is_err else "", html.escape(msg))

    page = COLLECT_PAGE
    page = page.replace("__MSG__", m)
    page = page.replace("__TASK__", html.escape(time.strftime("收集-%Y%m%d")))
    page = page.replace("__ROOTS__", opts)
    page = page.replace("__LIST__", listing)
    page = page.replace("__NOW__", time.strftime("%Y-%m-%d %H:%M:%S"))
    page = prefix_links(page, B)
    page = page.replace("__CSS__", SHELL_CSS)
    # 顶栏里是绝对路径（/img、/account、/inbox），必须放在前缀替换之后
    page = page.replace("__HEAD__", shell_head())
    return page


def render(uploads, seen):
    B = BASE_PATH
    new_ids = [u["id"] for u in uploads if u["id"] not in seen]
    new_set = set(new_ids)
    total_bytes = sum(u["total"] for u in uploads)
    n_files = sum(u["count"] for u in uploads)

    targets = load_json(TARGETS, {})

    pill = ' <span class="pill">%d 个新</span>' % len(new_ids) if new_ids else ""
    sub = "共 %d 次上传 · %d 个文件 · %s" % (len(uploads), n_files, human(total_bytes))

    if not uploads:
        body = '<div class="empty">还没有收到任何上传。<br><br>把反向分享链接发出去，别人上传后就会出现在这里。</div>'
    else:
        cards = []
        for u in uploads:
            sid = html.escape(u["id"], quote=True)
            if u["name"]:
                title = html.escape(u["name"])
            elif u["files"]:
                fn = u["files"][0]["name"]
                if len(fn) > 34:
                    fn = fn[:31] + "…"
                title = html.escape(fn)
                if u["count"] > 1:
                    title += ('<span style="color:#94a3b8;font-weight:400"> 等 %d 个</span>'
                              % u["count"])
            else:
                title = "（空上传）"
            bits = ["%d 个文件" % u["count"], human(u["total"]), fmt_ts(u["ts"])]
            tcfg = targets.get(u.get("rsToken") or "") or {}
            if tcfg.get("task"):
                bits.insert(0, "来自「%s」" % tcfg["task"])
            elif u.get("rsToken"):
                bits.insert(0, "来自「%s」" % u["rsToken"])
            if u["n_img"]:
                bits.append("%d 图" % u["n_img"])
            if u["n_vid"]:
                bits.append("%d 视频" % u["n_vid"])
            if u["expiration"]:
                days = int((u["expiration"] - time.time()) // 86400)
                bits.append("剩余 %d 天" % days if days >= 0 else "已过期")
            meta = html.escape(" · ".join(bits))

            thumbs = []
            for f in u["files"]:
                if f["kind"] != "img":
                    continue
                fid = html.escape(f["id"], quote=True)
                nm = html.escape(f["name"], quote=True)
                thumbs.append(
                    '<a class="th" href="/raw/%s/%s" target="_blank" title="%s">'
                    '<img loading="lazy" src="/t/%s/%s" alt="%s">'
                    '<span class="tag">%s</span></a>'
                    % (sid, fid, nm, sid, fid, nm, html.escape(human(f["size"])))
                )
            for f in u["files"]:
                if f["kind"] != "vid":
                    continue
                fid = html.escape(f["id"], quote=True)
                nm = html.escape(f["name"], quote=True)
                thumbs.append(
                    '<a class="th" href="/raw/%s/%s" target="_blank" title="%s">'
                    '<span class="ph">▶</span>'
                    '<span class="tag">%s</span></a>'
                    % (sid, fid, nm, html.escape(human(f["size"])))
                )
            grid = '<div class="grid">%s</div>' % "".join(thumbs) if thumbs else ""

            rows = []
            for f in u["files"]:
                fid = html.escape(f["id"], quote=True)
                nm = html.escape(f["name"])
                rows.append(
                    '<li><span class="fn">%s</span><span class="fs">%s</span>'
                    '<a class="dl" href="/f/%s/%s">下载</a></li>'
                    % (nm, html.escape(human(f["size"])), sid, fid)
                )
            listing = ""
            if rows:
                listing = (
                    '<details><summary>展开文件列表（%d）</summary><ul class="fl">%s</ul></details>'
                    % (len(rows), "".join(rows))
                )

            note_html = ""
            if u.get("note"):
                note_html = '<div class="note">备注：%s</div>' % html.escape(u["note"])

            cards.append(
                '<div class="card%s"><div class="chead"><div>'
                '<div class="title">%s</div><div class="meta">%s</div></div>'
                '<a class="btn" href="/z/%s">下载全部 (ZIP)</a></div>'
                "%s%s%s</div>"
                % (" new" if u["id"] in new_set else "", title, meta, sid,
                   note_html, grid, listing)
            )
        body = "".join(cards)

    # 这里的替换串不含 a，B 必须自带前导斜杠（与 prefix_links 的规则相反）
    body = (body.replace('href="/', 'href="%s/' % B)
                .replace('src="/', 'src="%s/' % B))

    page = PAGE
    page = page.replace("__PILL__", pill)
    page = page.replace("__SUB__", html.escape(sub))
    page = page.replace("__BODY__", body)
    page = page.replace("__NOW__", time.strftime("%Y-%m-%d %H:%M:%S"))
    page = page.replace("__BASE__", B)
    page = page.replace("__CSS__", SHELL_CSS)
    page = page.replace("__HEAD__", shell_head())
    return page


LOGIN_PAGE = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>收件箱 · 需要登录</title></head>
<body style="margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
background:#f8fafc;font:15px/1.7 -apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;color:#0f172a">
<div style="max-width:420px;padding:32px;background:#fff;border-radius:14px;
box-shadow:0 1px 3px rgba(15,23,42,.08);text-align:center">
<h2 style="margin:0 0 10px;font-size:19px">需要管理员登录</h2>
<p style="margin:0 0 20px;color:#64748b">收件箱用的是文件收集站的登录态。<br>请先用管理员账号登录，再回到这个页面。</p>
<a href="__BASE__/auth/signIn" style="display:inline-block;padding:10px 20px;background:#544AF4;color:#fff;
border-radius:8px;text-decoration:none;font-weight:600">去登录</a>
<p style="margin:16px 0 0"><a href="__BASE__/" style="color:#64748b;font-size:13px">已登录？点此重试</a></p>
</div></body></html>"""


# --------------------------------------------------------------------------- HTTP

class Handler(BaseHTTPRequestHandler):
    server_version = "Inbox/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        print("%s %s" % (self.address_string(), fmt % args), flush=True)

    # ---- 鉴权：直接复用文件收集站的登录态，只有管理员能看
    _sess_cache = {}

    def current_user(self):
        """把浏览器带来的 cookie 原样转给主站 /api/users/me 判断。"""
        cookie = self.headers.get("Cookie") or ""
        if not cookie:
            return None
        now = time.time()
        hit = Handler._sess_cache.get(cookie)
        if hit and hit[0] > now:
            return hit[1]
        user = None
        try:
            req = urllib.request.Request(
                PINGVIN_API + "/api/users/me",
                headers={"Cookie": cookie, "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=6) as r:
                if r.status == 200:
                    user = json.loads(r.read().decode("utf-8"))
        except Exception:
            user = None
        if user:            # 只缓存成功结果，刚登录不用等缓存过期
            if len(Handler._sess_cache) > 500:
                Handler._sess_cache.clear()
            Handler._sess_cache[cookie] = (now + 60, user)
        return user

    def authorized(self):
        u = self.current_user()
        return bool(u) and bool(u.get("isAdmin"))

    def deny(self):
        return self.send_bytes(LOGIN_PAGE.replace("__BASE__", BASE_PATH).encode("utf-8"),
                               "text/html; charset=utf-8", 403)

    # ---- 响应helper
    def send_bytes(self, data, ctype, code=200, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_file(self, path, name, inline=False):
        try:
            st = os.stat(path)
        except OSError:
            return self.send_bytes(b"not found", "text/plain; charset=utf-8", 404)
        size = st.st_size
        ctype = MIME.get(ext_of(name), "application/octet-stream")
        start, end, code = 0, size - 1, 200
        rng = self.headers.get("Range")
        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)", rng.strip())
            if m:
                if m.group(1):
                    start = int(m.group(1))
                if m.group(2):
                    end = int(m.group(2))
                if start >= size:
                    self.send_response(416)
                    self.send_header("Content-Range", "bytes */%d" % size)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                end = min(end, size - 1)
                code = 206
        length = end - start + 1
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Last-Modified", formatdate(st.st_mtime, usegmt=True))
        self.send_header("Cache-Control", "private, max-age=3600")
        self.send_header(
            "Content-Disposition",
            "%s; filename*=UTF-8''%s" % ("inline" if inline else "attachment",
                                         urllib.parse.quote(name or "file")),
        )
        if code == 206:
            self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
        self.end_headers()
        try:
            with open(path, "rb") as f:
                f.seek(start)
                left = length
                while left > 0:
                    chunk = f.read(min(262144, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    # ---- 表单提交
    def redirect(self, to):
        self.send_response(303)
        self.send_header("Location", to)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _read_body(self):
        """必须把请求体读完再回响应。

        没读完的话，keep-alive 连接上剩下的字节会被当成下一个请求行解析，
        日志里出现 `Unsupported method ('token=xxxGET')` 这种 501，
        而且只在「POST 被拒」之后才复现，很难查。
        """
        try:
            ln = int(self.headers.get("Content-Length") or 0)
        except Exception:
            ln = 0
        if ln <= 0:
            return b""
        if ln > MAX_BODY:
            # 太大：不读，但标记这条连接不要复用，避免污染后续请求
            self.close_connection = True
            return b""
        return self.rfile.read(ln)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        if BASE_PATH and (path == BASE_PATH or path.startswith(BASE_PATH + "/")):
            path = path[len(BASE_PATH):]
        if not path.startswith("/"):
            path = "/" + path
        raw = self._read_body()          # 先读完，再判权限
        if not self.authorized():
            return self.deny()
        form = {k: v[0] for k, v in
                urllib.parse.parse_qs(raw.decode("utf-8", "replace")).items()}
        try:
            if path == "/collect/create":
                return self.post_create(form)
            if path == "/collect/target":
                return self.post_target(form)
            if path == "/collect/config":
                return self.post_config(form)
            if path == "/collect/delete":
                return self.post_delete(form)
            if path == "/collect/sync":
                n = sync_targets()
                return self.redirect("%s/collect?m=%s" % (
                    BASE_PATH, urllib.parse.quote("归档完成，本次复制了 %d 个文件" % n)))
            return self.send_bytes(b"not found", "text/plain; charset=utf-8", 404)
        except Exception as e:
            print("POST ERROR %s: %r" % (self.path, e), flush=True)
            return self.redirect("%s/collect?err=1&m=%s" % (
                BASE_PATH, urllib.parse.quote("操作失败：%r" % e)))

    def _cfg_from_form(self, form):
        task = (form.get("task") or "").strip()
        root = (form.get("root") or "").strip()
        mode = (form.get("mode") or "").strip()
        if form.get("auto_folder"):
            mode = "auto"
        if mode not in ("root", "folder", "auto"):
            mode = "root"
        cfg = {"task": task, "root": root, "mode": mode,
               "folder": (form.get("folder") or "").strip(),
               "needNote": bool(form.get("needNote"))}
        _dest, err = resolve_dest(cfg)
        if err:
            return None, err
        return cfg, None

    def post_create(self, form):
        cfg, err = self._cfg_from_form(form)
        if err:
            return self.redirect("%s/collect?err=1&m=%s" % (BASE_PATH, urllib.parse.quote(err)))
        try:
            uses = int(form.get("maxUseCount") or 1000)
        except Exception:
            uses = 1000
        uses = max(1, min(1000, uses))
        exp = form.get("expiration") or "30-days"
        if not re.fullmatch(r"[0-9]{1,5}-(minutes|hours|days|weeks|months|years)", exp):
            exp = "30-days"
        maxsize = pingvin_config("share.maxSize") or "10737418240"
        if not re.fullmatch(r"[0-9]+", maxsize):
            maxsize = "10737418240"
        body = {"sendEmailNotification": False, "maxShareSize": maxsize,
                "shareExpiration": exp, "maxUseCount": uses,
                "simplified": True, "publicAccess": True}
        code, text = pingvin_api("POST", "/api/reverseShares", body,
                                 cookie=self.headers.get("Cookie") or "")
        if code not in (200, 201):
            return self.redirect("%s/collect?err=1&m=%s" % (
                BASE_PATH, urllib.parse.quote("主站拒绝创建：%s %s" % (code, text[:160]))))
        try:
            tok = json.loads(text).get("token")
        except Exception:
            tok = None
        if not tok:
            return self.redirect("%s/collect?err=1&m=%s" % (
                BASE_PATH, urllib.parse.quote("主站没返回 token：%s" % text[:160])))
        cfg["createdAt"] = time.time()
        cfg["lastError"] = ""
        tg = load_json(TARGETS, {})
        tg[tok] = cfg
        save_json(TARGETS, tg)
        try:
            os.makedirs(cfg.get("root") or "/", exist_ok=True)
        except Exception:
            pass
        n = sync_targets()
        return self.redirect("%s/collect?m=%s" % (BASE_PATH, urllib.parse.quote(
            "已创建收集链接，保存到 %s（本次归档 %d 个文件）" % (describe_target(cfg), n))))

    def post_target(self, form):
        tok = (form.get("token") or "").strip()
        tg = load_json(TARGETS, {})
        if not re.fullmatch(r"[A-Za-z0-9_-]{3,50}", tok):
            return self.redirect("%s/collect?err=1&m=%s" % (
                BASE_PATH, urllib.parse.quote("链接标识不合法")))
        cfg, err = self._cfg_from_form(form)
        if err:
            return self.redirect("%s/collect?err=1&m=%s" % (BASE_PATH, urllib.parse.quote(err)))
        old = tg.get(tok) or {}
        cfg["createdAt"] = old.get("createdAt") or time.time()
        cfg["lastError"] = ""
        tg[tok] = cfg
        save_json(TARGETS, tg)
        n = sync_targets()
        return self.redirect("%s/collect?m=%s" % (BASE_PATH, urllib.parse.quote(
            "已更新保存位置为 %s（本次归档 %d 个文件）" % (describe_target(cfg), n))))

    def post_config(self, form):
        """给「创建文件收集」弹窗用：链接已由主站创建，这里只登记保存目录配置。"""
        tok = (form.get("token") or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{3,50}", tok):
            return self.send_bytes(
                json.dumps({"ok": False, "error": "链接标识不合法"},
                           ensure_ascii=False).encode("utf-8"),
                "application/json; charset=utf-8", 400)
        cfg, err = self._cfg_from_form(form)
        if err:
            return self.send_bytes(
                json.dumps({"ok": False, "error": err}, ensure_ascii=False).encode("utf-8"),
                "application/json; charset=utf-8", 400)
        tg = load_json(TARGETS, {})
        old = tg.get(tok) or {}
        cfg["createdAt"] = old.get("createdAt") or time.time()
        tg[tok] = cfg
        save_json(TARGETS, tg)
        dest, _ = resolve_dest(cfg)
        return self.send_bytes(
            json.dumps({"ok": True, "dest": dest}, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8")

    def post_delete(self, form):
        tok = (form.get("token") or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{3,50}", tok):
            return self.redirect("%s/collect?err=1&m=%s" % (
                BASE_PATH, urllib.parse.quote("链接标识不合法")))
        # 删链接之前先归档一次，确保已收到的文件在保存目录里有一份
        sync_targets()
        con = sqlite3.connect("file:%s?mode=ro" % DB_PATH, uri=True, timeout=10)
        try:
            row = con.execute("SELECT id FROM ReverseShare WHERE token = ?", (tok,)).fetchone()
        finally:
            con.close()
        if not row:
            return self.redirect("%s/collect?err=1&m=%s" % (
                BASE_PATH, urllib.parse.quote("这个链接已经不存在了")))
        code, text = pingvin_api("DELETE", "/api/reverseShares/" + row[0],
                                 cookie=self.headers.get("Cookie") or "")
        if code not in (200, 204):
            return self.redirect("%s/collect?err=1&m=%s" % (
                BASE_PATH, urllib.parse.quote("主站拒绝删除：%s %s" % (code, text[:160]))))
        tg = load_json(TARGETS, {})
        tg.pop(tok, None)
        save_json(TARGETS, tg)
        return self.redirect("%s/collect?m=%s" % (BASE_PATH, urllib.parse.quote("已删除该收集链接")))

    # ---- 路由
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        if BASE_PATH and (path == BASE_PATH or path.startswith(BASE_PATH + "/")):
            path = path[len(BASE_PATH):]
        if not path.startswith("/"):
            path = "/" + path
        parts = [p for p in path.split("/") if p]

        if path == "/healthz":           # 探活不需要鉴权
            return self.send_bytes(b"ok", "text/plain; charset=utf-8")
        if path == "/collect/note.json":  # 上传页要问「这链接要不要备注」，访客未登录
            q = urllib.parse.parse_qs(parsed.query)
            tok = (q.get("token") or [""])[0].strip()
            need = False
            if re.fullmatch(r"[A-Za-z0-9_-]{3,50}", tok):
                need = bool((load_json(TARGETS, {}).get(tok) or {}).get("needNote"))
            return self.send_bytes(
                json.dumps({"need": need}, ensure_ascii=False).encode("utf-8"),
                "application/json; charset=utf-8")
        if not self.authorized():
            return self.deny()

        try:
            if path == "/collect/roots.json":
                return self.send_bytes(
                    json.dumps({"roots": available_roots()},
                               ensure_ascii=False).encode("utf-8"),
                    "application/json; charset=utf-8")

            if path == "/collect":
                q = urllib.parse.parse_qs(parsed.query)
                return self.send_bytes(
                    render_collect(fetch_links(),
                                   (q.get("m") or [""])[0],
                                   (q.get("err") or [""])[0] == "1").encode("utf-8"),
                    "text/html; charset=utf-8")

            if path == "/" or path == "/index.html":
                uploads = fetch_uploads()
                st = load_state()
                seen = set(st.get("seen") or [])
                page = render(uploads, seen)
                # 渲染后把当前所有上传标记为已读，下次访问只高亮新到的
                st["seen"] = sorted(set(seen) | {u["id"] for u in uploads})
                save_state(st)
                return self.send_bytes(page.encode("utf-8"), "text/html; charset=utf-8")

            if len(parts) == 3 and parts[0] in ("f", "raw"):
                sid, fid = parts[1], parts[2]
                uploads = {u["id"]: u for u in fetch_uploads()}
                u = uploads.get(sid)
                if not u:
                    return self.send_bytes(b"not found", "text/plain; charset=utf-8", 404)
                f = next((x for x in u["files"] if x["id"] == fid), None)
                if not f:
                    return self.send_bytes(b"not found", "text/plain; charset=utf-8", 404)
                p = file_path(sid, fid)
                if not p or not os.path.exists(p):
                    return self.send_bytes(b"file missing on disk", "text/plain; charset=utf-8", 404)
                return self.send_file(p, f["name"], inline=(parts[0] == "raw"))

            if len(parts) == 3 and parts[0] == "t":
                sid, fid = parts[1], parts[2]
                uploads = {u["id"]: u for u in fetch_uploads()}
                u = uploads.get(sid)
                f = next((x for x in (u or {}).get("files", []) if x["id"] == fid), None)
                if not f:
                    return self.send_bytes(b"not found", "text/plain; charset=utf-8", 404)
                tp = thumb_path(sid, f)
                if tp:
                    return self.send_file(tp, "thumb.jpg", inline=True)
                p = file_path(sid, fid)          # 回退：直接给原图
                if p and os.path.exists(p):
                    return self.send_file(p, f["name"], inline=True)
                return self.send_bytes(b"not found", "text/plain; charset=utf-8", 404)

            if len(parts) == 2 and parts[0] == "z":
                sid = parts[1]
                u = next((x for x in fetch_uploads() if x["id"] == sid), None)
                if not u:
                    return self.send_bytes(b"not found", "text/plain; charset=utf-8", 404)
                zp = fresh_archive_zip(sid, u["files"]) or build_zip(sid, u["files"])
                label = (u["name"] or "上传") + ".zip"
                return self.send_file(zp, label, inline=False)

            return self.send_bytes(b"not found", "text/plain; charset=utf-8", 404)
        except Exception as e:
            print("ERROR %s: %r" % (self.path, e), flush=True)
            try:
                return self.send_bytes(("internal error: %r" % e).encode("utf-8"),
                                       "text/plain; charset=utf-8", 500)
            except Exception:
                pass



def main():
    print("inbox: db=%s uploads=%s pil=%s port=%d" % (DB_PATH, UPLOADS, HAVE_PIL, PORT), flush=True)
    print("inbox: roots=%s targets=%s" % (available_roots(), TARGETS), flush=True)
    threading.Thread(target=sync_worker, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
