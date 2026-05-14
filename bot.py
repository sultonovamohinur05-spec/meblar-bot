import telebot
from telebot import types
from google import genai
import json
import re
import time
import os
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

bot = telebot.TeleBot(TOKEN)

# Yangi google.genai kutubxonasi bilan ulanish
client = genai.Client(api_key=GEMINI_API_KEY)

# Soxta mahsulotlar ro'yxati
products = {
    "stul": {"narx": "250,000 so'm", "alternativ": "kreslo"},
    "stol": {"narx": "1,200,000 so'm", "alternativ": "jurnalniy stol"},
    "kreslo": {"narx": "800,000 so'm", "alternativ": "stul"},
    "jurnalniy stol": {"narx": "600,000 so'm", "alternativ": "stol"},
    "yumshoq mebel": {"narx": "4,500,000 so'm", "alternativ": "divan"},
    "divan": {"narx": "3,000,000 so'm", "alternativ": "yumshoq mebel"},
    "aksesuar": {"narx": "50,000 so'm", "alternativ": "boshqa bezaklar"},
    "shkaf": {"narx": "2,500,000 so'm", "alternativ": "komod"},
    "shfaner": {"narx": "2,500,000 so'm", "alternativ": "komod"},
    "komod": {"narx": "1,500,000 so'm", "alternativ": "shkaf"},
    "oyna": {"narx": "400,000 so'm", "alternativ": "trio oyna"},
    "kravat": {"narx": "3,200,000 so'm", "alternativ": "yotoq mebeli"},
    "yotoqxona mebeli": {"narx": "12,000,000 so'm", "alternativ": "kravat va shkaf to'plami"},
    "oshxona mebeli": {"narx": "8,000,000 so'm", "alternativ": "oshxona stoli"},
    "pufik": {"narx": "300,000 so'm", "alternativ": "kichik stul"},
    "gilam": {"narx": "1,000,000 so'm", "alternativ": "palas"},
    "pardalar": {"narx": "800,000 so'm", "alternativ": "jalyuzi"},
    "qandil": {"narx": "1,200,000 so'm", "alternativ": "lyustra"}
}

system_instruction = f"""Sen Xolidaxonsan — mebel va aksessuarlar do'konida ishlaydigan sotuvchi qizsan.

MUHIM QOIDALAR:
1. FAQAT O'ZBEK TILIDA gapir. HECH QACHON inglizcha javob berma.
2. Sodda ko'cha tilida, samimiy gapir. Xuddi bozordagi oddiy sotuvchi qizdek.
3. Javoblaring qisqa bo'lsin — 1-3 gap.
4. "THOUGHT:" yoki boshqa inglizcha so'zlar ISHLATMA.
5. Hech qanday ichki fikr, izoh yoki tushuntirish yozma. Faqat mijozga javob ber.

Senda quyidagi mahsulotlar bor:
{json.dumps(products, ensure_ascii=False, indent=2)}

Qoidalar:
- Mijoz narsa so'rasa, ro'yxatdan tekshir. Bor bo'lsa narxini ayt.
- Yo'q bo'lsa, alternativni taklif qil.
- Mijoz "ha", "olaman", "yaxshi", "ok", "bo'ladi" desa — telefon raqamini so'ra.
- Har doim o'zbekcha gapir!"""

# Chat sessiyalari
chat_sessions = {}
user_states = {}

def get_ai_response(user_id, user_message):
    """Gemini AI dan javob olish"""
    if user_id not in chat_sessions:
        chat_sessions[user_id] = []
    
    # Suhbat tarixiga qo'shish
    chat_sessions[user_id].append({
        "role": "user",
        "parts": [{"text": user_message}]
    })
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=chat_sessions[user_id],
            config={
                "system_instruction": system_instruction,
                "temperature": 0.7,
                "max_output_tokens": 200,
            }
        )
        
        ai_text = response.text.strip()
        
        # "THOUGHT:" kabi inglizcha qismlarni olib tashlash
        lines = ai_text.split('\n')
        clean_lines = []
        for line in lines:
            if not line.strip().upper().startswith('THOUGHT:'):
                clean_lines.append(line)
        ai_text = '\n'.join(clean_lines).strip()
        
        # Javobni tarixga qo'shish
        chat_sessions[user_id].append({
            "role": "model",
            "parts": [{"text": ai_text}]
        })
        
        return ai_text
        
    except Exception as e:
        print(f"AI xatolik: {e}")
        # Tarixdan oxirgi xabarni olib tashlash
        if chat_sessions[user_id]:
            chat_sessions[user_id].pop()
        return None

def fallback_response(text):
    """AI ishlamasa oddiy javob berish"""
    text_lower = text.lower()
    for prod_name, details in products.items():
        if prod_name in text_lower:
            return f"Ha, {prod_name} bor! Narxi {details['narx']}. Olamizmi?"
    
    import random
    alt = random.choice(list(products.keys()))
    return f"Hozir bunaqasi yo'q, lekin {alt} bor ({products[alt]['narx']}). Shu bo'ladimi?"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.chat.id
    # Yangi suhbatni boshlash
    chat_sessions[user_id] = []
    user_states[user_id] = 'chatting'
    
    ai_text = get_ai_response(user_id, "Salom, men keldim")
    if ai_text:
        bot.send_message(user_id, ai_text)
    else:
        bot.send_message(user_id, "Assalomu alaykum! Men Xolidaxonman 👋 Qanday yordam bera olaman? Mebel yoki aksessuar kerakmi?")

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    contact = message.contact
    phone_number = contact.phone_number
    
    bot.send_message(message.chat.id, "Katta rahmat! Tez orada aloqaga chiqamiz, kuting 📞", reply_markup=types.ReplyKeyboardRemove())
    
    admin_msg = f"🔔 Yangi xarid/so'rov!\n\nXaridor: {message.from_user.first_name}\nTelefon: {phone_number}"
    try:
        bot.send_message(ADMIN_ID, admin_msg)
    except Exception as e:
        print(e)
        
    user_states[message.chat.id] = 'chatting'

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.chat.id
    
    # Telefon raqam yuborgan bo'lsa
    if re.search(r'\+?[0-9]{9,13}', message.text):
        bot.send_message(user_id, "Katta rahmat! Tez orada aloqaga chiqamiz, kuting 📞", reply_markup=types.ReplyKeyboardRemove())
        admin_msg = f"🔔 Yangi xarid/so'rov!\n\nXaridor: {message.from_user.first_name}\nTelefon: {message.text}"
        try:
            bot.send_message(ADMIN_ID, admin_msg)
        except:
            pass
        return

    # AI dan javob olish
    ai_text = get_ai_response(user_id, message.text)
    
    if not ai_text:
        ai_text = fallback_response(message.text)
    
    # Agar raqam so'rayotgan bo'lsa, tugma chiqarish
    reply_markup = None
    if any(word in ai_text.lower() for word in ['nomer', 'raqam', 'telefon', 'tashlab', 'yuboring']):
        reply_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        btn = types.KeyboardButton("Telefon raqamni yuborish 📱", request_contact=True)
        reply_markup.add(btn)
        
    bot.send_message(user_id, ai_text, reply_markup=reply_markup)

print("Bot ishga tushdi...")
bot.polling(none_stop=True)
