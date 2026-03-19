from typing import List, Union
from fastapi import WebSocket


class ConnectionManager:
    """Універсальний менеджер WebSocket з'єднань"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except:
            self.disconnect(websocket)

    async def broadcast(self, message: Union[str, dict]):
        """
        Розумний broadcast: сам визначає, що відправляти.
        Якщо рядок (str) -> відправляє текст (стара логіка).
        Якщо словник (dict) -> відправляє JSON (нова логіка кнопок).
        """
        disconnected = []
        for connection in self.active_connections:
            try:
                if isinstance(message, str):
                    await connection.send_text(message)
                else:
                    await connection.send_json(message)
            except:
                # Якщо клієнт відключився, додаємо його в список на видалення
                disconnected.append(connection)

        # Очищуємо всі мертві з'єднання після розсилки
        for connection in disconnected:
            self.disconnect(connection)


# 1. СТАРИЙ менеджер з'єднань (залишаємо назву manager, щоб не зламати ваш існуючий код)
# Використовується для екрану глядачів (/ws/display)
manager = ConnectionManager()

# 2. НОВИЙ менеджер з'єднань для брейн-системи
# Використовується виключно для кнопок (/ws/buzzer)
buzzer_manager = ConnectionManager()