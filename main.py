import sys
import threading
import configparser
import ctypes
import msvcrt
import signal
from ctypes import wintypes
from PyQt5.QtCore import Qt, QTimer, QEventLoop
from PyQt5.QtGui import QPainter, QBrush, QColor
from PyQt5.QtWidgets import QApplication, QWidget

# Global variables for rectangle parameters
outline_width = 2
move_step = 10  # Step size for movement
config_file = "rect_config.ini"  # Configuration file path

class GameOverlay(QWidget):
    def __init__(self, rect_x, rect_y, rect_width=100, rect_height=50, config_section="rectA", outline_color=Qt.red):
        super().__init__()

        self.rect_x = rect_x
        self.rect_y = rect_y
        self.rect_width = rect_width  # Rectangle width
        self.rect_height = rect_height  # Rectangle height
        self.config_section = config_section  # Unique configuration section for this overlay
        self.outline_color = outline_color  # Outline color for the rectangle
        self.dot_x = None  # Dot x-coordinate
        self.dot_y = None  # Dot y-coordinate

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()

        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        self.setGeometry(0, 0, screen_width, screen_height)  # Set the overlay size to match the screen
        self.show()

    def draw_dot(self, x, y):
        """Set the dot position and trigger a repaint."""
        self.dot_x = x
        self.dot_y = y
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw a transparent background
        painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
        painter.drawRect(self.rect())

        # Draw the rectangle outline
        painter.setPen(QColor(self.outline_color))  # Use the instance's outline color
        painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
        painter.drawRect(self.rect_x, self.rect_y, self.rect_width, self.rect_height)

        # Draw the dot if it exists
        if self.dot_x is not None and self.dot_y is not None:
            painter.setBrush(QBrush(Qt.black))  # Black dot
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(self.dot_x) - 5, int(self.dot_y) - 5, 10, 10)  # Convert to int
        painter.end()

    def move_rectangle(self, dx, dy=0):
        self.rect_x += dx
        self.rect_y += dy
        self.update()
        save_rect_config(self.config_section, self.rect_x, self.rect_y, self.rect_width, self.rect_height)

    def resize_rectangle(self, dw, dh):
        self.rect_width = max(10, self.rect_width + dw)  # Ensure minimum width
        self.rect_height = max(5, self.rect_height + dh)  # Ensure minimum height
        self.update()
        save_rect_config(self.config_section, self.rect_x, self.rect_y, self.rect_width, self.rect_height)

def save_rect_config(section, x, y, width, height, screen_index=1):
    config = configparser.ConfigParser()
    config.read(config_file)
    if section not in config:
        config[section] = {}
    config[section].update({
        'x': str(x),
        'y': str(y),
        'width': str(width),
        'height': str(height),
        'screen': str(screen_index)
    })
    with open(config_file, 'w') as configfile:
        config.write(configfile)

def load_rect_config(section):
    config = configparser.ConfigParser()
    if config.read(config_file) and section in config:
        x = int(config[section].get('x', 0))
        y = int(config[section].get('y', 0))
        width = int(config[section].get('width', 100))
        height = int(config[section].get('height', 50))
        screen_index = int(config[section].get('screen', 0))
        return x, y, width, height, screen_index
    return 0, 0, 100, 50, 0  # Default values

def is_cursor_inside_rect(rect_x, rect_y, rect_width, rect_height):
    cursor = wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(cursor))
    return rect_x <= cursor.x <= rect_x + rect_width and rect_y <= cursor.y <= rect_y + rect_height, cursor.x, cursor.y

def track_cursor_position():
    """Return the cursor position adjusted for the screen and the screen index."""
    cursor = wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(cursor))
    screens = QApplication.screens()
    for i, screen in enumerate(screens):
        geometry = screen.geometry()
        if geometry.contains(cursor.x, cursor.y):
            adjusted_x = cursor.x - geometry.x()  # Adjust x-coordinate relative to the screen
            adjusted_y = cursor.y - geometry.y()  # Adjust y-coordinate relative to the screen
            return adjusted_x, adjusted_y, i
    return cursor.x, cursor.y, -1  # Return -1 for screen if not found

def is_cursor_inside_rectA_and_draw_in_rectB(overlayA, overlayB):
    """Check if the cursor is inside rectA and draw a corresponding dot in rectB."""
    adjusted_x, adjusted_y, screen_index = track_cursor_position()
    if screen_index == -1:
        print("Cursor is not on any screen.")
        overlayB.draw_dot(None, None)  # Clear the dot in rectB
        return

    # print(f"Cursor position: ({adjusted_x}, {adjusted_y}), Screen: {screen_index}")

    if overlayA.rect_x <= adjusted_x <= overlayA.rect_x + overlayA.rect_width and \
       overlayA.rect_y <= adjusted_y <= overlayA.rect_y + overlayA.rect_height:
        print(f"Cursor is inside rectA on screen {screen_index}.")
        # Calculate scaled position in rectB
        relative_x = (adjusted_x - overlayA.rect_x) / overlayA.rect_width
        relative_y = (adjusted_y - overlayA.rect_y) / overlayA.rect_height
        dot_x = overlayB.rect_x + relative_x * overlayB.rect_width
        dot_y = overlayB.rect_y + relative_y * overlayB.rect_height
        overlayB.draw_dot(dot_x, dot_y)
    else:
        print(f"Cursor is outside rectA on screen {screen_index}.")
        overlayB.draw_dot(None, None)  # Clear the dot in rectB

