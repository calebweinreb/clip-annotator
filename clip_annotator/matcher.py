from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import json
import sys
import os
import numpy as np
import time
from .utils import VideoPlayer, set_style, ErrorDialog, safe_add, safe_remove


class MainWindow(QMainWindow):
    SIMILAR_COLOR = QColor(0, 0, 255)
    DISSIMILAR_COLOR = QColor(255, 0, 0)
    NEUTRAL_COLOR = QColor(45, 45, 45)
    SPLITTER_RATIO = 0.333

    def __init__(self, args):
        super().__init__()
        self.setWindowTitle("Clip Matcher")

        annotations_path = args[0]
        if not os.path.exists(annotations_path):
            error_msg = f"The annotations file:\n{annotations_path} does not exist."
            QMessageBox.warning(self, "Error", error_msg)
            sys.exit()

        # Load annotations and save path
        self.annotations_path = annotations_path
        self.max_videos = None  # will be set by load_annotations
        self.load_annotations()

        # Create label to display annotation file path
        self.annotation_path_label = QLabel(f"Annotation file: {annotations_path}")

        # Create label to display current index
        self.index_label = QLabel()

        # Create video players and debounce timer
        self.query_video_player = VideoPlayer()
        self.target_video_players = [VideoPlayer() for _ in range(self.max_videos)]
        for player in self.target_video_players:
            player.clicked.connect(self.classify_target_video)

        # Create grid for displaying target video players
        self.target_video_grid = VideoGrid(self.target_video_players)

        # Set the current index
        current_index = self.get_start_index()
        self.set_current_index(current_index)

        # Create scrollbar
        self.scrollbar = QScrollBar(Qt.Horizontal)
        self.scrollbar.setRange(0, len(self.annotations) - 1)
        self.scrollbar.setValue(self.current_index)
        self.scrollbar.valueChanged.connect(self.set_current_index)
        self.scrollbar.setFixedHeight(25)

        # Create save button
        self.unsaved_changes = False
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_annotations)

        # Initialize layout
        self.init_ui()

    def set_current_index(self, index):
        for video_player in [self.query_video_player] + self.target_video_players:
            video_player.clear_video()

        self.current_index = index
        self.index_label.setText(f"Clip {index}")
        self.update_target_colors()

        query_clip, target_clips, target_metadata = self.annotations[index][:3]
        self.query_video_player.load_video(query_clip)

        for i in range(len(target_clips)):
            if i < self.max_videos:
                self.target_video_players[i].load_video(target_clips[i])
                self.target_video_players[i].set_metadata(target_metadata[i])

    def update_target_colors(self):
        similar_targets, dissimilar_targets = self.annotations[self.current_index][3:5]
        for i, video_player in enumerate(self.target_video_players):
            if i in similar_targets:
                video_player.set_background_color(self.SIMILAR_COLOR)
            elif i in dissimilar_targets:
                video_player.set_background_color(self.DISSIMILAR_COLOR)
            else:
                video_player.set_background_color(self.NEUTRAL_COLOR)

    def init_ui(self):

        control_bar = QHBoxLayout()
        control_bar.addWidget(self.save_button)
        control_bar.addSpacing(10)
        control_bar.addWidget(self.index_label)
        control_bar.addWidget(self.scrollbar)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.query_video_player)
        splitter.addWidget(self.target_video_grid)
        splitter.setSizes([self.SPLITTER_RATIO * 100, (1 - self.SPLITTER_RATIO) * 100])

        layout = QVBoxLayout()
        layout.addWidget(self.annotation_path_label)
        layout.addWidget(splitter)
        layout.addLayout(control_bar)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.index_label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.scrollbar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.target_video_grid.arrange_grid()

    def classify_target_video(self, left_click):
        target_ix = self.target_video_players.index(self.sender())
        similar_targets, dissimilar_targets = self.annotations[self.current_index][3:5]
        if left_click:
            if target_ix in similar_targets:
                similar_targets = safe_remove(similar_targets, target_ix)
            else:
                similar_targets = safe_add(similar_targets, target_ix)
                dissimilar_targets = safe_remove(dissimilar_targets, target_ix)
        else:  # right click
            if target_ix in dissimilar_targets:
                dissimilar_targets = safe_remove(dissimilar_targets, target_ix)
            else:
                dissimilar_targets = safe_add(dissimilar_targets, target_ix)
                similar_targets = safe_remove(similar_targets, target_ix)
        self.annotations[self.current_index][3:5] = similar_targets, dissimilar_targets
        self.unsaved_changes = True
        self.update_target_colors()

    def load_annotations(self):
        """Annotations are a list of lists with the following format where each clip is
        a tuple of (path, start_frame, end_frame):

            [
                query_clip
                [target_clip1, target_clip2, ...],
                target_clip_metadata, # list of dicts
                similar_targets, # indexes of similar target clips
                dissimilar_targets # indexes of dissimilar target clips
            ]
        """
        with open(self.annotations_path, "r") as file:
            annotations = json.load(file)
        all_target_clips = sum([annotation[1] for annotation in annotations], [])
        all_query_clips = [annotation[0] for annotation in annotations]
        all_paths = set([path for path, _, _ in all_target_clips + all_query_clips])
        nonexistent_paths = [path for path in all_paths if not os.path.exists(path)]
        if nonexistent_paths:
            error_msg = "The following video files do not exist:\n"
            error_msg += "\n".join(nonexistent_paths)
            ErrorDialog(error_msg).exec()
            sys.exit()

        self.annotations = annotations
        self.max_videos = max([len(targets) for _, targets, _, _, _ in annotations])

    def save_annotations(self):
        with open(self.annotations_path, "w") as file:
            json.dump(self.annotations, file, indent=4)
        self.unsaved_changes = False

    def get_start_index(self):
        """Get the index that follows the last labeled clip"""
        is_annotated = [
            len(dissimilar_targets) + len(similar_targets) > 0
            for _, _, _, similar_targets, dissimilar_targets in self.annotations
        ]
        if not any(is_annotated):
            return 0
        else:
            index = np.nonzero(is_annotated)[0][-1] + 1
            return min(index, len(self.annotations) - 1)

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

    def closeEvent(self, event):
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save,
            )
            if reply == QMessageBox.Save:
                self.save_annotations()
                event.accept()  # After saving, allow the application to close
            elif reply == QMessageBox.Discard:
                event.accept()  # Discard changes and close the application
            else:
                event.ignore()  # Cancel the close event
        else:
            event.accept()  # No unsaved changes, close the application


class VideoGrid(QWidget):
    def __init__(self, video_players):
        super().__init__()
        self.video_players = video_players
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setHorizontalSpacing(0)
        self.layout.setVerticalSpacing(0)

    def resizeEvent(self, event):
        self.arrange_grid()

    def arrange_grid(self):
        width, height = self.width(), self.height()
        cols = np.ceil(np.sqrt(len(self.video_players) * width / height))
        for i, video_player in enumerate(self.video_players):
            self.layout.addWidget(video_player, i // cols, i % cols)


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
