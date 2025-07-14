import sys
import threading
import configparser
import ctypes
import msvcrt
import signal
from ctypes import wintypes
from PyQt5.QtCore import Qt, QTimer, QEventLoop, QPoint, QObject, pyqtSignal
from PyQt5.QtGui import QPainter, QBrush, QColor, QPen
from PyQt5.QtWidgets import QApplication, QWidget

# Global variables for rectangle parameters
outline_width = 2
move_step = 1  # Step size for movement
resize_step = 5  # Step size for resizing height and width
config_file = "rect_config.ini"  # Configuration file path

class OverlayManager(QObject):
    """Manages overlay creation and switching from main thread."""
    recreate_overlay = pyqtSignal(int, str, object)  # index, config_section, outline_color

    def __init__(self):
        super().__init__()
        self.overlays = []
        self.recreate_overlay.connect(self.handle_recreate_overlay)

    def set_overlays(self, overlays):
        self.overlays = overlays

    def handle_recreate_overlay(self, index, config_section, outline_color):
        """Handle overlay recreation on main thread."""
        if index < len(self.overlays):
            # Close old overlay
            old_overlay = self.overlays[index]
            old_overlay.close()
            old_overlay.deleteLater()

            # Create new overlay
            new_overlay = GameOverlay(config_section, outline_color)
            self.overlays[index] = new_overlay
            print(f"Recreated {config_section} overlay")

# Global overlay manager instance
overlay_manager = OverlayManager()

class GameOverlay(QWidget):
    def __init__(self, config_section="rectA", outline_color=Qt.red):
        super().__init__()

        self.config_section = config_section  # Unique configuration section for this overlay
        self.outline_color = outline_color  # Outline color for the rectangle

        # Load configuration from file
        self.rect_x, self.rect_y, self.rect_width, self.rect_height, self.screen_index = load_rect_config(config_section)

        # Get all available screens and validate screen index
        screens = QApplication.screens()
        self.screen_index = validate_screen_index(self.screen_index, config_section, screens)

        # Get the target screen geometry
        screen_geometry = screens[self.screen_index].geometry()

        # Adjust rectangle positions to fit within the selected screen
        self.rect_x = max(0, min(self.rect_x, screen_geometry.width() - self.rect_width))
        self.rect_y = max(0, min(self.rect_y, screen_geometry.height() - self.rect_height))

        self.dot_x = None  # Dot x-coordinate
        self.dot_y = None  # Dot y-coordinate

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Set the overlay geometry to match the target screen
        self.setGeometry(screen_geometry)
        self.show()

    def draw_cursor(self, x, y):
        """Set the cursor position and trigger a repaint."""
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

        # Draw the cursor arrow if it exists
        painter.setPen(QPen(QColor(Qt.black), 1.5))  # Black arrow lines with thickness 2
        painter.setBrush(QBrush(Qt.white))  # Fill the triangle with white color

        if self.dot_x is not None and self.dot_y is not None:
            # Define the points of the triangle
            tip = QPoint(int(self.dot_x), int(self.dot_y))  # Tip point
            bottom = QPoint(int(self.dot_x), int(self.dot_y) + 10)  # Bottom point
            bottom_right = QPoint(int(self.dot_x) + 10, int(self.dot_y) + 10)  # Bottom-right point

            # Draw the filled triangle
            painter.drawPolygon(tip, bottom, bottom_right)

            # Draw the lines for the arrow
            painter.drawLine(tip, bottom)  # Vertical line
            painter.drawLine(tip, bottom_right)  # Diagonal line
        painter.end()

    def move_rectangle(self, dx, dy=0):
        self.rect_x += dx
        self.rect_y += dy
        self.update()
        save_rect_config(self.config_section, self.rect_x, self.rect_y, self.rect_width, self.rect_height, self.screen_index)

    def resize_rectangle(self, dw, dh):
        self.rect_width = max(10, self.rect_width + dw)  # Ensure minimum width
        self.rect_height = max(5, self.rect_height + dh)  # Ensure minimum height
        self.update()
        save_rect_config(self.config_section, self.rect_x, self.rect_y, self.rect_width, self.rect_height, self.screen_index)

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

def validate_screen_index(screen_index, section_name, available_screens):
    """Validate screen index and return 0 with warning if screen doesn't exist."""
    if screen_index >= len(available_screens):
        print(f"Screen {screen_index} for {section_name} is not available. Defaulting to primary screen.")
        return 0
    return screen_index

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
    """Check if the cursor is inside rectA and draw a corresponding cursor in rectB."""
    adjusted_x, adjusted_y, screen_index = track_cursor_position()
    if screen_index == -1:
        print("Cursor is not on any screen.")
        overlayB.draw_cursor(None, None)  # Clear the cursor in rectB
        return

    # Check if cursor is on overlayA's screen
    if screen_index != overlayA.screen_index:
        overlayB.draw_cursor(None, None)  # Clear the cursor in rectB if not on correct screen
        return

    if overlayA.rect_x <= adjusted_x <= overlayA.rect_x + overlayA.rect_width and \
       overlayA.rect_y <= adjusted_y <= overlayA.rect_y + overlayA.rect_height:
        # Calculate scaled position in rectB
        relative_x = (adjusted_x - overlayA.rect_x) / overlayA.rect_width
        relative_y = (adjusted_y - overlayA.rect_y) / overlayA.rect_height
        cursor_x = overlayB.rect_x + relative_x * overlayB.rect_width
        cursor_y = overlayB.rect_y + relative_y * overlayB.rect_height
        overlayB.draw_cursor(cursor_x, cursor_y)
    else:
        overlayB.draw_cursor(None, None)  # Clear the cursor in rectB

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
                elif key == 'i':  # Increase height
                    overlays[current_overlay_index].resize_rectangle(0, resize_step)
                elif key == 'k':  # Decrease height
                    overlays[current_overlay_index].resize_rectangle(0, -resize_step)
                elif key == 'j':  # Decrease width
                    overlays[current_overlay_index].resize_rectangle(-resize_step, 0)
                elif key == 'l':  # Increase width
                    overlays[current_overlay_index].resize_rectangle(resize_step, 0)
                elif key.isdigit():  # Number keys 0-9 for screen switching
                    screen_num = int(key)
                    if screen_num < len(screens):
                        current_overlay = overlays[current_overlay_index]

                        # Store overlay info before closing
                        config_section = current_overlay.config_section
                        outline_color = current_overlay.outline_color

                        # Save current position/size with new screen index
                        save_rect_config(config_section, current_overlay.rect_x, current_overlay.rect_y, 
                                       current_overlay.rect_width, current_overlay.rect_height, screen_num)

                        print(f"Moving {config_section} to screen {screen_num}")

                        # Signal main thread to recreate overlay
                        overlay_manager.recreate_overlay.emit(current_overlay_index, config_section, outline_color)

                    else:
                        print(f"Screen {screen_num} is not available. Available screens: 0-{len(screens)-1}")
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

    # Create the overlays
    overlayA = GameOverlay("rectA", Qt.red)
    overlayB = GameOverlay("rectB", Qt.blue)

    overlays = [overlayA, overlayB]

    # Set up overlay manager
    overlay_manager.set_overlays(overlays)

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
