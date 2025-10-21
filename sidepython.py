import sys
import os
from io import StringIO
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPlainTextEdit, QPushButton, QLabel, QLineEdit,
    QFrame, QSplitter, QSystemTrayIcon, QMenu
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QTextCharFormat, QSyntaxHighlighter, QColor, QShortcut, QKeySequence, QIcon, QPixmap, QPainter

# Windows注册表操作
try:
    import winreg
except ImportError:
    winreg = None


class PythonSyntaxHighlighter(QSyntaxHighlighter):
    """Python语法高亮器"""
    def __init__(self, document):
        super().__init__(document)
        
        # 定义高亮规则
        self.highlighting_rules = []
        
        # 关键字
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569cd6"))
        keyword_format.setFontWeight(700)
        keywords = [
            "\\bclass\\b", "\\bdef\\b", "\\bif\\b", "\\belse\\b", "\\belif\\b",
            "\\bfor\\b", "\\bwhile\\b", "\\btry\\b", "\\bexcept\\b", "\\bfinally\\b",
            "\\bwith\\b", "\\bimport\\b", "\\bfrom\\b", "\\bas\\b", "\\breturn\\b",
            "\\bTrue\\b", "\\bFalse\\b", "\\bNone\\b", "\\band\\b", "\\bor\\b",
            "\\bnot\\b", "\\bin\\b", "\\bis\\b", "\\blambda\\b", "\\byield\\b"
        ]
        for pattern in keywords:
            self.highlighting_rules.append((pattern, keyword_format))
        
        # 字符串
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#ce9178"))
        self.highlighting_rules.append(('"[^"\\\\]*(\\\\.[^"\\\\]*)*"', string_format))
        self.highlighting_rules.append(("'[^'\\\\]*(\\\\.[^'\\\\]*)*'", string_format))
        
        # 注释
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6a9955"))
        self.highlighting_rules.append(("#[^\\n]*", comment_format))
        
        # 数字
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#b5cea8"))
        self.highlighting_rules.append(("\\b\\d+\\.?\\d*\\b", number_format))
        
        # 括号颜色（按层级）
        self.bracket_colors = [
            QColor("#ffd700"),  # 金色
            QColor("#da70d6"),  # 兰花紫
            QColor("#87ceeb"),  # 天蓝色
            QColor("#98fb98"),  # 浅绿色
        ]
    
    def highlightBlock(self, text):
        import re
        
        # 先应用基本的语法高亮规则
        for pattern, format in self.highlighting_rules:
            for match in re.finditer(pattern, text):
                start, end = match.span()
                self.setFormat(start, end - start, format)
        
        # 单独处理括号的多层级着色
        bracket_stack = []
        brackets = {'(': ')', '[': ']', '{': '}'}
        closing_brackets = {')', ']', '}'}
        
        for i, char in enumerate(text):
            if char in brackets:
                # 开括号
                level = len(bracket_stack)
                color = self.bracket_colors[level % len(self.bracket_colors)]
                bracket_format = QTextCharFormat()
                bracket_format.setForeground(color)
                bracket_format.setFontWeight(700)
                self.setFormat(i, 1, bracket_format)
                bracket_stack.append(char)
            elif char in closing_brackets:
                # 闭括号
                if bracket_stack:
                    bracket_stack.pop()
                level = len(bracket_stack)
                color = self.bracket_colors[level % len(self.bracket_colors)]
                bracket_format = QTextCharFormat()
                bracket_format.setForeground(color)
                bracket_format.setFontWeight(700)
                self.setFormat(i, 1, bracket_format)


