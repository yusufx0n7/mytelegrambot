import asyncio
import aiohttp
import time
import logging
import json
import os
import math
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- Konfiguratsiyalar ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# TOKEN va CHAT_ID (Bularni o'zingizning token va chat IDlaringiz bilan almashtiring)
TELEGRAM_TOKEN = '7780864447:AAESpcIqmzNkN1CiyLM1WfRkzPMWPeq7dzU' # Bot tokeningizni shu yerga qo'ying
# CHAT_IDS ni tekshiring! Guruh ID lari odatda '-' bilan boshlanadi.
CHAT_IDS = ['7971306481', '6329050233'] # CHAT ID LARINGIZNI KIRITING! (Agar guruhga yuborsangiz, - ni unutmang)

# CoinGecko pullik API kaliti (agar mavjud bo'lsa)
# COINGECKO_API_KEY = 'YOUR_COINGECKO_API_KEY_HERE'

MIN_VOLUME = 10000
MIN_PROFIT = 3
CHECKABLE_MIN = 1
CHECKABLE_MAX = 3
INVEST_AMOUNT = 200

# Yangi konfiguratsiyalar
COINS_PER_MINUTE = 25 # Bir partiyada tekshiriladigan koinlar soni
PAUSE_AFTER_BATCH_SECONDS = 60 # Har bir partiyadan keyin kutish vaqti (soniya)

# CoinGecko bepul API uchun taxminiy minimal so'rovlar oralig'i (daqiqada 50-100 so'rov degan taxmin bilan)
# Endi bu qiymat faqat bitta so'rov uchun minimal kechikishni belgilaydi
COINGECKO_REQUEST_LIMIT_PER_MINUTE = 50 # CoinGecko bepul versiyasi uchun taxminiy limit
COINGECKO_DELAY_PER_REQUEST = 60 / COINGECKO_REQUEST_LIMIT_PER_MINUTE # 1.2 soniya/so'rov

# Birjalarni guruhlash
API_DIRECT_EXCHANGES = {
    'Binance', 'CoinEx', 'AscendEX', 'HTX', 'Bitget',
    'Poloniex', 'BitMart', 'Bitrue', 'BingX', 'MEXC', 'DigiFinex'
}

COINGECKO_ONLY_EXCHANGES = {
    'SuperEx', 'CoinCola', 'Ourbit', 'Toobit', 'BloFin', 'BDFI',
    'BYDFi', 'CoinW', 'BTCC', 'WEEX', 'LBank', 'GMGN', 'KCEX',
    'Kraken' # Kraken endi CoinGecko orqali olinadi
}

# Barcha birjalar ro'yxati (yangi tizimga mos ravishda)
ALLOWED_EXCHANGES = API_DIRECT_EXCHANGES.union(COINGECKO_ONLY_EXCHANGES)


# Kuzatiladigan koinlar (Nomlari) - Siz bergan ro'yxat
# Sizning talabingizga binoan INITIAL_COIN_NAMES ro'yxati yangilandi
INITIAL_COIN_NAMES = [
    "Zeebu", "Fasttoken", "LayerZero", "IPVERSE", "Zignaly", "VeThor Token",
    "Orbler", "Boba Network", "CyberBots AI", "Helium Mobile", "Nosana",
    "Hivemapper", "World Mobile Token", "Shadow Token", "NYM", "Pocket Network",
    "CUDOS", "OctaSpace", "Coinweb", "Gaimin", "Aleph.im", "IAGON",
    "KYVE Network", "XRADERS", "Delysium", "Ozone Chain", "Oraichain",
    "Artificial Liquid Intelligence", "Forta", "PlatON", "Agoras: Currency of Tau",
    "Victoria VR", "Dimitra", "Moca Coin", "dKargo", "Commune AI",
    "Hacken Token", "Numbers Protocol", "Sentinel Protocol", "UXLINK",
    "Data Ownership Protocol", "Avive World", "Aurora", "NuNet", "iMe Lab",
    "Cere Network", "NeyroAI", "GT Protocol", "FROKAI", "HyperGPT", "PARSIQ",
    "Vectorspace AI", "Degen", "Koinos", "Synesis One", "Lumerin", "QnA3.AI",
    "Xelis", "DDMTOWN", "DeepBrain Chain", "Nuco.cloud", "Waves Enterprise",
    "Eclipse", "GamerCoin", "Optimus AI", "Ta-da", "TRVL", "Big Data Protocol",
    "Bad Idea AI", "Phantasma", "bitsCrunch", "PIBBLE", "Robonomics.network",
    "Swash", "Lambda", "MATH", "SubQuery Network", "Lithium", "Lossless",
    "Bridge Oracle", "Avail", "Mande Network", "Crypto-AI-Robo.com", "Metahero",
    "Netvrk", "Smart Layer Network", "Effect AI", "Chirpley", "Ispolink",
    "Edge Matrix Computing", "Dock", "PureFi Protocol", "GNY", "DxChain Token"
]

