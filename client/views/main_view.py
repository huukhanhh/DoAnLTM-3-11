# client/views/main_view.py
from PyQt5 import QtWidgets, QtCore, QtGui, QtMultimedia
try:
    from PyQt5 import QtMultimediaWidgets
    HAS_VIDEO_WIDGET = True
except ImportError:
    HAS_VIDEO_WIDGET = False
import sys
import json
import socket
import threading
import base64
import os
import io
import wave
import pyaudio
import tempfile
import subprocess
import platform
from config.config import SERVER_CONFIG
from client.controllers.auth_controller_client import AuthController
from client.views.profile_view import ProfileDialog


class ChatListItem(QtWidgets.QWidget):
    """Widget cho mỗi item trong danh sách chat"""

    def __init__(self, user_id, display_name, last_message="", avatar_base64=None, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.display_name = display_name
        self.avatar_base64 = avatar_base64

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)

        # Avatar
        avatar_label = QtWidgets.QLabel()
        avatar_label.setStyleSheet("""
            font-size: 32px;
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #667eea, stop:1 #764ba2);
            border-radius: 25px;
            padding: 5px;
            min-width: 50px;
            max-width: 50px;
            min-height: 50px;
            max-height: 50px;
        """)
        avatar_label.setAlignment(QtCore.Qt.AlignCenter)
        if self.avatar_base64:
            try:
                pix = QtGui.QPixmap()
                pix.loadFromData(base64.b64decode(self.avatar_base64))
                avatar_label.setPixmap(pix.scaled(50, 50, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
                avatar_label.setStyleSheet("border-radius:25px;")
            except Exception:
                avatar_label.setText("👤")
        else:
            avatar_label.setText("👤")
        layout.addWidget(avatar_label)

        # Info
        info_layout = QtWidgets.QVBoxLayout()
        info_layout.setSpacing(3)

        name_label = QtWidgets.QLabel(display_name)
        name_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #2c3e50;")
        info_layout.addWidget(name_label)

        last_msg_label = QtWidgets.QLabel(last_message if last_message else "Bắt đầu trò chuyện...")
        last_msg_label.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        last_msg_label.setWordWrap(True)
        info_layout.addWidget(last_msg_label)

        layout.addLayout(info_layout, 1)

        self.setLayout(layout)
        self.setStyleSheet("""
            ChatListItem {
                background-color: white;
                border-bottom: 1px solid #ecf0f1;
            }
            ChatListItem:hover {
                background-color: #f8f9fa;
            }
        """)


class VoiceMessageWidget(QtWidgets.QWidget):
    """Widget cho tin nhắn voice"""

    def __init__(self, voice_data, is_self=False, parent=None):
        super().__init__(parent)
        self.voice_data = voice_data
        self.is_playing = False
        self.audio_player = QtMultimedia.QMediaPlayer()
        self.temp_file = None  # Thêm biến lưu đường dẫn file tạm

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)

        # Nút play/pause
        self.play_button = QtWidgets.QPushButton("▶")
        self.play_button.setFixedSize(30, 30)
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                border: none;
                border-radius: 15px;
                color: white;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.play_button.clicked.connect(self.toggle_play)
        layout.addWidget(self.play_button)

        # Thanh tiến trình
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #e0e0e0;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Thời gian
        self.time_label = QtWidgets.QLabel("0:00")
        self.time_label.setStyleSheet("color: #666; font-size: 12px;")
        self.time_label.setFixedWidth(35)
        layout.addWidget(self.time_label)

        # Timer để cập nhật tiến trình
        self.progress_timer = QtCore.QTimer()
        self.progress_timer.timeout.connect(self.update_progress)

        # Kết nối sự kiện media player
        self.audio_player.positionChanged.connect(self.on_position_changed)
        self.audio_player.durationChanged.connect(self.on_duration_changed)
        self.audio_player.stateChanged.connect(self.on_state_changed)

        self.setFixedHeight(50)
        self.setStyleSheet(f"""
            VoiceMessageWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {'#667eea' if is_self else '#ffffff'}, 
                    stop:1 {'#764ba2' if is_self else '#f0f0f0'});
                border-radius: 25px;
                border: 1px solid {'#667eea' if is_self else '#ddd'};
            }}
        """)

    def toggle_play(self):
        """Bật/tắt phát voice message"""
        if not self.is_playing:
            self.play_voice()
        else:
            self.stop_voice()

    def play_voice(self):
        """Phát tin nhắn voice"""
        try:
            # Nếu chưa có file tạm hoặc file đã bị xóa, tạo mới
            if self.temp_file is None or not os.path.exists(self.temp_file):
                # Decode base64 và lưu file tạm
                audio_bytes = base64.b64decode(self.voice_data)

                # Sử dụng thư mục tạm của hệ thống thay vì thư mục hiện tại
                import tempfile
                temp_dir = tempfile.gettempdir()
                self.temp_file = os.path.join(temp_dir, f"temp_voice_message_{id(self)}.wav")

                with open(self.temp_file, 'wb') as f:
                    f.write(audio_bytes)

            content = QtMultimedia.QMediaContent(QtCore.QUrl.fromLocalFile(self.temp_file))
            self.audio_player.setMedia(content)
            self.audio_player.play()

        except Exception as e:
            print(f"Lỗi phát voice: {e}")
            QtWidgets.QMessageBox.warning(self, "Lỗi", "Không thể phát tin nhắn thoại")

    def stop_voice(self):
        """Dừng phát voice"""
        self.audio_player.stop()

    def on_position_changed(self, position):
        """Cập nhật vị trí phát"""
        if self.audio_player.duration() > 0:
            progress = int((position / self.audio_player.duration()) * 100)
            self.progress_bar.setValue(progress)

            # Cập nhật thời gian
            seconds = position // 1000
            self.time_label.setText(f"{seconds // 60}:{seconds % 60:02d}")

    def on_duration_changed(self, duration):
        """Khi có thông tin về độ dài audio"""
        if duration > 0:
            total_seconds = duration // 1000
            self.progress_bar.setMaximum(100)

    def on_state_changed(self, state):
        """Khi trạng thái player thay đổi"""
        if state == QtMultimedia.QMediaPlayer.PlayingState:
            self.is_playing = True
            self.play_button.setText("❚❚")
            self.progress_timer.start(100)
        else:
            self.is_playing = False
            self.play_button.setText("▶")
            self.progress_timer.stop()

            if state == QtMultimedia.QMediaPlayer.StoppedState:
                self.progress_bar.setValue(0)
                self.time_label.setText("0:00")

    def update_progress(self):
        """Cập nhật tiến trình"""
        if self.audio_player.duration() > 0:
            position = self.audio_player.position()
            duration = self.audio_player.duration()
            progress = int((position / duration) * 100)
            self.progress_bar.setValue(progress)

    def cleanup(self):
        """Dọn dẹp file tạm"""
        if self.temp_file and os.path.exists(self.temp_file):
            try:
                # Dừng player trước khi xóa file
                if self.audio_player.state() == QtMultimedia.QMediaPlayer.PlayingState:
                    self.audio_player.stop()

                os.remove(self.temp_file)
                self.temp_file = None
            except Exception as e:
                print(f"Không thể xóa file tạm: {e}")


class MainView(QtWidgets.QMainWindow):
    message_received = QtCore.pyqtSignal(str, str, str, int)  # message, sender_name, message_type, sender_id

    def __init__(self, app, socket, user_id, display_name):
        super().__init__()
        self.app = app
        self.socket = socket
        self.user_id = user_id
        self.display_name = display_name
        self.setWindowTitle("Chat App")
        self.setGeometry(100, 100, 1000, 800)

        # Main widget
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QtWidgets.QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top bar
        top_bar = QtWidgets.QWidget()
        top_bar.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #667eea, stop:0.5 #764ba2, stop:1 #f093fb);
            padding: 8px 15px;
        """)
        top_bar.setMaximumHeight(50)
        top_bar_layout = QtWidgets.QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(10, 5, 10, 5)

        self.user_label = QtWidgets.QLabel(f"👤 {self.display_name}")
        self.user_label.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
        self.user_label.mousePressEvent = self.open_profile_dialog
        top_bar_layout.addWidget(self.user_label)
        top_bar_layout.addStretch()

        self.logout_button = QtWidgets.QPushButton("⬅")
        self.logout_button.setToolTip("Đăng xuất")
        self.logout_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                border: 1px solid white;
                border-radius: 15px;
                padding: 5px;
                font-size: 16px;
                min-width: 30px;
                max-width: 30px;
                min-height: 30px;
                max-height: 30px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.3);
            }
        """)
        self.logout_button.clicked.connect(self.logout)
        top_bar_layout.addWidget(self.logout_button)

        main_layout.addWidget(top_bar)

        # Splitter
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        main_layout.addWidget(self.splitter)

        # Left panel
        self.chat_list_widget = QtWidgets.QWidget()
        self.chat_list_widget.setStyleSheet("background-color: #f5f6fa;")
        self.chat_list_main_layout = QtWidgets.QVBoxLayout(self.chat_list_widget)
        self.chat_list_main_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_list_main_layout.setSpacing(0)

        list_header = QtWidgets.QLabel("💬 Tin nhắn")
        list_header.setStyleSheet("""
            font-size: 18px; 
            font-weight: bold; 
            padding: 15px; 
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #a8edea, stop:1 #fed6e3);
            color: #2c3e50;
        """)
        self.chat_list_main_layout.addWidget(list_header)

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: white;
            }
            QScrollBar:vertical {
                width: 8px;
                background: #f5f6fa;
            }
            QScrollBar::handle:vertical {
                background: #bdc3c7;
                border-radius: 4px;
            }
        """)

        scroll_content = QtWidgets.QWidget()
        self.chat_list_layout = QtWidgets.QVBoxLayout(scroll_content)
        self.chat_list_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_list_layout.setSpacing(0)
        self.chat_list_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        self.chat_list_main_layout.addWidget(scroll_area)
        self.splitter.addWidget(self.chat_list_widget)

        # Right panel - Chat area
        self.chat_widget = QtWidgets.QWidget()
        self.chat_widget.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #e8f5e9, stop:1 #f3e5f5);
        """)
        self.chat_layout = QtWidgets.QVBoxLayout(self.chat_widget)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_layout.setSpacing(0)

        # Chat header
        chat_header = QtWidgets.QWidget()
        chat_header.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #667eea, stop:1 #764ba2);
            padding: 12px;
        """)
        chat_header_layout = QtWidgets.QHBoxLayout(chat_header)
        self.chat_label = QtWidgets.QLabel("Chọn người để bắt đầu trò chuyện")
        self.chat_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        chat_header_layout.addWidget(self.chat_label)
        self.chat_layout.addWidget(chat_header)

        # Chat scroll area
        chat_scroll = QtWidgets.QScrollArea()
        chat_scroll.setWidgetResizable(True)
        chat_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        self.chat_content = QtWidgets.QWidget()
        self.chat_messages_layout = QtWidgets.QVBoxLayout(self.chat_content)
        self.chat_messages_layout.setContentsMargins(15, 15, 15, 15)
        self.chat_messages_layout.setSpacing(10)
        self.chat_messages_layout.addStretch()

        chat_scroll.setWidget(self.chat_content)
        self.chat_layout.addWidget(chat_scroll)

        # Input area
        input_widget = QtWidgets.QWidget()
        input_widget.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #f093fb, stop:0.5 #f5576c, stop:1 #ffd6a5);
            padding: 10px;
        """)
        input_layout = QtWidgets.QHBoxLayout(input_widget)
        input_layout.setSpacing(10)

        self.image_button = QtWidgets.QPushButton("🖼")
        self.image_button.setToolTip("Gửi hình ảnh")
        self.image_button.setStyleSheet(self._get_button_style("#667eea", "#764ba2"))
        self.image_button.clicked.connect(self.send_image)
        input_layout.addWidget(self.image_button)

        self.video_button = QtWidgets.QPushButton("🎬")
        self.video_button.setToolTip("Gửi video")
        self.video_button.setStyleSheet(self._get_button_style("#8e44ad", "#9b59b6"))
        self.video_button.clicked.connect(self.send_video)
        input_layout.addWidget(self.video_button)

        self.emoji_button = QtWidgets.QPushButton("😊")
        self.emoji_button.setToolTip("Chọn emoji")
        self.emoji_button.setStyleSheet(self._get_button_style("#f093fb", "#f5576c"))
        self.emoji_button.clicked.connect(self.show_emoji_picker)
        input_layout.addWidget(self.emoji_button)

        self.message_input = QtWidgets.QLineEdit()
        self.message_input.setPlaceholderText("Nhập tin nhắn...")
        self.message_input.setStyleSheet("""
            QLineEdit {
                padding: 12px 15px;
                font-size: 14px;
                border: 2px solid rgba(255, 255, 255, 0.5);
                border-radius: 25px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #667eea;
            }
        """)
        self.message_input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.message_input)

        # Nút micro
        self.voice_button = QtWidgets.QPushButton("🎤")
        self.voice_button.setToolTip("Giữ để ghi âm, thả để gửi")
        self.voice_button.setStyleSheet(self._get_button_style("#ff6b6b", "#ff8e8e"))
        self.voice_button.pressed.connect(self.start_recording)
        self.voice_button.released.connect(self.stop_recording)
        input_layout.addWidget(self.voice_button)

        self.send_button = QtWidgets.QPushButton("✈")
        self.send_button.setToolTip("Gửi")
        self.send_button.setStyleSheet(self._get_button_style("#4facfe", "#00f2fe"))
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button)

        self.chat_layout.addWidget(input_widget)
        self.splitter.addWidget(self.chat_widget)

        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)

        self.controller = AuthController(self.socket)
        self.controller.current_user_id = self.user_id
        self.message_received.connect(self.display_incoming_message)
        self.current_receiver_id = None
        self.current_receiver_name = None
        self.self_avatar = None
        self.user_avatars = {}  # user_id -> base64

        # Biến cho ghi âm
        self.is_recording = False
        self.frames = []
        self.audio = None
        self.stream = None
        self.recording_thread = None

        # Load avatars and users
        self.refresh_self_profile()
        self.load_users()
        threading.Thread(target=self.check_incoming_messages, daemon=True).start()

    def _get_button_style(self, color1, color2):
        return f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {color1}, stop:1 {color2});
                color: white;
                border: none;
                border-radius: 22px;
                padding: 10px;
                font-size: 18px;
                min-width: 44px;
                max-width: 44px;
                min-height: 44px;
                max-height: 44px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {color2}, stop:1 {color1});
            }}
            QPushButton:pressed {{
                padding: 11px 9px 9px 11px;
            }}
        """

    def create_message_bubble(self, message, sender_name, is_self=False, is_image=False, is_voice=False, is_video=False, avatar_base64=None):
        """Tạo bubble tin nhắn giống Zalo - đã thêm hỗ trợ voice và video"""
        bubble_widget = QtWidgets.QWidget()
        bubble_layout = QtWidgets.QHBoxLayout(bubble_widget)
        bubble_layout.setContentsMargins(0, 0, 0, 0)
        bubble_layout.setSpacing(8)

        # Avatar
        avatar = QtWidgets.QLabel()
        avatar.setStyleSheet(f"""
            font-size: 28px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {'#667eea' if not is_self else '#4facfe'}, 
                stop:1 {'#764ba2' if not is_self else '#00f2fe'});
            border-radius: 20px;
            padding: 5px;
            min-width: 40px;
            max-width: 40px;
            min-height: 40px;
            max-height: 40px;
        """)
        avatar.setAlignment(QtCore.Qt.AlignCenter)
        if avatar_base64:
            try:
                pix = QtGui.QPixmap()
                pix.loadFromData(base64.b64decode(avatar_base64))
                avatar.setPixmap(pix.scaled(40, 40, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
                avatar.setStyleSheet("border-radius:20px;")
            except Exception:
                avatar.setText("👤" if not is_self else "😊")
        else:
            avatar.setText("👤" if not is_self else "😊")

        # Message content
        content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(3)

        if not is_self:
            name_label = QtWidgets.QLabel(sender_name)
            name_label.setStyleSheet("font-size: 11px; color: #7f8c8d; font-weight: bold;")
            content_layout.addWidget(name_label)

        if is_voice:
            # Voice message widget
            voice_widget = VoiceMessageWidget(message, is_self)
            content_layout.addWidget(voice_widget)
        elif is_video:
            # Hiển thị video với thumbnail và button để mở
            # Dùng VideoMessageWidget
            video_widget = self.VideoMessageWidget(message, is_self)
            content_layout.addWidget(video_widget)
            # Lưu để cleanup
            video_widget.temp_file = getattr(video_widget, 'temp_file', None)
            
            
        elif is_image:
            # Hiển thị ảnh
            image_label = QtWidgets.QLabel()
            try:
                pixmap = QtGui.QPixmap()
                image_bytes = base64.b64decode(message)
                if pixmap.loadFromData(image_bytes):
                    scaled_pixmap = pixmap.scaled(250, 250, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                    image_label.setPixmap(scaled_pixmap)
                else:
                    image_label.setText("📷 [Ảnh không thể hiển thị]")
            except Exception as e:
                print(f"Lỗi decode ảnh: {str(e)}")
                image_label.setText("📷 [Lỗi tải ảnh]")

            image_label.setStyleSheet("""
                background-color: white;
                border-radius: 10px;
                padding: 5px;
            """)
            content_layout.addWidget(image_label)
        else:
            # Tin nhắn text
            message_label = QtWidgets.QLabel(message)
            message_label.setWordWrap(True)
            message_label.setTextFormat(QtCore.Qt.RichText)
            message_label.setStyleSheet(f"""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {'#667eea' if is_self else '#ffffff'}, 
                    stop:1 {'#764ba2' if is_self else '#f0f0f0'});
                color: {'white' if is_self else '#2c3e50'};
                padding: 10px 15px;
                border-radius: 15px;
                font-size: 14px;
                max-width: 400px;
            """)
            content_layout.addWidget(message_label)

        # Layout theo vị trí
        if is_self:
            bubble_layout.addStretch()
            bubble_layout.addWidget(content_widget)
            bubble_layout.addWidget(avatar)
        else:
            bubble_layout.addWidget(avatar)
            bubble_layout.addWidget(content_widget)
            bubble_layout.addStretch()

        return bubble_widget

    def add_message_to_chat(self, message, sender_name, is_self=False, is_image=False, is_voice=False, is_video=False, avatar_base64=None):
        """Thêm tin nhắn vào chat - đã thêm hỗ trợ voice và video"""
        try:
            bubble = self.create_message_bubble(message, sender_name, is_self, is_image, is_voice, is_video, avatar_base64)
            self.chat_messages_layout.insertWidget(self.chat_messages_layout.count() - 1, bubble)

            # Auto scroll
            parent = self.chat_content.parentWidget()
            if parent and isinstance(parent, QtWidgets.QScrollArea):
                def scroll_to_bottom():
                    scrollbar = parent.verticalScrollBar()
                    scrollbar.setValue(scrollbar.maximum())

                QtCore.QTimer.singleShot(100, scroll_to_bottom)
        except Exception as e:
            print(f"Lỗi add message: {str(e)}")
            import traceback
            traceback.print_exc()

    def load_users(self):
        try:
            self.users = self.controller.get_users()

            for i in reversed(range(self.chat_list_layout.count())):
                item = self.chat_list_layout.itemAt(i)
                if item.widget() and not isinstance(item, QtWidgets.QSpacerItem):
                    item.widget().deleteLater()

            self.user_avatars = {}
            for user in self.users:
                if user["user_id"] != self.user_id:
                    chat_item = ChatListItem(
                        user["user_id"],
                        user["display_name"],
                        "Nhấn để bắt đầu chat",
                        user.get("avatar")
                    )
                    chat_item.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
                    chat_item.mousePressEvent = lambda e, uid=user["user_id"], name=user["display_name"]: self.select_chat_by_id(uid, name)
                    self.chat_list_layout.insertWidget(self.chat_list_layout.count() - 1, chat_item)
                self.user_avatars[user["user_id"]] = user.get("avatar")

            if len(self.users) > 1:
                first_user = next((u for u in self.users if u["user_id"] != self.user_id), None)
                if first_user:
                    self.select_chat_by_id(first_user["user_id"], first_user["display_name"])

        except Exception as e:
            print(f"Lỗi khi tải danh sách: {str(e)}")
            QtWidgets.QMessageBox.warning(self, "Lỗi", f"Không thể tải danh sách: {str(e)}")

    def select_chat_by_id(self, user_id, display_name):
        self.current_receiver_id = user_id
        self.current_receiver_name = display_name
        self.chat_label.setText(f"💬 {display_name}")

        # Clear messages
        for i in reversed(range(self.chat_messages_layout.count())):
            item = self.chat_messages_layout.itemAt(i)
            if item.widget() and not isinstance(item, QtWidgets.QSpacerItem):
                # Dọn dẹp voice và video widgets trước khi xóa
                widget = item.widget()
                if hasattr(widget, 'cleanup'):
                    widget.cleanup()
                # Cleanup video temp files
                if hasattr(widget, 'temp_file') and widget.temp_file and os.path.exists(widget.temp_file):
                    try:
                        if hasattr(widget, 'media_player'):
                            widget.media_player.stop()
                        os.remove(widget.temp_file)
                    except Exception as e:
                        print(f"Không thể xóa file video tạm: {e}")
                widget.deleteLater()

        try:
            if self.controller.client_socket and self.controller.client_socket.fileno() != -1:
                history = self.controller.get_chat_history(user_id)
                for msg in history:
                    sender_id = msg.get("sender_id")
                    sender_name = msg.get("sender_name", "Unknown")
                    sender_avatar = msg.get("sender_avatar")
                    is_image = bool(msg.get("is_image", False))
                    is_voice = bool(msg.get("is_voice", False))
                    is_video = bool(msg.get("is_video", False))
                    is_self = sender_id == self.user_id

                    if is_image:
                        image_data = msg.get("image_data")
                        if image_data:
                            self.add_message_to_chat(image_data, sender_name, is_self, True, False, False, self.self_avatar if is_self else sender_avatar)
                    elif is_voice:
                        voice_data = msg.get("voice_data")
                        if voice_data:
                            self.add_message_to_chat(voice_data, sender_name, is_self, False, True, False, self.self_avatar if is_self else sender_avatar)
                    elif is_video:
                        video_data = msg.get("video_data")
                        if video_data:
                            self.add_message_to_chat(video_data, sender_name, is_self, False, False, True, self.self_avatar if is_self else sender_avatar)
                    else:
                        message_text = msg.get("message", "")
                        if message_text:
                            self.add_message_to_chat(message_text, sender_name, is_self, False, False, False, self.self_avatar if is_self else sender_avatar)
        except Exception as e:
            print(f"Lỗi khi load chat: {str(e)}")
            import traceback
            traceback.print_exc()

    def send_message(self):
        message = self.message_input.text().strip()
        if not message:
            return

        if not self.current_receiver_id:
            QtWidgets.QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn người nhận!")
            return

        try:
            response = self.controller.send_message(self.current_receiver_id, message)
            if response and response.get("status") == "success":
                self.add_message_to_chat(message, "Bạn", is_self=True, is_image=False, is_voice=False, is_video=False)
                self.message_input.clear()
            else:
                error_msg = response.get('message', 'Không rõ lỗi') if response else 'Không nhận được phản hồi'
                QtWidgets.QMessageBox.warning(self, "Lỗi", f"Không thể gửi: {error_msg}")
        except Exception as e:
            print(f"Exception khi gửi tin nhắn: {str(e)}")
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.warning(self, "Lỗi", f"Lỗi gửi: {str(e)}")

    def send_image(self):
        """Gửi hình ảnh"""
        if not self.current_receiver_id:
            QtWidgets.QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn người nhận!")
            return

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Chọn hình ảnh",
            "",
            "Image Files (*.png *.jpg *.jpeg *.gif *.bmp)"
        )

        if file_path:
            try:
                # Đọc và encode ảnh
                with open(file_path, 'rb') as image_file:
                    image_data = image_file.read()
                    image_base64 = base64.b64encode(image_data).decode('utf-8')

                # Gửi qua controller
                request = {
                    "action": "send_image",
                    "receiver_id": self.current_receiver_id,
                    "image_data": image_base64,
                    "filename": os.path.basename(file_path)
                }
                response = self.controller.send_request(request)

                if response.get("status") == "success":
                    self.add_message_to_chat(image_base64, "Bạn", is_self=True, is_image=True, is_voice=False, is_video=False)
                else:
                    QtWidgets.QMessageBox.warning(self, "Lỗi", "Không thể gửi ảnh!")

            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Lỗi", f"Lỗi gửi ảnh: {str(e)}")

    def send_video(self):
        """Gửi video"""
        if not self.current_receiver_id:
            QtWidgets.QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn người nhận!")
            return

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Chọn video",
            "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm)"
        )

        if file_path:
            try:
                # Kiểm tra kích thước file (giới hạn 50MB để tối ưu)
                file_size = os.path.getsize(file_path)
                max_size = 50 * 1024 * 1024  # 50MB
                
                if file_size > max_size:
                    reply = QtWidgets.QMessageBox.question(
                        self, 
                        "Cảnh báo", 
                        f"Video có kích thước lớn ({file_size / (1024*1024):.1f}MB). "
                        "Gửi video lớn có thể mất nhiều thời gian. Bạn có muốn tiếp tục?",
                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                    )
                    if reply == QtWidgets.QMessageBox.No:
                        return

                # Hiển thị progress dialog
                progress = QtWidgets.QProgressDialog("Đang xử lý video...", "Hủy", 0, 100, self)
                progress.setWindowModality(QtCore.Qt.WindowModal)
                progress.setValue(0)
                progress.show()
                QtWidgets.QApplication.processEvents()

                # Đọc và encode video (tối ưu: đọc theo chunks để tránh memory overflow)
                progress.setValue(10)
                QtWidgets.QApplication.processEvents()
                
                chunk_size = 1024 * 1024  # 1MB chunks để tối ưu memory
                total_chunks = (file_size + chunk_size - 1) // chunk_size
                
                # Sử dụng list comprehension với generator để tối ưu memory
                chunks = []
                chunk_num = 0
                with open(file_path, 'rb') as video_file:
                    while True:
                        chunk = video_file.read(chunk_size)
                        if not chunk:
                            break
                        # Encode từng chunk để tránh load toàn bộ vào memory
                        chunks.append(base64.b64encode(chunk).decode('utf-8'))
                        chunk_num += 1
                        progress.setValue(10 + int((chunk_num / total_chunks) * 70))
                        QtWidgets.QApplication.processEvents()
                
                # Join tất cả chunks
                video_base64 = ''.join(chunks)
                # Giải phóng memory ngay sau khi join
                del chunks

                progress.setValue(90)
                QtWidgets.QApplication.processEvents()

                # Gửi qua controller
                request = {
                    "action": "send_video",
                    "receiver_id": self.current_receiver_id,
                    "video_data": video_base64,
                    "filename": os.path.basename(file_path)
                }
                response = self.controller.send_request(request, timeout=300)  # 5 phút cho video lớn

                progress.setValue(100)
                progress.close()

                if response.get("status") == "success":
                    self.add_message_to_chat(video_base64, "Bạn", is_self=True, is_image=False, is_voice=False, is_video=True)
                else:
                    QtWidgets.QMessageBox.warning(self, "Lỗi", "Không thể gửi video!")

            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Lỗi", f"Lỗi gửi video: {str(e)}")
                import traceback
                traceback.print_exc()

    def show_emoji_picker(self):
        emojis = ["😊", "😂", "❤️", "👍", "🎉", "😍", "😢", "😎", "🔥", "💯",
                  "✨", "🌟", "💪", "👏", "🙏", "😘", "😜", "🤔", "😱", "🥰"]

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Chọn emoji")
        dialog.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #a8edea, stop:1 #fed6e3);
            }
        """)

        layout = QtWidgets.QGridLayout()
        row = col = 0
        for emoji in emojis:
            btn = QtWidgets.QPushButton(emoji)
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 24px;
                    padding: 10px;
                    background-color: white;
                    border: 2px solid #ddd;
                    border-radius: 10px;
                    min-width: 50px;
                    min-height: 50px;
                }
                QPushButton:hover {
                    background-color: #f093fb;
                    border-color: #667eea;
                }
            """)
            btn.clicked.connect(lambda checked, e=emoji: self.insert_emoji(e, dialog))
            layout.addWidget(btn, row, col)
            col += 1
            if col > 4:
                col = 0
                row += 1

        dialog.setLayout(layout)
        dialog.exec_()

    def insert_emoji(self, emoji, dialog):
        self.message_input.setText(self.message_input.text() + emoji)
        self.message_input.setFocus()
        dialog.close()

    def check_incoming_messages(self):
        while True:
            try:
                message = self.controller.get_incoming_message(timeout=0.5)
                if message:
                    sender_name = message.get('sender_name', 'Unknown')
                    sender_id = message.get('sender_id')
                    is_image = message.get('is_image', False)
                    is_voice = message.get('is_voice', False)
                    is_video = message.get('is_video', False)

                    if is_voice:
                        msg_content = message.get('voice_data', '')
                        self.message_received.emit(msg_content, sender_name, 'voice', sender_id)
                    elif is_image:
                        msg_content = message.get('image_data', '')
                        self.message_received.emit(msg_content, sender_name, 'image', sender_id)
                    elif is_video:
                        msg_content = message.get('video_data', '')
                        self.message_received.emit(msg_content, sender_name, 'video', sender_id)
                    else:
                        msg_content = message.get('message', '')
                        self.message_received.emit(msg_content, sender_name, 'text', sender_id)
            except Exception as e:
                print(f"Lỗi check message: {str(e)}")
                break

    def display_incoming_message(self, message, sender_name, message_type, sender_id):
        is_image = (message_type == 'image')
        is_voice = (message_type == 'voice')
        is_video = (message_type == 'video')
        avatar = self.user_avatars.get(sender_id)
        self.add_message_to_chat(message, sender_name, is_self=False, is_image=is_image, is_voice=is_voice, is_video=is_video, avatar_base64=avatar)

    def logout(self):
        self.controller.stop()
        self.app.show_login()

    def closeEvent(self, event):
        # Dọn dẹp tất cả voice và video widgets trước khi đóng
        for i in reversed(range(self.chat_messages_layout.count())):
            item = self.chat_messages_layout.itemAt(i)
            if item.widget():
                widget = item.widget()
                if hasattr(widget, 'cleanup'):
                    widget.cleanup()
                # Cleanup video temp files
                if hasattr(widget, 'temp_file') and widget.temp_file and os.path.exists(widget.temp_file):
                    try:
                        if hasattr(widget, 'media_player'):
                            widget.media_player.stop()
                        os.remove(widget.temp_file)
                    except Exception as e:
                        print(f"Không thể xóa file video tạm: {e}")

        self.controller.stop()
        event.accept()

    # === CÁC PHƯƠNG THỨC XỬ LÝ VOICE MESSAGE ===

    def start_recording(self):
        """Bắt đầu ghi âm"""
        try:
            self.is_recording = True
            self.frames = []

            # Cấu hình audio
            self.audio = pyaudio.PyAudio()
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=44100,
                input=True,
                frames_per_buffer=1024
            )

            # Bắt đầu thread ghi âm
            self.recording_thread = threading.Thread(target=self.record_audio, daemon=True)
            self.recording_thread.start()

            # Hiển thị trạng thái
            self.message_input.setPlaceholderText("🎤 Đang ghi âm... Nhả nút để gửi")
            self.voice_button.setStyleSheet(self._get_button_style("#ff4757", "#ff3742"))

        except OSError as e:
            print(f"Lỗi microphone: {e}")
            QtWidgets.QMessageBox.warning(self, "Lỗi Microphone",
                                          "Không thể truy cập microphone. Hãy kiểm tra:\n"
                                          "1. Microphone đã được kết nối\n"
                                          "2. Ứng dụng có quyền sử dụng microphone\n"
                                          "3. Microphone không bị ứng dụng khác sử dụng")
        except Exception as e:
            print(f"Lỗi khi bắt đầu ghi âm: {e}")
            QtWidgets.QMessageBox.warning(self, "Lỗi",
                                          "Không thể bắt đầu ghi âm. Hãy chắc chắn rằng microphone đã được kết nối.")

    def record_audio(self):
        """Ghi âm trong thread riêng"""
        while self.is_recording:
            try:
                data = self.stream.read(1024, exception_on_overflow=False)
                self.frames.append(data)
            except Exception as e:
                print(f"Lỗi trong quá trình ghi âm: {e}")
                break

    def stop_recording(self):
        """Dừng ghi âm và gửi tin nhắn voice"""
        if not self.is_recording:
            return

        self.is_recording = False
        self.message_input.setPlaceholderText("Nhập tin nhắn...")
        self.voice_button.setStyleSheet(self._get_button_style("#ff6b6b", "#ff8e8e"))

        # Dừng stream
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()

        # Xử lý và gửi voice message nếu có dữ liệu
        if len(self.frames) > 0:
            self.process_and_send_voice()

    def process_and_send_voice(self):
        """Xử lý và gửi voice message"""
        try:
            # Kiểm tra xem có dữ liệu ghi âm không
            if len(self.frames) == 0:
                print("Không có dữ liệu ghi âm để gửi")
                return

            # Tạo file WAV trong memory
            buffer = io.BytesIO()
            wf = wave.open(buffer, 'wb')
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 2 bytes = 16 bit
            wf.setframerate(44100)
            wf.writeframes(b''.join(self.frames))
            wf.close()

            # Lấy dữ liệu và encode base64
            audio_data = buffer.getvalue()

            # Kiểm tra kích thước file
            if len(audio_data) == 0:
                print("Dữ liệu audio rỗng")
                return

            voice_base64 = base64.b64encode(audio_data).decode('utf-8')
            buffer.close()

            # Gửi đi
            if self.current_receiver_id:
                response = self.send_voice_message(self.current_receiver_id, voice_base64, "voice_message.wav")

                if response and response.get("status") == "success":
                    self.add_message_to_chat(voice_base64, "Bạn", is_self=True, is_image=False, is_voice=True, is_video=False)
                else:
                    error_msg = response.get('message', 'Không rõ lỗi') if response else 'Không nhận được phản hồi'
                    QtWidgets.QMessageBox.warning(self, "Lỗi", f"Không thể gửi tin nhắn thoại: {error_msg}")
            else:
                QtWidgets.QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn người nhận!")

        except Exception as e:
            print(f"Lỗi xử lý voice: {e}")
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.warning(self, "Lỗi", f"Lỗi xử lý tin nhắn thoại: {str(e)}")

    def send_voice_message(self, receiver_id, voice_data, filename):
        """Gửi tin nhắn voice qua controller"""
        request = {
            "action": "send_voice",
            "receiver_id": receiver_id,
            "voice_data": voice_data,
            "filename": filename
        }
        return self.controller.send_request(request, timeout=30)



    # === CÁC PHƯƠNG THỨC XỬ LÝ VIDEO MESSAGE ===
    class VideoMessageWidget(QtWidgets.QWidget):
        def __init__(self, video_data_base64, is_self=False, parent=None):
            global HAS_VIDEO_WIDGET
            super().__init__(parent)
            self.video_data = video_data_base64
            self.is_self = is_self
            
            self.temp_file = None
            self.media_player = QtMultimedia.QMediaPlayer()
            self.is_playing = False

            # Layout chính
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(5)

            # Container video
            self.video_container = QtWidgets.QWidget()
            self.video_container.setStyleSheet("""
                background-color: #000;
                border-radius: 12px;
                min-height: 200px;
                max-height: 300px;
            """)
            container_layout = QtWidgets.QVBoxLayout(self.video_container)
            container_layout.setContentsMargins(0, 0, 0, 0)

            # QVideoWidget (chỉ dùng nếu có)
            if HAS_VIDEO_WIDGET:
                try:
                    self.video_widget = QtMultimediaWidgets.QVideoWidget()
                    self.video_widget.setStyleSheet("background-color: #000;")
                    self.media_player.setVideoOutput(self.video_widget)
                    container_layout.addWidget(self.video_widget)
                except Exception as e:
                    print(f"QVideoWidget lỗi: {e}")
                    HAS_VIDEO_WIDGET = False

            # Nếu không có QVideoWidget → dùng placeholder
            if not HAS_VIDEO_WIDGET:
                placeholder = QtWidgets.QLabel("Video")
                placeholder.setAlignment(QtCore.Qt.AlignCenter)
                placeholder.setStyleSheet("""
                    color: white; font-size: 48px; background: #333;
                    min-height: 200px; border-radius: 12px;
                """)
                container_layout.addWidget(placeholder)

            layout.addWidget(self.video_container)

            # Controls
            controls = QtWidgets.QWidget()
            controls.setStyleSheet("background: rgba(0,0,0,0.6); border-radius: 8px;")
            controls_layout = QtWidgets.QHBoxLayout(controls)
            controls_layout.setContentsMargins(10, 5, 10, 5)
            controls_layout.setSpacing(10)

            # Play/Pause button
            self.play_button = QtWidgets.QPushButton("Play")
            self.play_button.setFixedSize(40, 40)
            self.play_button.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,0.3); color: white;
                    border-radius: 20px; font-size: 16px;
                }
                QPushButton:hover { background: rgba(255,255,255,0.5); }
            """)
            self.play_button.clicked.connect(self.toggle_play)
            controls_layout.addWidget(self.play_button)

            # Progress bar
            self.progress_bar = QtWidgets.QProgressBar()
            self.progress_bar.setFixedHeight(6)
            self.progress_bar.setTextVisible(False)
            self.progress_bar.setStyleSheet("""
                QProgressBar { background: #555; border-radius: 3px; }
                QProgressBar::chunk { background: #4CAF50; border-radius: 3px; }
            """)
            controls_layout.addWidget(self.progress_bar, 1)

            # Time label
            self.time_label = QtWidgets.QLabel("0:00 / 0:00")
            self.time_label.setStyleSheet("color: white; font-size: 12px;")
            self.time_label.setFixedWidth(80)
            controls_layout.addWidget(self.time_label)

            layout.addWidget(controls)

            # Timer cập nhật tiến trình
            self.timer = QtCore.QTimer()
            self.timer.timeout.connect(self.update_progress)

            # Kết nối signal
            self.media_player.positionChanged.connect(self.on_position_changed)
            self.media_player.durationChanged.connect(self.on_duration_changed)
            self.media_player.stateChanged.connect(self.on_state_changed)

            # Tạo file tạm ngay khi khởi tạo
            self.create_temp_file()

        def create_temp_file(self):
            """Tạo file tạm từ base64"""
            try:
                video_bytes = base64.b64decode(self.video_data)
                import tempfile, hashlib
                hash_name = hashlib.md5(self.video_data[:500].encode()).hexdigest()
                self.temp_file = os.path.join(tempfile.gettempdir(), f"chat_video_{hash_name}.mp4")
                
                if not os.path.exists(self.temp_file):
                    with open(self.temp_file, 'wb') as f:
                        f.write(video_bytes)

                # Set media
                if HAS_VIDEO_WIDGET:
                    content = QtMultimedia.QMediaContent(QtCore.QUrl.fromLocalFile(self.temp_file))
                    self.media_player.setMedia(content)

            except Exception as e:
                print(f"Lỗi tạo file video tạm: {e}")

        def toggle_play(self):
            if self.is_playing:
                self.media_player.pause()
            else:
                self.media_player.play()

        def on_position_changed(self, pos):
            if self.media_player.duration() > 0:
                progress = int((pos / self.media_player.duration()) * 100)
                self.progress_bar.setValue(progress)
                self.update_time_label(pos, self.media_player.duration())

        def on_duration_changed(self, duration):
            self.update_time_label(0, duration)
            self.progress_bar.setMaximum(100)

        def on_state_changed(self, state):
            if state == QtMultimedia.QMediaPlayer.PlayingState:
                self.is_playing = True
                self.play_button.setText("Pause")
                self.timer.start(100)
            elif state == QtMultimedia.QMediaPlayer.PausedState:
                self.is_playing = False
                self.play_button.setText("Play")
                self.timer.stop()
            elif state == QtMultimedia.QMediaPlayer.StoppedState:
                self.is_playing = False
                self.play_button.setText("Play")
                self.timer.stop()
                self.progress_bar.setValue(0)
                self.time_label.setText("0:00 / 0:00")

        def update_progress(self):
            self.on_position_changed(self.media_player.position())

        def update_time_label(self, pos_ms, dur_ms):
            pos_sec = pos_ms // 1000
            dur_sec = dur_ms // 1000
            self.time_label.setText(f"{pos_sec//60}:{pos_sec%60:02d} / {dur_sec//60}:{dur_sec%60:02d}")

        def cleanup(self):
            """Dọn dẹp khi widget bị xóa"""
            if self.media_player.state() == QtMultimedia.QMediaPlayer.PlayingState:
                self.media_player.stop()
            if self.temp_file and os.path.exists(self.temp_file):
                try:
                    os.remove(self.temp_file)
                except:
                    pass

    # === PROFILE ===
    def open_profile_dialog(self, event=None):
        try:
            dialog = ProfileDialog(self.controller, self.display_name, self.self_avatar, self)
            if dialog.exec_():
                # Refresh profile and users after successful update
                self.refresh_self_profile()
                self.user_label.setText(f"👤 {self.display_name}")
                self.load_users()
        except Exception as e:
            print(f"Lỗi mở hộp thoại hồ sơ: {e}")

    def refresh_self_profile(self):
        try:
            resp = self.controller.get_profile()
            if resp.get('status') == 'success':
                self.display_name = resp.get('display_name', self.display_name)
                self.self_avatar = resp.get('avatar')
        except Exception as e:
            print(f"Không thể tải hồ sơ: {e}")