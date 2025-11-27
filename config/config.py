# config/config.py
DATABASE_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "chat_app"
}

SERVER_CONFIG = {
    "host": "10.50.192.2",  # IP chung
    "port": 5001         # Port cho socket TCP
}

MULTICAST_CONFIG = {
    "group": "239.0.0.1",  # Multicast IP (phạm vi local)
    "port": 5008
}