# Global o'zgaruvchilar
global_http_session: aiohttp.ClientSession = None
coin_info_map = {} # Koin nomlarini ID va simvollarga xaritalash {lower_name: {id: ..., symbol: ...}, lower_symbol: {id: ..., symbol: ...}}
EFFECTIVE_COIN_IDS = []  # Faqat IDsi topilgan koinlar
# COIN_BATCHES va current_batch_index endi monitor_loop ichida boshqariladi


COINS_LIST_FILE = 'coingecko_coins_list.json' # Koinlar ro'yxati saqlanadigan fayd

# --- Yordamchi funksiyalar ---
async def send_telegram_message(text: str):
    """Telegramga xabar yuborish"""
    if not global_http_session:
        logger.error("Aiohttp session hali yaratilmagan!")
        return

    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'

    for chat_id in CHAT_IDS:
        payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': True}
        try:
            async with global_http_session.post(url, json=payload, timeout=10) as resp:
                if resp.status != 200:
                    logger.warning(f"Telegramga xabar yuborishda xato. Status: {resp.status}, Javob: {await resp.text()}")
                    if "chat not found" in await resp.text():
                        logger.error(f"❌ Xatolik: CHAT_ID {chat_id} topilmadi. Iltimos, CHAT_IDS ni to'g'ri kiriting.")
                else:
                    logger.info(f"Xabar {chat_id} ga muvaffaqiyatli yuborildi.")
        except asyncio.TimeoutError:
            logger.error(f"Telegramga xabar yuborishda timeout ({chat_id}).")
        except aiohttp.ClientError as e:
            logger.error(f"Telegramga xabar yuborishda tarmoq xatosi ({chat_id}): {e}")
        except Exception as e:
            logger.error(f"Telegramga xabar yuborishda kutilmagan xato ({chat_id}): {e}")

# Kesh mexanizmi
COIN_DATA_CACHE = {}
CACHE_EXPIRATION_SECONDS = 60 # Keshda saqlash vaqti kamaytirildi, tezroq yangilanish uchun

async def fetch_coingecko_tickers_data(session: aiohttp.ClientSession, coin_id: str, force_refresh: bool = False) -> dict:
    """
    CoinGecko API dan 'coins/{id}/tickers' endpointi orqali ma'lumotlarni olish.
    """
    current_time = time.time()
    if not force_refresh and coin_id in COIN_DATA_CACHE and \
       (current_time - COIN_DATA_CACHE[coin_id]['timestamp'] < CACHE_EXPIRATION_SECONDS):
        logger.debug(f"Keshdan yuklanmoqda (CoinGecko): {coin_id}")
        return COIN_DATA_CACHE[coin_id]['data']

    url = f'https://api.coingecko.com/api/v3/coins/{coin_id}/tickers'
    # if hasattr(__main__, 'COINGECKO_API_KEY') and COINGECKO_API_KEY:
    #     url = f'https://api.coingecko.com/api/v3/coins/{coin_id}/tickers?x_cg_pro_api_key={COINGECKO_API_KEY}'

    try:
        async with session.get(url, timeout=10) as resp:
            if resp.status == 200:
                data = await resp.json()
                COIN_DATA_CACHE[coin_id] = {'data': data, 'timestamp': current_time}
                return data
            elif resp.status == 429: # Too Many Requests
                logger.warning(f"CoinGecko API limitiga yetildi (tickers endpoint - {coin_id}). Avtomatik kutish...")
                retry_after = int(resp.headers.get('Retry-After', '60'))
                await asyncio.sleep(retry_after + 1)
                return {"tickers": []}
            else:
                logger.warning(f"CoinGecko API so'rovida xato ({coin_id}). Status: {resp.status}, Javob: {await resp.text()}")
                return {"tickers": []}
    except asyncio.TimeoutError:
        logger.error(f"CoinGecko API so'rovida timeout ({coin_id}).")
        return {"tickers": []}
    except aiohttp.ClientError as e:
        logger.error(f"CoinGecko API so'rovida tarmoq xatosi ({coin_id}): {e}")
        return {"tickers": []}
    except Exception as e:
        logger.error(f"CoinGecko API so'rovida kutilmagan xato ({coin_id}): {e}", exc_info=True)
        return {"tickers": []}

