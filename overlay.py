import sys
import json
import os # <-- Added this import
from PyQt5 import QtWidgets, QtCore, QtGui
import win32con, win32gui, win32api
from PyQt5.QtCore import Qt
import math

# --- NEW: Helper function to find bundled files ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- Collapsible GroupBox Widget ---
class CollapsibleBox(QtWidgets.QWidget):
    def __init__(self, title="", parent=None):
        super(CollapsibleBox, self).__init__(parent)
        self.toggle_button = QtWidgets.QToolButton(text=title, checkable=True, checked=False)
        self.toggle_button.setStyleSheet("QToolButton { border: none; font-weight: bold; }")
        self.toggle_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(QtCore.Qt.RightArrow)
        self.toggle_button.toggled.connect(self.on_toggled)

        self.content_area = QtWidgets.QWidget()
        self.content_area.setMaximumHeight(0)
        self.content_area.setMinimumHeight(0)
        
        self.toggle_animation = QtCore.QParallelAnimationGroup(self)
        self.content_animation = QtCore.QPropertyAnimation(self.content_area, b"maximumHeight")

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.toggle_button)
        main_layout.addWidget(self.content_area)
        
        self.toggle_animation.addAnimation(self.content_animation)

    def on_toggled(self, checked):
        self.toggle_button.setArrowType(QtCore.Qt.DownArrow if checked else QtCore.Qt.RightArrow)
        self.toggle_animation.setDirection(QtCore.QAbstractAnimation.Forward if checked else QtCore.QAbstractAnimation.Backward)
        self.toggle_animation.start()
        
        if checked:
            if hasattr(self.parent(), 'collapse_others'):
                self.parent().collapse_others(self)

    def setContentLayout(self, layout):
        self.content_area.setLayout(layout)
        content_height = layout.sizeHint().height()
        self.content_animation.setDuration(300)
        self.content_animation.setStartValue(0)
        self.content_animation.setEndValue(content_height)

    def collapse(self):
        self.toggle_button.setChecked(False)

