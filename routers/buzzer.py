from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.connection_manager import buzzer_manager, manager
from services.lighting import light_manager

router = APIRouter()


@router.websocket("/ws/buzzer")
async def buzzer_endpoint(websocket: WebSocket):
    """Ендпоінт для миттєвої передачі натискань кнопок між пристроями"""
    await buzzer_manager.connect(websocket)
    try:
        while True:
            # Отримуємо сигнал від панелі адміна або кнопок
            data = await websocket.receive_json()

            # --- ЛОГІКА ЛАМП ---
            action = data.get("action")
            if action == "press":
                team = data.get("team")
                light_manager.fire_and_forget(light_manager.trigger_buzzer(team))
            elif action == "start":
                light_manager.fire_and_forget(light_manager.start_timer())
            elif action == "reset":
                light_manager.fire_and_forget(light_manager.set_idle())
            elif action == "correct":
                light_manager.fire_and_forget(light_manager.answer_correct())
            elif action == "incorrect":
                light_manager.fire_and_forget(light_manager.answer_incorrect())
            elif action == "false_start":
                team = data.get("team")
                light_manager.fire_and_forget(light_manager.false_start(team))
            # -------------------

            await buzzer_manager.broadcast(data)

            # 2. Додаємо тип повідомлення і дублюємо на екран глядачів!
            data["type"] = "buzzer_event"
            await manager.broadcast(data)

    except WebSocketDisconnect:
        buzzer_manager.disconnect(websocket)
