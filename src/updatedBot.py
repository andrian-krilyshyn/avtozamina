from telethon import TelegramClient, events
import os
import sqlite3

# Функція для отримання даних акаунтів з бази даних
def get_account_data():
    try:
        conn = sqlite3.connect('accounts.db')
        cursor = conn.cursor()
        cursor.execute('SELECT api_id, api_hash, phone FROM accounts')
        accounts = cursor.fetchall()
        conn.close()
        return accounts
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}")
        return []

# Словник для зберігання клієнтів
clients = {}

# Ініціалізація клієнтів для всіх акаунтів
def initialize_clients():
    accounts = get_account_data()
    for api_id, api_hash, phone in accounts:
        client = TelegramClient(f'session_{phone}', api_id, api_hash)
        clients[phone] = client

# Функція для вибору клієнта за номером телефону
def get_client(phone):
    return clients.get(phone)

# ID чату, в якому дозволено адміністрування
allowed_chat_id = 0000000

# Словник для відповідності ключових слів до шляхів відео
video_mapping = {}

# Список ID адміністраторів
admin_ids = [0000000, 0000000]

# Стан зберігає інформацію про запити адміністраторів
admin_states = {}

# Папка для збереження відео
video_folder = 'videos'
os.makedirs(video_folder, exist_ok=True)

# Функція для ініціалізації мапінгу відео при старті бота
def initialize_video_mapping():
    global video_mapping
    video_mapping.clear()
    # Зчитування всіх файлів із папки
    for file_name in os.listdir(video_folder):
        if file_name.endswith('.mp4'):
            key = file_name.rsplit('.', 1)[0]
            video_mapping[key] = os.path.join(video_folder, file_name)
    print("Video mapping initialized:", video_mapping)

# Перевірка, чи є користувач адміністратором
def is_admin(user_id):
    return user_id in admin_ids

# Функція для збереження відео та оновлення мапінгу
async def save_video(event, key, phone):
    client = get_client(phone)
    if client is None:
        return

    file_path = await client.download_media(event.media, file=os.path.join(video_folder, f"{key}.mp4"))
    video_mapping[key] = file_path
    await event.respond(f"The video is saved under key '{key}'.")

# Функція для видалення відео за ключем
async def delete_video(event, key):
    if key in video_mapping:
        file_path = video_mapping.pop(key)
        if os.path.exists(file_path):
            os.remove(file_path)
        await event.respond(f"Key '{key}' and the corresponding video was deleted.")
    else:
        await event.respond(f"Key '{key}' not found.")

# Функція для обробки адміністративних команд
async def admin_handler(event, phone):
    user_id = event.sender_id
    message_text = event.raw_text.lower().strip('/')

    if not is_admin(user_id):
        return

    if message_text == 'add':
        admin_states[user_id] = {'state': 'awaiting_key'}
        await event.reply("Enter the key for the new video.")
        return

    if message_text == 'delete':
        admin_states[user_id] = {'state': 'awaiting_delete_key'}
        await event.reply("Enter the key to delete.")
        return

    if message_text == 'exit':
        if user_id in admin_states:
            del admin_states[user_id]
            await event.reply("The process has been cancelled.")
        return

    if admin_states.get(user_id, {}).get('state') == 'awaiting_key':
        admin_states[user_id] = {'state': 'awaiting_video', 'key': message_text}
        await event.reply(f"Key '{message_text}' saved. Now submit a video for this key.")
        return

    if admin_states.get(user_id, {}).get('state') == 'awaiting_delete_key':
        await delete_video(event, message_text)
        del admin_states[user_id]
        return

    if admin_states.get(user_id, {}).get('state') == 'awaiting_video' and event.media:
        key = admin_states[user_id]['key']
        await save_video(event, key, phone)
        del admin_states[user_id]
        return

# Функція для обробки відео за ключами
async def video_handler(event, phone):
    user_id = event.sender_id
    message_text = event.raw_text.lower().strip('/')

    if not is_admin(user_id):
        return

    if message_text in video_mapping:
        file = video_mapping[message_text]
        await event.delete()
        await get_client(phone).send_file(
            event.chat_id,
            file=file,
            video_note=True,
            mime_type='video/mp4'
        )
        print(f"Video note sent to chat {event.chat_id}!")

# Функція-обгортка для реєстрації обробників подій для клієнта
def register_handlers(client, phone):
    @client.on(events.NewMessage(chats=allowed_chat_id))
    async def handle_admin(event):
        await admin_handler(event, phone)

    @client.on(events.NewMessage)
    async def handle_video(event):
        await video_handler(event, phone)

# Реєстрація обробників подій для всіх клієнтів
async def setup_handlers():
    for phone, client in clients.items():
        register_handlers(client, phone)

async def main():
    initialize_clients()
    initialize_video_mapping()

    for client in clients.values():
        await client.start()
        print(f"Client started for phone: {client.session.filename}")

    await setup_handlers()

    await asyncio.gather(*[client.run_until_disconnected() for client in clients.values()])

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
