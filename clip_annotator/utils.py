from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import numpy as np
from vidio.read import OpenCVReader


def safe_add(items, new_item):
    """Add an item to a list if it is not already present

    Args:
        items (list): List of existing items
        new_item (str): Item to add

    Returns:
        updated_items (list): List of updated items
    """
    if new_item not in items:
        return sorted(items + [new_item])
    else:
        return items


def safe_remove(items, item):
    """Remove an item from a list if it is present

    Args:
        items (list): List of existing items
        item (str): Item to remove

    Returns:
        updated_items (list): List of updated items
    """
    return sorted([i for i in items if i != item])


def safe_substitute(items, old_item, new_item):
    """Replace an item in a list with a new item

    Args:
        items (list): List of existing items
        old_item (str): Item to replace
        new_item (str): Item to replace with

    Returns:
        updated_items (list): List of updated items
    """
    return sorted([new_item if i == old_item else i for i in items])


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super(FlowLayout, self).__init__(parent)

        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)

        self.setSpacing(spacing)
        self.margin = margin

        # spaces between each item
        self.spaceX = 5
        self.spaceY = 5

        self.itemList = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if index >= 0 and index < len(self.itemList):
            return self.itemList[index]

        return None

    def takeAt(self, index):
        if index >= 0 and index < len(self.itemList):
            return self.itemList.pop(index)

        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()

        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())

        size += QSize(2 * self.margin, 2 * self.margin)
        return size

    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0

        for item in self.itemList:
            wid = item.widget()
            # spaceX = self.spacing() + wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)
            # spaceY = self.spacing() + wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical)
            nextX = x + item.sizeHint().width() + self.spaceX
            if nextX - self.spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + self.spaceY
                nextX = x + item.sizeHint().width() + self.spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()


class VideoPlayer(QWidget):
    clicked = Signal(bool)  # True means left click, False means right click

    def __init__(self):
        super().__init__()

        self.medatada_label = QLabel()
        self.video_label = QLabel()
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self.update_frame)

        self.debounce_timer = QTimer()
        self.debounce_timer.setInterval(50)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self._load)

        self.video_info = None  # [path, start, end]
        self.video_array = None
        self.current_frame = None
        self.video_loader = None
        self.fps = 30

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 8)
        layout.setSpacing(2)
        layout.addWidget(self.medatada_label)
        layout.addWidget(self.video_label)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.medatada_label.setFixedHeight(12)
        self.medatada_label.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def update_frame(self):
        if self.video_array is None:
            return

        frame = self.video_array[self.current_frame]
        height, width, channels = frame.shape
        bytes_per_line = channels * width
        q_image = QImage(
            frame.data, width, height, bytes_per_line, QImage.Format_RGB888
        )
        pixmap = QPixmap.fromImage(q_image).scaled(
            self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.video_label.setPixmap(pixmap)
        self.current_frame = (self.current_frame + 1) % len(self.video_array)

    def load_video(self, video_info):
        self.video_info = video_info
        self.debounce_timer.start()

    def clear_video(self):
        if self.video_loader and self.video_loader.isRunning():
            self.video_loader.requestInterruption()
            self.video_loader.wait()
        self.debounce_timer.stop()
        self.video_array = None
        self.current_frame = None
        self.video_label.clear()
        self.medatada_label.clear()

    def _load(self):
        if self.video_loader and self.video_loader.isRunning():
            self.video_loader.requestInterruption()
            self.video_loader.wait()
        self.video_loader = VideoLoaderThread(self.video_info)
        self.video_loader.video_loaded.connect(self.play_video)
        self.video_loader.start()

    def play_video(self, video_array):
        self.video_array = video_array
        self.current_frame = 0
        self.frame_timer.start(int(1000 / self.fps))

    def set_metadata(self, metadata):
        text = ""
        for key, value in metadata.items():
            text += f"{key}: {value}\n"
        self.medatada_label.setText(text)

    def set_background_color(self, color):
        palette = self.palette()
        palette.setColor(QPalette.Window, color)
        self.setPalette(palette)
        self.setAutoFillBackground(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(True)
        elif event.button() == Qt.RightButton:
            self.clicked.emit(False)


class VideoLoaderThread(QThread):
    video_loaded = Signal(list)

    def __init__(self, video_info):
        super().__init__()
        self.video_info = video_info

    def run(self):
        video_path, start_frame, end_frame = self.video_info
        reader = OpenCVReader(video_path)
        video_array = []
        for frame in range(start_frame, end_frame):
            if self.isInterruptionRequested():
                return  # Exit the thread if interruption is requested
            video_array.append(reader[frame])
        self.video_loaded.emit(video_array)


class ErrorDialog(QDialog):
    def __init__(self, message: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Error")

        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)  # Make the text edit read-only
        self.text_edit.setText(message)  # Set the error message
        self.text_edit.setLineWrapMode(QTextEdit.NoWrap)  # Disable text wrapping

        # Ensure scroll bars are always shown
        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        # Add a close button
        self.close_button = QPushButton("Close", self)
        self.close_button.clicked.connect(self.accept)  # Close dialog on button click

        # Arrange widgets in the layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.text_edit)
        layout.addWidget(self.close_button)

        self.setLayout(layout)
        self.resize(600, 400)


def set_style(app):
    # https://www.wenzhaodesign.com/devblog/python-pyside2-simple-dark-theme
    # button from here https://github.com/persepolisdm/persepolis/blob/master/persepolis/gui/palettes.py
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
