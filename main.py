import asyncio
import sqlite3
import re
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, FSInputFile, 
    BotCommand, InlineKeyboardMarkup, InlineKeyboardButton, 
    ReplyKeyboardRemove, InputMediaPhoto
)
from dotenv import load_dotenv

# --- НАСТРОЙКИ ----
load_dotenv()
API_TOKEN = os.getenv('BOT_TOKEN')
raw_chat_id = os.getenv('AGENT_CHAT_ID')
AGENT_CHAT_ID = int(raw_chat_id)
HR_TAG = os.getenv('HR_TAG')
IB_TAG = os.getenv('IB_TAG')

CATALOG_FILE_ID = "BQACAgIAAxkDAAIEy2mKJ-fQgO3G4sgmDJt2kcuvMXhcAAKUlAACf8tQSMuHYMpCBk9-OgQ"

DB_PATH = "data/users.db" if os.path.exists("data") else "users.db"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())



# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            phone TEXT,
            username TEXT,
            referrer TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_user(user_id, name, phone, username, referrer="Прямой заход"):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?)', (user_id, name, phone, username, referrer))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT name, phone, referrer FROM users WHERE user_id = ?', (user_id,))
    return cursor.fetchone()

# --- СОСТОЯНИЯ ---
class Form(StatesGroup):
    reg_name = State()
    reg_phone = State()
    eval_city = State()
    eval_rooms = State()
    eval_photos = State()
    job_info = State()
    agent_request = State()
    mortgage_amount = State() 
    mortgage_payment = State()