def handle_input(overlays, input_done_event):
    try:
        screens = QApplication.screens()  # Get all available screens
        print(f"Number of screens: {len(screens)}")
        current_overlay_index = 0
        print(f"Set {overlays[current_overlay_index].config_section}...")

        while True:
            if msvcrt.kbhit():
                key = msvcrt.getch().decode('utf-8').lower()
                if key == 'a':  # Move left
                    overlays[current_overlay_index].move_rectangle(-move_step)
                elif key == 'd':  # Move right
                    overlays[current_overlay_index].move_rectangle(move_step)
                elif key == 'w':  # Move up
                    overlays[current_overlay_index].move_rectangle(0, -move_step)
                elif key == 's':  # Move down
                    overlays[current_overlay_index].move_rectangle(0, move_step)
                elif key == '+':  # Increase rectangle size
                    overlays[current_overlay_index].resize_rectangle(10, 5)
                elif key == '-':  # Decrease rectangle size
                    overlays[current_overlay_index].resize_rectangle(-10, -5)
                elif key == '\r':  # Enter key
                    current_overlay_index += 1
                    if current_overlay_index < len(overlays):
                        print(f"Set {overlays[current_overlay_index].config_section}...")
                    else:
                        print("All input done! Rectangles are still visible for further actions.")
                        input_done_event.set()  # Signal that input is done
                        break
    except KeyboardInterrupt:
        print("Exiting...")
        for overlay in overlays:
            overlay.close()
        sys.exit(0)  # Exit immediately on Ctrl+C

def main():
    app = QApplication(sys.argv)

    # Handle KeyboardInterrupt (Ctrl+C) gracefully
    def handle_interrupt(signal, frame):
        print("Exiting application...")
        app.quit()

    signal.signal(signal.SIGINT, handle_interrupt)

    # Get all available screens
    screens = QApplication.screens()
    print(f"Available screens: {len(screens)}")

    # Load rectangle configurations or use defaults
    rectA_x, rectA_y, rectA_width, rectA_height, rectA_screen_index = load_rect_config("rectA")
    rectB_x, rectB_y, rectB_width, rectB_height, rectB_screen_index = load_rect_config("rectB")

    # Validate screen indices
    if rectA_screen_index >= len(screens):
        print(f"Screen {rectA_screen_index} for rectA is not available. Defaulting to primary screen.")
        rectA_screen_index = 0
    if rectB_screen_index >= len(screens):
        print(f"Screen {rectB_screen_index} for rectB is not available. Defaulting to primary screen.")
        rectB_screen_index = 0

    # Adjust rectangle positions to fit within the selected screens
    rectA_geometry = screens[rectA_screen_index].geometry()
    rectA_x = max(0, min(rectA_x, rectA_geometry.width() - rectA_width))
    rectA_y = max(0, min(rectA_y, rectA_geometry.height() - rectA_height))

    rectB_geometry = screens[rectB_screen_index].geometry()
    rectB_x = max(0, min(rectB_x, rectB_geometry.width() - rectB_width))
    rectB_y = max(0, min(rectB_y, rectB_geometry.height() - rectB_height))

    # Create the overlays
    overlayA = GameOverlay(rectA_x, rectA_y, rectA_width, rectA_height, config_section="rectA", outline_color=Qt.red)
    overlayA.setGeometry(rectA_geometry)

    overlayB = GameOverlay(rectB_x, rectB_y, rectB_width, rectB_height, config_section="rectB", outline_color=Qt.blue)
    overlayB.setGeometry(rectB_geometry)

    overlays = [overlayA, overlayB]

    # Event to signal when input is done
    input_done_event = threading.Event()

    # Start the handle_input thread
    input_thread = threading.Thread(target=handle_input, args=(overlays, input_done_event), daemon=True)
    input_thread.start()

    # Use a QTimer to periodically check if the input thread has finished
    def check_input_done():
        if input_done_event.is_set():
            print("All input done! Rectangles are still visible for further actions.")
            timer.stop()  # Stop the timer once input is done

    timer = QTimer()
    timer.timeout.connect(check_input_done)
    timer.start(40)  # Check every 100 milliseconds

    # Wait for the QTimer to finish using a QEventLoop
    loop = QEventLoop()
    timer.timeout.connect(lambda: loop.quit() if not timer.isActive() else None)
    loop.exec_()

    print("QTimer has finished.")

    # Check if cursor is inside rectA and draw in rectB every second
    def check_cursor_in_rectA_and_draw_in_rectB():
        is_cursor_inside_rectA_and_draw_in_rectB(overlayA, overlayB)

    cursor_timer = QTimer()
    cursor_timer.timeout.connect(check_cursor_in_rectA_and_draw_in_rectB)
    cursor_timer.start(30)

    # Start the QApplication event loop
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
