#!/usr/bin/env python3
"""构建时改镜像自带的两个启动脚本，把收件箱接进去。

用 Python 而不是 sed：Alpine 是 BusyBox 的 sed，替换串里的换行/转义不可靠。
两处改动都做了幂等判断，重复构建不会叠加。
"""
import pathlib
import sys

ENTRY = pathlib.Path("/opt/app/scripts/docker/entrypoint.sh")
CREATE = pathlib.Path("/opt/app/scripts/docker/create-user.sh")

# --- 1) 启动脚本：在拉起前端之前，把收件箱放到后台 ---
s = ENTRY.read_text()
if "inbox/app.py" not in s:
    anchor = "# Run the frontend server"
    if anchor not in s:
        sys.exit("entrypoint.sh 结构变了（找不到锚点），补丁需要重写")
    block = (
        "# 收件箱服务（本镜像新增）\n"
        'echo "Starting inbox..."\n'
        "BASE_PATH=/inbox \\\n"
        '  PINGVIN_API="http://localhost:${BACKEND_PORT:-8080}" \\\n'
        "  DB_PATH=/opt/app/backend/data/pingvin-share.db \\\n"
        "  UPLOADS=/opt/app/backend/data/uploads/shares \\\n"
        "  STATE=/state/state.json CACHE=/cache PORT=8090 \\\n"
        "  python3 /opt/inbox/app.py &\n"
        "\n"
    )
    ENTRY.write_text(s.replace(anchor, block + anchor, 1))
    print("entrypoint.sh: 已插入收件箱启动")
else:
    print("entrypoint.sh: 已有收件箱启动，跳过")

# --- 2) 建用户脚本：/state /cache /collect 也要归 PUID 所有，否则收件箱写不进去 ---
s = CREATE.read_text()
if "/collect" not in s:
    anchor = "find /opt/app/frontend/public"
    if anchor not in s:
        sys.exit("create-user.sh 结构变了（找不到锚点），补丁需要重写")
    block = (
        "mkdir -p /state /cache /collect\n"
        'for d in /state /cache /collect; do chown "${PUID}:${PGID}" "$d"; done\n'
    )
    CREATE.write_text(s.replace(anchor, block + anchor, 1))
    print("create-user.sh: 已加入目录属主处理")
else:
    print("create-user.sh: 已处理过，跳过")
