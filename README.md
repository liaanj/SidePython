# SidePython

一个轻量的 Python 代码快速执行器（Windows，基于 PySide6）。支持输入参数、代码编辑/语法高亮、输出显示、系统托盘、全局热键与开机启动。
https://github.com/liaanj/SidePython/blob/main/Snipaste_2025-10-22_12-15-03.png
## 直接使用
运行SidePython.exe
## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
python sidepython.py
```

## 快捷键

- F5 / Ctrl+Enter：执行代码
- Ctrl+L：清空输出
- Ctrl+T：切换窗口置顶
- Alt+P（全局）：显示/隐藏窗口（托盘常驻）

## 功能概览

- 可添加/删除输入参数（自动命名为 x, y, z, a...，以 float 传入执行环境）
- 代码编辑器（VSCode 风格、Python 语法高亮、括号多层级着色）
- 输出面板显示 print/异常信息
- 托盘菜单：显示/隐藏、执行、清空、开机启动、退出
- 开机启动：写入注册表 HKEY_CURRENT_USER\...\Run

## 打包（可选）

如需生成独立可执行文件，可使用 PyInstaller（示例）：

```bash
pip install pyinstaller
pyinstaller --onefile --windowed sidepython.py
```

生成的可执行文件通常位于 dist/ 目录。