# --- Yangi: Har bir API ochiq birja uchun ma'lumot olish funksiyalari ---
# BU YERDAGI FUNKSIYALARNI HAR BIR BIRJA UCHUN TO'LIQ YOZIB CHIQISHINGIZ KERAK!
# Faqat Binance namuna sifatida qoldirildi.
# Kraken endi CoinGecko orqali olinadi.

async def fetch_binance_tickers(session: aiohttp.ClientSession, coin_symbol: str) -> list:
    """Binance API'dan ma'lumot olish"""
    # coin_symbol USD bilan birga, masalan, BTCUSDT
    pair = f"{coin_symbol}USDT"
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={pair}"
    try:
        async with session.get(url, timeout=5) as resp:
            if resp.status == 200:
                data = await resp.json()
                # Binance API da 'symbol' topilmasa xato qaytaradi.
                # Agar symbol topilmasa, bu yerda xatolik bo'lmaydi, shunchaki empty list qaytadi.
                if "symbol" in data and "lastPrice" in data and "volume" in data:
                    return [{
                        "market": {"name": "Binance"},
                        "target": "USDT",
                        "last": float(data["lastPrice"]),
                        "volume": float(data["volume"]),
                        "converted_volume": {"usd": float(data["quoteVolume"])} # USDT hajmi
                    }]
                else:
                    logger.debug(f"Binance API javobida kerakli kalitlar topilmadi ({pair}). Javob: {data}")
            elif resp.status == 400: # Agar juftlik mavjud bo'lmasa
                logger.debug(f"Binance API: {pair} juftligi topilmadi. Status: {resp.status}, Javob: {await resp.text()}")
            else:
                logger.warning(f"Binance API xatosi ({pair}). Status: {resp.status}, Javob: {await resp.text()}")
    except Exception as e:
        logger.error(f"Binance API chaqiruvida kutilmagan xato ({pair}): {e}", exc_info=True)
    return []

# fetch_kraken_tickers funksiyasi olib tashlandi.
# QOLGAN API OCHIQ BIRJA UCHUN XUDDI SHUNDAY FUNKSIYALARNI YOZISH KERAK:
# fetch_coinex_tickers, fetch_ascendex_tickers, fetch_htx_tickers, fetch_bitget_tickers,
# fetch_poloniex_tickers, fetch_bitmart_tickers, fetch_bitrue_tickers, fetch_bingx_tickers,
# fetch_mexc_tickers, fetch_digifinex_tickers

# Har bir funksiya quyidagi formatdagi listni qaytarishi kerak:
# [{ "market": {"name": "Birja Nomi"}, "target": "USDT", "last": narx, "volume": koin_hajmi, "converted_volume": {"usd": usd_hajmi} }]
# volume: Bu o'sha coin_symbol dagi hajm (masalan, BTC/USDT uchun 10 BTC bo'lsa, 10).
# converted_volume.usd: Bu USD (yoki USDT) dagi savdo hajmi (masalan, BTC/USDT uchun 10 BTC * $60000 = $600000).


