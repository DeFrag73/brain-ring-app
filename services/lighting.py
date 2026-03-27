import asyncio
import logging
import os
from tapo import ApiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LightingManager")


class LightingManager:
    def __init__(self, email: str, password: str, bulb1_ip: str, bulb2_ip: str):
        self.email = email.strip()
        self.password = password.strip()
        self.bulb1_ip = bulb1_ip.strip()
        self.bulb2_ip = bulb2_ip.strip()
        self.client = ApiClient(self.email, self.password)

        self.bulb1 = None
        self.bulb2 = None
        self.is_connected = False
        self._background_tasks: set[asyncio.Task] = set()

    def fire_and_forget(self, coro):
        """
        Створює фонову задачу із збереженням посилання,
        щоб garbage collector не знищив її передчасно.
        """
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def connect(self) -> bool:
        """Підключення до ламп при старті сервера"""
        if not self.email or not self.password:
            logger.error("❌ TAPO_EMAIL або TAPO_PASSWORD не задані")
            self.is_connected = False
            return False

        try:
            self.bulb1 = await self.client.l530(self.bulb1_ip)
            self.bulb2 = await self.client.l530(self.bulb2_ip)

            if self.bulb1 is None or self.bulb2 is None:
                raise RuntimeError("Не вдалося ініціалізувати одну або обидві лампи")

            self.is_connected = True
            logger.info("✅ Лампи Tapo успішно підключено!")
            await self.set_idle()
            return True

        except Exception as e:
            logger.error(
                "❌ Помилка підключення до ламп Tapo. "
                "Перевірте email/пароль, factory reset ламп і відключіть інші TP-Link/Tapo пристрої під час прив'язки."
            )
            logger.error(f"Деталі: {e}")
            self.bulb1 = None
            self.bulb2 = None
            self.is_connected = False
            return False

    async def safe_execute(self, coro_func):
        """
        Безпечне виконання команди (щоб помилка лампи не крашила гру).
        Приймає callable (лямбду), яка повертає корутину.
        """
        if not self.is_connected:
            return
        try:
            await coro_func()
        except Exception as e:
            logger.error(f"Помилка виконання команди лампи: {e}")

    # ==========================================
    # ІГРОВІ ЕФЕКТИ
    # ==========================================

    async def set_idle(self):
        """ЧАС ПРОСТОЮ: м'яке тепле біле світло (2700K), 30%."""
        logger.info("Лампи: Режим простою")
        await self.safe_execute(lambda: self.bulb1.set_color_temperature(2700))
        await self.safe_execute(lambda: self.bulb1.set_brightness(30))
        await self.safe_execute(lambda: self.bulb2.set_color_temperature(2700))
        await self.safe_execute(lambda: self.bulb2.set_brightness(30))

    async def start_timer(self):
        """ЧАС ПІШОВ (Пробіл): Лампи згасають (очікування натискання)."""
        logger.info("Лампи: Відлік часу (згасли)")
        # Встановлюємо 1% яскравості (майже непомітно), щоб тримати швидкий зв'язок з API
        await self.safe_execute(lambda: self.bulb1.set_brightness(1))
        await self.safe_execute(lambda: self.bulb2.set_brightness(1))

    async def trigger_buzzer(self, team_id: str):
        """НАТИСКАННЯ КНОПКИ: Лампа команди спалахує, інша залишається темною."""
        logger.info(f"Лампи: Кнопка команди {team_id}")
        if team_id in ["team1", "1"]:
            await self.safe_execute(lambda: self.bulb1.set_hue_saturation(240, 100))  # Синій
            await self.safe_execute(lambda: self.bulb1.set_brightness(100))
            await self.safe_execute(lambda: self.bulb2.set_brightness(1))
        elif team_id in ["team2", "2"]:
            await self.safe_execute(lambda: self.bulb2.set_hue_saturation(40, 100))  # Жовтий
            await self.safe_execute(lambda: self.bulb2.set_brightness(100))
            await self.safe_execute(lambda: self.bulb1.set_brightness(1))

    async def false_start(self, team_id: str):
        """ФАЛЬСТАРТ: Лампа команди-порушника блимає червоним 3 рази."""
        logger.info(f"Лампи: Фальстарт команди {team_id}")
        bulb = self.bulb1 if team_id in ["team1", "1"] else self.bulb2

        if bulb:
            for _ in range(3):
                await self.safe_execute(lambda: bulb.set_hue_saturation(0, 100))  # Червоний
                await self.safe_execute(lambda: bulb.set_brightness(100))
                await asyncio.sleep(0.2)
                await self.safe_execute(lambda: bulb.set_brightness(1))  # Згасає
                await asyncio.sleep(0.2)

        # Після фальстарту повертаємо у режим простою (можна змінити на set_idle)
        await self.set_idle()

    async def answer_correct(self):
        """ПРАВИЛЬНА ВІДПОВІДЬ: Обидві лампи блимають яскраво-зеленим."""
        logger.info("Лампи: Правильна відповідь")
        await self.safe_execute(lambda: self.bulb1.set_hue_saturation(120, 100))
        await self.safe_execute(lambda: self.bulb1.set_brightness(100))
        await self.safe_execute(lambda: self.bulb2.set_hue_saturation(120, 100))
        await self.safe_execute(lambda: self.bulb2.set_brightness(100))

        await asyncio.sleep(2)
        await self.set_idle()

    async def answer_incorrect(self):
        """НЕПРАВИЛЬНА ВІДПОВІДЬ: Обидві лампи блимають яскраво-червоним."""
        logger.info("Лампи: Неправильна відповідь")
        await self.safe_execute(lambda: self.bulb1.set_hue_saturation(0, 100))
        await self.safe_execute(lambda: self.bulb1.set_brightness(100))
        await self.safe_execute(lambda: self.bulb2.set_hue_saturation(0, 100))
        await self.safe_execute(lambda: self.bulb2.set_brightness(100))

        await asyncio.sleep(2)
        await self.set_idle()


