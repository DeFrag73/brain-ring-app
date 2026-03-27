import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.connection_manager import buzzer_manager, manager
from services.lighting import light_manager

router = APIRouter()

# Зберігаємо стан гри на сервері для синхронізації ламп
GAME_STATE = "IDLE"


@router.websocket("/ws/buzzer")
async def buzzer_endpoint(websocket: WebSocket):
    global GAME_STATE
    """Ендпоінт для миттєвої передачі натискань кнопок між пристроями"""
    await buzzer_manager.connect(websocket)
    try:
        while True:
            # Отримуємо сигнал від панелі адміна або кнопок
            data = await websocket.receive_json()

            # --- ЛОГІКА ЛАМП ---
            action = data.get("action")

            if action == "start":
                GAME_STATE = "ACTIVE"
                light_manager.fire_and_forget(light_manager.start_timer())
            elif action == "reset":
                GAME_STATE = "IDLE"
                light_manager.fire_and_forget(light_manager.set_idle())
            elif action in ["team1", "team2"]:
                if GAME_STATE == "IDLE":
                    GAME_STATE = "LOCKED"
                    light_manager.fire_and_forget(light_manager.false_start(action))
                elif GAME_STATE == "ACTIVE":
                    GAME_STATE = "LOCKED"
                    light_manager.fire_and_forget(light_manager.trigger_buzzer(action))
            elif action == "correct":
                GAME_STATE = "LOCKED"
                light_manager.fire_and_forget(light_manager.answer_correct())
            elif action == "incorrect":
                GAME_STATE = "LOCKED"
                light_manager.fire_and_forget(light_manager.answer_incorrect())
            elif action == "false_start":
                GAME_STATE = "LOCKED"
                team = data.get("team")
                light_manager.fire_and_forget(light_manager.false_start(team))
            # -------------------

            # Відправляємо сигнал назад усім підключеним кнопкам (адмінці)
            try:
                await buzzer_manager.broadcast(data)
            except Exception as e:
                print(f"Помилка buzzer_manager: {e}")

            # Безпечно дублюємо на екран глядачів
            data["type"] = "buzzer_event"
            try:
                await manager.broadcast(data)
            except TypeError:
                # Якщо manager очікує формат рядка (str), а не словник (dict)
                await manager.broadcast(json.dumps(data))
            except Exception as e:
                print(f"Помилка manager (екран глядачів): {e}")

    except WebSocketDisconnect:
        buzzer_manager.disconnect(websocket)