async def analyze_arbitrage_opportunity(session: aiohttp.ClientSession, coin_id: str, check_mode: bool = False):
    """
    Berilgan koin uchun arbitraj imkoniyatini tahlil qilish.
    Endi bir nechta manbadan ma'lumot yig'iladi.
    """
    all_tickers = []
    
    # Koin simvolini topish
    coin_symbol = ""
    for key, info in coin_info_map.items():
        if info.get('id') == coin_id:
            if info.get('symbol'):
                coin_symbol = info['symbol'].upper()
            break
    if not coin_symbol:
        coin_symbol = coin_id.split('-')[0].upper() # Agar topilmasa, ID ning birinchi qismidan simvol yasashga urinish

    # 1. To'g'ridan-to'g'ri API orqali ma'lumot olish (API_DIRECT_EXCHANGES)
    direct_api_tasks = []
    
    if "Binance" in API_DIRECT_EXCHANGES:
        direct_api_tasks.append(fetch_binance_tickers(session, coin_symbol))
    # if "CoinEx" in API_DIRECT_EXCHANGES:
    #     direct_api_tasks.append(fetch_coinex_tickers(session, coin_symbol))
    # ... va hokazo

    if direct_api_tasks: # Agar tasklar mavjud bo'lsa
        direct_api_results = await asyncio.gather(*direct_api_tasks)
        for result_list in direct_api_results:
            all_tickers.extend(result_list)


    # 2. CoinGecko orqali ma'lumot olish (COINGECKO_ONLY_EXCHANGES)
    # CoinGecko'dan olingan barcha tickerlar ichidan faqat COINGECKO_ONLY_EXCHANGES dagi birjalar filterlanadi
    coingecko_data = await fetch_coingecko_tickers_data(session, coin_id)
    if coingecko_data and "tickers" in coingecko_data:
        coingecko_tickers = [
            t for t in coingecko_data["tickers"]
            if t.get("market", {}).get("name") in COINGECKO_ONLY_EXCHANGES
            and t.get("target") == "USDT" # Faqat USDT juftliklari
            and t.get("last") is not None and t.get("last") > 0 # Narx mavjud va noldan katta
            and t.get("converted_volume", {}).get("usd", 0) >= MIN_VOLUME # CoinGecko uchun hajm filtri
        ]
        all_tickers.extend(coingecko_tickers)


    # Barcha manbalardan olingan tickerlarni birlashtirib tahlil qilish
    # Filter tickers based on minimum volume (for ALL tickers, whether from direct API or CoinGecko)
    filtered_tickers = [
        ticker for ticker in all_tickers
        if ticker.get("converted_volume", {}).get("usd", 0) >= MIN_VOLUME
    ]

    if len(filtered_tickers) < 2:
        return

    # Eng arzon sotib olish va eng qimmat sotish narxini topish
    buy = min(filtered_tickers, key=lambda x: x["last"])
    sell = max(filtered_tickers, key=lambda x: x["last"])

    buy_price = buy["last"]
    sell_price = sell["last"]

    buy_volume_usd = buy.get("converted_volume", {}).get("usd", 0)
    sell_volume_usd = sell.get("converted_volume", {}).get("usd", 0)

    # Agar 'converted_volume' yo'q bo'lsa yoki 0 bo'lsa, 'volume' va 'last' narxdan hisoblash
    # Bu shart 'fetch_XXX_tickers' funksiyalaringiz 'converted_volume'ni to'g'ri qaytarmagan holatlar uchun.
    # Ideal holda, har bir fetch funksiyasi converted_volume ni to'g'ri hisoblashi kerak.
    if buy_volume_usd == 0 and buy.get('volume') is not None and buy_price > 0:
        buy_volume_usd = buy['volume'] * buy_price

    if sell_volume_usd == 0 and sell.get('volume') is not None and sell_price > 0:
        sell_volume_usd = sell['volume'] * sell_price

    volume = min(buy_volume_usd, sell_volume_usd) # Arbitraj uchun eng kam hajm

    if volume < MIN_VOLUME:
        logger.debug(f"Hajm yetarli emas: {coin_id} - {volume:.0f} < {MIN_VOLUME}")
        return

    # Foyda hisoblashda 0 ga bo'lish xatosidan saqlanish
    if buy_price <= 0:
        logger.warning(f"Sotib olish narxi nol yoki manfiy ({buy_price}) bo'lgani sababli arbitraj hisoblanmadi: {coin_id}")
        return

    quantity = INVEST_AMOUNT / buy_price
    gross = quantity * sell_price
    net = gross - INVEST_AMOUNT
    roi = (net / INVEST_AMOUNT) * 100

    if roi >= 20: # Juda yuqori ROI odatda ma'lumot xatosi ekanligini anglatadi
        logger.warning(f"Juda yuqori ROI topildi ({roi:.2f}%): {coin_id}. Yuborilmaydi (ma'lumot xatosi bo'lishi mumkin).")
        return

    if roi >= MIN_PROFIT and not check_mode:
        message = (
            f"🎉📈 **Qaynoq Arbitraj Imkoniyati Topildi!** 📈🎉\n\n"
            f"💰 **Koin:** {coin_id.replace('-', ' ').title()} ({coin_symbol})\n"
            f"🔥 **Hajm (USD):** {volume:,.0f} USDT\n\n"
            f"⬇️ **Sotib olish:** {buy_price:.4f} @ **{buy['market']['name']}**\n"
            f"⬆️ **Sotish:** {sell_price:.4f} @ **{sell['market']['name']}**\n\n"
            f"💸 **Sof Foyda:** {net:.2f} USD\n"
            f"🚀 **ROI (Daromad):** {roi:.2f}%"
        )
        await send_telegram_message(message)
        logger.info(f"Arbitraj imkoniyati topildi va xabar yuborildi: {coin_id} ({coin_symbol}), ROI: {roi:.2f}%")

    elif check_mode and CHECKABLE_MIN <= roi < CHECKABLE_MAX:
        message = (
            f"🔎 **Tekshiruv Natijasi:** {coin_id.replace('-', ' ').title()} ({coin_symbol})\n\n"
            f"⬇️ **Sotib olish:** {buy_price:.4f} @ **{buy['market']['name']}**\n"
            f"⬆️ **Sotish:** {sell_price:.4f} @ **{sell['market']['name']}**\n"
            f"🚀 **ROI (Daromad):** {roi:.2f}%"
        )
        try:
            await send_telegram_message(message)
            logger.info(f"Tekshiruv xabari yuborildi: {coin_id} ({coin_symbol}), ROI: {roi:.2f}%")
        except Exception as e:
            logger.error(f"⚠️ Arbitraj tahlilida kutilmagan xato ({coin_id}): {e}", exc_info=True)


