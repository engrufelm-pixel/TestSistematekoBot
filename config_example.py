# =============================================================================
#  config_example.py — Пример настроек
#  Скопируйте этот файл как config.py и впишите свои данные
# =============================================================================

BOT_TOKEN = "ВСТАВЬТЕ_ТОКЕН_СЮДА"
ADMIN_IDS = [123456789]
DB_FILE = "sistemateko.db"

ROOM_TYPES = {
    "apartment": "🏠 Квартира",
    "house":     "🏡 Частный дом",
    "office":    "🏢 Офис",
    "warehouse": "🏭 Склад / производство",
    "retail":    "🏬 Торговое помещение",
}

CLEANING_TYPES = {
    "standard": {
        "label":    "🧹 Стандартная уборка",
        "one_time": True,
        "desc":     "Ежедневная поддерживающая уборка помещений",
    },
    "general": {
        "label":    "✨ Генеральная уборка",
        "one_time": True,
        "desc":     "Полная глубокая уборка всего помещения",
    },
    "after_repair": {
        "label":    "🔨 Послеремонтная уборка",
        "one_time": True,
        "desc":     "Уборка после строительных и ремонтных работ",
    },
    "regular": {
        "label":    "🔄 Регулярная уборка (постоянная основа)",
        "one_time": False,
        "desc":     "Уборка на постоянной основе по договору",
    },
    "office_regular": {
        "label":    "🏢 Офисное обслуживание (постоянная основа)",
        "one_time": False,
        "desc":     "Ежедневное или еженедельное обслуживание офиса",
    },
}

EXTRA_SERVICES = {
    "windows":   {"label": "🪟 Мытьё окон",             "price": 500},
    "fridge":    {"label": "🧊 Чистка холодильника",     "price": 400},
    "oven":      {"label": "🍳 Чистка плиты / духовки",  "price": 400},
    "balcony":   {"label": "🌿 Уборка балкона / лоджии", "price": 600},
    "carpets":   {"label": "🛋️ Чистка ковров",           "price": 800},
    "furniture": {"label": "🪑 Химчистка мягкой мебели", "price": 1000},
    "walls":     {"label": "🧱 Мытьё стен",              "price": 700},
}

PRICE_PER_SQM = {
    "standard":     80,
    "general":      150,
    "after_repair": 200,
}

MIN_PRICE = 2000

STATUSES = {
    "new":         "🆕 Новая",
    "reviewing":   "🔍 На рассмотрении",
    "approved":    "✅ Одобрена",
    "in_progress": "🧹 Выполняется",
    "done":        "✔️ Выполнена",
    "cancelled":   "❌ Отменена",
    "meeting":     "📅 Назначена встречи",
}

NOTIFY_CLIENT_ON = {"approved", "in_progress", "done", "cancelled", "meeting"}

PRIORITIES = {
    "high":   "🔴 Высокий",
    "medium": "🟡 Средний",
    "low":    "🟢 Низкий",
}