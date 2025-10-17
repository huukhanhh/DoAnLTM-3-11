# server/run_server.py
import sys
sys.path.append("D:/Python_VsCode/Mid_Tern")  # Thêm đường dẫn gốc của dự án

def main():
    from controllers.auth_controller import ChatController
    server = ChatController()
    server.start()

if __name__ == "__main__":
    main()