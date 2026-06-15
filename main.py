import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from qfluentwidgets import FluentTranslator, Theme
from PySide6.QtCore import QTranslator, QLocale
from main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("配音返稿追踪器")
    
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    translator = FluentTranslator(QLocale(QLocale.Chinese, QLocale.China))
    app.installTranslator(translator)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
