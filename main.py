import sys
import msvcrt
import threading
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QBrush, QColor
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget

# Global variables for rectangle parameters
rect_width = 100
rect_height = 50
outline_width = 2
outline_color = Qt.white

class GameOverlay(QWidget):
    def __init__(self, rect_x, rect_y):
        super().__init__()

        self.rect_x = rect_x
        self.rect_y = rect_y

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
        painter.drawRect(self.rect_x, self.rect_y, rect_width, rect_height)

    def move_rectangle(self, dx, dy=0):
        self.rect_x += dx
        self.rect_y += dy
        self.update()

def handle_input(overlay):
    try:
        while True:
            if msvcrt.kbhit():
                key = msvcrt.getch().decode('utf-8').lower()
                if key == 'a':  # Move left
                    overlay.move_rectangle(-10)
                elif key == 'd':  # Move right
                    overlay.move_rectangle(10)
                elif key == 'w':  # Move up
                    overlay.move_rectangle(0, -10)
                elif key == 's':  # Move down
                    overlay.move_rectangle(0, 10)
    except KeyboardInterrupt:
        print("Exiting...")
        overlay.close()
        sys.exit(0)  # Exit immediately on Ctrl+C

def main():
    app = QApplication(sys.argv)

    # Initial rectangle position
    screen = QApplication.primaryScreen()
    screen_geometry = screen.geometry()
    initial_x = (screen_geometry.width() - rect_width) // 2
    initial_y = (screen_geometry.height() - rect_height) // 2

    overlay = GameOverlay(initial_x, initial_y)

    timer = QTimer()
    timer.timeout.connect(overlay.update)
    timer.start(16)  # Update the overlay approximately every 16 milliseconds (about 60 FPS)

    input_thread = threading.Thread(target=handle_input, args=(overlay,), daemon=True)
    input_thread.start()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
