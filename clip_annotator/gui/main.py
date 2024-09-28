import sys
import os
import json
import numpy as np
from PySide2.QtWidgets import QApplication, QMainWindow, QLabel, QStyleFactory
from PySide2.QtGui import QPalette, QColor, QIcon
from PySide2.QtCore import Qt


def set_style(app):
    # Set the Fusion style and apply a dark theme
    app.setStyle(QStyleFactory.create("Fusion"))

    darktheme = QPalette()
    darktheme.setColor(QPalette.Window, QColor(45, 45, 45))
    darktheme.setColor(QPalette.WindowText, QColor(222, 222, 222))
    darktheme.setColor(QPalette.Button, QColor(45, 45, 45))
    darktheme.setColor(QPalette.ButtonText, QColor(222, 222, 222))
    darktheme.setColor(QPalette.AlternateBase, QColor(222, 222, 222))
    darktheme.setColor(QPalette.ToolTipBase, QColor(222, 222, 222))
    darktheme.setColor(QPalette.Highlight, QColor(45, 45, 45))
    darktheme.setColor(QPalette.Disabled, QPalette.Light, QColor(60, 60, 60))
    darktheme.setColor(QPalette.Disabled, QPalette.Shadow, QColor(50, 50, 50))
    darktheme.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(111, 111, 111))
    darktheme.setColor(QPalette.Disabled, QPalette.Text, QColor(122, 118, 113))
    darktheme.setColor(QPalette.Disabled, QPalette.WindowText, QColor(122, 118, 113))
    darktheme.setColor(QPalette.Disabled, QPalette.Base, QColor(32, 32, 32))
    app.setPalette(darktheme)
    return app


class MainWindow(QMainWindow):
    def __init__(self, args):
        super().__init__()

        # Set window title
        self.setWindowTitle("MainWindow")

        # Example of adding a central widget
        label = QLabel("Hello, PySide2!", self)
        label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(label)


def run():
    app = QApplication(sys.argv)
    app = set_style(app)

    # Create main window
    window = MainWindow(sys.argv[1:])

    # Resize to take up most of the screen
    screen_geometry = app.primaryScreen().availableGeometry()
    window.resize(int(screen_geometry.width() * 0.8), int(screen_geometry.height() * 0.8))

    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    run()
