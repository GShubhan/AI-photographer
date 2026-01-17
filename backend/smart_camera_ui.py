"""
Smart Camera — PyQt5 Desktop UI Prototype (face + eyes checks) with Start/Stop and Gallery fullscreen

Changes from previous prototype:
- Start/Stop button to pause/resume the background capture worker.
- "View Gallery" button to open a gallery dialog that lists saved photos from
  sarcastic-photographer/gallery. Clicking any image (in history strip or gallery)
  opens it fullscreen in an ImageViewer.
- History thumbnails are clickable and open the fullscreen viewer.

Usage:
- Place this file next to your modules: frame_cap.py, local_checks.py, analyze_image.py,
  TTS_function.py, gallery_dir.py
- Ensure gallery dir exists: mkdir -p sarcastic-photographer/gallery
- Run: python smart_camera_ui.py
"""

import sys
import os
import time
import threading
import base64
from io import BytesIO

from PyQt5 import QtCore, QtGui, QtWidgets

import cv2
import numpy as np
from PIL import Image

# Import your existing modules
from frame_cap import frame_cap
from local_checks import face_check, eyes_open_check
from TTS_function import speak
from analyze_image import llm_response, encode_image
from gallery_dir import add_to_gallery

# -----------------------
# Helper clickable label
# -----------------------
class ClickableLabel(QtWidgets.QLabel):
    clicked = QtCore.pyqtSignal(object)  # payload: either data_url or file path

    def __init__(self, parent=None, payload=None):
        super().__init__(parent)
        self.payload = payload
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

    def mousePressEvent(self, ev):
        self.clicked.emit(self.payload)


# -----------------------
# Fullscreen image viewer
# -----------------------
# Replace the existing ImageViewer class with this corrected version.

