from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from .utils import set_style
from .matcher import Matcher
from .labeler import Labeler

import json
import sys
import os

class CustomTabBar(QTabBar):
    def __init__(self, parent=None):
        super(CustomTabBar, self).__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.showContextMenu(event.pos())
        else:
            super(CustomTabBar, self).mousePressEvent(event)

    def showContextMenu(self, pos):
        global_pos = self.mapToGlobal(pos)
        index = self.tabAt(pos)
        if index != -1:
            contextMenu = CustomContextMenu(self)
            close_action = contextMenu.add_item(
                "Close Tab", lambda: self.parent().close_tab(index)
            )
            copy_action = contextMenu.add_item(
                "Copy Name", lambda: self.copyTabName(index)
            )
            contextMenu.exec_(global_pos)

    def copyTabName(self, index):
        clipboard = QApplication.clipboard()
        tab_name = self.tabText(index)
        clipboard.setText(tab_name)


class MainWindow(QMainWindow):

    def __init__(self, args):
        super().__init__()
        self.tabs = QTabWidget()
        self.tabs.setTabBar(CustomTabBar(self.tabs))
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabs)
        self.setWindowTitle("Clip Annotator")

        open = QAction("&Open", self)
        open.setShortcut("Ctrl+O")
        open.triggered.connect(self.open)

        save = QAction("&Save", self)
        save.setShortcut("Ctrl+S")
        save.triggered.connect(self.save)

        mainMenu = self.menuBar()
        mainMenu.setNativeMenuBar(False)

        fileMenu = mainMenu.addMenu("&File")
        fileMenu.addAction(open)
        fileMenu.addAction(save)

        # try to open annotation files that are passed as command line arguments
        self.open(annotations_paths=args)

    def close_tab(self, i):
        if self.tabs.widget(i).close():
            self.tabs.removeTab(i)
            return True
        return False

    def close_all_tabs(self):
        for i in range(self.tabs.count() - 1, -1, -1):
            if not self.close_tab(i):
                return False
        return True

    def closeEvent(self, event):
        if self.close_all_tabs():
            event.accept()
        else:
            event.ignore()

    def open(self, *args, annotations_paths=None):
        """Open given annotation files or create a dialog to select them."""
        if annotations_paths is None:
            file_dialog = QFileDialog(self)
            file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
            file_dialog.setNameFilter("JSON Files (*.json)")
            file_dialog.setDefaultSuffix("json")
            if file_dialog.exec():
                annotations_paths = file_dialog.selectedFiles()

        if annotations_paths is not None:
            error_paths = []
            for annotations_path in annotations_paths:
                if not os.path.exists(annotations_path):
                    error_paths.append(f"{annotations_path}: File does not exist.")
                    continue
                try:
                    self.load_annotations(annotations_path)
                except Exception as e:
                    error_paths.append(f"{annotations_path}: {str(e)}")

            if error_paths:
                error_msg = "Failed to open the following files:\n"
                error_msg += "\n".join(error_paths)
                QMessageBox.warning(self, "Error", error_msg)

    def load_annotations(self, annotations_path):
        annotation_type = json.load(open(annotations_path))["type"]
        if annotation_type == "match":
            tab = Matcher(annotations_path)
        elif annotation_type == "label":
            tab = Labeler(annotations_path)
        else:
            raise ValueError(f"Unknown annotation type: {annotation_type}")
        index = self.tabs.addTab(tab, os.path.basename(annotations_path))
        self.tabs.setCurrentIndex(index)

    def save(self):
        current_tab = self.tabs.currentWidget()
        if current_tab is not None:
            current_tab.save_annotations()

    def eventFilter(self, obj, event):
        """Handle left and right key presses"""
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Left:
                self.tabs.currentWidget().left_keypress()
                return True
            elif event.key() == Qt.Key_Right:
                self.tabs.currentWidget().right_keypress()
                return True
        return super().eventFilter(obj, event)

        
        

def run():
    app = QApplication(sys.argv)
    app = set_style(app)

    window = MainWindow(sys.argv[1:])
    window.resize(1200, 900)
    window.show()

    app.installEventFilter(window)
    sys.exit(app.exec_())


if __name__ == "__main__":
    run()
