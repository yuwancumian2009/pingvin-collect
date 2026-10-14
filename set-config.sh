#!/bin/sh
# 首次装完后跑一次，把该改的配置一次设好。
#
# 用法：./set-config.sh <你访问用的地址> <管理员登录名或邮箱> <管理员密码>
# 例：  ./set-config.sh http://192.168.1.10:8080 admin '你的密码'
#       ./set-config.sh http://192.168.1.10:8080 me@example.com '你的密码'
#
# 前提：已经用浏览器打开过站点、建好了管理员账号（首次启动会引导建）。
# 密码只在本机 curl 里用一次，不写进任何文件。

set -eu

BASE="${1:-}"
USER="${2:-}"
PASS="${3:-}"
if [ -z "$BASE" ] || [ -z "$USER" ] || [ -z "$PASS" ]; then
    echo "用法: $0 <访问地址> <管理员登录名或邮箱> <管理员密码>"
    echo "例:   $0 http://192.168.1.10:8080 admin '你的密码'"
    exit 1
fi
BASE="${BASE%/}"
command -v curl >/dev/null 2>&1 || { echo "需要 curl"; exit 1; }

# 带 @ 当邮箱发，否则当用户名发（后端两种都认）
case "$USER" in
    *@*) CRED="\"email\":\"$USER\"" ;;
    *)   CRED="\"username\":\"$USER\"" ;;
esac

JAR=$(mktemp)
OUT=$(mktemp)
trap 'rm -f "$JAR" "$OUT"' EXIT

echo "==> 1/3 登录 $BASE"
CODE=$(curl -s -o "$OUT" -w '%{http_code}' -c "$JAR" \
    -X POST "$BASE/api/auth/signIn" \
    -H 'Content-Type: application/json' \
    -d "{$CRED,\"password\":\"$PASS\"}")
if [ "$CODE" != "200" ] && [ "$CODE" != "201" ]; then
    echo "    登录失败 (HTTP $CODE)：$(head -c 200 "$OUT")"
    echo "    检查：地址对不对、登录名/邮箱填对没有、账号建了没有。"
    exit 1
fi
echo "    登录成功"

echo "==> 2/3 写入配置"
# appUrl                      生成分享链接用的地址，必须和实际访问地址一致
# defaultLanguage             界面语言
# showHomePage / showAuthButtons  访客打开首页只看上传界面，不显示登录入口
# secureCookies               局域网是 http 就保持 false（将来上 HTTPS 再改 true）
# allowRegistration           访客不需要注册账号
# allowUnauthenticatedShares  安全开关，绝不能开
# maxSize                     单次上传上限，默认只有 1GB，大视频会传不了
# defaultExpiration           收集链接默认有效期，默认 7 天太短
# fileRetentionPeriod         -1 = 关掉「过期分享自动清理」，避免误删收到的文件
# reverseShareSimpleOnly      新建收集链接一律简化模式（对方只看到上传界面）
BODY=$(cat <<JSON
[
  {"key":"general.appUrl","value":"$BASE"},
  {"key":"general.defaultLanguage","value":"zh-CN"},
  {"key":"general.showHomePage","value":false},
  {"key":"general.showAuthButtons","value":false},
  {"key":"security.secureCookies","value":false},
  {"key":"security.allowRegistration","value":false},
  {"key":"security.allowUnauthenticatedShares","value":false},
  {"key":"share.maxSize","value":21474836480},
  {"key":"share.defaultExpiration","value":"1 year"},
  {"key":"share.fileRetentionPeriod","value":-1},
  {"key":"share.reverseShareSimpleOnly","value":true}
]
JSON
)
CODE=$(curl -s -o "$OUT" -w '%{http_code}' -b "$JAR" \
    -X PATCH "$BASE/api/configs/admin" \
    -H 'Content-Type: application/json' -d "$BODY")
if [ "$CODE" != "200" ] && [ "$CODE" != "201" ]; then
    echo "    写入失败 (HTTP $CODE)：$(head -c 300 "$OUT")"
    exit 1
fi
echo "    已写入 11 项"

echo "==> 3/3 回读确认"
curl -s -b "$JAR" "$BASE/api/configs" > "$OUT"
FAILN=0
check() {   # check <配置项> <期望值>
    V=$(tr '{' '\n' < "$OUT" | grep "\"key\":\"$1\"" | \
        sed -n 's/.*"value":"\([^"]*\)".*/\1/p' | head -1)
    if [ "$V" = "$2" ]; then
        echo "    ✓ $1 = $V"
    else
        echo "    ✗ $1 期望 $2 实际 '$V'"
        FAILN=$((FAILN+1))
    fi
}
check general.appUrl "$BASE"
check general.defaultLanguage zh-CN
check general.showHomePage false
check general.showAuthButtons false
check security.allowRegistration false
check security.allowUnauthenticatedShares false
check share.maxSize 21474836480
check share.defaultExpiration "1 year"
check share.fileRetentionPeriod -1
check share.reverseShareSimpleOnly true
echo "    · security.secureCookies 是隐藏项，接口不回显（已随上面一起写入 false）"

if [ "$FAILN" != "0" ]; then
    echo
    echo "有 $FAILN 项没对上，把上面的输出发我看看。"
    exit 1
fi

cat <<'TIP'

完成。接下来：
  1. 浏览器打开站点 -> 登录 -> 右上角「创建文件收集链接」
  2. 弹窗里可以选保存位置、任务名称、存放方式、是否要求上传者填备注
  3. 把生成的链接发出去，对方不用注册就能传
  4. 收到的文件在右上角「收件箱」里看，同时会复制到 COLLECT_DIR
TIP
