# client/views/login_view.py
from PyQt5 import QtWidgets, QtCore, QtGui
import socket
import json
from config.config import SERVER_CONFIG


class LoginView(QtWidgets.QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowTitle("Đăng nhập - Chat App")
        self.setGeometry(100, 100, 450, 550)
        self.setup_ui()

    def setup_ui(self):
        # Main layout
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Background gradient
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:0.5 #764ba2, stop:1 #f093fb);
            }
        """)

        # Container với bo góc
        container = QtWidgets.QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 0.95);
                border-radius: 25px;
            }
        """)
        container.setMaximumWidth(400)

        container_layout = QtWidgets.QVBoxLayout(container)
        container_layout.setContentsMargins(40, 40, 40, 40)
        container_layout.setSpacing(20)

        # Logo/Icon
        icon_label = QtWidgets.QLabel("💬")
        icon_label.setStyleSheet("font-size: 60px; background: transparent;")
        icon_label.setAlignment(QtCore.Qt.AlignCenter)
        container_layout.addWidget(icon_label)

        # Title
        title = QtWidgets.QLabel("Đăng nhập")
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #2c3e50;
            background: transparent;
        """)
        title.setAlignment(QtCore.Qt.AlignCenter)
        container_layout.addWidget(title)

        subtitle = QtWidgets.QLabel("Chào mừng bạn trở lại!")
        subtitle.setStyleSheet("""
            font-size: 14px;
            color: #7f8c8d;
            background: transparent;
        """)
        subtitle.setAlignment(QtCore.Qt.AlignCenter)
        container_layout.addWidget(subtitle)

        container_layout.addSpacing(20)

        # Email input
        email_label = QtWidgets.QLabel("📧 Email")
        email_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #2c3e50; background: transparent;")
        container_layout.addWidget(email_label)

        self.email_input = QtWidgets.QLineEdit()
        self.email_input.setPlaceholderText("example@email.com")
        self.email_input.setStyleSheet("""
            QLineEdit {
                padding: 12px 15px;
                font-size: 14px;
                border: 2px solid #e0e0e0;
                border-radius: 15px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #667eea;
            }
        """)
        container_layout.addWidget(self.email_input)

        # Password input
        password_label = QtWidgets.QLabel("🔒 Mật khẩu")
        password_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #2c3e50; background: transparent;")
        container_layout.addWidget(password_label)

        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password_input.setPlaceholderText("Nhập mật khẩu")
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 12px 15px;
                font-size: 14px;
                border: 2px solid #e0e0e0;
                border-radius: 15px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #667eea;
            }
        """)
        self.password_input.returnPressed.connect(self.login)
        container_layout.addWidget(self.password_input)

        # Status label
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px; background: transparent;")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        container_layout.addWidget(self.status_label)

        container_layout.addSpacing(10)

        # Login button
        self.login_button = QtWidgets.QPushButton("Đăng nhập")
        self.login_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border: none;
                border-radius: 15px;
                padding: 14px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #764ba2, stop:1 #667eea);
            }
            QPushButton:pressed {
                padding: 15px 13px 13px 15px;
            }
        """)
        self.login_button.clicked.connect(self.login)
        self.login_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        container_layout.addWidget(self.login_button)

        # Divider
        divider_layout = QtWidgets.QHBoxLayout()
        line1 = QtWidgets.QFrame()
        line1.setFrameShape(QtWidgets.QFrame.HLine)
        line1.setStyleSheet("background-color: #e0e0e0;")
        divider_layout.addWidget(line1)

        or_label = QtWidgets.QLabel("hoặc")
        or_label.setStyleSheet("color: #7f8c8d; font-size: 12px; background: transparent; padding: 0 10px;")
        divider_layout.addWidget(or_label)

        line2 = QtWidgets.QFrame()
        line2.setFrameShape(QtWidgets.QFrame.HLine)
        line2.setStyleSheet("background-color: #e0e0e0;")
        divider_layout.addWidget(line2)

        container_layout.addLayout(divider_layout)

        # Register button
        self.register_button = QtWidgets.QPushButton("Tạo tài khoản mới")
        self.register_button.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #667eea;
                border: 2px solid #667eea;
                border-radius: 15px;
                padding: 14px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f8f9fa;
                border-color: #764ba2;
                color: #764ba2;
            }
            QPushButton:pressed {
                background-color: #e9ecef;
            }
        """)
        self.register_button.clicked.connect(self.go_to_register)
        self.register_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        container_layout.addWidget(self.register_button)

        # Center container in main layout
        main_layout.addStretch()
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.addStretch()
        h_layout.addWidget(container)
        h_layout.addStretch()
        main_layout.addLayout(h_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

    def login(self):
        email = self.email_input.text().strip()
        password = self.password_input.text()

        if not email or not password:
            self.status_label.setText("⚠️ Vui lòng nhập đầy đủ thông tin")
            return

        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((SERVER_CONFIG["host"], SERVER_CONFIG["port"]))
            client_socket.settimeout(10)

            request = {
                "action": "login",
                "email": email,
                "password": password
            }
            client_socket.send(json.dumps(request).encode('utf-8'))
            # Tăng buffer để nhận avatar (base64) từ server
            response = json.loads(client_socket.recv(10485760).decode('utf-8'))

            if response.get("status") == "success":
                user_id = response.get("user_id")
                display_name = response.get("display_name")
                self.app.show_main(client_socket, user_id, display_name)
            else:
                self.status_label.setText(f"❌ {response.get('message')}")
                client_socket.close()

        except socket.error as e:
            self.status_label.setText(f"🔌 Lỗi kết nối: {str(e)}")
        except json.JSONDecodeError:
            self.status_label.setText("⚠️ Lỗi phản hồi từ server")
        except Exception as e:
            self.status_label.setText(f"❌ Lỗi: {str(e)}")

    def go_to_register(self):
        self.app.show_register()