class SidePython(QMainWindow):
    def __init__(self):
        super().__init__()
        self.is_topmost = False  # 置顶状态
        self.input_widgets = []  # 存储输入框
        self.var_names = []  # 存储变量名
        self.init_ui()
        self.create_tray_icon()

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("SidePython - Python 快速执行器")
        self.setWindowIcon(self.create_icon())
        self.setGeometry(100, 100, 380, 400)
        self.setMinimumWidth(320)
        
        # 设置VSCode风格的样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 14px;
                border: none;
                border-radius: 7px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #424242;
                border-radius: 7px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4e4e4e;
            }
            QScrollBar::handle:vertical:pressed {
                background-color: #595959;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                background-color: #1e1e1e;
                height: 14px;
                border: none;
                border-radius: 7px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background-color: #424242;
                border-radius: 7px;
                min-width: 30px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #4e4e4e;
            }
            QScrollBar::handle:horizontal:pressed {
                background-color: #595959;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)

        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 1. 输入区域容器
        input_container_label = QLabel("📥 输入数据：")
        input_container_label.setStyleSheet("""
            font-weight: bold; 
            font-size: 10pt; 
            color: #569cd6;
            margin-bottom: 5px;
        """)
        main_layout.addWidget(input_container_label)

        # 输入框容器布局（水平排列）
        self.input_layout = QHBoxLayout()
        self.input_layout.setSpacing(8)
        self.input_layout.setContentsMargins(0, 0, 0, 0)

        main_layout.addLayout(self.input_layout)

        # 先创建按钮（但不添加到布局）
        self.add_btn = QPushButton("+")
        self.add_btn.setFixedSize(28, 28)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: 1px solid #007acc;
                font-size: 12pt;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1177bb;
                border-color: #0099ff;
            }
            QPushButton:pressed {
                background-color: #0d5a8a;
            }
        """)
        self.add_btn.clicked.connect(self.add_input_field)
        self.input_layout.addWidget(self.add_btn)

        self.remove_btn = QPushButton("-")
        self.remove_btn.setFixedSize(28, 28)
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #d73a49;
                color: white;
                border: 1px solid #f85149;
                font-size: 12pt;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e5534b;
                border-color: #ff6b6b;
            }
            QPushButton:pressed {
                background-color: #c5302f;
            }
        """)
        self.remove_btn.clicked.connect(self.remove_last_input)
        self.input_layout.addWidget(self.remove_btn)
        self.remove_btn.setVisible(False)  # 初始隐藏

        # 添加弹性空间，让输入框和按钮靠左
        self.input_layout.addStretch()

        # 添加第一个输入框
        self.add_input_field()

        # 2. 创建可拖动调整大小的Splitter
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(6)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #3c3c3c;
                margin: 2px 0px;
            }
            QSplitter::handle:hover {
                background-color: #007acc;
            }
        """)

        # 代码编辑区域容器
        code_container = QWidget()
        code_layout = QVBoxLayout(code_container)
        code_layout.setContentsMargins(0, 0, 0, 0)
        code_layout.setSpacing(5)

        code_label = QLabel("💻 Python 代码：")
        code_label.setStyleSheet("""
            font-weight: bold; 
            font-size: 10pt; 
            color: #569cd6;
            margin-bottom: 5px;
        """)
        code_layout.addWidget(code_label)

        self.code_editor = QPlainTextEdit()
        self.code_editor.setPlaceholderText("在此编写 Python 代码...")
        self.code_editor.setFont(QFont("Consolas", 10))
        
        # 设置VSCode风格的代码编辑器样式
        self.code_editor.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                line-height: 1.4;
            }
            QPlainTextEdit:focus {
                border-color: #007acc;
            }
        """)
        
        # 设置Tab宽度为4个空格
        self.code_editor.setTabStopDistance(4 * self.code_editor.fontMetrics().horizontalAdvance(' '))
        
        # 添加语法高亮
        self.highlighter = PythonSyntaxHighlighter(self.code_editor.document())
        
        code_layout.addWidget(self.code_editor)

        # 3. 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        button_layout.addStretch()  # 左侧弹性空间，让按钮居中

        self.run_button = QPushButton("▶ 执行")
        self.run_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: 1px solid #28a745;
                padding: 8px 16px;
                font-size: 10pt;
                font-weight: bold;
                border-radius: 4px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #218838;
                border-color: #1e7e34;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        self.run_button.clicked.connect(self.execute_code)
        button_layout.addWidget(self.run_button)

        self.clear_button = QPushButton("🗑 清空")
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: 1px solid #dc3545;
                padding: 8px 16px;
                font-size: 10pt;
                font-weight: bold;
                border-radius: 4px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #c82333;
                border-color: #bd2130;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
        """)
        self.clear_button.clicked.connect(self.clear_output)
        button_layout.addWidget(self.clear_button)

        self.topmost_button = QPushButton("📌 置顶")
        self.topmost_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: 1px solid #007bff;
                padding: 8px 16px;
                font-size: 10pt;
                font-weight: bold;
                border-radius: 4px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #0056b3;
                border-color: #004085;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """)
        self.topmost_button.clicked.connect(self.toggle_topmost)
        button_layout.addWidget(self.topmost_button)

        button_layout.addStretch()
        code_layout.addLayout(button_layout)
        
        splitter.addWidget(code_container)

        # 4. 输出区域容器
        output_container = QWidget()
        output_layout = QVBoxLayout(output_container)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.setSpacing(5)

        output_label = QLabel("📤 输出结果：")
        output_label.setStyleSheet("""
            font-weight: bold; 
            font-size: 10pt; 
            color: #569cd6;
            margin-bottom: 5px;
        """)
        output_layout.addWidget(output_label)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 10))
        self.output_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                line-height: 1.4;
            }
        """)
        output_layout.addWidget(self.output_text)
        
        splitter.addWidget(output_container)
        
        # 设置初始比例 (代码区:输出区 = 2:1)
        splitter.setSizes([400, 200])
        
        # 将splitter添加到主布局
        main_layout.addWidget(splitter)

        # 设置初始代码示例
        self.set_example_code()
        
        # 添加快捷键支持
        self.setup_shortcuts()

    def setup_shortcuts(self):
        """设置快捷键"""
        # F5 执行代码
        run_shortcut = QShortcut(QKeySequence("F5"), self)
        run_shortcut.activated.connect(self.execute_code)
        
        # Ctrl+Enter 执行代码
        ctrl_enter_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        ctrl_enter_shortcut.activated.connect(self.execute_code)
        
        # Ctrl+L 清空输出
        clear_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        clear_shortcut.activated.connect(self.clear_output)
        
        # Ctrl+T 切换置顶
        topmost_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
        topmost_shortcut.activated.connect(self.toggle_topmost)

    def get_next_var_name(self):
        """获取下一个变量名"""
        count = len(self.var_names)
        if count == 0:
            return 'x'
        elif count == 1:
            return 'y'
        elif count == 2:
            return 'z'
        else:
            # 之后使用 a, b, c...
            return chr(ord('a') + count - 3)

    def add_input_field(self):
        """添加一个输入框"""
        var_name = self.get_next_var_name()
        self.var_names.append(var_name)

        # 变量名标签
        label = QLabel(f"{var_name}=")
        label.setFont(QFont("Consolas", 10))
        label.setStyleSheet("color: #d4d4d4; font-weight: bold;")

        # 输入框
        input_field = QLineEdit()
        input_field.setPlaceholderText("数字...")
        input_field.setFont(QFont("Consolas", 10))
        input_field.setFixedHeight(32)
        input_field.setFixedWidth(70)
        input_field.setStyleSheet("""
            QLineEdit {
                background-color: #2d2d30;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 4px 8px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            }
            QLineEdit:focus {
                border-color: #007acc;
                background-color: #1e1e1e;
            }
            QLineEdit:hover {
                border-color: #5a5a5a;
            }
        """)

        # 存储输入框和标签
        self.input_widgets.append({
            'label': label,
            'input': input_field
        })

        # 在按钮之前插入（按钮始终在最后两个位置）
        insert_position = len(self.input_widgets) * 2 - 2  # 每个输入框占2个位置（label + input）
        self.input_layout.insertWidget(insert_position, label)
        self.input_layout.insertWidget(insert_position + 1, input_field)

        # 更新删除按钮可见性
        self.remove_btn.setVisible(len(self.input_widgets) > 1)

    def remove_last_input(self):
        """移除最后一个输入框"""
        if len(self.input_widgets) > 1:
            # 移除最后一个输入框
            last_widget = self.input_widgets.pop()
            self.var_names.pop()

            # 删除控件
            last_widget['label'].deleteLater()
            last_widget['input'].deleteLater()

            # 更新删除按钮可见性
            self.remove_btn.setVisible(len(self.input_widgets) > 1)

    def set_example_code(self):
        """设置示例代码"""
        example_code = """# 变量会自动创建为 float 类型
# 支持数学运算
result = x * 2 + y
print(f"计算结果: {result}")

# 支持条件判断
if result > 10:
    print("结果大于10")
else:
    print("结果小于等于10")

# 支持循环
for i in range(3):
    print(f"循环 {i+1}: {result * (i+1)}")
"""
        self.code_editor.setPlainText(example_code)
        self.input_widgets[0]['input'].setText("5")

    def execute_code(self):
        """执行用户代码"""
        code = self.code_editor.toPlainText()

        if not code.strip():
            self.output_text.append("❌ 错误：代码为空！\n")
            return

        # 清空之前的输出
        self.output_text.clear()

        # 重定向标准输出
        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            # 创建执行环境，提供所有变量
            exec_globals = {}

            # 将每个输入框的值转换为 float 并添加到执行环境
            for i, widget_dict in enumerate(self.input_widgets):
                var_name = self.var_names[i]
                input_text = widget_dict['input'].text().strip()

                if input_text:
                    try:
                        exec_globals[var_name] = float(input_text)
                    except ValueError:
                        self.output_text.append(f"❌ 错误：变量 {var_name} 的值 '{input_text}' 不是有效的数字")
                        return
                else:
                    exec_globals[var_name] = 0.0

            exec_locals = {}

            # 执行代码
            exec(code, exec_globals, exec_locals)

            # 获取输出
            output = sys.stdout.getvalue()

            if output:
                self.output_text.append(output)
            else:
                self.output_text.append("✓ 执行成功（无输出）")

        except Exception as e:
            # 显示错误信息
            self.output_text.append(f"❌ 错误：{type(e).__name__}: {str(e)}")

        finally:
            # 恢复标准输出
            sys.stdout = old_stdout

    def clear_output(self):
        """清空输出框"""
        self.output_text.clear()

    def toggle_topmost(self):
        """切换窗口置顶状态"""
        self.is_topmost = not self.is_topmost
        
        # 保存当前窗口位置和状态
        geometry = self.geometry()
        was_visible = self.isVisible()

        if self.is_topmost:
            self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
            self.topmost_button.setText("📌 取消置顶")
            self.topmost_button.setStyleSheet("""
                QPushButton {
                    background-color: #ff6b35;
                    color: white;
                    border: 1px solid #ff6b35;
                    padding: 8px 16px;
                    font-size: 10pt;
                    font-weight: bold;
                    border-radius: 4px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #ff5722;
                    border-color: #ff5722;
                }
                QPushButton:pressed {
                    background-color: #e64a19;
                }
            """)
        else:
            self.setWindowFlag(Qt.WindowStaysOnTopHint, False)
            self.topmost_button.setText("📌 置顶")
            self.topmost_button.setStyleSheet("""
                QPushButton {
                    background-color: #007bff;
                    color: white;
                    border: 1px solid #007bff;
                    padding: 8px 16px;
                    font-size: 10pt;
                    font-weight: bold;
                    border-radius: 4px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                    border-color: #004085;
                }
                QPushButton:pressed {
                    background-color: #004085;
                }
            """)

        # 恢复窗口位置和状态
        self.setGeometry(geometry)
        if was_visible:
            self.show()

    def create_icon(self):
        """创建应用图标"""
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制圆形背景
        painter.setBrush(QColor("#569cd6"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, 4, 56, 56)
        
        # 绘制Python符号 "Py"
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Arial", 20, QFont.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "Py")
        
        painter.end()
        return QIcon(pixmap)

    def is_autostart_enabled(self):
        """检查是否已启用开机启动"""
        if not winreg:
            return False
        
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ
            )
            try:
                winreg.QueryValueEx(key, "SidePython")
                winreg.CloseKey(key)
                return True
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except Exception:
            return False

    def set_autostart(self, enable):
        """设置开机启动"""
        if not winreg:
            self.tray_icon.showMessage(
                "SidePython",
                "当前系统不支持自动启动功能",
                QSystemTrayIcon.Warning,
                2000
            )
            return
        
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE | winreg.KEY_READ
            )
            
            if enable:
                # 获取当前程序的完整路径
                app_path = os.path.abspath(sys.argv[0])
                # 如果是.py文件，使用pythonw.exe运行（避免显示命令行窗口）
                if app_path.endswith('.py'):
                    python_path = sys.executable.replace('python.exe', 'pythonw.exe')
                    if not os.path.exists(python_path):
                        python_path = sys.executable
                    value = f'"{python_path}" "{app_path}"'
                else:
                    value = f'"{app_path}"'
                
                winreg.SetValueEx(key, "SidePython", 0, winreg.REG_SZ, value)
                winreg.CloseKey(key)
                self.tray_icon.showMessage(
                    "SidePython",
                    "已启用开机启动",
                    QSystemTrayIcon.Information,
                    2000
                )
            else:
                try:
                    winreg.DeleteValue(key, "SidePython")
                    winreg.CloseKey(key)
                    self.tray_icon.showMessage(
                        "SidePython",
                        "已禁用开机启动",
                        QSystemTrayIcon.Information,
                        2000
                    )
                except FileNotFoundError:
                    winreg.CloseKey(key)
        except Exception as e:
            self.tray_icon.showMessage(
                "SidePython",
                f"设置开机启动失败：{str(e)}",
                QSystemTrayIcon.Critical,
                2000
            )

    def toggle_autostart(self):
        """切换开机启动状态"""
        current_state = self.is_autostart_enabled()
        self.set_autostart(not current_state)
        # 更新菜单项文本
        self.update_autostart_action()

    def update_autostart_action(self):
        """更新开机启动菜单项文本"""
        if self.is_autostart_enabled():
            self.autostart_action.setText("✓ 开机启动")
        else:
            self.autostart_action.setText("开机启动")

    def create_tray_icon(self):
        """创建系统托盘图标"""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.create_icon())
        self.tray_icon.setToolTip("SidePython - Python 快速执行器")
        
        # 创建托盘菜单
        tray_menu = QMenu()
        
        show_action = tray_menu.addAction("显示窗口")
        show_action.triggered.connect(self.show_window)
        
        hide_action = tray_menu.addAction("隐藏窗口")
        hide_action.triggered.connect(self.hide)
        
        tray_menu.addSeparator()
        
        execute_action = tray_menu.addAction("▶ 执行代码")
        execute_action.triggered.connect(self.execute_code)
        
        clear_action = tray_menu.addAction("🗑 清空输出")
        clear_action.triggered.connect(self.clear_output)
        
        tray_menu.addSeparator()
        
        # 开机启动选项
        self.autostart_action = tray_menu.addAction("开机启动")
        self.autostart_action.triggered.connect(self.toggle_autostart)
        self.update_autostart_action()  # 初始化菜单项文本
        
        tray_menu.addSeparator()
        
        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(QApplication.instance().quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        
        # 双击托盘图标显示/隐藏窗口
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        
        # 显示托盘图标
        self.tray_icon.show()

    def on_tray_icon_activated(self, reason):
        """托盘图标被激活时的处理"""
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show_window()

    def show_window(self):
        """显示并激活窗口"""
        self.show()
        self.activateWindow()
        self.raise_()

    def closeEvent(self, event):
        """窗口关闭事件 - 最小化到托盘而不是退出"""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "SidePython",
            "程序已最小化到系统托盘",
            QSystemTrayIcon.Information,
            2000
        )


def main():
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyle('Fusion')

    window = SidePython()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
