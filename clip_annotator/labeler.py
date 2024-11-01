from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import json
import sys
import os
import colorsys
import hashlib
import numpy as np
from vidio.read import OpenCVReader
from .utils import (
    FlowLayout,
    VideoPlayer,
    ErrorDialog,
    set_style,
    safe_add,
    safe_remove,
    safe_substitute,
)


def get_unique_labels(annotations):
    """Get all unique labels in the annotations

    Args:
        annotations (list): Annotations in the format [[path, start, end, labels]]

    Returns:
        unique_labels (list): Sorted list of unique labels
    """
    unique_labels = set()
    for path, start, end, labels in annotations:
        unique_labels.update(labels)
    return sorted(unique_labels)


def text_to_color(text):
    """Generate a color psuedo-randomly using input text as a seed

    Args:
        text (str): Input text to generate the color

    Returns:
        color (list): RGB color in the range [0, 255]
    """
    hash_int = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)
    hue = (hash_int % (10**8)) / float(10**8)
    return [int(255 * x) for x in colorsys.hsv_to_rgb(hue, 1, 1)]


class MainWindow(QMainWindow):
    def __init__(self, args):
        super().__init__()
        self.setWindowTitle("Clip Labeler")

        annotations_path = args[0]
        if not os.path.exists(annotations_path):
            error_msg = f"The annotations file:\n{annotations_path} does not exist."
            QMessageBox.warning(self, "Error", error_msg)
            sys.exit()

        # Load annotations and save path
        self.annotations_path = annotations_path
        self.load_annotations()

        # Select the current index
        self.current_index = self.get_start_index()

        # Create label options box
        unique_labels = get_unique_labels(self.annotations)
        self.label_options_box = LabelsBox(self)
        self.label_options_box.set_labels(unique_labels)
        self.label_options_box.label_clicked.connect(self.add_label)
        self.label_options_box.edit_clicked.connect(self.edit_label)
        self.label_options_box.delete_clicked.connect(self.delete_label)
        self.label_options_box.next_clicked.connect(self.go_to_next_instance)
        self.label_options_box.prev_clicked.connect(self.go_to_prev_instance)

        # Create label entry box
        self.label_entry_box = TextBox(self)
        self.label_entry_box.setFont(QFont("Arial", 18))
        self.label_entry_box.text_entered.connect(self.add_label)
        self.label_entry_box.textChanged.connect(self.label_options_box.filter_labels)
        self.label_options_box.label_clicked.connect(self.label_entry_box.clear)

        # Create metadata box
        self.metadata_box = QLabel()

        # Create video player
        self.video_player = VideoPlayer()

        # Create current labels box
        self.current_labels_box = LabelsBox(self)
        self.current_labels_box.label_clicked.connect(self.remove_label)

        # Set the current index
        current_index = get_start_index(self.annotations)
        self.set_current_index(current_index)

        # Create scrollbar
        self.scrollbar = QScrollBar(Qt.Horizontal)
        self.scrollbar.setRange(0, len(self.annotations) - 1)
        self.scrollbar.setValue(self.current_index)
        self.scrollbar.valueChanged.connect(self.set_current_index)
        self.scrollbar.setFixedHeight(25)

        # Initialize layout
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(self.label_options_box)
        layout.addWidget(self.label_entry_box)
        layout.addWidget(self.metadata_box)
        layout.addWidget(self.video_player)
        layout.addWidget(self.current_labels_box)
        layout.addWidget(self.scrollbar)

        layout.setStretch(0, 1)
        layout.setStretch(3, 4)

        self.label_options_box.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        self.label_entry_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.metadata_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.current_labels_box.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Minimum
        )
        self.scrollbar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def add_label(self, label):
        """Add a label to the current clip"""
        current_labels = self.annotations[self.current_index][3]
        current_labels = safe_add(current_labels, label)
        self.annotations[self.current_index][3] = current_labels
        self.update_annotations()

    def remove_label(self, label):
        """Remove a label from the current clip"""
        current_labels = self.annotations[self.current_index][3]
        current_labels = safe_remove(current_labels, label)
        self.annotations[self.current_index][3] = current_labels
        self.update_annotations()

    def delete_label(self, label):
        """Delete a label from all annotations"""
        reply = QMessageBox.question(
            self,
            "Delete label",
            f'Are you sure you want to delete the label: "{label}"?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.annotations = [
                [path, start, end, safe_remove(labels, label)]
                for path, start, end, labels in self.annotations
            ]
            self.update_annotations()

    def edit_label(self, old_label):
        """Edit a label in all annotations"""
        new_label, ok = QInputDialog.getText(
            self, "Edit label", f'Change "{old_label}" to:'
        )
        if ok and new_label:
            self.annotations = [
                [path, start, end, safe_substitute(labels, old_label, new_label)]
                for path, start, end, labels in self.annotations
            ]
            self.update_annotations()

    def go_to_next_instance(self, label):
        pass

    #     """Go to the next instance of a given label"""
    #     for index in range(self.current_index+1, len(self.annotations)):
    #         if label in

    def go_to_prev_instance(self, label):
        pass

    def update_annotations(self):
        """Propogate changes to the annotations"""
        self.label_options_box.set_labels(get_unique_labels(self.annotations))
        self.current_labels_box.set_labels(self.annotations[self.current_index][3])
        self.save_annotations()

    def set_current_index(self, index):
        """Set the current index and update the UI"""
        self.current_index = index
        path, start, end, labels = self.annotations[index]
        self.metadata_box.setText(
            f"Clip index: {index}\nPath: {path}\nFrames: ({start} - {end})"
        )
        self.current_labels_box.set_labels(labels)
        self.video_player.load_video((path, start, end))

    def eventFilter(self, obj, event):
        """Handle left and right key presses to navigate clips"""
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Left:
                self.scrollbar.setValue(self.scrollbar.value() - 1)
                return True
            elif event.key() == Qt.Key_Right:
                self.scrollbar.setValue(self.scrollbar.value() + 1)
                return True
        return super().eventFilter(obj, event)

    def save_annotations(self):
        with open(self.annotations_path, "w") as file:
            json.dump(self.annotations, file, indent=4)

    def load_annotations(self):
        with open(self.annotations_path, "r") as file:
            annotations = json.load(file)
        all_paths = set([path for path, _, _, _ in annotations])
        nonexitent_paths = [path for path in all_paths if not os.path.exists(path)]
        if nonexitent_paths:
            error_msg = "The following video files do not exist:\n"
            error_msg += "\n".join(nonexitent_paths)
            ErrorDialog(error_msg, self).exec()
            sys.exit()
        else:
            self.annotations = annotations

    def get_start_index(self):
        """Get the index that follows the last labeled clip"""
        is_annotated = [len(labels) > 0 for _, _, _, labels in self.annotations]
        if not any(is_annotated):
            return 0
        else:
            return np.nonzero(is_annotated)[0][-1] + 1


