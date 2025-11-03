# client/views/profile_view.py
from PyQt5 import QtWidgets, QtCore, QtGui
import base64


class ProfileDialog(QtWidgets.QDialog):
    def __init__(self, controller, current_display_name, current_avatar_base64=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Cập nhật thông tin cá nhân")
        self.setModal(False)
        self.resize(420, 520)

        self.avatar_base64 = current_avatar_base64

        layout = QtWidgets.QVBoxLayout(self)

        # Avatar preview
        self.avatar_label = QtWidgets.QLabel()
        self.avatar_label.setFixedSize(120, 120)
        self.avatar_label.setAlignment(QtCore.Qt.AlignCenter)
        self.avatar_label.setStyleSheet("border-radius: 60px; background: #eee;")
        layout.addWidget(self.avatar_label, 0, QtCore.Qt.AlignHCenter)
        self._refresh_avatar_preview()

        self.change_avatar_btn = QtWidgets.QPushButton("Chọn ảnh đại diện...")
        self.change_avatar_btn.clicked.connect(self.choose_avatar)
        layout.addWidget(self.change_avatar_btn, 0, QtCore.Qt.AlignHCenter)

        # Display name
        form = QtWidgets.QFormLayout()
        self.display_name_edit = QtWidgets.QLineEdit()
        self.display_name_edit.setText(current_display_name or "")
        form.addRow("Tên hiển thị", self.display_name_edit)

        # Password change (optional)
        self.old_password_edit = QtWidgets.QLineEdit(); self.old_password_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.new_password_edit = QtWidgets.QLineEdit(); self.new_password_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.new_password2_edit = QtWidgets.QLineEdit(); self.new_password2_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        form.addRow("Mật khẩu hiện tại", self.old_password_edit)
        form.addRow("Mật khẩu mới", self.new_password_edit)
        form.addRow("Nhập lại mật khẩu", self.new_password2_edit)
        layout.addLayout(form)

        # Status label
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setStyleSheet("color:#e74c3c")
        layout.addWidget(self.status_label)

        # Buttons
        btns = QtWidgets.QHBoxLayout()
        self.save_btn = QtWidgets.QPushButton("Lưu thay đổi")
        self.save_btn.clicked.connect(self.save_changes)
        btns.addStretch(); btns.addWidget(self.save_btn)
        layout.addLayout(btns)

    def _refresh_avatar_preview(self):
        if self.avatar_base64:
            try:
                pixmap = QtGui.QPixmap()
                pixmap.loadFromData(base64.b64decode(self.avatar_base64))
                self.avatar_label.setPixmap(pixmap.scaled(120, 120, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
            except Exception:
                self.avatar_label.setText("[Ảnh lỗi]")
        else:
            self.avatar_label.setText("👤")
            self.avatar_label.setStyleSheet("font-size:48px; border-radius:60px; background:#eee;")

    def choose_avatar(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Chọn ảnh đại diện", "", "Image Files (*.png *.jpg *.jpeg *.gif *.bmp)")
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    self.avatar_base64 = base64.b64encode(f.read()).decode('utf-8')
                self._refresh_avatar_preview()
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Lỗi", f"Không thể đọc ảnh: {e}")

    def save_changes(self):
        # Update profile
        name = self.display_name_edit.text().strip()
        if name == "":
            self.status_label.setText("Tên hiển thị không được để trống")
            return

        resp = self.controller.update_profile(display_name=name, avatar=self.avatar_base64)
        if resp.get("status") != "success":
            self.status_label.setText(resp.get("message", "Không thể cập nhật hồ sơ"))
            return

        # Change password if provided
        if self.old_password_edit.text() or self.new_password_edit.text() or self.new_password2_edit.text():
            if self.new_password_edit.text() != self.new_password2_edit.text():
                self.status_label.setText("Mật khẩu xác nhận không khớp")
                return
            if len(self.new_password_edit.text()) < 6:
                self.status_label.setText("Mật khẩu mới phải >= 6 ký tự")
                return
            resp2 = self.controller.change_password(self.old_password_edit.text(), self.new_password_edit.text())
            if resp2.get("status") != "success":
                self.status_label.setText(resp2.get("message", "Đổi mật khẩu thất bại"))
                return

        QtWidgets.QMessageBox.information(self, "Thành công", "Đã cập nhật thông tin")
        self.accept()