# --- КЛАВИАТУРЫ ---
def main_menu():
    kb = [
        [KeyboardButton(text="🏢 Посмотреть каталог")],
        [KeyboardButton(text="📏 Оценить стоимость квартиры")],
        [KeyboardButton(text="🏠 Одобрить ипотеку")],
        [KeyboardButton(text="🤝 Записаться на собеседование")],
        [KeyboardButton(text="👨‍💼 Связаться с агентом")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def cancel_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)

def photo_kb():
    kb = [
        [KeyboardButton(text="✅ Готово")],
        [KeyboardButton(text="🚫 Отправить без фото")],
        [KeyboardButton(text="❌ Отмена")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def is_valid_phone(phone: str):
    # Удаляем всё кроме цифр и проверяем длину
    clean_phone = re.sub(r'\D', '', str(phone))
    return 10 <= len(clean_phone) <= 15

def start_social_kb():
    kb = [[InlineKeyboardButton(text="📱 Мы в соцсетях", url="https://www.instagram.com/vybor_pervyh_ufa?igsh=bnd0MW9mdmF6ZXdz&utm_source=qr")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

async def check_reg_and_ask(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("Давайте сначала познакомимся! 😊\n\nКак к вам обращаться? Введите ваше Имя:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(Form.reg_name)
        return False
    return user

# --- ОБРАБОТЧИКИ ---

@dp.message(F.text == "❌ Отмена")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено", reply_markup=main_menu())

@dp.message(Command("start"))
async def start_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    args = message.text.split()
    referrer = args[1] if len(args) > 1 else "Прямой заход"
    await state.update_data(referrer=referrer)
    
    user = get_user(message.from_user.id)
    
    welcome_text = (
        "✨ **Добро пожаловать в агентство недвижимости «Выбор Первых»!**\n\n"
        "Наша команда — проводник в мир недвижимости, мы берем все сложные процессы на себя.\n\n"
        "**Наши услуги:**\n"
        "• Покупка / Продажа недвижимости\n"
        "• Подбор в других регионах и городах\n"
        "• Одобрение ипотеки (любая сложность)\n"
        "• Все виды страхования\n"
        "• Инвестиции с высокой доходностью\n"
        "• Полное юридическое сопровождение\n\n"
        "💻 Работаем для вас офлайн и онлайн!\n\n"
        "С чего начнем? Выберите интересующий вас раздел в меню ниже 🔽"
    )
    
    if user:
        await message.answer(f"С возвращением, {user[0]}! Рады видеть вас снова в агентстве «Выбор Первых»! С чего начнем?", reply_markup=main_menu())
    else:
        try:
            await message.answer_photo(
                photo="AgACAgIAAxkBAAIBhGmEgidS5gOioomMOB4ufTjWhd-DAAMNaxvlmylIWc5zLfy8uNQBAAMCAAN5AAM4BA", 
                caption=welcome_text, 
                reply_markup=start_social_kb(),
                parse_mode="Markdown"
            )
            await message.answer("Воспользуйтесь кнопками меню для навигации:", reply_markup=main_menu())
        except:
            await message.answer(welcome_text, reply_markup=main_menu(), parse_mode="Markdown")

# --- СОБЕСЕДОВАНИЕ (РАЗРЕШЕНО ПРИНИМАТЬ ФАЙЛЫ) ---
@dp.message(F.text == "🤝 Записаться на собеседование")
async def job_start(message: types.Message, state: FSMContext):
    if not await check_reg_and_ask(message, state): return
    await message.answer("Опишите ваш опыт работы или прикрепите резюме (файлом или фото) 👇", reply_markup=cancel_kb())
    await state.set_state(Form.job_info)

# ОБРАБОТЧИК ДЛЯ ФАЙЛОВ И ТЕКСТА В СОБЕСЕДОВАНИИ
@dp.message(Form.job_info)
async def job_end(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Действие отменено", reply_markup=main_menu())
        return

    user = get_user(message.from_user.id)
    
    # 1. Получаем никнейм через @. Если ника нет — пишем "Скрыт"
    username = f"@{message.from_user.username}" if message.from_user.username else "Скрыт"
    
    # 2. Формируем текст с новой строчкой
    caption = (
        f"💼 ЗАЯВКА НА СОБЕСЕДОВАНИЕ\n\n"
        f"👤 Кандидат: {user[0]}\n"
        f"📞 Телефон: {user[1]}\n"
        f"🔗 ТГ клиента: {username}\n" # Добавили никнейм
        f"🤝 Пришел от агента: {user[2]}\n"
        f"📝 Комментарий: {message.text or message.caption or 'Прикреплен файл'}\n\n"
        f"❗️ {HR_TAG} заявка на собес"
    )

    # 3. При отправке ВЕЗДЕ добавляем parse_mode="Markdown"
    if message.photo:
        await bot.send_photo(AGENT_CHAT_ID, photo=message.photo[-1].file_id, caption=caption, parse_mode="Markdown")
    elif message.document:
        await bot.send_document(AGENT_CHAT_ID, document=message.document.file_id, caption=caption, parse_mode="Markdown")
    else:
        await bot.send_message(AGENT_CHAT_ID, caption, parse_mode="Markdown")

    await message.answer("Ваша заявка принята! Мы свяжемся с вами для уточнения деталей 😊", reply_markup=main_menu())
    await state.clear()

# --- ОЦЕНКА КВАРТИРЫ (РАЗРЕШЕНО ПРИНИМАТЬ ФОТО) ---
@dp.message(F.text == "📏 Оценить стоимость квартиры")
async def eval_1(message: types.Message, state: FSMContext):
    if not await check_reg_and_ask(message, state): return
    await message.answer("В каком районе или ЖК находится квартира?", reply_markup=cancel_kb())
    await state.set_state(Form.eval_city)

@dp.message(Form.eval_city, F.text)
async def eval_2(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("Укажите площадь и количество комнат:", reply_markup=cancel_kb())
    await state.set_state(Form.eval_rooms)

@dp.message(Form.eval_rooms, F.text)
async def eval_3(message: types.Message, state: FSMContext):
    await state.update_data(rooms=message.text, photos=[])
    await message.answer("Пришлите фото квартиры. Когда закончите, нажмите '✅ Готово' 👇", reply_markup=photo_kb())
    await state.set_state(Form.eval_photos)

@dp.message(Form.eval_photos)
async def eval_4(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    
    # Если пользователь прислал документ (фото без сжатия)
    if message.document:
        await message.answer("⚠️ Пожалуйста, отправьте фото **как изображение** (со сжатием). \n\n"
                             "Фотографии «файлом» я принять не смогу. Попробуйте еще раз или нажмите '✅ Готово'.", 
                             parse_mode="Markdown")
        return

    # Если пользователь прислал обычное фото
    if message.photo:
        photos.append(message.photo[-1].file_id)
        await state.update_data(photos=photos)
        return

    # Логика завершения (кнопки)
    if message.text in ["✅ Готово", "🚫 Отправить без фото"]:
        user = get_user(message.from_user.id)
        username = f"@{message.from_user.username}" if message.from_user.username else "Скрыт"
        
        report = (
            f"📏 **ЗАПРОС НА ОЦЕНКУ КВАРТИРЫ**\n\n"
            f"👤 Клиент: {user[0]}\n"
            f"📞 Телефон: {user[1]}\n"
            f"🔗 Ссылка на тг: {username}\n"
            f"🤝 Пришел от агента: {user[2]}\n\n"
            f"Информация об объекте:\n"
            f"📍 Район/ЖК: {data['city']}\n"
            f"📏 Параметры: {data['rooms']}"
        )

        try:
            if photos:
                media = [InputMediaPhoto(media=photos[0], caption=report, parse_mode="Markdown")]
                for p in photos[1:10]: 
                    media.append(InputMediaPhoto(media=p))
                await bot.send_media_group(AGENT_CHAT_ID, media)
            else:
                await bot.send_message(AGENT_CHAT_ID, report + "\n📸 (Без фото)", parse_mode="Markdown")
            
            await message.answer("Заявка передана агенту! 😊", reply_markup=main_menu())
        except Exception as e:
            print(f"Ошибка в оценке: {e}")
            await message.answer("Произошла ошибка при отправке. Попробуйте позже.", reply_markup=main_menu())
            
        await state.clear()

# --- ОСТАЛЬНЫЕ РАЗДЕЛЫ (ТОЛЬКО ТЕКСТ) ---
@dp.message(Form.reg_name, F.text)
async def reg_name_step(message: types.Message, state: FSMContext):
    await state.update_data(user_name=message.text) # Сохраняем имя в память бота
    kb = [[KeyboardButton(text="📱 Отправить контакт", request_contact=True)]]
    await message.answer(
        f"Приятно познакомиться, {message.text}! 👋\nДля завершения укажите ваш номер телефона:",
        reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)
    )
    await state.set_state(Form.reg_phone) # Переходим к телефону

# ТУТ ДОБАВЛЕН ФИЛЬТР Form.reg_phone
@dp.message(Form.reg_phone)
async def reg_phone_step(message: types.Message, state: FSMContext):
    # Берем номер из кнопки или из текста
    phone_raw = message.contact.phone_number if message.contact else message.text
    
    if not is_valid_phone(str(phone_raw)):
        await message.answer("⚠️ Пожалуйста, введите корректный номер (только цифры) или нажмите кнопку ниже 👇")
        return

    data = await state.get_data()
    referrer = data.get('referrer', 'Прямой заход')
    username = f"@{message.from_user.username}" if message.from_user.username else "Скрыт"
    
    # Сохраняем в БД
    save_user(
        message.from_user.id, 
        data['user_name'], 
        str(phone_raw), 
        username,
        referrer
    )
    
    await bot.send_message(AGENT_CHAT_ID, f"✅ НОВАЯ РЕГИСТРАЦИЯ\n\n👤Клиент: {data['user_name']}\n📞Телефон: {phone_raw}\n🤝 Клиент пришел от агента: {referrer}")
    await message.answer("Регистрация завершена! 😊 Теперь все функции доступны.", reply_markup=main_menu())
    await state.clear()

@dp.message(F.text == "👨‍💼 Связаться с агентом")
async def contact_agent_start(message: types.Message, state: FSMContext):
    if not await check_reg_and_ask(message, state): return
    await message.answer("Напишите ваш вопрос:", reply_markup=cancel_kb())
    await state.set_state(Form.agent_request)

@dp.message(Form.agent_request, F.text)
async def contact_agent_end(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    
    # Получаем никнейм через @. Если ника нет — пишем "Скрыт"
    username = f"@{message.from_user.username}" if message.from_user.username else "Скрыт"
    
    report = (
        f"🙋‍♂️ ВОПРОС АГЕНТУ\n\n"
        f"👤 Клиент: {user[0]}\n"
        f"📞 Номер телефона: {user[1]}\n"
        f"🔗 ТГ клиента: {username}\n" # Добавили эту строчку
        f"🤝 Пришел от агента: {user[2]}\n\n"
        f"❓ Вопрос: {message.text}"
    )
    
    # Добавляем parse_mode="Markdown", чтобы текст выглядел красиво
    await bot.send_message(AGENT_CHAT_ID, report, parse_mode="Markdown")
    
    await message.answer("Запрос отправлен! В ближайшее время мы с вами свяжемся 😊", reply_markup=main_menu())
    await state.clear()

# --- КАТАЛОГ И ИПОТЕКА ---
@dp.message(F.text == "🏠 Одобрить ипотеку")
async def mortgage_1(message: types.Message, state: FSMContext):
    if not await check_reg_and_ask(message, state): return
    await message.answer("Какая сумма кредита вам необходима?", reply_markup=cancel_kb())
    await state.set_state(Form.mortgage_amount)

@dp.message(Form.mortgage_amount, F.text)
async def mortgage_2(message: types.Message, state: FSMContext):
    await state.update_data(m_amount=message.text)
    await message.answer("Ваш первоначальный взнос?", reply_markup=cancel_kb())
    await state.set_state(Form.mortgage_payment)

@dp.message(Form.mortgage_payment, F.text)
async def mortgage_final(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    data = await state.get_data()
    
    # 1. ОБЯЗАТЕЛЬНО добавляем эту строчку, чтобы бот знал, что такое user_link
    username = f"@{message.from_user.username}" if message.from_user.username else "Ник не установлен"
    
    # 2. Формируем текст (используем Markdown для работы ссылки)
    report = (
        f"💸 ЗАЯВКА НА ОДОБРЕНИЕ ИПОТЕКИ\n\n"
        f"👤 Клиент: {user[0]}\n"
        f"📞 Телефон: {user[1]}\n"
        f"🔗 Ссылка на тг клиента: {username}\n"
        f"🤝 Пришел от агента: {user[2]}\n\n"
        f"Информация от клиента:\n"
        f"💰 Сумма необходимая: {data['m_amount']}\n"
        f"💼 ПВ: {message.text}\n\n"
        f"❗️ {IB_TAG}"
    )
    
    # 3. В send_message указываем переменную 'report' (у вас была report_text)
    # И обязательно добавляем parse_mode="Markdown"
    await bot.send_message(AGENT_CHAT_ID, report)
    
    await message.answer("Заявка передана брокеру! После анализа мы с вами свяжемся 😊", reply_markup=main_menu())
    await state.clear()

@dp.message(F.text == "🏢 Посмотреть каталог")
async def send_catalog(message: types.Message, state: FSMContext):
    user = await check_reg_and_ask(message, state)
    if not user: return

    try:
        # Мгновенная отправка по file_id
        await message.answer_document(document=CATALOG_FILE_ID, caption="🏠 Каталог новостроек от команды «Выбор Первых»!")
        
        # Отчет агентам
        username = f"@{message.from_user.username}" if message.from_user.username else "Скрыт"
        report = (f"🗂 КЛИЕНТ СКАЧАЛ КАТАЛОГ\n\n"
                  f"👤 Имя: {user[0]}\n"
                  f"📞 Телефон: {user[1]}\n"
                  f"🔗 Ссылка на тг: {username}")\n"
                  f"🤝 Пришел от агента: {user[2]}"
        await bot.send_message(AGENT_CHAT_ID, report, parse_mode="Markdown")
    except Exception as e:
        print(f"Ошибка каталога: {e}")
        await message.answer("Каталог временно недоступен.")

# --- ФИНАЛЬНАЯ ЗАЩИТА (ОШИБКА ДЛЯ КАРТИНОК ТАМ, ГДЕ ИХ НЕ ЖДЕМ) ---
@dp.message(F.photo | F.document | F.video | F.sticker)
async def wrong_content_handler(message: types.Message):
    await message.answer("⚠️ Извините, здесь я принимаю только текст.")

    # --- ОБРАБОТЧИК ЛЮБОГО ДРУГОГО ТЕКСТА ---
@dp.message(F.text)
async def unknown_text_handler(message: types.Message):
    # Текст ответа клиенту
    reply_text = (
        "🤖 Я — автоматический помощник агентства «Выбор Первых».\n\n"
        "К сожалению, я не понимаю свободный текст. Пожалуйста, **воспользуйтесь кнопками меню** ниже, "
        "чтобы я смог вам помочь. 👇\n\n"
        "Если вы хотите задать конкретный вопрос человеку, нажмите кнопку **«👨‍💼 Связаться с агентом»**."
    )
    
    await message.answer(reply_text, reply_markup=main_menu(), parse_mode="Markdown")

# --- ЗАПУСК ---
async def main():
    # 1. Инициализация базы данных
    init_db()
    
    # 2. Получаем информацию о боте для красивого вывода
    bot_info = await bot.get_me()
    
    print("=" * 30)
    print(f"🚀 БОТ ЗАПУЩЕН!")
    print(f"🤖 Имя бота: @{bot_info.username}")
    print(f"📈 База данных: users.db подключена")
    print(f"📡 Статус: Ожидание сообщений...")
    print("=" * 30)
    
    # 3. Установка команд (меню) в интерфейсе ТГ
    await bot.set_my_commands([
        BotCommand(command="/start", description="Запустить бота / Главное меню")
    ])

    # 4. Запуск прослушивания серверов
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:

        print("\n🛑 Бот остановлен пользователем")





