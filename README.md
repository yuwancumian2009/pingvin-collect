# pingvin-collect

**一个镜像 = 文件收集站 + 收件箱。**

发一个链接给别人，对方不用注册就能传照片/视频/文件到你自己的服务器；收到的文件在
「收件箱」里按批次看，同时按链接的配置自动复制到你指定的目录。

基于 [Pingvin Share X](https://github.com/smp46/pingvin-share-x)（BSD-2-Clause）构建，
在它之上加了收件箱服务、若干界面补丁，以及「删收集链接不会连带删掉已收到的文件」的修复。

---

## 快速开始

```sh
docker run -d --name pingvin-collect \
  -p 8080:3000 \
  -e PUID=1000 -e PGID=1000 -e TZ=Asia/Shanghai \
  -v $PWD/data:/opt/app/backend/data \
  -v $PWD/state:/state \
  -v $PWD/cache:/cache \
  -v $PWD/collect:/collect \
  yuwancumian2009/pingvin-collect:latest
```

或者用 compose（推荐）：

```sh
docker compose up -d
```

`.env`：

```ini
IMAGE=yuwancumian2009/pingvin-collect:latest
HTTP_PORT=8080
COLLECT_DIR=/volume1/photo/收件     # 收集到的文件落哪，默认 ./collect
PUID=1000
PGID=1000
TZ=Asia/Shanghai
```

浏览器打开 `http://<IP>:8080` → 首次会引导建管理员账号 → 然后跑一次：

```sh
./set-config.sh http://<IP>:8080 admin '你的密码'
```

它会把 11 个该改的配置一次设好并回读确认。**别跳过**——其中一项是单次上传上限，
默认只有 1GB，大视频传不上去，而界面上只报「超出大小限制」。

---

## 怎么用

1. 登录 → 右上角 **「创建文件收集链接」**
2. 弹窗里选：
   - **保存位置**：收到的文件复制到哪
   - **任务名称**：比如「家庭照片」
   - **存放方式**：以任务名建子文件夹 / 直接放根目录 / 自己起文件夹名
   - **要求上传者填写备注**：打开后对方每次上传都要填一次备注
     （多人共用一个链接时，就知道哪批是谁传的）
3. 把链接发出去。对方不用注册，打开就能传。
4. 你在右上角 **「收件箱」** 里看：每次上传是一张卡片，显示备注、来自哪个链接、
   文件名和大小，可单文件下载或打包下载。文件同时已复制到 `COLLECT_DIR`。

---

## 环境变量与挂载

| 变量 | 默认 | 说明 |
|---|---|---|
| `HTTP_PORT` | `8080` | 宿主机上对外开放的端口（容器内固定 3000） |
| `COLLECT_DIR` | `./collect` | 收集到的文件落哪。指向 NAS 共享目录即可 |
| `PUID` / `PGID` | `1000` | 容器内运行身份。挂进来的目录要归它所有 |
| `TZ` | `Asia/Shanghai` | 时区 |
| `TRUST_PROXY` | `true` | 前面有反代时保持 true |

| 挂载点 | 说明 |
|---|---|
| `/opt/app/backend/data` | 数据库 + 上传的文件本体（**备份这个**） |
| `/state` | 收件箱自己的记录：归档清单、每个链接的保存目录配置 |
| `/cache` | 缩略图缓存（丢了会自动重建） |
| `/collect` | 收集到的文件副本 |

---

## set-config.sh 设了哪 11 项

| 配置项 | 值 | 为什么 |
|---|---|---|
| `general.appUrl` | 你的访问地址 | 生成分享链接用，填错链接点不开 |
| `general.defaultLanguage` | `zh-CN` | 默认是英文 |
| `general.showHomePage` | `false` | 访客打开首页直接是上传页 |
| `general.showAuthButtons` | `false` | 访客页不显示登录入口 |
| `security.secureCookies` | `false` | 局域网 http。将来上 HTTPS 改回 `true` |
| `security.allowRegistration` | `false` | 访客不需要账号 |
| `security.allowUnauthenticatedShares` | `false` | **安全开关，永远别开**（名字无害，实际是鉴权失败时的兜底返回值，开了等于所有受保护接口对匿名放行） |
| `share.maxSize` | 20 GB | **默认只有 1GB** |
| `share.defaultExpiration` | `1 year` | 默认 7 天太短，过期链接在界面上显眼、易误删 |
| `share.fileRetentionPeriod` | `-1` | 关掉「过期分享自动清理」，避免误删收到的文件 |
| `share.reverseShareSimpleOnly` | `true` | 新建收集链接一律简化模式 |

---

## 镜像里改了什么

原版有 8 处行为是硬编码的、没有配置项，只能替换编译产物。本镜像在构建时把这些文件覆盖掉：

| 文件 | 改了什么 |
|---|---|
| `6009.js` | 并发上传 3→12；上传页自动提交；自动命名；链接要求备注时弹出必填备注框 |
| `edit.js` | 分享编辑页并发 3→12 |
| `reverseShares.js` | 新建收集链接一律简化模式 |
| `signIn.js` | 登录成功后落到收集链接管理页，而不是上传页 |
| `app.js` | 顶部导航加「收件箱」；创建弹窗里注入保存位置/任务名称/存放方式/备注开关 |
| `sw.js` | 推高改过的 chunk 的缓存版本号，否则 Service Worker 一直吐旧缓存 |
| `middleware.js` | 登录用户访问 `/` 直接去收集链接管理页 |
| `reverseShare.service.js` | **重要**：删除/过期收集链接时不再把已收到的文件一并删掉 |

另外新增了 `/inbox`（收件箱服务，Python + Pillow 生成缩略图），
并在镜像自带的 Caddy 里加了一条路由把它接进来，所以**不需要额外的反向代理容器**。

> ⚠️ 补丁是按 `smp46/pingvin-share-x:v2.0.0` 的编译产物改的，**上游版本必须钉死**。
> 升上游版本要重做补丁，否则会挂空（界面会回到原版，且日志里能看到 chunk 加载 404）。

---

## 自己构建

```sh
docker build -t pingvin-collect:dev .
```

双架构（amd64 + arm64）由 GitHub Actions 构建：push 到 `main` 或发布 Release
即自动推送 `<用户名>/pingvin-collect:<tag>` 和 `:latest` 到 Docker Hub。
需要在仓库里加两个 secret：`DOCKERHUB_USERNAME`、`DOCKERHUB_TOKEN`。

---

## 已知点

- **删链接不再删文件**（已打补丁），「过期分享自动清理」也一并关了。
  文件会一直留着，要清理自己去 `data/uploads/shares/` 按需删。
- **归档是复制不是移动**：原文件留在 `data/uploads/shares/`，`COLLECT_DIR` 里是副本，占两份空间。
- **手机上界面更新要打开两次**：装了 Service Worker，第一次是后台换缓存。
- **收件箱只有管理员能看**：它拿浏览器的登录态去问主站 `/api/users/me`，非管理员 403。
- 容器内以 `PUID:PGID`（默认 1000:1000）运行，`/state`、`/cache`、`/collect` 会在启动时 chown 给它。

---

## 许可与致谢

BSD 2-Clause，见 [LICENSE](LICENSE)。

上游：[smp46/pingvin-share-x](https://github.com/smp46/pingvin-share-x)
（[stonith404/pingvin-share](https://github.com/stonith404/pingvin-share) 的维护中分支），
原始版权归 Elias Schneider 所有。本仓库只新增补丁、收件箱服务与构建配置，
未修改上游源代码仓库。
