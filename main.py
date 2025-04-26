import sys
import msvcrt
import threading
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QBrush, QColor
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget

# Global variables for rectangle parameters
outline_width = 2
outline_color = Qt.white
move_step = 10  # Step size for movement

class GameOverlay(QWidget):
    def __init__(self, rect_x, rect_y):
        super().__init__()

        self.rect_x = rect_x
        self.rect_y = rect_y
        self.rect_width = 100  # Rectangle width
        self.rect_height = 50  # Rectangle height

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()

        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        self.setGeometry(0, 0, screen_width, screen_height)  # Set the overlay size to match the screen
        self.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw a transparent background
        painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
        painter.drawRect(self.rect())

        # Draw the rectangle outline
        painter.setPen(QColor(outline_color))
        painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
        painter.drawRect(self.rect_x, self.rect_y, self.rect_width, self.rect_height)

    def move_rectangle(self, dx, dy=0):
        self.rect_x += dx
        self.rect_y += dy
        self.update()

    def resize_rectangle(self, dw, dh):
        self.rect_width = max(10, self.rect_width + dw)  # Ensure minimum width
        self.rect_height = max(5, self.rect_height + dh)  # Ensure minimum height
        self.update()

def handle_input(overlays):
    try:
        while True:
            if msvcrt.kbhit():
                key = msvcrt.getch().decode('utf-8').lower()
                if key == 'a':  # Move left
                    overlays[0].move_rectangle(-move_step)
                elif key == 'd':  # Move right
                    overlays[0].move_rectangle(move_step)
                elif key == 'w':  # Move up
                    overlays[0].move_rectangle(0, -move_step)
                elif key == 's':  # Move down
                    overlays[0].move_rectangle(0, move_step)
                elif key == '+':  # Increase rectangle size
                    overlays[0].resize_rectangle(10, 5)
                elif key == '-':  # Decrease rectangle size
                    overlays[0].resize_rectangle(-10, -5)
    except KeyboardInterrupt:
        print("Exiting...")
        for overlay in overlays:
            overlay.close()
        sys.exit(0)  # Exit immediately on Ctrl+C

def main():
    app = QApplication(sys.argv)

    # Initial rectangle position
    screen = QApplication.primaryScreen()
    screen_geometry = screen.geometry()
    initial_x = (screen_geometry.width() - 100) // 2
    initial_y = (screen_geometry.height() - 50) // 2

    # Create the first overlay
    overlays = [GameOverlay(initial_x, initial_y)]

    timer = QTimer()
    timer.timeout.connect(overlays[0].update)
    timer.start(16)  # Update the overlay approximately every 16 milliseconds (about 60 FPS)

    input_thread = threading.Thread(target=handle_input, args=(overlays,), daemon=True)
    input_thread.start()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
