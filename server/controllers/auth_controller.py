# server/controllers/auth_controller.py
import json
import socket
import struct
from config.config import SERVER_CONFIG
import logging
import threading
import time

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='server.log',
    filemode='a'
)
logger = logging.getLogger(__name__)


class ChatController:
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((SERVER_CONFIG["host"], SERVER_CONFIG["port"]))
        self.server_socket.listen(5)
        self.clients = {}
        self.user_sockets = {}
        self.offline_messages = {}
        self.lock = threading.Lock()
        try:
            from server.models.user_model import UserModel
            self.model = UserModel()
            logger.info("UserModel initialized successfully")
        except Exception as e:
            logger.error(f"Không thể khởi tạo UserModel: {str(e)}")
            raise

    def _send_all(self, sock, data):
        """Gửi tất cả dữ liệu, đảm bảo gửi đủ"""
        total_sent = 0
        while total_sent < len(data):
            sent = sock.send(data[total_sent:])
            if sent == 0:
                raise socket.error("Socket connection broken")
            total_sent += sent
        return total_sent

    def _recv_all(self, sock, length):
        """Nhận đủ số bytes cần thiết"""
        data = b''
        while len(data) < length:
            chunk = sock.recv(min(length - len(data), 10485760))  # 10MB chunks
            if not chunk:
                raise socket.error("Socket connection broken")
            data += chunk
        return data

    def send_to_client(self, client_socket, message):
        try:
            if client_socket.fileno() != -1:
                data = json.dumps(message).encode('utf-8')
                # Gửi với length prefix
                length = struct.pack('>I', len(data))
                self._send_all(client_socket, length + data)
                return True
        except Exception as e:
            logger.error(f"Lỗi gửi message: {str(e)}")
            return False
        return False

    def handle_client(self, client_socket):
        client_socket.settimeout(600)  # Tăng timeout cho video lớn (10 phút)
        logger.info("New client session started")
        current_user_id = None

        try:
            while True:
                try:
                    # Nhận length prefix (4 bytes)
                    length_data = self._recv_all(client_socket, 4)
                    if not length_data:
                        logger.info("No data received, closing connection")
                        break
                    
                    # Unpack length
                    data_length = struct.unpack('>I', length_data)[0]
                    
                    # Kiểm tra kích thước hợp lệ (tối đa 100MB)
                    if data_length > 100 * 1024 * 1024:
                        logger.error(f"Data too large: {data_length} bytes")
                        self.send_to_client(
                            client_socket,
                            {"status": "error", "message": "Dữ liệu quá lớn"}
                        )
                        break
                    
                    # Nhận đủ dữ liệu
                    data = self._recv_all(client_socket, data_length)
                    message = data.decode('utf-8')
                    
                    request = json.loads(message)
                    action = request.get("action")
                    logger.debug(f"Received action: {action} from client")

                    response = {"status": "error", "message": "Hành động không hợp lệ"}

                    if action == "register":
                        response = self.model.register_user(
                            request.get("display_name"),
                            request.get("email"),
                            request.get("password")
                        )

                    elif action == "login":
                        response = self.model.login_user(
                            request.get("email"),
                            request.get("password")
                        )
                        if response.get("status") == "success":
                            user_id = self.model.get_user_id(request.get("email"))
                            if user_id:
                                with self.lock:
                                    self.clients[client_socket] = user_id
                                    self.user_sockets[user_id] = client_socket
                                    current_user_id = user_id

                                response["user_id"] = user_id
                                response["display_name"] = self.model.get_display_name(user_id)
                                response["avatar"] = self.model.get_avatar(user_id)
                                logger.info(f"User {user_id} logged in")

                                if user_id in self.offline_messages:
                                    for msg in self.offline_messages[user_id]:
                                        self.send_to_client(client_socket, msg)
                                    del self.offline_messages[user_id]
                            else:
                                response = {"status": "error", "message": "Không tìm thấy user_id"}

                    elif action == "get_users":
                        response = {"status": "success", "users": self.model.get_all_users()}

                    elif action == "get_chat_history":
                        if client_socket in self.clients:
                            receiver_id = request.get("receiver_id")
                            history = self.model.get_chat_history(
                                self.clients[client_socket],
                                receiver_id
                            )
                            response = {"status": "success", "history": history}
                            logger.debug(f"Chat history sent for receiver {receiver_id}")
                        else:
                            response = {"status": "error", "message": "Không xác định user"}

                    elif action == "get_recent_chats":
                        if client_socket in self.clients:
                            user_id = self.clients[client_socket]
                            response = {
                                "status": "success",
                                "chats": self.model.get_recent_chats(user_id)
                            }
                        else:
                            response = {"status": "error", "message": "Không xác định user"}

                    elif action == "message":
                        if client_socket in self.clients:
                            sender_id = self.clients[client_socket]
                            receiver_id = request.get("receiver_id")
                            message = request.get("message")

                            self.model.save_message(sender_id, receiver_id, message)

                            msg_data = {
                                "action": "message",
                                "sender_id": sender_id,
                                "sender_name": self.model.get_display_name(sender_id),
                                "sender_avatar": self.model.get_avatar(sender_id),
                                "receiver_id": receiver_id,
                                "message": message,
                                "is_image": False
                            }

                            with self.lock:
                                if receiver_id in self.user_sockets:
                                    receiver_socket = self.user_sockets[receiver_id]
                                    if not self.send_to_client(receiver_socket, msg_data):
                                        if receiver_id not in self.offline_messages:
                                            self.offline_messages[receiver_id] = []
                                        self.offline_messages[receiver_id].append(msg_data)
                                    else:
                                        logger.debug(f"Message sent to user {receiver_id}")
                                else:
                                    if receiver_id not in self.offline_messages:
                                        self.offline_messages[receiver_id] = []
                                    self.offline_messages[receiver_id].append(msg_data)
                                    logger.debug(f"User {receiver_id} offline, message saved")

                            response = {"status": "success", "message": "Tin nhắn đã gửi"}
                        else:
                            response = {"status": "error", "message": "Không xác định user"}

                    elif action == "send_voice":
                        if client_socket in self.clients:
                            sender_id = self.clients[client_socket]
                            receiver_id = request.get("receiver_id")
                            voice_data = request.get("voice_data")
                            filename = request.get("filename", "voice.wav")

                            # Lưu voice vào database
                            self.model.save_voice_message(sender_id, receiver_id, voice_data, filename)

                            # Tạo message data
                            msg_data = {
                                "action": "message",
                                "sender_id": sender_id,
                                "sender_name": self.model.get_display_name(sender_id),
                                "sender_avatar": self.model.get_avatar(sender_id),
                                "receiver_id": receiver_id,
                                "voice_data": voice_data,
                                "is_voice": True
                            }

                            # Gửi đến receiver
                            with self.lock:
                                if receiver_id in self.user_sockets:
                                    receiver_socket = self.user_sockets[receiver_id]
                                    if not self.send_to_client(receiver_socket, msg_data):
                                        if receiver_id not in self.offline_messages:
                                            self.offline_messages[receiver_id] = []
                                        self.offline_messages[receiver_id].append(msg_data)
                                    else:
                                        logger.debug(f"Voice sent to user {receiver_id}")
                                else:
                                    if receiver_id not in self.offline_messages:
                                        self.offline_messages[receiver_id] = []
                                    self.offline_messages[receiver_id].append(msg_data)
                                    logger.debug(f"User {receiver_id} offline, voice saved")

                            response = {"status": "success", "message": "Tin nhắn thoại đã gửi"}
                        else:
                            response = {"status": "error", "message": "Không xác định user"}





                    elif action == "send_image":
                        if client_socket in self.clients:
                            sender_id = self.clients[client_socket]
                            receiver_id = request.get("receiver_id")
                            image_data = request.get("image_data")
                            filename = request.get("filename", "image.jpg")

                            # Lưu ảnh vào database
                            self.model.save_image_message(sender_id, receiver_id, image_data, filename)

                            # Tạo message data
                            msg_data = {
                                "action": "message",
                                "sender_id": sender_id,
                                "sender_name": self.model.get_display_name(sender_id),
                                "sender_avatar": self.model.get_avatar(sender_id),
                                "receiver_id": receiver_id,
                                "image_data": image_data,
                                "is_image": True
                            }

                            # Gửi đến receiver
                            with self.lock:
                                if receiver_id in self.user_sockets:
                                    receiver_socket = self.user_sockets[receiver_id]
                                    if not self.send_to_client(receiver_socket, msg_data):
                                        if receiver_id not in self.offline_messages:
                                            self.offline_messages[receiver_id] = []
                                        self.offline_messages[receiver_id].append(msg_data)
                                    else:
                                        logger.debug(f"Image sent to user {receiver_id}")
                                else:
                                    if receiver_id not in self.offline_messages:
                                        self.offline_messages[receiver_id] = []
                                    self.offline_messages[receiver_id].append(msg_data)
                                    logger.debug(f"User {receiver_id} offline, image saved")

                            response = {"status": "success", "message": "Ảnh đã gửi"}
                        else:
                            response = {"status": "error", "message": "Không xác định user"}

                    elif action == "send_video":
                        if client_socket in self.clients:
                            sender_id = self.clients[client_socket]
                            receiver_id = request.get("receiver_id")
                            video_data = request.get("video_data")
                            filename = request.get("filename", "video.mp4")

                            # Lưu video vào database
                            self.model.save_video_message(sender_id, receiver_id, video_data, filename)

                            # Tạo message data
                            msg_data = {
                                "action": "message",
                                "sender_id": sender_id,
                                "sender_name": self.model.get_display_name(sender_id),
                                "sender_avatar": self.model.get_avatar(sender_id),
                                "receiver_id": receiver_id,
                                "video_data": video_data,
                                "is_video": True
                            }

                            # Gửi đến receiver
                            with self.lock:
                                if receiver_id in self.user_sockets:
                                    receiver_socket = self.user_sockets[receiver_id]
                                    if not self.send_to_client(receiver_socket, msg_data):
                                        if receiver_id not in self.offline_messages:
                                            self.offline_messages[receiver_id] = []
                                        self.offline_messages[receiver_id].append(msg_data)
                                    else:
                                        logger.debug(f"Video sent to user {receiver_id}")
                                else:
                                    if receiver_id not in self.offline_messages:
                                        self.offline_messages[receiver_id] = []
                                    self.offline_messages[receiver_id].append(msg_data)
                                    logger.debug(f"User {receiver_id} offline, video saved")

                            response = {"status": "success", "message": "Video đã gửi"}
                        else:
                            response = {"status": "error", "message": "Không xác định user"}

                    # Hồ sơ người dùng
                    elif action == "get_profile":
                        if client_socket in self.clients:
                            user_id = self.clients[client_socket]
                            response = self.model.get_profile(user_id)
                        else:
                            response = {"status": "error", "message": "Không xác định user"}

                    elif action == "update_profile":
                        if client_socket in self.clients:
                            user_id = self.clients[client_socket]
                            response = self.model.update_profile(
                                user_id,
                                display_name=request.get("display_name"),
                                avatar_data=request.get("avatar")
                            )
                        else:
                            response = {"status": "error", "message": "Không xác định user"}

                    elif action == "change_password":
                        if client_socket in self.clients:
                            user_id = self.clients[client_socket]
                            response = self.model.change_password(
                                user_id,
                                request.get("old_password", ""),
                                request.get("new_password", "")
                            )
                        else:
                            response = {"status": "error", "message": "Không xác định user"}

                    # Khôi phục session khi client reconnect
                    elif action == "resume_session":
                        user_id = request.get("user_id")
                        if user_id:
                            with self.lock:
                                self.clients[client_socket] = user_id
                                self.user_sockets[user_id] = client_socket
                            response = {"status": "success", "message": "Đã khôi phục phiên"}
                        else:
                            response = {"status": "error", "message": "Thiếu user_id"}

                    time.sleep(0.05)
                    if not self.send_to_client(client_socket, response):
                        logger.warning("Client disconnected before sending response")
                        break
                    logger.debug(f"Response sent: {action}")

                except json.JSONDecodeError:
                    logger.error("Invalid JSON data received")
                    self.send_to_client(
                        client_socket,
                        {"status": "error", "message": "Dữ liệu không hợp lệ"}
                    )
                except socket.timeout:
                    logger.warning("Connection timed out")
                    break
                except socket.error as e:
                    logger.error(f"Socket error: {str(e)}")
                    break
                except Exception as e:
                    logger.error(f"Error handling client: {str(e)}")
                    self.send_to_client(
                        client_socket,
                        {"status": "error", "message": f"Lỗi server: {str(e)}"}
                    )
                    break
        finally:
            with self.lock:
                if client_socket in self.clients:
                    user_id = self.clients[client_socket]
                    del self.clients[client_socket]
                    if user_id in self.user_sockets:
                        del self.user_sockets[user_id]
                    logger.info(f"User {user_id} disconnected")

            if client_socket.fileno() != -1:
                client_socket.close()
            logger.info("Client connection closed")

    def start(self):
        print(f"Server started at {SERVER_CONFIG['host']}:{SERVER_CONFIG['port']}")
        while True:
            try:
                client_socket, address = self.server_socket.accept()
                logger.info(f"New connection from {address}")
                threading.Thread(
                    target=self.handle_client,
                    args=(client_socket,),
                    daemon=True
                ).start()
            except socket.error as e:
                logger.error(f"Error accepting connection: {str(e)}")