# --- Main Settings Window ---
class SettingsWindow(QtWidgets.QWidget):
    def __init__(self, overlay):
        super().__init__()
        self.overlay = overlay
        self.setWindowTitle("SmartCue Settings")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.drag_pos = None
        self.boxes = []
        
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 5, 10, 10)
        self.init_ui()
        self.update_info_panel()
        self.apply_theme()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        bg_color = QtGui.QColor(*self.overlay.settings['gui_theme']['color'])
        painter.setBrush(bg_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 10, 10)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def collapse_others(self, current_box):
        for box in self.boxes:
            if box != current_box:
                box.collapse()

    def create_color_button(self, key):
        button = QtWidgets.QPushButton()
        button.setFixedSize(24, 24)
        button.clicked.connect(lambda: self.pick_color(key, button))
        return button

    def update_color_button(self, button, color_tuple):
        q_color = QtGui.QColor(*color_tuple)
        button.setStyleSheet(f"background-color: {q_color.name()}; border: 1px solid white;")

    def pick_color(self, key, button):
        current_color = QtGui.QColor(*self.overlay.settings[key]['color'])
        color = QtWidgets.QColorDialog.getColor(current_color, self, "Pick a color")
        if color.isValid():
            alpha = self.overlay.settings[key]['color'][3]
            self.overlay.settings[key]['color'] = [color.red(), color.green(), color.blue(), alpha]
            self.update_color_button(button, self.overlay.settings[key]['color'])
            self.overlay.save_settings()
            self.overlay.update()
            self.update()
            if key == 'gui_theme' or key == 'font_color':
                self.apply_theme()

    def create_setting_group(self, group_key, title):
        box = CollapsibleBox(title, self)
        layout = QtWidgets.QGridLayout()
        
        visibility_check = QtWidgets.QCheckBox("Visible")
        visibility_check.setChecked(self.overlay.settings[group_key]['visible'])
        visibility_check.stateChanged.connect(lambda state, k=group_key: self.toggle_visibility(k, state))
        layout.addWidget(visibility_check, 0, 0)

        size_spin = QtWidgets.QSpinBox()
        size_spin.setRange(1, 100)
        size_spin.setValue(self.overlay.settings[group_key]['size'])
        size_spin.valueChanged.connect(lambda val, k=group_key: self.change_size(k, val))
        layout.addWidget(QtWidgets.QLabel("Size:"), 1, 0)
        layout.addWidget(size_spin, 1, 1)

        color_button = self.create_color_button(group_key)
        self.update_color_button(color_button, self.overlay.settings[group_key]['color'])
        layout.addWidget(QtWidgets.QLabel("Color:"), 2, 0)
        layout.addWidget(color_button, 2, 1)

        alpha_slider = QtWidgets.QSlider(Qt.Horizontal)
        alpha_slider.setRange(0, 255)
        alpha_slider.setValue(self.overlay.settings[group_key]['color'][3])
        alpha_slider.valueChanged.connect(lambda val, k=group_key, b=color_button: self.change_alpha(k, val, b))
        layout.addWidget(QtWidgets.QLabel("Alpha:"), 3, 0)
        layout.addWidget(alpha_slider, 3, 1, 1, 2)
        
        if group_key == 'bounce_visuals':
            count_spin = QtWidgets.QSpinBox()
            count_spin.setRange(1, 5)
            count_spin.setValue(self.overlay.settings.get('bounce_count', 5))
            count_spin.valueChanged.connect(self.change_bounce_count)
            layout.addWidget(QtWidgets.QLabel("Count:"), 4, 0)
            layout.addWidget(count_spin, 4, 1)

        box.setContentLayout(layout)
        self.boxes.append(box)
        return box

    def toggle_visibility(self, key, state):
        self.overlay.settings[key]['visible'] = (state == Qt.Checked)
        self.overlay.save_settings()
        self.overlay.update()

    def change_size(self, key, value):
        self.overlay.settings[key]['size'] = value
        self.overlay.save_settings()
        self.overlay.update()

    def change_alpha(self, key, value, button):
        self.overlay.settings[key]['color'][3] = value
        self.update_color_button(button, self.overlay.settings[key]['color'])
        self.overlay.save_settings()
        self.overlay.update()
        self.update()
        if key == 'gui_theme' or key == 'font_color':
            self.apply_theme()

    def change_bounce_count(self, value):
        self.overlay.settings['bounce_count'] = value
        self.overlay.save_settings()
        self.overlay.update()

    def update_info_panel(self):
        for spin in [self.rect_x_spin, self.rect_y_spin, self.rect_w_spin, self.rect_h_spin]:
            spin.blockSignals(True)
        self.rect_x_spin.setValue(self.overlay.table_border.x())
        self.rect_y_spin.setValue(self.overlay.table_border.y())
        self.rect_w_spin.setValue(self.overlay.table_border.width())
        self.rect_h_spin.setValue(self.overlay.table_border.height())
        for spin in [self.rect_x_spin, self.rect_y_spin, self.rect_w_spin, self.rect_h_spin]:
            spin.blockSignals(False)
        obj_ball, ghost_ball = self.overlay.control_points
        self.obj_ball_label.setText(f"Obj Ball: ({int(obj_ball[0])}, {int(obj_ball[1])})")
        self.ghost_ball_label.setText(f"Ghost Ball: ({int(ghost_ball[0])}, {int(ghost_ball[1])})")

    def set_table_border_from_input(self):
        x, y, w, h = self.rect_x_spin.value(), self.rect_y_spin.value(), self.rect_w_spin.value(), self.rect_h_spin.value()
        self.overlay.table_border.setRect(x, y, w, h)
        self.overlay.update_pockets()
        self.overlay.save_settings()
        self.overlay.update()

    def init_ui(self):
        title_bar_layout = QtWidgets.QHBoxLayout()
        title_label = QtWidgets.QLabel("SmartCue")
        font_path = resource_path("MarckScript-Regular.ttf")
        font_id = QtGui.QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            font_family = QtGui.QFontDatabase.applicationFontFamilies(font_id)[0]
            title_font = QtGui.QFont(font_family, 24, QtGui.QFont.Bold)
            title_label.setFont(title_font)
        title_bar_layout.addWidget(title_label)
        title_bar_layout.addStretch()

        self.minimize_button = QtWidgets.QToolButton(text="—")
        self.restore_button = QtWidgets.QToolButton(text="+", visible=False)
        close_button = QtWidgets.QToolButton(text="X")
        self.minimize_button.clicked.connect(self.toggle_minimize)
        self.restore_button.clicked.connect(self.toggle_minimize)
        close_button.clicked.connect(self.overlay.close)
        title_bar_layout.addWidget(self.minimize_button)
        title_bar_layout.addWidget(self.restore_button)
        title_bar_layout.addWidget(close_button)
        self.main_layout.addLayout(title_bar_layout)
        
        self.content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0,0,0,0)

        groups = {
            'outer_rect': "Outer Rectangle", 'inner_rect': "Inner Rectangle",
            'pocket_lines': "Pocket Lines", 'center_ghost': "Object Ball",
            'connecting_line': "Connecting Line", 'bounce_ghost': "Movable Ghost Ball", 
            'bounce_visuals': "Bounce Ghost Balls", 'bounce_lines': "Bounce Lines"
        }
        for key, title in groups.items():
            content_layout.addWidget(self.create_setting_group(key, title))
        
        content_layout.addWidget(self.create_gui_theme_group())
        content_layout.addWidget(self.create_info_group())
        content_layout.addWidget(self.create_app_controls_group())
        
        self.main_layout.addWidget(self.content_widget)

    def create_gui_theme_group(self):
        box = CollapsibleBox("GUI Theme", self)
        layout = QtWidgets.QGridLayout()
        
        bg_color_button = self.create_color_button('gui_theme')
        self.update_color_button(bg_color_button, self.overlay.settings['gui_theme']['color'])
        layout.addWidget(QtWidgets.QLabel("BG Color:"), 0, 0)
        layout.addWidget(bg_color_button, 0, 1)
        
        font_color_button = self.create_color_button('font_color')
        self.update_color_button(font_color_button, self.overlay.settings['font_color']['color'])
        layout.addWidget(QtWidgets.QLabel("Font Color:"), 1, 0)
        layout.addWidget(font_color_button, 1, 1)

        alpha_slider = QtWidgets.QSlider(Qt.Horizontal)
        alpha_slider.setRange(0, 255)
        alpha_slider.setValue(self.overlay.settings['gui_theme']['color'][3])
        alpha_slider.valueChanged.connect(lambda val, k='gui_theme', b=bg_color_button: self.change_alpha(k, val, b))
        layout.addWidget(QtWidgets.QLabel("Alpha:"), 2, 0)
        layout.addWidget(alpha_slider, 2, 1, 1, 2)
        
        box.setContentLayout(layout)
        self.boxes.append(box)
        return box

    def create_info_group(self):
        info_group = QtWidgets.QGroupBox("Info & Manual Position")
        info_layout = QtWidgets.QGridLayout()
        self.rect_x_spin = QtWidgets.QSpinBox(); self.rect_x_spin.setRange(-5000, 5000)
        self.rect_y_spin = QtWidgets.QSpinBox(); self.rect_y_spin.setRange(-5000, 5000)
        self.rect_w_spin = QtWidgets.QSpinBox(); self.rect_w_spin.setRange(0, 5000)
        self.rect_h_spin = QtWidgets.QSpinBox(); self.rect_h_spin.setRange(0, 5000)
        info_layout.addWidget(QtWidgets.QLabel("X:"), 0, 0); info_layout.addWidget(self.rect_x_spin, 0, 1)
        info_layout.addWidget(QtWidgets.QLabel("Y:"), 0, 2); info_layout.addWidget(self.rect_y_spin, 0, 3)
        info_layout.addWidget(QtWidgets.QLabel("W:"), 1, 0); info_layout.addWidget(self.rect_w_spin, 1, 1)
        info_layout.addWidget(QtWidgets.QLabel("H:"), 1, 2); info_layout.addWidget(self.rect_h_spin, 1, 3)
        self.obj_ball_label = QtWidgets.QLabel("Obj Ball: (0,0)")
        self.ghost_ball_label = QtWidgets.QLabel("Ghost Ball: (0,0)")
        info_layout.addWidget(self.obj_ball_label, 2, 0, 1, 2)
        info_layout.addWidget(self.ghost_ball_label, 2, 2, 1, 2)
        for spin in [self.rect_x_spin, self.rect_y_spin, self.rect_w_spin, self.rect_h_spin]:
            spin.valueChanged.connect(self.set_table_border_from_input)
        info_group.setLayout(info_layout)
        return info_group

    def create_app_controls_group(self):
        app_controls_group = QtWidgets.QGroupBox("App Controls")
        app_controls_layout = QtWidgets.QHBoxLayout()
        hide_button = QtWidgets.QPushButton("Hide/Show Overlay")
        hide_button.clicked.connect(self.overlay.toggle_visibility)
        reset_button = QtWidgets.QPushButton("Reset Settings")
        reset_button.clicked.connect(self.overlay.reset_settings_to_default)
        app_controls_layout.addWidget(hide_button)
        app_controls_layout.addWidget(reset_button)
        app_controls_group.setLayout(app_controls_layout)
        return app_controls_group

    def apply_theme(self):
        font_color = QtGui.QColor(*self.overlay.settings['font_color']['color']).name()
        self.setStyleSheet(f"""
            QWidget {{ color: {font_color}; }}
            QGroupBox {{ border: 1px solid {font_color}; margin-top: 10px; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }}
        """)

    def toggle_minimize(self):
        is_minimized = not self.content_widget.isVisible()
        self.content_widget.setVisible(is_minimized)
        self.minimize_button.setVisible(is_minimized)
        self.restore_button.setVisible(not is_minimized)
        if is_minimized:
            self.setFixedSize(self.sizeHint())
        else:
            self.setFixedSize(self.minimumSizeHint())

    def closeEvent(self, event):
        self.overlay.close()

