// ...existing code...
#!/usr/bin/env bash
set -euo pipefail

# 安全版 reset_migrations 腳本
# - 僅備份並刪除專案 repo（非 .venv）下的 migration 檔案
# - 預設不會清空資料庫的 django_migrations 表；要清空請加 --clear-db
# - 會在 backups/ 下建立備份

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# 如果是以 sudo/root 執行，記錄原始使用者
ORIGINAL_USER="${SUDO_USER-}"
if [ -z "$ORIGINAL_USER" ]; then
  ORIGINAL_USER="$(id -un)"
fi

# 若使用者誤以 sudo 執行，優先改為以原使用者重新執行本腳本以避免建立 root-owned 檔案。
# 若確實需要以 root 執行（例如對某些受限檔案操作），可以傳入 --force-root
FORCE_ROOT=false
for a in "${@-}"; do
  if [ "$a" = "--force-root" ]; then
    FORCE_ROOT=true
    break
  fi
done

if [ "$(id -u)" -eq 0 ] && [ -n "${SUDO_USER-}" ] && [ "$FORCE_ROOT" = false ] && [ -z "${RESTARTED_BY_RESET-}" ]; then
  echo "偵測到你以 sudo/root 執行；為避免建立 root-owned 的備份，腳本會以原使用者 ($SUDO_USER) 重新執行。"
  echo "如果你要強制以 root 執行，請加 --force-root（不建議）。"
  export RESTARTED_BY_RESET=1
  exec sudo -u "$SUDO_USER" env RESTARTED_BY_RESET=1 bash "$0" "$@"
fi

if [ "$(id -u)" -eq 0 ]; then
  echo "注意：你目前以 root 執行腳本（因為傳入了 --force-root 或 RESTARTED_BY_RESET）。腳本會在可能的情況下把備份 chown 回原使用者。"
fi

if [ ! -f manage.py ]; then
  echo "錯誤：在專案根目錄找不到 manage.py，請從專案根執行本腳本。"
  exit 1
fi

TS=$(date +%s)
BACKUP_DIR="backups/migrations_backup_$TS"
mkdir -p "$BACKUP_DIR"

# 設定安全的 umask，確保檔案可由原使用者刪除（若用 sudo 執行，稍後會 chown）
umask 0022

echo "備份 db.sqlite3（若存在）..."
if [ -f db.sqlite3 ]; then
  DB_BAK="db.sqlite3.bak.$TS"
  cp db.sqlite3 "$DB_BAK"
  echo "  db.sqlite3 已備份為 $DB_BAK"
  # 如果是由 sudo 執行，讓原使用者擁有備份檔
  if [ -n "${SUDO_USER-}" ]; then
    chown "$ORIGINAL_USER" "$DB_BAK" || true
  fi
else
  echo "  未發現 db.sqlite3，跳過 db 備份。"
fi

echo "收集專案內的 migrations 檔案（會排除 .venv / venv / .git）並備份..."
# 找出所有 migrations 裡的 .py 檔（排除 venv/.venv/.git）
find . \( -path "./.venv" -o -path "./venv" -o -path "./.git" \) -prune -o -type f -path "*/migrations/*.py" -print0 |
  while IFS= read -r -d '' f; do
    dst="$BACKUP_DIR/${f#./}"
    mkdir -p "$(dirname "$dst")"
    cp "$f" "$dst"
    # 如果是由 sudo 執行，改回原使用者擁有權
    if [ -n "${SUDO_USER-}" ]; then
      chown "$ORIGINAL_USER" "$dst" || true
    fi
  done

echo "已在 $BACKUP_DIR 備份所有 migrations 檔案。"

# 若以 sudo 執行，確保整個備份目錄可由原使用者操作（避免 root 擁有導致無法刪除）
if [ -n "${SUDO_USER-}" ]; then
  echo "檢測到 sudo：將備份目錄的擁有權改回 $ORIGINAL_USER ..."
  chown -R "$ORIGINAL_USER" "$BACKUP_DIR" || true
fi

echo "刪除專案中的 migrations 檔案（保留 __init__.py）..."
find . \( -path "./.venv" -o -path "./venv" -o -path "./.git" \) -prune -o -type f -path "*/migrations/*.py" ! -name "__init__.py" -print0 |
  while IFS= read -r -d '' f; do
    echo "  刪除: $f"
    rm -f "$f"
  done

echo "清除 migrations 相關的編譯暫存 (pyc / __pycache__)（排除 .venv）..."
find . \( -path "./.venv" -o -path "./venv" -o -path "./.git" \) -prune -o -type f -name "*.pyc" -print0 |
  while IFS= read -r -d '' f; do
    rm -f "$f"
  done
find . \( -path "./.venv" -o -path "./venv" -o -path "./.git" \) -prune -o -type d -name "__pycache__" -print0 |
  while IFS= read -r -d '' d; do
    rm -rf "$d"
  done

echo "確保每個 migrations 資料夾至少有 __init__.py（若不存在則建立）..."
find . \( -path "./.venv" -o -path "./venv" -o -path "./.git" \) -prune -o -type d -name "migrations" -print0 |
  while IFS= read -r -d '' d; do
    if [ ! -f "$d/__init__.py" ]; then
      touch "$d/__init__.py"
      echo "  已建立 $d/__init__.py"
    fi
  done

CLEAR_DB=false
for a in "${@-}"; do
  if [ "$a" = "--clear-db" ]; then
    CLEAR_DB=true
    break
  fi
done

if [ "$CLEAR_DB" = true ]; then
  echo "--clear-db 參數已啟用：將嘗試清空資料庫內的 django_migrations 記錄（僅支援 sqlite3 by default）"
  if [ -f db.sqlite3 ]; then
    if command -v sqlite3 >/dev/null 2>&1; then
      sqlite3 db.sqlite3 "DELETE FROM django_migrations;"
      echo "  已清空 db.sqlite3 的 django_migrations 表。"
    else
      echo "  找不到 sqlite3 CLI，改用 Python 清空 django_migrations。"
      python3 - <<PY
import sqlite3, sys
try:
    conn = sqlite3.connect('db.sqlite3')
    cur = conn.cursor()
    cur.execute('DELETE FROM django_migrations;')
    conn.commit()
    print('  已用 Python 清空 django_migrations')
except Exception as e:
    print('  清空 django_migrations 失敗:', e, file=sys.stderr)
    sys.exit(1)
finally:
    try:
        conn.close()
    except:
        pass
PY
    fi
  else
    echo "  找不到 db.sqlite3，無法清空 sqlite3 的 django_migrations。若使用其他 DB，請用該 DB 的管理工具清空。"
  fi
else
  echo "未啟用 --clear-db，資料庫的 django_migrations 保持不變。若需要清空，請再次執行並加上 --clear-db（小心使用）。"
fi

echo "完成。接下來你可以在 .venv 中執行："
echo "  source .venv/bin/activate"
echo "  python3 manage.py makemigrations"
echo "  python3 manage.py migrate"
echo "若你的 .venv 被意外破壞，請重新建立或重新安裝依賴："
echo "  python3 -m venv .venv && source .venv/bin/activate && python3 -m pip install -r requirements.txt"
// ...existing code...