class LabelsBox(QWidget):
    label_clicked = Signal(str)
    next_clicked = Signal(str)
    prev_clicked = Signal(str)
    edit_clicked = Signal(str)
    delete_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.label_buttons = []
        self.layout = FlowLayout(self)

        tmp_button = QPushButton("tmp")
        tmp_button.setFont(QFont("Arial", 16))
        self.setMinimumHeight(tmp_button.sizeHint().height())

    def set_labels(self, labels):
        for label_button in self.label_buttons:
            self.layout.removeWidget(label_button)
            label_button.deleteLater()
        self.label_buttons = []
        for label in labels:
            self.add_label(label)

    def add_label(self, label):
        # Create button
        label_button = QPushButton(label)
        label_button.setContextMenuPolicy(Qt.CustomContextMenu)
        label_button.customContextMenuRequested.connect(self.show_button_context_menu)
        label_button.clicked.connect(lambda: self.label_clicked.emit(label))
        self.label_buttons.append(label_button)
        self.layout.addWidget(label_button)

        # Set button style
        label_button.setFont(QFont("Arial", 16))
        color = text_to_color(label)
        label_button.setStyleSheet(
            f"background-color: rgb({color[0]}, {color[1]}, {color[2]}); color: black"
        )

    def show_button_context_menu(self, pos):
        button = self.sender()
        label = button.text()
        context_menu = QMenu(self)
        context_menu.addAction(f"Edit").triggered.connect(
            lambda: self.edit_clicked.emit(label)
        )
        context_menu.addAction(f"Delete").triggered.connect(
            lambda: self.delete_clicked.emit(label)
        )
        context_menu.addAction(f"Next instance").triggered.connect(
            lambda: self.next_clicked.emit(label)
        )
        context_menu.addAction(f"Previous instance").triggered.connect(
            lambda: self.prev_clicked.emit(label)
        )
        context_menu.exec_(button.mapToGlobal(pos))

    def filter_labels(self, text):
        for label_button in self.label_buttons:
            label_button.setVisible(
                label_button.text().lower().startswith(text.lower())
            )


class TextBox(QLineEdit):
    text_entered = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.returnPressed.connect(self.on_enter_pressed)

    def on_enter_pressed(self):
        self.text_entered.emit(self.text())
        self.clear()


def run():
    app = QApplication(sys.argv)
    app = set_style(app)

    window = MainWindow(sys.argv[1:])
    window.resize(800, 600)
    window.show()

    app.installEventFilter(window)
    sys.exit(app.exec_())


if __name__ == "__main__":
    run()