# --- Main Overlay Window ---
class OverlayWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.settings = {}
        self.load_settings()

        self.interactive = True
        self.control_points = self.settings['control_points']
        self.dragging_idx = None
        self.keyboard_focus_idx = 0
        self.table_border = QtCore.QRect(*self.settings['table_rect'])
        self.border_dragging = False
        self.border_resize_corner = None
        self.keyboard_resize_mode = False
        self.keyboard_resize_corner = 'top_left'
        self.pockets = []
        self.update_pockets()

        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.showFullScreen()
        self.make_click_through(False)

        self.settings_window = SettingsWindow(self)
        self.settings_window.show()

    def get_default_settings(self):
        return {
            'table_rect': [384, 347, 1090, 545],
            'control_points': [[927, 620], [1456, 755]],
            'outer_rect': {'visible': True, 'size': 2, 'color': [255, 255, 255, 128]},
            'inner_rect': {'visible': True, 'size': 1, 'color': [255, 255, 255, 100]},
            'pocket_lines': {'visible': True, 'size': 2, 'color': [255, 0, 0, 255]},
            'center_ghost': {'visible': True, 'size': 17, 'color': [0, 255, 0, 128]},
            'connecting_line': {'visible': True, 'size': 3, 'color': [255, 0, 0, 255]},
            'bounce_ghost': {'visible': True, 'size': 17, 'color': [0, 255, 0, 100]},
            'bounce_visuals': {'visible': True, 'size': 17, 'color': [255, 255, 255, 60]},
            'bounce_lines': {'visible': True, 'size': 2, 'color': [255, 255, 0, 255]},
            'gui_theme': {'visible': True, 'size': 1, 'color': [0, 179, 255, 113]},
            'font_color': {'visible': True, 'size': 1, 'color': [0, 0, 0, 255]},
            'bounce_count': 2,
        }

    def load_settings(self):
        try:
            with open('settings.json', 'r') as f:
                loaded_settings = json.load(f)
                self.settings = self.get_default_settings()
                self.settings.update(loaded_settings)
        except (FileNotFoundError, json.JSONDecodeError):
            self.settings = self.get_default_settings()

    def save_settings(self):
        self.settings['table_rect'] = [self.table_border.x(), self.table_border.y(), self.table_border.width(), self.table_border.height()]
        self.settings['control_points'] = self.control_points
        with open('settings.json', 'w') as f:
            json.dump(self.settings, f, indent=4)

    def reset_settings_to_default(self):
        print("Resetting settings to default...")
        self.settings = self.get_default_settings()
        self.control_points = self.settings['control_points']
        self.table_border = QtCore.QRect(*self.settings['table_rect'])
        self.save_settings()
        
        self.settings_window.close()
        self.settings_window = SettingsWindow(self)
        self.settings_window.show()
        
        self.update_pockets_and_info()

    def make_click_through(self, enable):
        hwnd = int(self.winId())
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        if enable:
            ex_style |= win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
        else:
            ex_style &= ~win32con.WS_EX_TRANSPARENT
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F8: self.toggle_interactive()
        elif event.key() == Qt.Key_Escape: self.close()
        elif event.key() == Qt.Key_F7:
            self.keyboard_resize_mode = not self.keyboard_resize_mode
            self.update()
        elif event.key() == Qt.Key_Tab:
            if self.keyboard_resize_mode:
                self.keyboard_resize_corner = 'bottom_right' if self.keyboard_resize_corner == 'top_left' else 'top_left'
            else:
                self.keyboard_focus_idx = 1 - self.keyboard_focus_idx
            self.update()
        elif event.key() in [Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right]:
            self.handle_arrow_keys(event)

    def handle_arrow_keys(self, event):
        if not self.interactive: return
        distance = 5 if event.modifiers() == Qt.ShiftModifier else 1
        if self.keyboard_resize_mode:
            self.move_border_with_keys(event.key(), distance)
        elif self.keyboard_focus_idx is not None:
            self.move_ball_with_keys(event.key(), distance)

    def move_border_with_keys(self, key, distance):
        if self.keyboard_resize_corner == 'top_left':
            old_bottom_right = self.table_border.bottomRight()
            new_top_left = self.table_border.topLeft()
            if key == Qt.Key_Up: new_top_left.setY(new_top_left.y() - distance)
            elif key == Qt.Key_Down: new_top_left.setY(new_top_left.y() + distance)
            elif key == Qt.Key_Left: new_top_left.setX(new_top_left.x() - distance)
            elif key == Qt.Key_Right: new_top_left.setX(new_top_left.x() + distance)
            self.table_border = QtCore.QRect(new_top_left, old_bottom_right)
        else:
            new_bottom_right = self.table_border.bottomRight()
            if key == Qt.Key_Up: new_bottom_right.setY(new_bottom_right.y() - distance)
            elif key == Qt.Key_Down: new_bottom_right.setY(new_bottom_right.y() + distance)
            elif key == Qt.Key_Left: new_bottom_right.setX(new_bottom_right.x() - distance)
            elif key == Qt.Key_Right: new_bottom_right.setX(new_bottom_right.x() + distance)
            self.table_border.setBottomRight(new_bottom_right)
        self.update_pockets_and_info()

    def move_ball_with_keys(self, key, distance):
        x, y = self.control_points[self.keyboard_focus_idx]
        if key == Qt.Key_Up: y -= distance
        elif key == Qt.Key_Down: y += distance
        elif key == Qt.Key_Left: x -= distance
        elif key == Qt.Key_Right: x += distance
        radius = self.settings['center_ghost']['size']
        physics_border = self.table_border.adjusted(radius, radius, -radius, -radius)
        x = max(physics_border.left(), min(physics_border.right(), x))
        y = max(physics_border.top(), min(physics_border.bottom(), y))
        self.control_points[self.keyboard_focus_idx] = (x, y)
        self.update_pockets_and_info()

    def toggle_interactive(self):
        self.interactive = not self.interactive
        self.make_click_through(not self.interactive)

    def toggle_visibility(self):
        if self.isVisible(): self.hide()
        else: self.show()

    def mousePressEvent(self, event):
        if not self.interactive: return
        pos = event.pos()
        if self.is_near_corner(pos):
            self.border_dragging = True
            self.border_resize_corner = self.get_corner(pos)
            self.keyboard_resize_corner = self.border_resize_corner
            self.update()
            return
        for idx, (x, y) in enumerate(self.control_points):
            radius = self.settings['center_ghost']['size']
            if (pos.x() - x) ** 2 + (pos.y() - y) ** 2 < radius ** 2:
                self.dragging_idx = idx
                self.keyboard_focus_idx = idx
                self.update()
                break

    def mouseMoveEvent(self, event):
        if not self.interactive: return
        pos = event.pos()
        if self.border_dragging and self.border_resize_corner:
            self.resize_border(pos)
            self.update_pockets_and_info()
        elif self.dragging_idx is not None:
            radius = self.settings['center_ghost']['size']
            physics_border = self.table_border.adjusted(radius, radius, -radius, -radius)
            x = max(physics_border.left(), min(physics_border.right(), pos.x()))
            y = max(physics_border.top(), min(physics_border.bottom(), pos.y()))
            self.control_points[self.dragging_idx] = (x, y)
            self.update_pockets_and_info()

    def mouseReleaseEvent(self, event):
        self.dragging_idx = None
        self.border_dragging = False
        self.border_resize_corner = None
        self.save_settings()

    def is_near_corner(self, pos):
        margin = 15
        return (self.table_border.topLeft() - pos).manhattanLength() < margin or \
               (self.table_border.bottomRight() - pos).manhattanLength() < margin

    def get_corner(self, pos):
        margin = 15
        if (self.table_border.topLeft() - pos).manhattanLength() < margin: return 'top_left'
        if (self.table_border.bottomRight() - pos).manhattanLength() < margin: return 'bottom_right'
        return None

    def resize_border(self, pos):
        if self.border_resize_corner == 'top_left':
            old_bottom_right = self.table_border.bottomRight()
            self.table_border = QtCore.QRect(pos, old_bottom_right)
        else:
            self.table_border.setBottomRight(pos)

    def update_pockets_and_info(self):
        self.update_pockets()
        self.settings_window.update_info_panel()
        self.update()

    def update_pockets(self):
        self.pockets = [
            self.table_border.topLeft(), self.table_border.topRight(),
            self.table_border.bottomLeft(), self.table_border.bottomRight(),
            QtCore.QPointF(self.table_border.center().x(), self.table_border.top()),
            QtCore.QPointF(self.table_border.center().x(), self.table_border.bottom())
        ]

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        s = self.settings

        if s['outer_rect']['visible']:
            painter.setPen(QtGui.QPen(QtGui.QColor(*s['outer_rect']['color']), s['outer_rect']['size']))
            painter.drawRect(self.table_border)

        if s['inner_rect']['visible']:
            inner_border = self.table_border.adjusted(17, 17, -17, -17)
            pen = QtGui.QPen(QtGui.QColor(*s['inner_rect']['color']), s['inner_rect']['size'], Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(inner_border)

        handle_size = 16
        painter.setBrush(QtGui.QBrush(Qt.yellow))
        painter.setPen(QtGui.QPen(Qt.black, 1))
        painter.drawRect(QtCore.QRect(self.table_border.left() - handle_size // 2, self.table_border.top() - handle_size // 2, handle_size, handle_size))
        painter.drawRect(QtCore.QRect(self.table_border.right() - handle_size // 2, self.table_border.bottom() - handle_size // 2, handle_size, handle_size))

        object_ball, ghost_ball = self.control_points
        if s['pocket_lines']['visible']:
            painter.setPen(QtGui.QPen(QtGui.QColor(*s['pocket_lines']['color']), s['pocket_lines']['size']))
            for pocket in self.pockets:
                painter.drawLine(int(object_ball[0]), int(object_ball[1]), int(pocket.x()), int(pocket.y()))
        
        if s['connecting_line']['visible']:
            painter.setPen(QtGui.QPen(QtGui.QColor(*s['connecting_line']['color']), s['connecting_line']['size']))
            painter.drawLine(int(object_ball[0]), int(object_ball[1]), int(ghost_ball[0]), int(ghost_ball[1]))

        if s['center_ghost']['visible']:
            painter.setBrush(QtGui.QBrush(QtGui.QColor(*s['center_ghost']['color'])))
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(QtCore.QPointF(*object_ball), s['center_ghost']['size'], s['center_ghost']['size'])

        if s['bounce_ghost']['visible']:
            painter.setBrush(QtGui.QBrush(QtGui.QColor(*s['bounce_ghost']['color'])))
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(QtCore.QPointF(*ghost_ball), s['bounce_ghost']['size'], s['bounce_ghost']['size'])

        if self.interactive and not self.keyboard_resize_mode:
            selected_ball = self.control_points[self.keyboard_focus_idx]
            painter.setPen(QtGui.QPen(Qt.white, 2, Qt.DotLine)); painter.setBrush(Qt.transparent)
            painter.drawEllipse(QtCore.QPointF(*selected_ball), s['center_ghost']['size'] + 3, s['center_ghost']['size'] + 3)
        
        if self.interactive and self.keyboard_resize_mode:
            pen = QtGui.QPen(Qt.cyan, 2, Qt.DashLine); painter.setPen(pen); painter.setBrush(Qt.transparent)
            corner_pos = self.table_border.topLeft() if self.keyboard_resize_corner == 'top_left' else self.table_border.bottomRight()
            painter.drawRect(QtCore.QRect(corner_pos.x() - handle_size, corner_pos.y() - handle_size, handle_size * 2, handle_size * 2))

        self.draw_bounce_prediction(painter, ghost_ball)
        painter.end()

    def draw_bounce_prediction(self, painter, ghost_ball):
        radius = self.settings['center_ghost']['size']
        physics_border = self.table_border.adjusted(radius, radius, -radius, -radius)
        tolerance = 1.0
        is_on_physics_border = (abs(ghost_ball[0] - physics_border.left()) <= tolerance or
                                abs(ghost_ball[0] - physics_border.right()) <= tolerance or
                                abs(ghost_ball[1] - physics_border.top()) <= tolerance or
                                abs(ghost_ball[1] - physics_border.bottom()) <= tolerance)
        if not is_on_physics_border: return
        object_ball = self.control_points[0]
        dx = ghost_ball[0] - object_ball[0]
        dy = ghost_ball[1] - object_ball[1]
        if dx == 0 and dy == 0: return
        length = math.hypot(dx, dy)
        dx /= length; dy /= length
        if abs(ghost_ball[0] - physics_border.left()) <= tolerance and dx < 0: dx = -dx
        if abs(ghost_ball[0] - physics_border.right()) <= tolerance and dx > 0: dx = -dx
        if abs(ghost_ball[1] - physics_border.top()) <= tolerance and dy < 0: dy = -dy
        if abs(ghost_ball[1] - physics_border.bottom()) <= tolerance and dy > 0: dy = -dy
        self.draw_physics_bounces(painter, ghost_ball, dx, dy)

    def draw_physics_bounces(self, painter, start_pos, dx, dy):
        s = self.settings
        max_bounces = s.get('bounce_count', 5)
        current_pos = start_pos
        current_dx, current_dy = dx, dy
        for bounce_num in range(max_bounces):
            intersection = self.find_table_intersection(current_pos[0], current_pos[1], current_dx, current_dy)
            if not intersection: break
            if s['bounce_visuals']['visible']:
                painter.setBrush(QtGui.QBrush(QtGui.QColor(*s['bounce_visuals']['color'])))
                painter.setPen(QtCore.Qt.NoPen)
                painter.drawEllipse(QtCore.QPointF(*intersection), s['bounce_visuals']['size'], s['bounce_visuals']['size'])
            if s['bounce_lines']['visible']:
                color = s['bounce_lines']['color']
                painter.setPen(QtGui.QPen(QtGui.QColor(*color), s['bounce_lines']['size'], Qt.DashLine))
                painter.drawLine(int(current_pos[0]), int(current_pos[1]), int(intersection[0]), int(intersection[1]))
            bounce_dx, bounce_dy = self.calculate_physics_reflection(current_dx, current_dy, intersection)
            current_pos = intersection
            current_dx, current_dy = bounce_dx, bounce_dy

    def calculate_physics_reflection(self, dx, dy, intersection):
        radius = self.settings['center_ghost']['size']
        physics_border = self.table_border.adjusted(radius, radius, -radius, -radius)
        tolerance = 1e-6
        if abs(intersection[0] - physics_border.left()) < tolerance or abs(intersection[0] - physics_border.right()) < tolerance:
            return -dx, dy
        elif abs(intersection[1] - physics_border.top()) < tolerance or abs(intersection[1] - physics_border.bottom()) < tolerance:
            return dx, -dy
        return dx, dy

    def find_table_intersection(self, x, y, dx, dy):
        radius = self.settings['center_ghost']['size']
        physics_border = self.table_border.adjusted(radius, radius, -radius, -radius)
        t_vals = []
        if dx != 0:
            t_vals.append((physics_border.left() - x) / dx)
            t_vals.append((physics_border.right() - x) / dx)
        if dy != 0:
            t_vals.append((physics_border.top() - y) / dy)
            t_vals.append((physics_border.bottom() - y) / dy)
        positive_t_vals = [t for t in t_vals if t > 1e-6]
        if not positive_t_vals: return None
        t_min = min(positive_t_vals)
        return (x + dx * t_min, y + dy * t_min)

    def closeEvent(self, event):
        self.save_settings()
        # --- FIX: Explicitly quit the application to terminate the process ---
        QtWidgets.QApplication.instance().quit()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    overlay = OverlayWindow()
    sys.exit(app.exec_())
