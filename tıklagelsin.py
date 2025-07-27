import requests
import uuid
import time
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from flask import Flask
from threading import Thread
from apscheduler.schedulers.background import BackgroundScheduler

# Sabitler
TOKEN = "8273999259:AAHZzcTlctE3FiahDsLP1IFQU8moB-5XnAU"
ADMIN_ID = 7137081566
AUTHORIZED_USERS = {ADMIN_ID}
MAX_COUPONS = 20

URL = "https://tiklagelsin.game.api.zuzzuu.com/request_from_game/event_create/Mz2Ex38cykBsH6GjhpZ5fX7KJdSaet4nLFDAWQ9U"
HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://tiklagelsin.game.core.tiklaeslestir.zuzzuu.com",
    "X-Requested-With": "com.ataexpress.tiklagelsin",
    "User-Agent": "Mozilla/5.0 (Linux; Android 9...)",
    "Accept": "*/*"
}

# Saat kontrol fonksiyonu
def saat_uygun_mu():
    simdi = datetime.now().time()
    return simdi >= datetime.strptime("08:00", "%H:%M").time() and simdi <= datetime.strptime("23:59", "%H:%M").time()

# Flask (Railway'de kapanmasın diye)
app_web = Flask('')

@app_web.route('/')
def home():
    return "Bot aktif 🎯"

def run():
    app_web.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Kupon alma
async def kupon_al(sayi: int):
    kazanilan = 0
    kuponlar = []

    while kazanilan < sayi:
        payload = {
            "game_name": "tikla-eslestir",
            "event_name": "oyun_tamamlandi",
            "user_id": str(uuid.uuid4())
        }
        try:
            resp = requests.post(URL, headers=HEADERS, json=payload, timeout=5)
            data = resp.json()
        except Exception:
            continue

        reward_info = data.get("reward_info", {})
        if reward_info.get("status"):
            reward = reward_info.get("reward", {})
            kampanya = reward.get("campaign_name", "Kampanya adı yok")
            kod = reward.get("coupon_code", "Kod yok")
            kuponlar.append((kampanya, kod))
            kazanilan += 1

        time.sleep(0.2)

    return kuponlar

# Günlük saat 12:00 otomatik gönderim
async def gunluk_kupon_gonder():
    kuponlar = await kupon_al(5)
    if not kuponlar:
        return

    mesajlar = []
    for kampanya, kod in kuponlar:
        mesajlar.append(
            f"🎉 Yeni Kupon Kazandın!\n"
            f"📦 Kampanya: {kampanya}\n"
            f"🎟️ Kupon: <code>{kod}</code>"
        )

    mesaj = "\n\n──────────────\n\n".join(mesajlar)

    for user_id in AUTHORIZED_USERS:
        try:
            await app.bot.send_message(chat_id=user_id, text=mesaj, parse_mode="HTML")
        except Exception as e:
            print(f"❗ Kupon gönderilemedi → {user_id}: {e}")

# /kupon komutu
async def kupon_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    chat_id = update.effective_chat.id

    if not saat_uygun_mu():
        await context.bot.send_message(chat_id=chat_id, text="⏰ Bu bot sadece 08:00 - 00:00 saatleri arasında çalışır.")
        return

    if user_id not in AUTHORIZED_USERS:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"❗ <b>Yeni Yetkisiz Kullanım</b>\n\n"
                f"👤 <b>Kullanıcı:</b> @{user.username or user.first_name}\n"
                f"🆔 <b>ID:</b> <code>{user_id}</code>\n\n"
                f"🛠️ Yetki vermek için:\n<code>/yetki {user_id}</code>"
            ),
            parse_mode="HTML"
        )
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Bu botu kullanmaya yetkiniz yok. Yöneticiye bildirildiniz."
        )
        return

    if not context.args:
        sayi = 5
    else:
        try:
            sayi = int(context.args[0])
        except ValueError:
            await context.bot.send_message(chat_id=chat_id, text="Geçerli bir sayı girin: /kupon 5")
            return

    if sayi < 1 or sayi > MAX_COUPONS:
        await context.bot.send_message(chat_id=chat_id, text=f"Lütfen 1 ile {MAX_COUPONS} arasında bir sayı girin.")
        return

    await context.bot.send_message(chat_id=chat_id, text=f"🎯 {sayi} kupon alınıyor, lütfen bekleyin...")

    kuponlar = await kupon_al(sayi)

    if not kuponlar:
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Kupon alınamadı. Lütfen tekrar deneyin.")
        return

    mesajlar = []
    for kampanya, kod in kuponlar:
        mesajlar.append(
            f"🎉 Yeni Kupon Kazandın!\n"
            f"📦 Kampanya: {kampanya}\n"
            f"🎟️ Kupon: <code>{kod}</code>"
        )

    mesaj = "\n\n──────────────\n\n".join(mesajlar)
    await context.bot.send_message(chat_id=chat_id, text=mesaj, parse_mode="HTML")

# /yetki komutu
async def yetki_ver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Kullanıcı ID girin: /yetki 12345678")
        return

    try:
        user_id = int(context.args[0])
        AUTHORIZED_USERS.add(user_id)
        await update.message.reply_text(f"✅ Kullanıcı {user_id} yetkilendirildi.")
    except ValueError:
        await update.message.reply_text("Geçersiz kullanıcı ID.")

# /start komutu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in AUTHORIZED_USERS:
        await update.message.reply_text("👋 Merhaba! Kupon almak için /kupon 5 gibi bir komut yazabilirsin.")
    else:
        await update.message.reply_text("⚠️ Bu botu kullanmaya yetkiniz yok. Yetkiliye bildirildiniz.")

# /kupon dışında yazılan her şey
async def bilgilendirme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not saat_uygun_mu():
        return

    await update.message.reply_text(
        "ℹ️ Lütfen aşağıdaki şekilde komut kullanın:\n\n"
        "🔹 /kupon → Otomatik olarak 5 kupon gönderir\n"
        "🔹 /kupon 6 → Belirttiğiniz sayı kadar kupon gönderir (en fazla 20)\n\n"
        "📌 Kuponlar her gün saat 12:00'de otomatik olarak gönderilir.\n"
        "❗ Diğer mesajlara yanıt verilmez.",
        parse_mode="HTML"
    )

# Çalıştırıcı
if __name__ == '__main__':
    keep_alive()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("yetki", yetki_ver))
    app.add_handler(CommandHandler("kupon", kupon_komutu))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), bilgilendirme))

    scheduler = BackgroundScheduler(timezone="Europe/Istanbul")
    scheduler.add_job(lambda: app.create_task(gunluk_kupon_gonder()), 'cron', hour=12, minute=0)
    scheduler.start()

    print("✅ Bot çalışıyor ve saat kontrolü aktif...")
    app.run_polling()
