# client/controllers/auth_controller_client.py
import socket
import json
import threading
import time
from config.config import SERVER_CONFIG
from queue import Queue


class AuthController:
    def __init__(self, socket, host=SERVER_CONFIG["host"], port=SERVER_CONFIG["port"]):
        self.host = host
        self.port = port
        self.client_socket = socket
        self.current_user_id = None
        self.reconnect_attempts = 3
        self.message_queue = Queue()
        self.response_queue = Queue()
        self.running = True
        threading.Thread(target=self._receive_loop, daemon=True).start()

    def _receive_loop(self):
        """Thread riêng để nhận tất cả dữ liệu từ server"""
        while self.running:
            try:
                if self.client_socket and self.client_socket.fileno() != -1:
                    # Tăng buffer cho ảnh
                    data = self.client_socket.recv(10485760)  # 10MB
                    if not data:
                        print("Kết nối bị đóng bởi server")
                        break

                    message = data.decode('utf-8')
                    response = json.loads(message)

                    # Phân loại message
                    if response.get("action") == "message":
                        # Tin nhắn chat từ người khác
                        self.message_queue.put(response)
                    else:
                        # Response từ request
                        self.response_queue.put(response)
                else:
                    if not self.reconnect():
                        break
                    time.sleep(0.5)
            except (socket.error, json.JSONDecodeError) as e:
                print(f"Lỗi nhận dữ liệu: {str(e)}")
                if not self.reconnect():
                    break
                time.sleep(0.5)
            except Exception as e:
                print(f"Lỗi không xác định trong _receive_loop: {str(e)}")
                break

    def reconnect(self):
        """Thử kết nối lại với server"""
        for _ in range(self.reconnect_attempts):
            try:
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client_socket.connect((self.host, self.port))
                print("Kết nối lại thành công")
                # Gửi resume session nếu đã có user_id
                try:
                    if self.current_user_id is not None:
                        resume_req = {"action": "resume_session", "user_id": self.current_user_id}
                        self.client_socket.send(json.dumps(resume_req).encode('utf-8'))
                        # nhận phản hồi (nhỏ)
                        data = self.client_socket.recv(4096)
                        _ = json.loads(data.decode('utf-8'))
                except Exception:
                    pass
                return True
            except socket.error as e:
                print(f"Thử kết nối lại: {str(e)}")
                time.sleep(1)
        return False

    def send_request(self, request, timeout=10):
        """Gửi request và đợi response"""
        if not self.client_socket or self.client_socket.fileno() == -1:
            if not self.reconnect():
                raise Exception("Không thể kết nối lại với server")

        try:
            # Xóa queue cũ
            while not self.response_queue.empty():
                self.response_queue.get_nowait()

            # Gửi request
            data = json.dumps(request).encode('utf-8')
            self.client_socket.send(data)

            # Đợi response từ queue
            try:
                response = self.response_queue.get(timeout=timeout)
                return response
            except:
                raise Exception(f"Không nhận được phản hồi sau {timeout}s")

        except socket.error as e:
            raise Exception(f"Lỗi gửi request: {str(e)}")

    def get_users(self):
        """Lấy danh sách users"""
        request = {"action": "get_users"}
        return self.send_request(request).get("users", [])

    def send_message(self, receiver_id, message):
        """Gửi tin nhắn"""
        request = {"action": "message", "receiver_id": receiver_id, "message": message}
        return self.send_request(request)

    def send_image(self, receiver_id, image_data, filename):
        """Gửi hình ảnh"""
        request = {
            "action": "send_image",
            "receiver_id": receiver_id,
            "image_data": image_data,
            "filename": filename
        }
        return self.send_request(request, timeout=30)  # Timeout lớn hơn cho ảnh

    def send_voice(self, receiver_id, voice_data, filename):
        """Gửi tin nhắn voice"""
        request = {
            "action": "send_voice",
            "receiver_id": receiver_id,
            "voice_data": voice_data,
            "filename": filename
        }
        return self.send_request(request, timeout=30)  # Timeout lớn cho voice



    def get_chat_history(self, receiver_id):
        """Lấy lịch sử chat"""
        request = {"action": "get_chat_history", "receiver_id": receiver_id}
        response = self.send_request(request)
        return response.get("history", [])

    # === Profile APIs ===
    def get_profile(self):
        request = {"action": "get_profile"}
        return self.send_request(request)

    def update_profile(self, display_name=None, avatar=None):
        request = {"action": "update_profile"}
        if display_name is not None:
            request["display_name"] = display_name
        if avatar is not None:
            request["avatar"] = avatar
        return self.send_request(request)

    def change_password(self, old_password, new_password):
        request = {
            "action": "change_password",
            "old_password": old_password,
            "new_password": new_password
        }
        return self.send_request(request)

    def get_incoming_message(self, timeout=0.1):
        """Lấy tin nhắn incoming từ queue (non-blocking)"""
        try:
            return self.message_queue.get(timeout=timeout)
        except:
            return None

    def stop(self):
        """Dừng controller"""
        self.running = False
        if self.client_socket and self.client_socket.fileno() != -1:
            self.client_socket.close()