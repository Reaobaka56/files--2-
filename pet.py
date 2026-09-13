"""
Pikachu Desktop Pet (Windows)
-----------------------------
A transparent overlay pet that sits on your desktop, follows whichever
window/app you switch focus to (sitting on top of it), and can be
dragged anywhere. Built with PySide6 + pygetwindow.

Sprite states (drop your own GIFs into sprites/ to swap these out):
    idle     -> sprites/Animated_Sticker.gif
    happy    -> sprites/happy_anything_is_possible_STICKER.gif
    charging -> sprites/pokemon_charging_up_STICKER.gif
    dancing  -> sprites/Dance_Dancing_Sticker.gif

Behavior:
    - Stays put by default (no random wandering).
    - When you switch focus to a different window/app, it walks over
      and hops onto the top edge of that window.
    - Left-drag to move it anywhere yourself.
    - Double-click to make it dance. Right-click for a menu with more
      emotes. Nothing changes state on its own except the focus-follow.

Install deps:
    pip install PySide6 pygetwindow pynput

Run:
    python pet.py
"""
import sys
import os

from PySide6.QtWidgets import QApplication, QLabel, QWidget, QMenu
from PySide6.QtCore import Qt, QTimer, QPoint, QSize
from PySide6.QtGui import QMovie, QAction
import pygetwindow as gw


def _base_dir():
    # When frozen by PyInstaller, bundled data lives in sys._MEIPASS instead
    # of next to the exe.
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


SPRITE_DIR = os.path.join(_base_dir(), "sprites")

SPRITES = {
    "idle":     "Animated_Sticker.gif",
    "happy":    "happy_anything_is_possible_STICKER.gif",
    "charging": "pokemon_charging_up_STICKER.gif",
    "dancing":  "Dance_Dancing_Sticker.gif",
}

# Every sprite is displayed at this exact size, regardless of its
# original GIF resolution, so nothing changes size when it switches state.
SPRITE_SIZE = QSize(110, 110)

# How long (ms) a double-click / menu emote plays before returning to idle
EMOTE_DURATION_MS = 3000

WALK_SPEED = 8
JUMP_STEP = 0.06

# How far above a window's top edge to perch, and how far in from the
# left edge (so it doesn't sit dead-center on the title bar text).
PERCH_OFFSET_X = 40
PERCH_OFFSET_Y = 10

# How often (ms) to check which window/app currently has focus.
FOCUS_POLL_MS = 400


class Pet(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.label = QLabel(self)
        self.label.setFixedSize(SPRITE_SIZE)
        self.setFixedSize(SPRITE_SIZE)

        self.movies = {}
        for name, filename in SPRITES.items():
            path = os.path.join(SPRITE_DIR, filename)
            movie = QMovie(path)
            movie.setScaledSize(SPRITE_SIZE)  # normalize every sprite to one size
            self.movies[name] = movie

        self.current_state = None
        self.set_sprite("idle")

        # start somewhere reasonable on screen
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.width() // 2 - SPRITE_SIZE.width() // 2,
            screen.height() - SPRITE_SIZE.height(),
        )

        self.behavior_state = "idle"   # idle / walking / jumping
        self.target = None
        self.drag_offset = QPoint()
        self._dragging = False
        self._own_hwnd = int(self.winId())
        self._last_focus_id = None

        self.emote_timer = QTimer(self)
        self.emote_timer.setSingleShot(True)
        self.emote_timer.timeout.connect(lambda: self.set_sprite("idle"))

        # 20fps loop for walk/jump movement
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(50)

        # separate, slower loop just for "what's focused now?"
        self.focus_timer = QTimer(self)
        self.focus_timer.timeout.connect(self.check_focus)
        self.focus_timer.start(FOCUS_POLL_MS)

        self.show()

    # ---------- sprite handling ----------
    def set_sprite(self, name):
        if self.current_state == name:
            return
        if self.current_state is not None:
            self.movies[self.current_state].stop()
        self.current_state = name
        movie = self.movies[name]
        self.label.setMovie(movie)
        movie.start()

    def emote(self, name, duration_ms=EMOTE_DURATION_MS):
        """Play a temporary animation, then fall back to idle."""
        self.set_sprite(name)
        self.emote_timer.start(duration_ms)

    # ---------- focus tracking ----------
    def check_focus(self):
        if self._dragging or self.behavior_state != "idle":
            return
        try:
            win = gw.getActiveWindow()
        except Exception:
            return
        if win is None or not win.title:
            return

        # Ignore our own pet window and ignore "no real change" cases.
        hwnd = getattr(win, "_hWnd", None)
        if hwnd == self._own_hwnd:
            return
        if hwnd is not None and hwnd == self._last_focus_id:
            return
        if win.width < 150 or win.height < 100:
            return  # too small to be a real app window (tooltips etc.)

        self._last_focus_id = hwnd
        self.go_to_window(win)

    def go_to_window(self, win):
        target_x = win.left + PERCH_OFFSET_X
        target_y = win.top + PERCH_OFFSET_Y
        self.target = QPoint(target_x, target_y)
        self.behavior_state = "walking"

    # ---------- movement loop ----------
    def tick(self):
        if self._dragging:
            return
        if self.behavior_state == "walking":
            self.walk_step()
        elif self.behavior_state == "jumping":
            self.jump_step()

    def walk_step(self):
        pos = self.pos()
        dx = self.target.x() - pos.x()
        if abs(dx) > 8:
            self.move(pos.x() + (WALK_SPEED if dx > 0 else -WALK_SPEED), pos.y())
        else:
            self.behavior_state = "jumping"
            self.jump_progress = 0
            self.start_y = pos.y()

    def jump_step(self):
        self.jump_progress += JUMP_STEP
        t = self.jump_progress
        if t >= 1:
            self.move(self.target.x(), self.target.y())
            self.behavior_state = "idle"
            return
        x = int(self.pos().x() + (self.target.x() - self.pos().x()) * 0.15)
        y = int(
            self.start_y
            - (self.start_y - self.target.y()) * t
            - 30 * 4 * t * (1 - t)
        )
        self.move(x, y)

    # ---------- interaction ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self.behavior_state = "idle"
            self.drag_offset = e.globalPosition().toPoint() - self.pos()
        elif e.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        if self._dragging and (e.buttons() & Qt.MouseButton.LeftButton):
            self.move(e.globalPosition().toPoint() - self.drag_offset)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._dragging = False

    def mouseDoubleClickEvent(self, e):
        self.emote("dancing")

    def show_context_menu(self, global_pos):
        menu = QMenu(self)
        for label, state in [
            ("Dance", "dancing"),
            ("Charge up", "charging"),
            ("Happy", "happy"),
        ]:
            action = QAction(label, self)
            action.triggered.connect(lambda checked=False, s=state: self.emote(s))
            menu.addAction(action)
        menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(quit_action)
        menu.exec(global_pos)


def main():
    app = QApplication(sys.argv)
    pet = Pet()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
