from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.connection_manager import buzzer_manager

router = APIRouter()

@router.websocket("/ws/buzzer")
async def buzzer_endpoint(websocket: WebSocket):
    """Ендпоінт для миттєвої передачі натискань кнопок між пристроями"""
    await buzzer_manager.connect(websocket)
    try:
        while True:
            # Отримуємо сигнал у форматі JSON
            data = await websocket.receive_json()
            # Наш оновлений універсальний broadcast сам зрозуміє, що це dict, і відправить як JSON
            await buzzer_manager.broadcast(data)
    except WebSocketDisconnect:
        buzzer_manager.disconnect(websocket)
