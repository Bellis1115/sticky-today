# 今日便利贴

一个 Linux 桌面小便利贴，用来快速记录今天要做的事。

## 启动

```bash
cd /home/xinyi/codeX/sticky-today
./run.sh
```

Windows 用户可以双击项目目录里的 `install.bat`。它会自动在桌面创建“今日便利贴”快捷方式，之后直接双击桌面图标即可启动，不需要打开终端。

Linux 用户首次在项目目录执行：

```bash
bash install.sh
```

脚本会在桌面创建“今日便利贴”快捷方式，之后直接双击桌面图标即可启动。

如果提示缺少 Tkinter，Ubuntu/Debian 可以安装：

```bash
sudo apt install python3-tk
```

## 功能

- 添加今日任务：输入后按 `Enter` 或点击“添加”
- 勾选完成：完成项会加删除线
- 删除单项：点击任务右侧 `×`
- 清除已完成：一键移除完成项
- 随手记：下面文本框自动保存零散备注
- 窗口置顶：默认打开，可取消
- 本地保存：数据在 `~/.local/share/sticky-today/today.json`

## 快捷键

- `Ctrl+N`：聚焦到新任务输入框
- `Ctrl+S`：立即保存

## 桌面图标

已生成桌面启动图标：`/home/xinyi/桌面/今日便利贴.desktop`。

如果桌面环境提示“不信任的启动器”，右键该图标选择“允许运行”或“信任此启动器”。
