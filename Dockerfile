# 单镜像：Pingvin Share X + 收件箱 + 网关
#
# 基于官方镜像 smp46/pingvin-share-x（BSD-2-Clause），在其上：
#   1. 覆盖 8 个编译产物补丁（原版这些行为硬编码，没有配置项）
#   2. 装 Python + Pillow，塞进收件箱服务
#   3. 用镜像自带的 Caddy 加一条 /inbox 路由（不再需要单独的 nginx）
#   4. 改启动脚本，让收件箱跟主站一起起来
#
# 只暴露 3000 一个端口。

FROM smp46/pingvin-share-x:v2.0.0

# ---------- 1) 前端 / 后端补丁 ----------
# 并发数、自动提交、自动命名、备注开关、收件箱入口、缓存版本、登录落地页、
# 以及「删收集链接不再连带删文件」的后端修复
COPY patch/6009.js                 /opt/app/frontend/.next/static/chunks/6009-a7371246ad12ed46.js
COPY patch/edit.js                 /opt/app/frontend/.next/static/chunks/pages/share/[shareId]/edit-3389d64cd0743a44.js
COPY patch/reverseShares.js        /opt/app/frontend/.next/static/chunks/pages/account/reverseShares-a91e1357a9015fac.js
COPY patch/signIn.js               /opt/app/frontend/.next/static/chunks/pages/auth/signIn-41a6b21d8c4fe78c.js
COPY patch/app.js                  /opt/app/frontend/.next/static/chunks/pages/_app-0cd7e115ec11260d.js
COPY patch/sw.js                   /opt/app/frontend/public/sw.js
COPY patch/middleware.js           /opt/app/frontend/.next/server/src/middleware.js
COPY patch/reverseShare.service.js /opt/app/backend/dist/src/reverseShare/reverseShare.service.js

# ---------- 2) 收件箱服务 ----------
# Pillow 生成缩略图；pillow-heif 让 iPhone 的 HEIC 也能出缩略图（装不上不影响主功能）
RUN apk add --no-cache python3 py3-pip \
 && (pip install --no-cache-dir --break-system-packages Pillow \
     || pip install --no-cache-dir Pillow) \
 && (pip install --no-cache-dir --break-system-packages pillow-heif \
     || echo "pillow-heif 未安装：HEIC 缩略图不可用") \
 && rm -rf /root/.cache
COPY inbox/app.py /opt/inbox/app.py

# ---------- 3) 网关：镜像自带的 Caddy 里加一条 /inbox ----------
COPY caddy/Caddyfile             /opt/app/reverse-proxy/Caddyfile
COPY caddy/Caddyfile.trust-proxy /opt/app/reverse-proxy/Caddyfile.trust-proxy

# ---------- 4) 启动脚本拉起收件箱；补上目录属主 ----------
COPY build/patch-entrypoint.py /tmp/patch-entrypoint.py
RUN python3 /tmp/patch-entrypoint.py && rm /tmp/patch-entrypoint.py

EXPOSE 3000

# 健康检查：收件箱的探活接口是公开的（不需要登录）
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD wget -qO- http://127.0.0.1:3000/inbox/healthz || exit 1
