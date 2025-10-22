import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import Qt

try:
    # 创建QApplication实例（GUI操作需要）
    app = QApplication(sys.argv)
    
    # 创建一个更大尺寸的图标以获得更好的质量
    pixmap = QPixmap(256, 256)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # 绘制圆形背景
    painter.setBrush(QColor("#569cd6"))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(16, 16, 224, 224)

    # 绘制Python符号 "Py"
    painter.setPen(QColor("#ffffff"))
    painter.setFont(QFont("Arial", 80, QFont.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "Py")

    painter.end()

    # 保存为PNG
    success = pixmap.save("sidepython_icon.png", "PNG")
    if success:
        print("图标已保存为 sidepython_icon.png")
    else:
        print("保存图标失败")
        
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
