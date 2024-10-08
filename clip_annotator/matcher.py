from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import json
import sys
import os
import numpy as np
from .utils import VideoPlayer, set_style, ErrorDialog


def load_annotations(annotations_path):
    """Load annotations from the JSON file and check if all video files exist.

    Args:
        annotations_path (str): Path to the JSON file containing annotations

    Returns:
        annotations (list): Annotations are in the following format, where each clip is
        a list of [path, start, end]::

            [[query_clip], [target_clip1, [target_clip2, ...]]
    """
    with open(annotations_path, "r") as file:
        annotations = json.load(file)

    all_clips = sum([target_clips for _, target_clips in annotations], [])
    all_clips += [query_clip for query_clip, _ in annotations]
    all_paths = set([path for path, _, _ in all_clips])
    if not all([os.path.exists(path) for path in all_paths]):
        error_msg = "The following video files do not exist:\n"
        error_msg += "\n".join([path for path in all_paths if not os.path.exists(path)])
    else:
        error_msg = ""
    return annotations, error_msg


def get_start_index(annotations):
    return 0


class MainWindow(QMainWindow):
    def __init__(self, args):
        super().__init__()
        self.setWindowTitle("Clip Matcher")
        self.num_videos = 10

        annotations_path = args[0]
        if not os.path.exists(annotations_path):
            error_msg = f"The annotations file:\n{annotations_path} does not exist."
            QMessageBox.warning(self, "Error", error_msg)
            sys.exit()

        # Load annotations and save path
        self.annotations_path = annotations_path
        annotations, error_msg = load_annotations(self.annotations_path)
        if error_msg:
            error_dialog = ErrorDialog(error_msg)
            error_dialog.exec()
            sys.exit()
        else:
            self.annotations = annotations

        # Create metadata box
        self.metadata_box = QLabel()

        # Create video players and debounce timer
        self.query_video_player = VideoPlayer()
        self.target_video_players = [VideoPlayer() for _ in range(self.num_videos)]

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

    def set_current_index(self, index):
        for video_player in [self.query_video_player] + self.target_video_players:
            video_player.clear_video()

        self.current_index = index
        query_clip, target_clips = self.annotations[index]
        self.query_video_player.load_video(query_clip)
        for i, target_clip in enumerate(target_clips):
            if i < self.num_videos:
                self.target_video_players[i].load_video(target_clip)

        path, start, end = query_clip
        self.metadata_box.setText(
            f"Clip index = {index}, Path = {path}, Frames = ({start} - {end})"
        )

    def init_ui(self):
        query_video_ratio = 0.4
        width, height = self.width(), self.height()
        target_video_grid_height = height * (1 - query_video_ratio)
        cols = np.ceil(np.sqrt(self.num_videos * width / target_video_grid_height))

        target_video_grid = QGridLayout()
        target_video_grid.setContentsMargins(0, 0, 0, 0)
        target_video_grid.setHorizontalSpacing(0)
        target_video_grid.setVerticalSpacing(0)
        for i, video_player in enumerate(self.target_video_players):
            target_video_grid.addWidget(video_player, i // cols, i % cols)

        layout = QVBoxLayout()
        layout.addWidget(self.metadata_box)
        layout.addWidget(self.query_video_player, int(query_video_ratio * 10))
        layout.addLayout(target_video_grid, int((1 - query_video_ratio) * 10))
        layout.addWidget(self.scrollbar)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.metadata_box.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.scrollbar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

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
