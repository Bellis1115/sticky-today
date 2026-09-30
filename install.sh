#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="$(command -v python3 || true)"
if [[ -z "$PYTHON_BIN" ]]; then
    echo "找不到 python3，请先安装 Python 3。"
    exit 1
fi
if ! "$PYTHON_BIN" -c 'import tkinter' 2>/dev/null; then
    echo "缺少 Tkinter，请安装：sudo apt install python3-tk"
    exit 1
fi

ICON="$PROJECT_DIR/sticky_today.png"
DESKTOP_FILE="$PROJECT_DIR/今日便利贴.desktop"
DESKTOP_DIR="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
if [[ ! -d "$DESKTOP_DIR" && -d "$HOME/桌面" ]]; then
    DESKTOP_DIR="$HOME/桌面"
fi
mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=今日便利贴
Comment=记录今天要做什么
Exec=$PYTHON_BIN $PROJECT_DIR/sticky_today.py
Path=$PROJECT_DIR
Icon=$ICON
Terminal=false
Categories=Utility;
StartupNotify=true
StartupWMClass=Stickytoday
EOF

chmod +x "$DESKTOP_FILE"
cp "$DESKTOP_FILE" "$DESKTOP_DIR/今日便利贴.desktop"
chmod +x "$DESKTOP_DIR/今日便利贴.desktop"
gio set "$DESKTOP_DIR/今日便利贴.desktop" metadata::trusted true 2>/dev/null || true

APPLICATIONS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPLICATIONS_DIR"
cp "$DESKTOP_FILE" "$APPLICATIONS_DIR/sticky-today.desktop"
chmod +x "$APPLICATIONS_DIR/sticky-today.desktop"
update-desktop-database "$APPLICATIONS_DIR" 2>/dev/null || true

echo "安装完成：$DESKTOP_DIR/今日便利贴.desktop"
echo "以后直接双击桌面图标即可启动。"
