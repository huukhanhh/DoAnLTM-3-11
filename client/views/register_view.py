# client/views/register_view.py
from PyQt5 import QtWidgets, QtCore, QtGui
import socket
import json
import struct
import re
from config.config import SERVER_CONFIG


class RegisterView(QtWidgets.QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowTitle("Đăng ký - Chat App")
        self.setGeometry(100, 100, 450, 650)
        self.setup_ui()

    def setup_ui(self):
        # Main layout
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Background gradient
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f093fb, stop:0.5 #f5576c, stop:1 #ffd6a5);
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
        container_layout.setSpacing(15)

        # Logo/Icon
        icon_label = QtWidgets.QLabel("✨")
        icon_label.setStyleSheet("font-size: 50px; background: transparent;")
        icon_label.setAlignment(QtCore.Qt.AlignCenter)
        container_layout.addWidget(icon_label)

        # Title
        title = QtWidgets.QLabel("Tạo tài khoản")
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #2c3e50;
            background: transparent;
        """)
        title.setAlignment(QtCore.Qt.AlignCenter)
        container_layout.addWidget(title)

        subtitle = QtWidgets.QLabel("Tham gia cùng chúng tôi!")
        subtitle.setStyleSheet("""
            font-size: 14px;
            color: #7f8c8d;
            background: transparent;
        """)
        subtitle.setAlignment(QtCore.Qt.AlignCenter)
        container_layout.addWidget(subtitle)

        container_layout.addSpacing(15)

        # Display Name input
        name_label = QtWidgets.QLabel("👤 Tên hiển thị")
        name_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #2c3e50; background: transparent;")
        container_layout.addWidget(name_label)

        self.name_input = QtWidgets.QLineEdit()
        self.name_input.setPlaceholderText("Tên của bạn")
        self.name_input.setStyleSheet(self._get_input_style())
        container_layout.addWidget(self.name_input)

        # Email input
        email_label = QtWidgets.QLabel("📧 Email")
        email_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #2c3e50; background: transparent;")
        container_layout.addWidget(email_label)

        self.email_input = QtWidgets.QLineEdit()
        self.email_input.setPlaceholderText("example@email.com")
        self.email_input.setStyleSheet(self._get_input_style())
        container_layout.addWidget(self.email_input)

        # Password input
        password_label = QtWidgets.QLabel("🔒 Mật khẩu")
        password_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #2c3e50; background: transparent;")
        container_layout.addWidget(password_label)

        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password_input.setPlaceholderText("Tối thiểu 6 ký tự")
        self.password_input.setStyleSheet(self._get_input_style())
        container_layout.addWidget(self.password_input)

        # Confirm Password input
        confirm_label = QtWidgets.QLabel("🔐 Xác nhận mật khẩu")
        confirm_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #2c3e50; background: transparent;")
        container_layout.addWidget(confirm_label)

        self.confirm_password_input = QtWidgets.QLineEdit()
        self.confirm_password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.confirm_password_input.setPlaceholderText("Nhập lại mật khẩu")
        self.confirm_password_input.setStyleSheet(self._get_input_style())
        self.confirm_password_input.returnPressed.connect(self.register)
        container_layout.addWidget(self.confirm_password_input)

        # Status label
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px; background: transparent;")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        container_layout.addWidget(self.status_label)

        container_layout.addSpacing(5)

        # Register button
        self.register_button = QtWidgets.QPushButton("Đăng ký")
        self.register_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #f093fb, stop:1 #f5576c);
                color: white;
                border: none;
                border-radius: 15px;
                padding: 14px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #f5576c, stop:1 #f093fb);
            }
            QPushButton:pressed {
                padding: 15px 13px 13px 15px;
            }
        """)
        self.register_button.clicked.connect(self.register)
        self.register_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        container_layout.addWidget(self.register_button)

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

        # Back to log in button
        self.back_button = QtWidgets.QPushButton("Đã có tài khoản? Đăng nhập")
        self.back_button.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #f093fb;
                border: 2px solid #f093fb;
                border-radius: 15px;
                padding: 14px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f8f9fa;
                border-color: #f5576c;
                color: #f5576c;
            }
            QPushButton:pressed {
                background-color: #e9ecef;
            }
        """)
        self.back_button.clicked.connect(self.go_to_login)
        self.back_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        container_layout.addWidget(self.back_button)

        # Center container in main layout
        main_layout.addStretch()
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.addStretch()
        h_layout.addWidget(container)
        h_layout.addStretch()
        main_layout.addLayout(h_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

    def _get_input_style(self):
        return """
            QLineEdit {
                padding: 12px 15px;
                font-size: 14px;
                border: 2px solid #e0e0e0;
                border-radius: 15px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #f093fb;
            }
        """

    def register(self):
        display_name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()

        # Validation
        if not display_name or not email or not password:
            self.status_label.setText("Vui lòng nhập đầy đủ thông tin")
            return

        if len(password) < 6:
            self.status_label.setText("Mật khẩu phải có ít nhất 6 ký tự")
            return

        if password != confirm_password:
            self.status_label.setText("Mật khẩu xác nhận không khớp")
            return

        # Check email format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            self.status_label.setText("Email không hợp lệ")
            return

        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((SERVER_CONFIG["host"], SERVER_CONFIG["port"]))

            request = {
                "action": "register",
                "display_name": display_name,
                "email": email,
                "password": password
            }
            # Gửi với length prefix
            data = json.dumps(request).encode('utf-8')
            length = struct.pack('>I', len(data))
            client_socket.send(length + data)
            
            # Nhận với length prefix
            length_data = client_socket.recv(4)
            if len(length_data) < 4:
                raise socket.error("Không nhận đủ dữ liệu")
            resp_length = struct.unpack('>I', length_data)[0]
            resp_data = b''
            while len(resp_data) < resp_length:
                chunk = client_socket.recv(min(resp_length - len(resp_data), 4096))
                if not chunk:
                    raise socket.error("Kết nối bị đóng")
                resp_data += chunk
            response = json.loads(resp_data.decode('utf-8'))
            client_socket.close()

            if response.get("status") == "success":
                self.status_label.setStyleSheet("color: #27ae60; font-size: 12px; background: transparent;")
                self.status_label.setText("Đăng ký thành công!")

                # Show success message
                msg_box = QtWidgets.QMessageBox(self)
                msg_box.setWindowTitle("Thành công")
                msg_box.setText("Đăng ký thành công! Vui lòng đăng nhập.")
                msg_box.setIcon(QtWidgets.QMessageBox.Information)
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: white;
                    }
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #f093fb, stop:1 #f5576c);
                        color: white;
                        border: none;
                        border-radius: 8px;
                        padding: 8px 20px;
                        font-weight: bold;
                    }
                """)
                msg_box.exec_()

                self.app.show_login()
            else:
                self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px; background: transparent;")
                self.status_label.setText(f"{response.get('message')}")

        except socket.error as e:
            self.status_label.setText(f"Lỗi kết nối: {str(e)}")
        except json.JSONDecodeError:
            self.status_label.setText("Lỗi phản hồi từ server")
        except Exception as e:
            self.status_label.setText(f"Lỗi: {str(e)}")

    def go_to_login(self):
        self.app.show_login()