class ImageViewer(QtWidgets.QDialog):
    def __init__(self, image_source, parent=None):
        """
        image_source: either a file path or a data URL string (data:image/...;base64,...)
        """
        super().__init__(parent)
        self.setWindowTitle("Photo Viewer")
        self.setModal(True)
        self.image_source = image_source

        # Layout + label
        self.layout = QtWidgets.QVBoxLayout(self)
        self.label = QtWidgets.QLabel()
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        # Make sure label expands and doesn't force the window size
        self.label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.label.setScaledContents(False)
        self.layout.addWidget(self.label)

        self.setStyleSheet("background: black;")
        # sensible minimum to avoid zero-size problems
        self.setMinimumSize(800, 600)

        # Load the image (store original pixmap in self._pix)
        self._pix = None
        self._load_image()

        # Defer maximizing / initial scale until the dialog is actually shown
        QtCore.QTimer.singleShot(0, self._apply_scaled)

    def _load_image(self):
        try:
            if isinstance(self.image_source, str) and self.image_source.startswith("data:image"):
                header, b64 = self.image_source.split(",", 1)
                b = base64.b64decode(b64)
                img = QtGui.QImage.fromData(b)
                pix = QtGui.QPixmap.fromImage(img)
            else:
                pix = QtGui.QPixmap(self.image_source)
            if pix.isNull():
                self.label.setText("Unable to load image")
                return
            # keep original pixmap untouched for future resizes
            self._pix = pix
        except Exception as e:
            self.label.setText(f"Error loading image: {e}")

    def _apply_scaled(self):
        # Only scale if we have an original pixmap
        if not self._pix or self._pix.isNull():
            return
        size = self.size()
        # Leave some padding so the pixmap doesn't touch window borders
        target_w = max(1, size.width() - 24)
        target_h = max(1, size.height() - 24)
        scaled = self._pix.scaled(target_w, target_h, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.label.setPixmap(scaled)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        # Re-scale from the original pixmap to exactly fit the new window size
        # Guard ensures no repeated work if pixmap missing
        if self._pix and not self._pix.isNull():
            self._apply_scaled()

    def keyPressEvent(self, ev):
        if ev.key() == QtCore.Qt.Key_Escape:
            self.accept()
# -----------------------
    def _load_image(self):
        try:
            if isinstance(self.image_source, str) and self.image_source.startswith("data:image"):
                header, b64 = self.image_source.split(",", 1)
                b = base64.b64decode(b64)
                img = QtGui.QImage.fromData(b)
                pix = QtGui.QPixmap.fromImage(img)
            else:
                pix = QtGui.QPixmap(self.image_source)
            if pix.isNull():
                self.label.setText("Unable to load image")
                return
            # scale to dialog size on show/resize
            self._pix = pix
            self._apply_scaled()
        except Exception as e:
            self.label.setText(f"Error loading image: {e}")

    def _apply_scaled(self):
        if not hasattr(self, "_pix") or self._pix.isNull():
            return
        size = self.size()
        scaled = self._pix.scaled(size.width() - 24, size.height() - 24, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.label.setPixmap(scaled)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._apply_scaled()

    def keyPressEvent(self, ev):
        if ev.key() == QtCore.Qt.Key_Escape:
            self.accept()


# -----------------------
# Gallery dialog
# -----------------------
class GalleryDialog(QtWidgets.QDialog):
    def __init__(self, gallery_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gallery")
        self.setModal(True)
        self.gallery_dir = gallery_dir
        self.resize(1000, 700)

        layout = QtWidgets.QVBoxLayout(self)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        content = QtWidgets.QWidget()
        self.grid = QtWidgets.QGridLayout(content)
        self.grid.setSpacing(8)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        self._load_images()

    def _load_images(self):
        files = sorted([f for f in os.listdir(self.gallery_dir) if f.startswith("photo_") and f.endswith(".jpg")])
        if not files:
            lbl = QtWidgets.QLabel("No photos in gallery yet.")
            lbl.setAlignment(QtCore.Qt.AlignCenter)
            self.grid.addWidget(lbl, 0, 0)
            return

        col = 0
        row = 0
        for i, fname in enumerate(reversed(files)):
            path = os.path.join(self.gallery_dir, fname)
            pix = QtGui.QPixmap(path).scaledToWidth(220, QtCore.Qt.SmoothTransformation)
            cl = ClickableLabel(payload=path)
            cl.setPixmap(pix)
            cl.clicked.connect(self._open_viewer)
            self.grid.addWidget(cl, row, col)
            col += 1
            if col >= 4:
                col = 0
                row += 1

    def _open_viewer(self, payload):
        viewer = ImageViewer(payload, parent=self)
        viewer.exec_()


# -----------------------
# Communicator & Worker
# -----------------------
class Communicator(QtCore.QObject):
    frame_ready = QtCore.pyqtSignal(np.ndarray)
    checks_updated = QtCore.pyqtSignal(dict)
    thinking = QtCore.pyqtSignal()
    instruction = QtCore.pyqtSignal(str)
    thumbnail_added = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)


class CaptureWorker(threading.Thread):
    def __init__(self, comm: Communicator, config):
        super().__init__(daemon=True)
        self.comm = comm
        self.config = config
        self._stop_event = threading.Event()
        self.last_eval_ts = 0.0
        self.attempt_count = 0
        self.gallery_count = self._init_gallery_count()

    def _init_gallery_count(self):
        gallery_path = self.config["gallery_path"]
        if not os.path.exists(gallery_path):
            os.makedirs(gallery_path, exist_ok=True)
            return 0
        files = [f for f in os.listdir(gallery_path) if f.startswith("photo_") and f.endswith(".jpg")]
        return len(files)

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        while not self.stopped():
            try:
                frame = None
                try:
                    frame = frame_cap()
                except Exception as e:
                    self.comm.error.emit(f"frame_cap() error: {e}")
                    time.sleep(self.config["poll_interval"])
                    continue

                if frame is None:
                    time.sleep(self.config["poll_interval"])
                    continue

                self.comm.frame_ready.emit(frame)

                try:
                    cv2.imwrite("temp.jpg", frame)
                except Exception:
                    pass

                # Only face & eyes checks
                face = False
                eyes = False
                try:
                    face = face_check("temp.jpg")
                except Exception as e:
                    self.comm.error.emit(f"face_check error: {e}")

                try:
                    eyes = eyes_open_check("temp.jpg")
                except Exception as e:
                    self.comm.error.emit(f"eyes_open_check error: {e}")

                checks = {
                    "face": bool(face),
                    "eyes": bool(eyes),
                    "time_since_eval": time.time() - self.last_eval_ts,
                }
                self.comm.checks_updated.emit(checks)

                time_ok = checks["time_since_eval"] >= self.config["eval_interval"]
                all_ok = checks["face"] and checks["eyes"] and time_ok and self.config.get("auto_enabled", True)

                if all_ok:
                    self.last_eval_ts = time.time()
                    self.attempt_count += 1

                    thumb_dataurl = self._frame_to_data_url(frame, max_w=320)
                    self.comm.thumbnail_added.emit(thumb_dataurl)

                    threading.Thread(target=self._analyze_and_speak, args=(frame.copy(), self.attempt_count), daemon=True).start()

                time.sleep(self.config["poll_interval"])
            except Exception as e:
                self.comm.error.emit(f"Capture loop error: {e}")
                time.sleep(self.config["poll_interval"])

    def _frame_to_data_url(self, frame_bgr, max_w=320):
        try:
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            pil = Image.fromarray(rgb)
            w, h = pil.size
            if w > max_w:
                pil = pil.resize((max_w, int(h * max_w / w)), Image.LANCZOS)
            buf = BytesIO()
            pil.save(buf, format="JPEG", quality=75)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{b64}"
        except Exception as e:
            self.comm.error.emit(f"_frame_to_data_url error: {e}")
            return ""

    def _analyze_and_speak(self, frame, attempt_count):
        try:
            self.comm.thinking.emit()
            try:
                cv2.imwrite("temp_for_llm.jpg", frame)
                image_b64 = encode_image("temp_for_llm.jpg")
            except Exception as e:
                self.comm.error.emit(f"encode_image write error: {e}; trying temp.jpg")
                image_b64 = encode_image("temp.jpg")

            response = llm_response(image_b64, attempt_count)

            if isinstance(response, dict) and "content" in response:
                text = response["content"].strip()
            else:
                text = str(response).strip()

            self.comm.instruction.emit(text)

            tts_thread = threading.Thread(target=self._run_tts_and_handle_accept, args=(text, frame), daemon=True)
            tts_thread.start()

        except Exception as e:
            self.comm.error.emit(f"LLM analysis error: {e}")

    def _run_tts_and_handle_accept(self, text, frame):
        try:
            speak(text)
        except Exception as e:
            self.comm.error.emit(f"TTS speak error: {e}")

        if "accepted" in text.lower() or "accepted - finally" in text.lower():
            try:
                add_to_gallery(self.gallery_count, frame)
                self.gallery_count += 1
                thumb = self._frame_to_data_url(frame, max_w=320)
                self.comm.thumbnail_added.emit(thumb)
            except Exception as e:
                self.comm.error.emit(f"add_to_gallery error: {e}")


# -----------------------
# Main Window
# -----------------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Camera - Desktop Prototype")
        self.resize(1200, 760)

        self.config = {
            "poll_interval": 0.9,
            "eval_interval": 10,
            "gallery_path": "sarcastic-photographer/gallery",
            "auto_enabled": True,
        }

        # ensure gallery path
        os.makedirs(self.config["gallery_path"], exist_ok=True)

        self.comm = Communicator()
        self.comm.frame_ready.connect(self.on_frame_ready)
        self.comm.checks_updated.connect(self.on_checks_updated)
        self.comm.thinking.connect(self.on_thinking)
        self.comm.instruction.connect(self.on_instruction)
        self.comm.thumbnail_added.connect(self.on_thumbnail_added)
        self.comm.error.connect(self.on_error)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QHBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        left = QtWidgets.QVBoxLayout()
        main_layout.addLayout(left, stretch=3)

        # topbar with Start/Stop and Gallery
        topbar = QtWidgets.QHBoxLayout()
        self.logo = QtWidgets.QLabel("<b>Smart Camera</b>")
        self.logo.setStyleSheet("color: #dff6f2; font-size: 18px;")
        topbar.addWidget(self.logo)
        topbar.addStretch()

        self.start_stop_btn = QtWidgets.QPushButton("Stop")
        self.start_stop_btn.clicked.connect(self.toggle_capture)
        topbar.addWidget(self.start_stop_btn)

        self.gallery_btn = QtWidgets.QPushButton("View Gallery")
        self.gallery_btn.clicked.connect(self.open_gallery)
        topbar.addWidget(self.gallery_btn)

        self.settings_btn = QtWidgets.QPushButton("Settings")
        self.settings_btn.clicked.connect(self.open_settings)
        topbar.addWidget(self.settings_btn)

        left.addLayout(topbar)

        # video display
        self.video_label = QtWidgets.QLabel()
        self.video_label.setStyleSheet("background: black; border-radius: 8px;")
        self.video_label.setMinimumSize(640, 360)
        self.video_label.setAlignment(QtCore.Qt.AlignCenter)
        left.addWidget(self.video_label, stretch=1)

        overlay = QtWidgets.QHBoxLayout()
        overlay.setContentsMargins(0, 4, 0, 4)
        self.status_chip = QtWidgets.QLabel("Checks: — / 2")
        self.status_chip.setStyleSheet("padding:6px;border-radius:8px;background:#082a2a;color:#dff6f2;")
        overlay.addWidget(self.status_chip)
        self.last_eval_label = QtWidgets.QLabel("Last eval: —s")
        self.last_eval_label.setStyleSheet("color: #98a1ad; margin-left:12px;")
        overlay.addWidget(self.last_eval_label)
        overlay.addStretch()
        left.addLayout(overlay)

        ctrls = QtWidgets.QHBoxLayout()
        self.capture_btn = QtWidgets.QPushButton("📸 Capture")
        self.capture_btn.clicked.connect(self.manual_capture)
        ctrls.addWidget(self.capture_btn)
        self.auto_cb = QtWidgets.QCheckBox("Auto")
        self.auto_cb.setChecked(True)
        self.auto_cb.stateChanged.connect(self._auto_changed)
        ctrls.addWidget(self.auto_cb)
        ctrls.addStretch()
        left.addLayout(ctrls)

        self.instruction_label = QtWidgets.QLabel("")
        self.instruction_label.setWordWrap(True)
        self.instruction_label.setAlignment(QtCore.Qt.AlignCenter)
        self.instruction_label.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #082124, stop:1 #052022);"
            "color: #dff6f2; padding:10px; border-radius:10px; font-weight:600;"
        )
        self.instruction_label.setVisible(False)
        left.addWidget(self.instruction_label)

        right = QtWidgets.QVBoxLayout()
        main_layout.addLayout(right, stretch=1)

        hist_card = QtWidgets.QGroupBox("History")
        hist_layout = QtWidgets.QVBoxLayout(hist_card)
        self.thumb_container = QtWidgets.QWidget()
        self.thumb_layout = QtWidgets.QHBoxLayout(self.thumb_container)
        self.thumb_layout.setContentsMargins(4, 4, 4, 4)
        self.thumb_layout.setSpacing(6)
        hist_layout.addWidget(self.thumb_container)
        right.addWidget(hist_card)

        status_card = QtWidgets.QGroupBox("Live status")
        status_layout = QtWidgets.QVBoxLayout(status_card)
        self.status_text = QtWidgets.QLabel("Face: —\nEyes: —\nAuto-capture: On\nLast instruction: —")
        status_layout.addWidget(self.status_text)
        right.addWidget(status_card)

        console_card = QtWidgets.QGroupBox("Console")
        console_layout = QtWidgets.QVBoxLayout(console_card)
        self.console = QtWidgets.QTextEdit()
        self.console.setReadOnly(True)
        console_layout.addWidget(self.console)
        right.addWidget(console_card, stretch=1)

        # start worker
        self.capture_worker = CaptureWorker(self.comm, self.config)
        self.capture_worker.start()
        self.capture_running = True

        self.last_instruction_ts = 0.0

        self._ui_timer = QtCore.QTimer()
        self._ui_timer.setInterval(500)
        self._ui_timer.timeout.connect(self._tick)
        self._ui_timer.start()

    def toggle_capture(self):
        if self.capture_running:
            self.stop_capture()
        else:
            self.start_capture()

    def start_capture(self):
        if self.capture_running:
            return
        self.capture_worker = CaptureWorker(self.comm, self.config)
        self.capture_worker.start()
        self.capture_running = True
        self.start_stop_btn.setText("Stop")
        self.console_append("Capture worker started")

    def stop_capture(self):
        if not self.capture_running:
            return
        try:
            self.capture_worker.stop()
            # give thread a moment to exit
            time.sleep(0.2)
        except Exception:
            pass
        self.capture_running = False
        self.start_stop_btn.setText("Start")
        self.console_append("Capture worker stopped")

    def open_gallery(self):
        dlg = GalleryDialog(self.config["gallery_path"], parent=self)
        dlg.exec_()

    def closeEvent(self, ev):
        try:
            if self.capture_worker and self.capture_running:
                self.capture_worker.stop()
                time.sleep(0.2)
        except Exception:
            pass
        return super().closeEvent(ev)

    def on_frame_ready(self, frame_bgr):
        try:
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qimg = QtGui.QImage(rgb.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
            pix = QtGui.QPixmap.fromImage(qimg).scaled(self.video_label.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            self.video_label.setPixmap(pix)
        except Exception as e:
            self.console_append(f"Display frame error: {e}")

    def on_checks_updated(self, checks: dict):
        try:
            face = checks.get("face", False)
            eyes = checks.get("eyes", False)
            time_since = checks.get("time_since_eval", 0.0)

            passed = sum([face, eyes])

            self.status_chip.setText(f"Checks: {passed} / 2")
            if passed == 2:
                self.status_chip.setStyleSheet("padding:6px;border-radius:8px;background:#08332f;color:#dff6f2;")
            elif passed == 1:
                self.status_chip.setStyleSheet("padding:6px;border-radius:8px;background:#3b2f07;color:#ffdca6;")
            else:
                self.status_chip.setStyleSheet("padding:6px;border-radius:8px;background:#3b0a0a;color:#ffd6d6;")

            self.last_eval_label.setText(f"Last eval: {int(time_since)}s")
            stat_text = f"Face: {'✓' if face else '✗'}\nEyes: {'✓' if eyes else '✗'}\nAuto-capture: {'On' if self.auto_cb.isChecked() else 'Off'}"
            self.status_text.setText(stat_text)
        except Exception as e:
            self.console_append(f"on_checks_updated error: {e}")

    def on_thinking(self):
        self.instruction_label.setText("Thinking...")
        self.instruction_label.setVisible(True)

    def on_instruction(self, text: str):
        self.instruction_label.setText(text)
        self.instruction_label.setVisible(True)
        self.last_instruction_ts = time.time()

    def on_thumbnail_added(self, data_url: str):
        try:
            if data_url.startswith("data:image"):
                header, b64 = data_url.split(",", 1)
                b = base64.b64decode(b64)
                img = QtGui.QImage.fromData(b)
                pix = QtGui.QPixmap.fromImage(img).scaledToWidth(120, QtCore.Qt.SmoothTransformation)
                payload = data_url
            else:
                pix = QtGui.QPixmap(data_url).scaledToWidth(120, QtCore.Qt.SmoothTransformation)
                payload = data_url

            cl = ClickableLabel(payload=payload)
            cl.setPixmap(pix)
            cl.clicked.connect(self._open_fullscreen)
            # insert at beginning
            self.thumb_layout.insertWidget(0, cl)
            while self.thumb_layout.count() > 8:
                w = self.thumb_layout.itemAt(self.thumb_layout.count() - 1).widget()
                if w:
                    w.setParent(None)
        except Exception as e:
            self.console_append(f"on_thumbnail_added error: {e}")

    def _open_fullscreen(self, payload):
        viewer = ImageViewer(payload, parent=self)
        viewer.exec_()

    def on_error(self, message: str):
        self.console_append(f"ERROR: {message}")

    def console_append(self, text: str):
        ts = time.strftime("%H:%M:%S")
        self.console.append(f"[{ts}] {text}")

    def manual_capture(self):
        try:
            frame = frame_cap()
            if frame is None:
                self.console_append("manual_capture: no frame")
                return
            gallery_path = self.config["gallery_path"]
            if not os.path.exists(gallery_path):
                os.makedirs(gallery_path, exist_ok=True)
            existing = [f for f in os.listdir(gallery_path) if f.startswith("photo_") and f.endswith(".jpg")]
            idx = len(existing)
            add_to_gallery(idx, frame)
            thumb = CaptureWorker(self.comm, self.config)._frame_to_data_url(frame, max_w=320)
            self.on_thumbnail_added(thumb)
            self.console_append("Manual capture saved")
        except Exception as e:
            self.console_append(f"manual_capture error: {e}")

    def open_settings(self):
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Settings")
        layout = QtWidgets.QFormLayout(dlg)
        eval_spin = QtWidgets.QSpinBox()
        eval_spin.setMinimum(1)
        eval_spin.setMaximum(60)
        eval_spin.setValue(self.config.get("eval_interval", 10))
        layout.addRow("Evaluation interval (s)", eval_spin)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addRow(btns)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            val = eval_spin.value()
            self.config["eval_interval"] = val
            self.console_append(f"Settings updated: eval_interval={val}")

    def _tick(self):
        if self.instruction_label.isVisible():
            if time.time() - self.last_instruction_ts > 10:
                self.instruction_label.setVisible(False)
        try:
            if hasattr(self.capture_worker, "last_eval_ts"):
                secs = int(time.time() - self.capture_worker.last_eval_ts)
                self.last_eval_label.setText(f"Last eval: {secs}s")
        except Exception:
            pass

    def _auto_changed(self, state):
        self.config["auto_enabled"] = bool(state == QtCore.Qt.Checked)
        self.console_append(f"Auto-capture set to {self.config['auto_enabled']}")


def main():
    app = QtWidgets.QApplication(sys.argv)
    palette = app.palette()
    palette.setColor(QtGui.QPalette.Window, QtGui.QColor("#0b0f14"))
    app.setPalette(palette)

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()