# Глобальний екземпляр менеджера
light_manager = LightingManager(
    email=os.getenv("TAPO_EMAIL", ""),
    password=os.getenv("TAPO_PASSWORD", ""),
    bulb1_ip=os.getenv("TAPO_BULB1_IP", "192.168.1.50"),
    bulb2_ip=os.getenv("TAPO_BULB2_IP", "192.168.1.51"),
)


# ==========================================
# БЛОК ТЕСТУВАННЯ
# ==========================================
async def test_bulbs_sequence():
    print("\n" + "=" * 50)
    print("🚦 ЗАПУСК ТЕСТУВАННЯ ЛАМП TAPO 🚦")
    print("=" * 50)

    if not light_manager.email or not light_manager.password:
        print("\n❌ ПОМИЛКА: Не задані email або пароль.")
        print("Будь ласка, переконайтеся, що змінні TAPO_EMAIL та TAPO_PASSWORD встановлені.")
        return

    print(f"\n📡 Підключення до облікового запису: {light_manager.email}")
    print(f"💡 IP Лампи 1: {light_manager.bulb1_ip}")
    print(f"💡 IP Лампи 2: {light_manager.bulb2_ip}\n")

    # 1. Тестування підключення
    print("[КРОК 1] Спроба підключення...")
    await light_manager.connect()

    if not light_manager.is_connected:
        print("\n❌ Тестування зупинено. Не вдалося підключитися до обох ламп.")
        print("Перевірте IP-адреси та чи знаходяться лампи в тій самій мережі.")
        return

    print("✅ Підключення успішне!\n")

    # 2. Тестування візуальних ефектів
    print("[КРОК 2] Запуск демонстрації ефектів (кожен ефект триватиме 3 секунди)...\n")

    effects = [
        ("Режим простою (Очікування)", light_manager.set_idle, 3),
        ("Відлік часу (Час пішов)", light_manager.start_timer, 3),
        ("Кнопка команди 1 (Синій)", lambda: light_manager.trigger_buzzer("1"), 3),
        ("Кнопка команди 2 (Жовтий)", lambda: light_manager.trigger_buzzer("2"), 3),
        ("Правильна відповідь (Зелений)", light_manager.answer_correct, 1),  # Сам метод має затримку 2с
        ("Неправильна відповідь (Червоний)", light_manager.answer_incorrect, 1)  # Сам метод має затримку 2с
    ]

    for name, func, delay in effects:
        print(f"👉 Демонстрація: {name}")
        await func()
        await asyncio.sleep(delay)

    print("\n[КРОК 3] Повернення ламп у початковий стан...")
    await light_manager.set_idle()

    print("\n✨ ТЕСТУВАННЯ УСПІШНО ЗАВЕРШЕНО! ✨\n")


if __name__ == "__main__":
    # Щоб протестувати код, запустіть цей файл з терміналу:
    # python services/lighting.py
    # Якщо ви використовуєте змінні середовища (env variables), переконайтеся, що вони завантажені
    try:
        # Спроба завантажити .env файл автоматично, якщо встановлено python-dotenv
        from dotenv import load_dotenv

        load_dotenv()

        # Оновлюємо дані менеджера після завантаження .env
        light_manager.email = os.getenv("TAPO_EMAIL", "")
        light_manager.password = os.getenv("TAPO_PASSWORD", "")
        light_manager.bulb1_ip = os.getenv("TAPO_BULB1_IP", "192.168.1.50")
        light_manager.bulb2_ip = os.getenv("TAPO_BULB2_IP", "192.168.1.51")
        # Оновлюємо клієнт з новими даними
        light_manager.client = ApiClient(light_manager.email, light_manager.password)
    except ImportError:
        pass  # python-dotenv не встановлено, ігноруємо

    asyncio.run(test_bulbs_sequence())