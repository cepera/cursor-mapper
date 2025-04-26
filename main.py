import sys
import msvcrt
import threading
import configparser
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QBrush, QColor
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget

# Global variables for rectangle parameters
outline_width = 2
outline_color = Qt.white
move_step = 10  # Step size for movement
config_file = "rect_config.ini"  # Configuration file path

class GameOverlay(QWidget):
    def __init__(self, rect_x, rect_y, rect_width=100, rect_height=50):
        super().__init__()

        self.rect_x = rect_x
        self.rect_y = rect_y
        self.rect_width = rect_width  # Rectangle width
        self.rect_height = rect_height  # Rectangle height

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
        save_rect_config(self.rect_x, self.rect_y, self.rect_width, self.rect_height)

    def resize_rectangle(self, dw, dh):
        self.rect_width = max(10, self.rect_width + dw)  # Ensure minimum width
        self.rect_height = max(5, self.rect_height + dh)  # Ensure minimum height
        self.update()
        save_rect_config(self.rect_x, self.rect_y, self.rect_width, self.rect_height)

def save_rect_config(x, y, width, height, screen_index=0):
    config = configparser.ConfigParser()
    config['rectA'] = {
        'x': str(x),
        'y': str(y),
        'width': str(width),
        'height': str(height),
        'screen': str(screen_index)
    }
    with open(config_file, 'w') as configfile:
        config.write(configfile)

def load_rect_config():
    config = configparser.ConfigParser()
    if config.read(config_file) and 'rectA' in config:
        x = int(config['rectA'].get('x', 0))
        y = int(config['rectA'].get('y', 0))
        width = int(config['rectA'].get('width', 100))
        height = int(config['rectA'].get('height', 50))
        screen_index = int(config['rectA'].get('screen', 0))
        return x, y, width, height, screen_index
    return 0, 0, 100, 50, 0  # Default values

def handle_input(overlays):
    try:
        screens = QApplication.screens()  # Get all available screens
        print(f"Number of screens: {len(screens)}")
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

    # Get all available screens
    screens = QApplication.screens()
    print(f"Available screens: {len(screens)}")

    # Load rectangle configuration or use defaults
    rect_x, rect_y, rect_width, rect_height, screen_index = load_rect_config()

    # Validate screen index
    if screen_index >= len(screens):
        print(f"Screen {screen_index} is not available. Defaulting to primary screen.")
        screen_index = 0

    # Adjust rectangle position to fit within the selected screen
    screen_geometry = screens[screen_index].geometry()
    rect_x = max(0, min(rect_x, screen_geometry.width() - rect_width))
    rect_y = max(0, min(rect_y, screen_geometry.height() - rect_height))

    # Create the first overlay
    overlay = GameOverlay(rect_x, rect_y, rect_width, rect_height)
    overlay.setGeometry(screen_geometry)  # Explicitly set the overlay to match the selected screen's geometry
    overlays = [overlay]

    timer = QTimer()
    timer.timeout.connect(overlays[0].update)
    timer.start(16)  # Update the overlay approximately every 16 milliseconds (about 60 FPS)

    input_thread = threading.Thread(target=handle_input, args=(overlays,), daemon=True)
    input_thread.start()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
