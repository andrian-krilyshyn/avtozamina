from telethon import TelegramClient, events
import os

# Ваші дані (дістається з сайту https://my.telegram.org/auth)
api_id = 'api_id'
api_hash = 'api_hash'
phone = '+phone'

# ID чату, в якому дозволено адміністрування
allowed_chat_id = 0000000 # ID конкретного чату для адміністрування (лише в цьому чаті можна буде виконувати дії адміна) 
allowed_chat_id_to_using = 0000000  # ID від кого все повинно відправлятись

# Словник для відповідності ключових слів до шляхів відео
video_mapping = {}

# Список ID адміністраторів
admin_ids = [000000]  # Введіть свій Telegram ID

# Ініціалізація клієнта
client = TelegramClient('session_name', api_id, api_hash)

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
async def save_video(event, key):
    # Зберігаємо відео в папку videos під відповідним ключем
    file_path = await client.download_media(event.media, file=os.path.join(video_folder, f"{key}.mp4"))
    video_mapping[key] = file_path
    await event.respond(f"The video is saved under lock and key '{key}'.")

# Функція для видалення відео за ключем
async def delete_video(event, key):
    # Перевірка наявності ключа у мапінгу
    if key in video_mapping:
        file_path = video_mapping.pop(key)  # Видаляємо ключ з мапінгу
        # Видалення файлу з диска, якщо він існує
        if os.path.exists(file_path):
            os.remove(file_path)
        await event.respond(f"Key '{key}' and the corresponding video was deleted.")
    else:
        await event.respond(f"Key '{key}' not found.")

# Обробник адміністративних команд
@client.on(events.NewMessage(chats=allowed_chat_id))
async def admin_handler(event):
    user_id = event.sender_id
    message_text = event.raw_text.lower().strip('/')

    # Перевірка, чи користувач є адміністратором
    if not is_admin(user_id):
        return  # Ігноруємо всі повідомлення від неадміністраторів

    # Якщо адміністратор хоче додати ключове слово
    if message_text == 'add':
        admin_states[user_id] = 'awaiting_key'
        await event.reply("Enter the key for the new video.")
        return

    # Якщо адміністратор хоче видалити ключ
    if message_text == 'delete':
        admin_states[user_id] = 'awaiting_delete_key'
        await event.reply("Enter the key to delete.")
        return

    # Якщо адміністратор хоче скасувати процес
    if message_text == 'exit':
        if user_id in admin_states:
            del admin_states[user_id]  # Скидаємо стан
            await event.reply("The process has been cancelled.")
        return

    # Якщо бот очікує ключ від адміністратора для додавання
    if admin_states.get(user_id) == 'awaiting_key':
        admin_states[user_id] = {'state': 'awaiting_video', 'key': message_text}
        await event.reply(f"Key '{message_text}' saved. Now submit a video for this key.")
        return

    # Якщо бот очікує ключ від адміністратора для видалення
    if admin_states.get(user_id) == 'awaiting_delete_key':
        await delete_video(event, message_text)
        del admin_states[user_id]  # Скидаємо стан після завершення
        return

    # Якщо бот очікує відео від адміністратора
    if admin_states.get(user_id, {}).get('state') == 'awaiting_video' and event.media:
        key = admin_states[user_id]['key']
        await save_video(event, key)
        del admin_states[user_id]  # Скидаємо стан після завершення
        return

# Обробник для відправки відео за ключами в будь-яких чатах
@client.on(events.NewMessage)
async def video_handler(event):
    user_id = event.sender_id
    message_text = event.raw_text.lower().strip('/')

    # Перевірка, чи повідомлення надіслане конкретним користувачем
    if user_id != allowed_chat_id_to_using:
        return  # Ігноруємо повідомлення від інших користувачів

    # Відправка відео на основі ключа
    if message_text in video_mapping:
        file = video_mapping[message_text]

        # Видалення отриманого повідомлення
        await event.delete()

        # Відправка відео як відео повідомлення
        await client.send_file(
            event.chat_id,
            file=file,
            video_note=True,
            mime_type='video/mp4'
        )
        print(f"Video note sent to chat {event.chat_id}!")

async def main():
    # Ініціалізація мапінгу відео
    initialize_video_mapping()
    await client.start(phone)
    print("Bot is running...")

    # Очікування подій
    await client.run_until_disconnected()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