async def get_or_load_coin_list(session: aiohttp.ClientSession):
    """
    CoinGecko'dan koinlar ro'yxatini yuklaydi yoki fayldan o'qiydi.
    Faqat bir marta, bot ishga tushganda chaqirilishi kerak.
    """
    if os.path.exists(COINS_LIST_FILE):
        logger.info(f"'{COINS_LIST_FILE}' faylidan koinlar ro'yxati yuklanmoqda. 🔄")
        with open(COINS_LIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        logger.info("CoinGecko API dan koinlar ro'yxati olinmoqda (birinchi marta). 🌐")
        url = "https://api.coingecko.com/api/v3/coins/list"
        try:
            async with session.get(url, timeout=30) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    with open(COINS_LIST_FILE, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)
                    logger.info(f"Koinlar ro'yxati '{COINS_LIST_FILE}' fayliga saqlandi. ✅")
                    return data
                else:
                    logger.error(f"Coin list olishda xato. Status: {resp.status}, Javob: {await resp.text()} ❌")
                    return []
        except Exception as e:
            logger.error(f"Coin list olishda kutilmagan xato: {e} ⛔")
            return []

async def init_coin_ids():
    """Bot ishga tushganda koin nomlarini IDlarga va simvollarga tarjima qilish"""
    global coin_info_map, EFFECTIVE_COIN_IDS

    full_coin_list = await get_or_load_coin_list(global_http_session)
    for coin_entry in full_coin_list:
        # Nom bo'yicha xaritalash
        coin_info_map[coin_entry['name'].lower()] = {
            'id': coin_entry['id'],
            'symbol': coin_entry.get('symbol', '').upper()
        }
        # Simvol bo'yicha xaritalash
        if coin_entry.get('symbol'):
            symbol_lower = coin_entry['symbol'].lower()
            if symbol_lower not in coin_info_map or coin_info_map[symbol_lower]['id'] != coin_entry['id']:
                coin_info_map[symbol_lower] = {
                    'id': coin_entry['id'],
                    'symbol': coin_entry['symbol'].upper()
                }

    found_count = 0
    not_found_names = []
    for name_or_symbol in INITIAL_COIN_NAMES:
        coin_data = coin_info_map.get(name_or_symbol.lower())
        if coin_data:
            coin_id = coin_data['id']
            if coin_id not in EFFECTIVE_COIN_IDS:
                EFFECTIVE_COIN_IDS.append(coin_id)
                found_count += 1
        else:
            not_found_names.append(name_or_symbol)

    logger.info(f"Topilgan koin IDlari soni: {found_count} / {len(INITIAL_COIN_NAMES)} 🎯")
    if not_found_names:
        logger.warning(f"CoinGecko'da topilmagan koin nomlari/simvollari: {', '.join(not_found_names[:10])}{'...' if len(not_found_names) > 10 else ''} ⚠️")

    if not EFFECTIVE_COIN_IDS:
        logger.error("Koin IDlari topilmadi, monitoring boshlanmaydi. ⛔")


async def monitor_loop():
    """
    Asosiy monitoring tsikli - koinlarni kichik partiyalarga bo'lib, har bir partiyadan keyin dam olib tekshirish.
    """
    global EFFECTIVE_COIN_IDS

    while not EFFECTIVE_COIN_IDS:
        logger.info("Koinlar ro'yxati yuklanishini kutilmoqda... ⏳")
        await asyncio.sleep(5)
        if not EFFECTIVE_COIN_IDS:
            await init_coin_ids() # Agar hali yuklanmagan bo'lsa, qayta urinish

    logger.info(f"Koinlarni {COINS_PER_MINUTE} tadan partiyalarga bo'lib tekshirish boshlandi. Har {PAUSE_AFTER_BATCH_SECONDS} soniyada dam olinadi. ✨")

    while True:
        # Koinlar ro'yxatini aralashtirish, har safar har xil koinlar birinchi bo'lishi uchun
        # random.shuffle(EFFECTIVE_COIN_IDS) # Bu yerga random import qilish kerak bo'ladi, agar kerak bo'lsa

        total_coins = len(EFFECTIVE_COIN_IDS)
        current_coin_index = 0
        cycle_start_time = time.time()

        while current_coin_index < total_coins:
            batch_start_index = current_coin_index
            batch_end_index = min(current_coin_index + COINS_PER_MINUTE, total_coins)
            current_batch_ids = EFFECTIVE_COIN_IDS[batch_start_index:batch_end_index]

            if not current_batch_ids:
                break # Agar bo'sh partiya bo'lsa, tsikldan chiqish

            logger.info(f"🔍 Partiyani skanerlash boshlandi ({batch_start_index + 1}-{batch_end_index}/{total_coins} koin).")
            
            batch_scan_start_time = time.time()
            tasks = []
            for coin_id in current_batch_ids:
                tasks.append(analyze_arbitrage_opportunity(global_http_session, coin_id))

            if tasks:
                await asyncio.gather(*tasks)
            
            elapsed_time_for_batch = time.time() - batch_scan_start_time
            logger.info(f"✅ Bu partiyadagi {len(current_batch_ids)} ta koin tekshirildi. Davomiyligi: {elapsed_time_for_batch:.2f} soniya.")

            current_coin_index = batch_end_index

            if current_coin_index < total_coins: # Agar oxirgi partiya bo'lmasa, dam olish
                logger.info(f"😴 {PAUSE_AFTER_BATCH_SECONDS} soniya dam olinmoqda...")
                await asyncio.sleep(PAUSE_AFTER_BATCH_SECONDS)

        elapsed_cycle_time = time.time() - cycle_start_time
        logger.info(f"🚀 To'liq aylanish yakunlandi. Umumiy davomiyligi: {elapsed_cycle_time:.2f} soniya. Yangi tsikl boshlanadi. 🎉")
        # Butun ro'yxatni tekshirib bo'lgandan keyin qayta boshlash uchun hech qanday qo'shimcha kutish shart emas.
        # monitor_loop() funksiyasi "while True" ichida, shuning uchun u avtomatik ravishda yangi tsiklni boshlaydi.

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start komandasi"""
    await update.message.reply_html(
        "👋 **Assalomu alaykum, Arbitraj Botiga xush kelibsiz!**\n\n"
        "Men 24/7 rejimida bozorlarni kuzatib, siz uchun eng yaxshi arbitraj imkoniyatlarini izlayman. "
        "Har bir topilgan imkoniyat haqida sizga darhol xabar beraman!\n\n"
        "👉 `/check` - Hozirgi arbitraj holatini tekshirish uchun ushbu buyruqdan foydalaning. 📊"
    )
    logger.info(f"'{update.effective_user.full_name}' (/start) buyrug'ini ishlatdi. ▶️")

async def check_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/check komandasi"""
    await update.message.reply_text("🔍 Tekshiruv boshlandi... Biroz kuting. Natijalar alohida xabar sifatida yuboriladi (agar topilsa). ⏳")
    logger.info(f"'{update.effective_user.full_name}' (/check) buyrug'ini ishlatdi. ✅")

    if not EFFECTIVE_COIN_IDS:
        await update.message.reply_text("Koinlar ro'yxati hali yuklanmadi yoki bo'sh. Bir ozdan so'ng qayta urinib ko'ring. 😔")
        logger.warning("Check buyrug'i berilganda koinlar ro'yxati bo'sh. ⚠️")
        return

    tasks = []
    # /check buyrug'i uchun barcha koinlarni emas, balki birinchi 50 tasini tekshirish.
    # Agar 50 tadan kam koin bo'lsa, barchasini tekshiradi.
    COINS_TO_CHECK_FOR_COMMAND = min(50, len(EFFECTIVE_COIN_IDS)) 

    checked_count = 0
    start_check_time = time.time()
    for coin_id in EFFECTIVE_COIN_IDS:
        if checked_count >= COINS_TO_CHECK_FOR_COMMAND:
            break

        tasks.append(analyze_arbitrage_opportunity(global_http_session, coin_id, check_mode=True))
        checked_count += 1

    if tasks:
        await asyncio.gather(*tasks)
        elapsed_time = time.time() - start_check_time
        # Bu yerda ham API limitini hisobga olish
        if elapsed_time < COINGECKO_DELAY_PER_REQUEST * checked_count:
            wait_time = (COINGECKO_DELAY_PER_REQUEST * checked_count) - elapsed_time
            logger.debug(f"Check buyrug'i uchun CoinGecko API limiti bo'yicha {wait_time:.2f} soniya kutish.")
            await asyncio.sleep(max(0, wait_time))


    await update.message.reply_text("✅ Tekshiruv yakunlandi! Natijalar yuqoridagi xabarlarda yuborilgan bo'lishi mumkin. 🎉")
    logger.info("Tekshiruv yakunlandi. 👍")

async def start_bot():
    """Botni ishga tushirish va asosiy tsiklni boshlash"""
    global global_http_session
    global_http_session = aiohttp.ClientSession() # Session bu yerda ochiladi

    try:
        await init_coin_ids() # Koinlar ro'yxatini yuklash

        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

        app.add_handler(CommandHandler("start", start_handler))
        app.add_handler(CommandHandler("check", check_handler))

        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        logger.info("Telegram bot ishga tushirildi. 🟢")

        # Monitoring loopini alohida task sifatida ishga tushirish
        asyncio.create_task(monitor_loop())

        # Bot ishlashi uchun asosiy event loopni bloklamasdan kutish
        while True:
            await asyncio.sleep(3600) # Har soatda uxlab turadi, bu botni aktiv holda ushlab turadi

    except Exception as e:
        logger.critical(f"❌ Botning ishga tushishida yoki ishlashi davomida halokatli xato: {e}", exc_info=True)
        raise # Xatoni yuqoriga (main() ga) uzatish
    finally:
        if global_http_session and not global_http_session.closed:
            await global_http_session.close()
            logger.info("Aiohttp session yopildi. 🔴")
        logger.info("Telegram bot o'chirildi. 🛑")


async def main():
    """Asosiy funksiya: botni qayta-qayta ishga tushiradi (agar xato bo'lsa)"""
    while True:
        try:
            logger.info(f"\n🚀 Bot ishga tushirilmoqda ({time.strftime('%Y-%m-%d %H:%M:%S')})")
            await start_bot() # Botni ishga tushirish
        except Exception as e:
            logger.critical(f"❌ Botda halokatli xato yuz berdi va to'xtatildi: {e}", exc_info=True)
            await send_telegram_message(f"🆘 Bot to'xtatildi! Halokatli xato: <code>{e}</code> Iltimos, loglarni tekshiring.")
            logger.info("♻️ 30 soniyadan keyin qayta ishga tushirilmoqda...")
            await asyncio.sleep(30) # 30 soniya kutib, qayta urinish

if __name__ == "__main__":
    # Konfiguratsiyaning to'g'riligini tekshirish
    if not TELEGRAM_TOKEN or not CHAT_IDS or any(not str(chat_id).strip() for chat_id in CHAT_IDS):
        logger.error("❌ Xatolik: TELEGRAM_TOKEN yoki CHAT_IDS konfiguratsiyasi to'g'ri emas. Iltimos, kod ichida ularni o'zgartiring.")
        print("\n" * 3)
        print("############################################################")
        print("#                                                          #")
        print("#  DIQQAT! TELEGRAM_TOKEN VA CHAT_IDS NI O'ZGARTIRING!    #")
        print("#                                                          #")
        print("############################################################")
    else:
        asyncio.run(main())
