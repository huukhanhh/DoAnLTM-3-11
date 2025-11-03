# config/config.py
DATABASE_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "chat_app"
}

SERVER_CONFIG = {
    "host": "192.168.110.44",  # IP chung
    "port": 5000         # Port cho socket TCP
}

MULTICAST_CONFIG = {
    "group": "239.0.0.1",  # Multicast IP (phạm vi local)
    "port": 5007
}