from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.connection_manager import buzzer_manager, manager

router = APIRouter()


@router.websocket("/ws/buzzer")
async def buzzer_endpoint(websocket: WebSocket):
    """Ендпоінт для миттєвої передачі натискань кнопок між пристроями"""
    await buzzer_manager.connect(websocket)
    try:
        while True:
            # Отримуємо сигнал від панелі адміна або кнопок
            data = await websocket.receive_json()

            # 1. Відправляємо назад системі кнопок (адміну)
            await buzzer_manager.broadcast(data)

            # 2. Додаємо тип повідомлення і дублюємо на екран глядачів!
            data["type"] = "buzzer_event"
            await manager.broadcast(data)

    except WebSocketDisconnect:
        buzzer_manager.disconnect(websocket)
