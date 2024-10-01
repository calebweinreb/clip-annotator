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
from .utils import FlowLayout, VideoPlayer, set_style


def load_annotations(annotations_path):
    """Load annotations from the JSON file

    Args:
        annotations_path (str): Path to the JSON file containing annotations

    Returns:
        annotations (list): Annotations in the format [[path, start, end, labels]]
    """
    with open(annotations_path, "r") as file:
        annotations = json.load(file)
    return annotations


def save_annotations(annotations, annotations_path):
    """Save annotations to the JSON file

    Args:
        annotations (list): Annotations in the format [[path, start, end, labels]]
        annotations_path (str): Path to the JSON file to save the annotations
    """
    with open(annotations_path, "w") as file:
        json.dump(annotations, file, indent=4)


def get_next_unlabeled_clip(annotations):
    """Get the index of the next clip that has not been labeled, or 0 if all clips have
    been labeled

    Args:
        annotations (list): Annotations in the format [[path, start, end, labels]]

    Returns:
        clip_index (int): Index of the next clip that has not been labeled
    """
    is_annotated = [len(labels) > 0 for (path, start, end, labels) in annotations]
    if all(is_annotated):
        return 0
    else:
        return is_annotated.index(False)


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


def safe_add_label(existing_labels, new_label):
    """Add a new label to the existing labels if it is not already present

    Args:
        existing_labels (list): List of existing labels
        new_label (str): New label to add

    Returns:
        updated_labels (list): List of updated labels
    """
    if new_label not in existing_labels:
        return sorted(existing_labels + [new_label])
    else:
        return existing_labels


def safe_remove_label(existing_labels, label_to_remove):
    """Remove a label from the existing labels if it is present

    Args:
        existing_labels (list): List of existing labels
        label_to_remove (str): Label to remove

    Returns:
        updated_labels (list): List of updated labels
    """
    if label_to_remove in existing_labels:
        return sorted([label for label in existing_labels if label != label_to_remove])
    else:
        return existing_labels


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
        self.setWindowTitle("Clip Annotator")

        annotations_path = args[0]
        if not os.path.exists(annotations_path):
            error_msg = f"The annotations file:\n{annotations_path} does not exist."
            QMessageBox.warning(self, "Error", error_msg)
            sys.exit()

        # Load annotations and save path
        self.annotations_path = annotations_path
        self.annotations = load_annotations(self.annotations_path)

        # Select the current clip index
        self.current_clip_index = get_next_unlabeled_clip(self.annotations)

        # Create label options box
        unique_labels = get_unique_labels(self.annotations)
        self.label_options_box = LabelsBox(self)
        self.label_options_box.set_labels(unique_labels)

        # Create label entry box
        self.label_entry_box = TextBox(self)
        self.label_entry_box.setFont(QFont("Arial", 18))

        # Create metadata box
        self.metadata_box = QLabel()

        # Create video player and debounce timer
        self.video_player = VideoPlayer()
        self.debounce_timer = QTimer()
        self.debounce_timer.setInterval(50)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self.load_video)

        # Create current labels box
        self.current_labels_box = LabelsBox(self)

        # Create scrollbar
        self.scrollbar = QScrollBar(Qt.Horizontal)
        self.scrollbar.setRange(0, len(self.annotations) - 1)
        self.scrollbar.setValue(self.current_clip_index)
        self.scrollbar.setFixedHeight(25)

        # Connect signals to slots
        self.label_entry_box.text_entered.connect(self.add_label)
        self.scrollbar.valueChanged.connect(self.set_current_clip)
        self.current_labels_box.label_clicked.connect(self.remove_label)
        self.label_options_box.label_clicked.connect(self.add_label)

        # Set the current clip
        self.set_current_clip(self.current_clip_index)

        # Initialize layout
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(self.label_options_box)
        layout.addWidget(self.label_entry_box)
        layout.addWidget(self.metadata_box)
        layout.addWidget(self.video_player)
        layout.addWidget(self.current_labels_box)
        layout.addStretch()
        layout.addWidget(self.scrollbar)
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def add_label(self, label):
        current_labels = self.annotations[self.current_clip_index][3]
        current_labels = safe_add_label(current_labels, label)
        self.annotations[self.current_clip_index][3] = current_labels
        self.label_options_box.set_labels(get_unique_labels(self.annotations))
        self.current_labels_box.set_labels(current_labels)
        save_annotations(self.annotations, self.annotations_path)

    def remove_label(self, label):
        current_labels = self.annotations[self.current_clip_index][3]
        current_labels = safe_remove_label(current_labels, label)
        self.annotations[self.current_clip_index][3] = current_labels
        self.label_options_box.set_labels(get_unique_labels(self.annotations))
        self.current_labels_box.set_labels(current_labels)
        save_annotations(self.annotations, self.annotations_path)

    def set_current_clip(self, index):
        self.current_clip_index = index
        path, start, end, labels = self.annotations[index]
        self.metadata_box.setText(
            f"Clip index: {index}\nPath: {path}\nFrames: ({start} - {end})"
        )
        self.current_labels_box.set_labels(labels)
        self.debounce_timer.start()

    def load_video(self):
        path, start, end, labels = self.annotations[self.current_clip_index]
        if not os.path.exists(path):
            error_msg = f"The video file:\n{path} does not exist."
            QMessageBox.warning(self, "Error", error_msg)
        else:
            reader = OpenCVReader(path)
            video_array = reader[start:end]
            self.video_player.play_video(video_array)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Left:
                self.scrollbar.setValue(self.scrollbar.value() - 1)
                return True
            elif event.key() == Qt.Key_Right:
                self.scrollbar.setValue(self.scrollbar.value() + 1)
                return True
        return super().eventFilter(obj, event)


class LabelsBox(QWidget):
    label_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.label_buttons = []
        self.layout = FlowLayout(self)

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
        label_button.clicked.connect(lambda: self.label_clicked.emit(label))
        self.label_buttons.append(label_button)
        self.layout.addWidget(label_button)

        # Set button style
        label_button.setFont(QFont("Arial", 18))
        color = text_to_color(label)
        label_button.setStyleSheet(
            f"background-color: rgb({color[0]}, {color[1]}, {color[2]}); color: black"
        )


class TextBox(QLineEdit):
    text_entered = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.returnPressed.connect(self.on_enter_pressed)

    @Slot()
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
