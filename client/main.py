# client/main.py
import sys
from PyQt5 import QtWidgets
from views.login_view import LoginView
from views.register_view import RegisterView
from views.main_view import MainView

class ChatApp:
    def __init__(self):
        self.app = QtWidgets.QApplication(sys.argv)
        self.current_window = None
        self.socket = None  # Lưu socket toàn cục
        self.user_id = None
        self.display_name = None

    def show_login(self):
        if self.current_window:
            self.current_window.close()
        self.current_window = LoginView(self)
        self.current_window.show()

    def show_register(self):
        if self.current_window:
            self.current_window.close()
        self.current_window = RegisterView(self)
        self.current_window.show()

    def show_main(self, socket, user_id, display_name):
        self.socket = socket  # Lưu socket từ login
        self.user_id = user_id
        self.display_name = display_name
        if self.current_window:
            self.current_window.close()
        self.current_window = MainView(self, socket, user_id, display_name)
        self.current_window.show()

    def run(self):
        self.show_login()
        sys.exit(self.app.exec_())

if __name__ == "__main__":
    app = ChatApp()
    app.run()