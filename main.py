import os
import json
import requests
import telebot
import youtube_dl
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor


load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
YOU_TUBE_KEY = os.getenv("YOU_TUBE_KEY")
bot = telebot.TeleBot(TELEGRAM_TOKEN)
executor = ThreadPoolExecutor(max_workers=5)


@bot.message_handler(commands=['start', 'начать'])
def start_command(message):
    bot.send_message(message.chat.id, "Привет! Напиши название музыки которую хочешь найти.")


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    audio_file = download_audio(call.data)
    if audio_file is not None:
        with open(audio_file, 'rb') as audio_file:
            info_dict = get_video_info(call.data)
            title = info_dict.get('title')
            bot.send_audio(call.message.chat.id, audio_file, title=title)
        os.remove(audio_file.name)
    else:
        bot.send_message(call.message.chat.id, f"Аудио не найдено.")


def download_audio(song_url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'music.mp3',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'age_limit': 18,
        'quiet': True,
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(song_url, download=False)
        duration = info_dict.get('duration')
        if duration is None or duration < 60 or duration > 600:
            return None
        ydl.download([song_url])
    return 'music.mp3'


def get_video_info(video_url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'writeinfojson': True,
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(video_url, download=False)
    return info_dict


def search_and_send_audio(chat_id, query):
    try:
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&type=video&key={YOU_TUBE_KEY}"
        response = requests.get(url)
        data = json.loads(response.text)

        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        songs = [data['items'][i] for i in range(5) if i < len(data['items'])]
        buttons = ([telebot.types.InlineKeyboardButton(
            text=song['snippet']['title'],
            callback_data=f"https://www.youtube.com/watch?v={song['id']['videoId']}") for song in songs]
            )
        markup.add(*buttons)
        bot.send_message(chat_id, "Выберите музыку:", reply_markup=markup)
    except requests.exceptions.RequestException as e:
        bot.send_message(chat_id, f"Произошла ошибка при поиске музыки: {e}. Попробуйте позже.")


@bot.message_handler(content_types=['text'])
def music_request(message):
    try:
        query = message.text.replace(' ', '+')
        executor.submit(search_and_send_audio, message.chat.id, query)
        bot.send_message(message.chat.id, "Поиск музыки начался, пожалуйста, подождите несколько секунд.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка при поиске музыки: {e}. Попробуйте позже.")


bot.polling(none_stop=True)
