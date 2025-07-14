import asyncio
import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# 🟡 TOKEN va CHAT_ID ni to'ldiring
TELEGRAM_TOKEN = '7780864447:AAESpcIqmzNkN1CiyLM1WfRkzPMWPeq7dzU'
CHAT_ID = ['7971306481', '6329050233']  # ro'yxat ko'rinishida

# 🔧 Sozlamalar
MIN_VOLUME = 10000
MIN_PROFIT = 3
CHECKABLE_MIN = 1
CHECKABLE_MAX = 3
INVEST_AMOUNT = 200
FEE_RATE = 0.002

# ✅ Ruxsat etilgan birjalar
ALLOWED_EXCHANGES = {
    'SuperEx', 'CoinEx', 'Kraken', 'HTX', 'Toobit', 'AscendEX', 'Bitget',
    'BloFin', 'BDFI', 'Poloniex', 'BitMart', 'Bitrue', 'BYDFi', 'CoinW',
    'BingX', 'Ourbit', 'BTCC', 'WEEX', 'LBank', 'GMGN', 'KCEX',
    'DigiFinex', 'CoinCola', 'Binance', 'MEXC'
}

# 📌 Tahlil qilinadigan coinlar
COIN_IDS = [
    "Gitcoin", "Alchemy Pay", "Cardano", "AdEx", "Aergo", "Anchored Coins AEUR",
    "SingularityNET", "Algorand", "MyNeighborAlice", "Amp", "ApeCoin", "Polygon",
    "Verge", "Zilliqa", "VIDT DAO", "Bluzelle", "Stellar", "Chainlink", "Bitcoin",
    "Stratis", "Band Protocol", "Phala Network", "The Graph", "Polkadot",
    "Polymesh", "Solar", "LTO Network", "Vanar Chain", "IQ", "WAX",
    "First Digital USD", "JasmyCoin", "Nervos Network", "Arbitrum", "Drep [new]",
    "SPACE ID", "The Sandbox", "NEAR Protocol", "Internet Computer", "XRP",
    "Ethereum", "Celo", "Kadena", "Render", "Theta Network", "Theta Fuel", "Dusk",
    "Loom Network", "Avalanche", "Cartesi", "ORDI", "Syscoin", "Ravencoin",
    "Litecoin", "Loopring", "IOTA", "Livepeer", "Artificial Superintelligence Alliance",
    "Sei", "Bonfida", "Phoenix", "Ethereum Classic", "Gifto", "Celer Network",
    "Hive", "Horizen", "iExec RLC", "Powerledger", "Quant", "Crypterium", "DigiByte",
    "FIO Protocol", "Oasis Network", "DIA", "Ethereum Name Service",
    "Rootstock Infrastructure Framework", "Optimism", "TRON", "GMT", "Moonriver",
    "Measurable Data Token", "NFPrompt", "Klaytn", "Mina", "Filecoin", "Dogecoin",
    "Trust Wallet Token", "SuperRare", "Moonbeam", "VeChain", "Contentos", "Qtum",
    "MultiversX", "Pyth Network", "Conflux", "MANTRA", "SKALE", "Xai", "Portal",
    "Enjin Coin", "ARPA", "PlayDapp", "Cortex", "Nano", "Prom", "Reserve Rights",
    "Sui", "IOST", "SelfKey", "Flow", "Manta Network", "Tezos", "Bitcoin Cash",
    "Aptos", "Bitcoin Gold", "Dash", "Dent", "Lisk", "Firo", "PAX Gold", "eCash",
    "NEM", "Komodo", "Cosmos", "Solana", "Ocean Protocol", "Mask Network",
    "REI Network", "Streamr", "Viction", "Waves", "Automata Network", "Cyber",
    "Radworks", "API3", "Blur", "Gas", "Axelar", "Terra", "Galxe", "Decentraland",
    "Ardor", "Stacks", "ICON", "Golem", "WazirX", "Decred", "Steem", "Metal DAO",
    "NULS", "Flux", "Secret", "Biconomy", "COMBO", "Hedera", "Civic", "Request",
    "DeXe", "Origin Protocol", "MobileCoin", "Highstreet", "AVA (Travala)", "USD Coin",
    "Arweave", "Chiliz", "Harmony", "Storj", "TrueUSD", "PIVX", "IRISnet",
    "Basic Attention Token", "Metis", "Celestia", "NKN", "xMoney", "Marlin",
    "Wormhole", "QuarkChain", "Hooked Protocol", "Saga", "Astar", "Ark", "Tensor",
    "Beam", "Kusama", "Omni Network", "aelf", "Holo", "WINkLink", "Tellor",
    "Bittensor", "StormX", "Status", "SafePal", "Siacoin", "Orchid", "Ontology Gas",
    "IoTeX", "Toncoin", "Fame AI", "Alephium", "Hasaki", "Tether Gold",
    "OriginTrail", "Casper", "Zeebu", "Fasttoken", "LayerZero", "IPVERSE",
    "Zignaly", "VeThor Token", "Orbler", "Boba Network", "CyberBots AI",
    "Helium Mobile", "Nosana", "Hivemapper", "World Mobile Token", "Shadow Token",
    "NYM", "Pocket Network", "CUDOS", "OctaSpace", "Coinweb", "Gaimin", "Aleph.im",
    "IAGON", "KYVE Network", "XRADERS", "Delysium", "Ozone Chain", "Oraichain",
    "Artificial Liquid Intelligence", "Forta", "PlatON", "Agoras: Currency of Tau",
    "Victoria VR", "Dimitra", "Moca Coin", "dKargo", "Commune AI", "Hacken Token",
    "Numbers Protocol", "Sentinel Protocol", "UXLINK", "Data Ownership Protocol",
    "Avive World", "Aurora", "NuNet", "iMe Lab", "Cere Network", "NeyroAI",
    "GT Protocol", "FROKAI", "HyperGPT", "OORT", "PARSIQ", "Vectorspace AI", "Degen",
    "Koinos", "Synesis One", "Lumerin", "QnA3.AI", "Xelis", "DDMTOWN",
    "DeepBrain Chain", "Nuco.cloud", "Waves Enterprise", "Eclipse", "GamerCoin",
    "Optimus AI", "Ta-da", "TRVL", "Big Data Protocol", "Bad Idea AI", "Phantasma",
    "bitsCrunch", "PIBBLE", "Robonomics.network", "Swash", "Lambda", "MATH",
    "SubQuery Network", "Lithium", "Lossless", "Bridge Oracle", "Avail",
    "Mande Network", "Crypto-AI-Robo.com", "Metahero", "Netvrk", "Smart Layer Network",
    "Effect AI", "Chirpley", "Ispolink", "Edge Matrix Computing", "Dock",
    "PureFi Protocol", "GNY", "DxChain Token", "B-cube.ai", "DOJO Protocol", "Propy",
    "AXIS Token", "LBRY Credits", "ClinTex CTi", "GoCrypto Token", "Three Protocol Token",
    "Idena", "Aimedis (new)", "UBIX.Network", "Cirus Foundation", "All In", "Neurashi",
    "Aurora", "Ojamu", "Raze Network", "Ubex", "Censored Ai", "Triall", "Pawtocol",
    "Covalent", "Connectome", "Altered State Token", "Autonolas", "Dtec", "Work X",
    "Grow Token", "Lavita AI", "Arbius", "EpiK Protocol", "Multiverse", "enqAI",
    "Humans.ai", "Y8U", "AI Network", "Jackal Protocol", "Morpheus Infrastructure Node",
    "Tradetomato", "BasedAI", "ISSP", "Aventis Metaverse", "NFMart",
    "The Winkyverse", "Next Gem AI", "Human", "AlphaScan AI", "Eternal AI",
    "DataHighway", "Balance AI", "A3S Protocol", "Ore", "inheritance Art",
    "Raven Protocol", "Swan Chain (formerly FilSwan)", "VEMP", "Flourishing AI",
    "Cloudbric", "Kin", "META PLUS TOKEN", "LUKSO", "Neuroni AI", "AI PIN", "Layer3",
    "Trace Network Labs", "GoSleep", "Chappyz", "Kambria", "Aion", "Acria.AI",
    "Ctomorrow Platform", "The Emerald Company", "Gomining", "EPIK Prime", "Myria",
    "AutoCrypto", "Cindicator", "Bottos", "Eurite", "Bloktopia", "Runesterminal",
    "RSIC•GENESIS•RUNE", "WELL3", "Alpine F1 Team", "Verida", "Galaxis", "Energi",
    "Build", "DecideAI", "5ire", "Slash Vision Labs", "Star Protocol", "Fautor",
    "BIDZ Coin", "Port3 Network", "KITEAI", "Super Zero Protocol", "ChatAI Token",
    "Alltoscan", "Hathor", "Spacemesh", "Woonkly Power", "ANyONe Protocol", "Chromia",
    "Oasys", "Zano", "Concordium", "NuLink", "Wisdomise AI", "Synternet",
    "Q Protocol", "Self Chain", "XDAO", "EMAIL Token", "Hyve", "Kaarigar Connect",
    "ARCS", "GTC AI", "Taraxa", "Radiant", "Electra Protocol", "Nexa", "AgentLayer",
    "Epic Cash", "Saito", "Zenon", "Abelian", "Humanode", "MultiVAC",
    "Integritee Network", "MainnetZ", "Hide Coin", "Busy DAO", "WYZth", "CLV",
    "Karlsen", "Canxium", "Allbridge", "Ice Open Network", "KALICHAIN", "Witnet",
    "HIENS3", "Unique Network", "Calamari Network", "Ecoin official", "EthereumPoW",
    "/Reach", "Friend3", "ECOMI", "BORA", "MXC", "Adventure Gold", "Swarm",
    "LooksRare", "PolySwarm", "Virtual Versions", "SwftCoin", "Wirex Token",
    "Taki Games", "Polyhedra Network", "Dora Factory", "WiFi Map", "Sweat Economy",
    "Gala", "DappRadar", "EURC", "Iron Fish", "Scroll", "GEODNET", "POL (ex-MATIC)",
    "CARV", "Kylacoin", "Thought", "Naxion", "Andromeda", "LightLink", "Nordek",
    "SatoshiVM", "LiquidApps", "Holograph", "ZENQIRA", "AIA Chain", "Beldex",
    "Truflation", "Aki Network", "Aleo", "Cellframe", "Ariva", "FREEdom Coin",
    "Metaplex", "UMA", "Pirate Chain", "Dero", "HOPR", "ColossusXT", "Crypton",
    "Grass", "Bytecoin", "Vertcoin", "Cros", "MUA DAO", "FOGNET", "Fractal Network",
    "Wownero", "The Root Network", "XBorg", "Kaia", "NATIX Network", "Ctrl Wallet",
    "Assemble AI", "Telos", "KardiaChain", "Shiden Network", "xHashtag AI",
    "Lifeform Token", "EGO", "TARS AI", "Sui Name Service", "OMG Network", "Bit. Store",
    "Altura", "Cookie", "Æternity", "BytomDAO", "GoChain", "Batching. AI",
    "Plugin Decentralized Oracle", "Darwinia Network", "Revain", "myDID",
    "v. systems", "Vexanium", "Edgeware", "AME Chain", "Nexera", "Coreum",
    "Zircuit", "OORT", "Sensay", "Brickken", "Laika AI", "SUPRA", "PUMLx",
    "Banana Gun", "ACENT", "Fame AI", "Gather", "BRC App", "Rowan Coin", "Tamkin",
    "XRP Healthcare", "Open Loot", "Tornado Cash", "peaq", "MVL", "Open Campus",
    "Simmi Token", "XION", "ORA", "Alkimi", "Gravity", "BugsCoin", "Fluence",
    "Magic Eden", "Movement", "DIMO", "Heurist AI", "OBORTECH", "KLEAR", "Neuton",
    "KIP Protocol", "Propchain", "Agents AI", "Ripple USD", "Kaspa", "Worldcoin",
    "Chromia", "Shieldeum", "AI Agent Layer", "Guru Network", "UnMarshal", "Vana",
    "Nirvana", "Skillful AI", "Bepro", "Solvex Network", "RWA Inc.", "CodeXchain",
    "Deeper Network", "RARI", "U2U Network", "Pax Dollar", "Peercoin",
    "Quantum Resistant Ledger", "Elastos", "StorX Network", "Helium IOT", "Sentinel",
    "Stratos", "Bitfinity Network", "Kroma", "Laïka", "Handshake", "Crust Network",
    "PAAL AI", "KARRAT", "KOLZ", "OctonetAI", "Edge", "GRIFFAIN", "Parex",
    "Circular Protocol", "ResearchCoin", "Hippocrat", "CryptoAutos", "Pepecoin",
    "Luckycoin", "SETAI", "Junkcoin", "Reploy", "FLock..io", "Network DSYNC",
    "Bio Protocol", "Mobius", "Mysterium", "Raiden Network Token", "YOM", "Odyssey",
    "SōzōAI", "aixbt by Virtuals", "Sonic (prev. FTM)", "CRT AI Network",
    "STORAGENT", "BoltAI", "Fuel Network", "Function X", "cheqd", "neur.sh",
    "Limitus", "ZayaAI", "sekoia by Virtuals", "Realis Worlds", "HTERM", "HashAI",
    "CGAI", "SUIRWA", "Nodecoin", "BIDP", "Envision", "Spore.fun", "GoatIndex.ai",
    "DigiHealth", "ULTIMA", "Act I : The AI Prophecy", "Energy Web Token",
    "Dragonchain", "Phicoin", "ai16z", "Plume", "HAT", "SONIC", "VirtualDaos",
    "Chintai", "DAR Open Network", "Venice Token", "Creo Engine", "Morpheus",
    "GoPlus Security", "yesnoerror", "CreatorBid", "Alchemist AI", "Symbol",
    "Etherland", "Hive Intelligence", "Network3", "LAK3", "NTMPI", "Onyxcoin",
    "Partisia Blockchain", "SUI Desci Agents", "Aventus", "Blocery", "Boson Protocol",
    "CENNZnet", "Unification", "SOLVE", "Bitswift", "Hyperblox", "Neblio",
    "Smart MFG", "BLOCKv", "Suku", "Analog", "DIAM", "Atomicals", "Camino Network",
    "Story", "Nexus", "Ancient8", "Coldstack", "ScPrime", "Etho Protocol", "Sallar",
    "Academic Labs", "Electroneum", "KAITO", "Groestlcoin", "FileStar", "Particl",
    "Micro GPT", "PSJGlobal", "StorageChain", "Agoric", "MyShell", "EPAY",
    "Open Custody Protocol", "Assist AI", "AIST", "Collaterize", "JobSeek AI",
    "SafeCircle", "SwarmNode.ai", "MAIAR", "ArtGee AI", "Immutable", "Kendo AI",
    "Helio", "AI Rig Complex", "Bifrost", "Skey Network", "Xterio", "Blombard",
    "OpenBlox", "Bubblemaps", "Roam", "HYPE3-cool", "SINGULAR", "Uquid Coin",
    "Nillion", "CrypTalk", "GINI", "Particle Network", "Nireafty", "Safe Road Club AI",
    "StraitsX USD", "XSGD", "XIDR", "Paraverse", "Walrus", "Flare AI", "Sender",
    "MiL.k", "Wayfinder", "WalletConnect", "Mind Network", "Talken", "ACENT",
    "Hyperlane", "Saakuru Protocol", "Balance", "Arkham", "Ankr", "Altlayer",
    "Royalty", "Mansory", "Arcana Network", "Sign", "Pundi X (New)", "AQA",
    "AGiXT", "Treasure", "Nuklai", "AirDAO", "Neutron", "NexusChain", "AVA AI",
    "VITE", "OKZOO", "Cratos", "Propbase", "Step App", "Obortech", "Carnomaly",
    "Cryptify AI", "Argocoin", "Frictionless", "Heima", "Space and Time", "GPUs",
    "Domin Network", "Jupiter", "SKYAI", "SIX", "UPCX", "BSquared Network", "RWAI",
    "REENTAL", "Okratech Token", "MuxyAI", "Neon EVM", "TRI SIGMA", "DuckChain",
    "Alaya Governance Token", "Mint Blockchain", "Privasea AI", "Keep Network",
    "Houdini Swap", "OpenServ", "Rivalz Network", "Keeta", "Reef", "SOON",
    "Quai Network", "RYO Coin", "Epic Chain", "SoSoValue", "AWE Network",
    "Project Rescue", "Jambo", "Sophon", "Patex", "Moonchain", "Orbiter Finance",
    "iAI Center", "Assisterr", "DELNORTE", "Inferium", "Shardeum", "LayerEdge",
    "DeBox", "Block Vault", "Subsquid", "Everscale", "BONDEX", "Neuron", "NERTA",
    "NFTAI", "Lagrange", "Infinaeon", "LENS", "AB", "TokenFi", "ssv.network",
    "solayer", "Zcash", "Fly.trade", "Mythos", "Ronin", "CUDIS", "PinLink",
    "DeepLink Protocol", "Skate", "AO", "ASTRA", "Token Metrics AI", "Reddio",
    "The Arena", "GAG Token", "ESX", "Matchain", "NAM", "DAOBase", "Tagger",
    "Bitcoin Silver AI", "REDBRICK", "BOTIFY", "SmartPractice", "Coral Protocol",
    "CLI.AI", "Newton Protocol", "Sahara AI", "Mango Network", "Distribute..ai",
    "Humanity Protocol", "DeLorean", "REVOX", "Paragon Tweaks", "Mealy",
    "Impossible Cloud Network", "WaterMinder", "Paynetic AI", "Velo", "LF",
    "VeBetterDAO", "MAP Protocol", "ChainGPT", "Cobak Token", "Blockprompt",
    "Sabai Protocol", "JuChain", "Pundi AI", "Infinity Ground", "Validity", "B3 (Base)"]

# 📨 Telegram xabar yuborish
async def send_telegram_message(text):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    async with aiohttp.ClientSession() as session:
        for chat_id in CHAT_ID:
            payload = {'chat_id': chat_id, 'text': text}
            await session.post(url, data=payload)

# 🟩 Coin ma’lumotlarini olish
async def fetch_tickers(session, coin_id):
    url = f'https://api.coingecko.com/api/v3/coins/{coin_id}/tickers'
    async with session.get(url) as resp:
        if resp.status != 200:
            return {}
        return await resp.json()

# 📊 Tahlil qilish
async def analyze_coin(session, coin_id, check_mode=False):
    data = await fetch_tickers(session, coin_id)
    tickers = data.get("tickers", [])
    filtered = [t for t in tickers if t.get("market", {}).get("name") in ALLOWED_EXCHANGES and t.get("target") == "USDT"]

    if len(filtered) < 2:
        return

    sorted_by_price = sorted(filtered, key=lambda x: x["last"])
    buy = sorted_by_price[0]
    sell = sorted_by_price[-1]

    buy_price = buy["last"]
    sell_price = sell["last"]
    volume = min(
        buy.get("converted_volume", {}).get("usd", 0),
        sell.get("converted_volume", {}).get("usd", 0)
    )

    if volume < MIN_VOLUME:
        return

    quantity = INVEST_AMOUNT / buy_price
    gross = quantity * sell_price
    fee = quantity * (buy_price + sell_price) * FEE_RATE
    net = gross - INVEST_AMOUNT - fee
    roi = (net / INVEST_AMOUNT) * 100

    if roi >= MIN_PROFIT and not check_mode:
        await send_telegram_message(
            f"🚨 Arbitraj Imkoniyati\nCoin: {coin_id}\nHajm: {volume:.0f} USDT\nBuy: {buy_price:.4f} ({buy['market']['name']})\nSell: {sell_price:.4f} ({sell['market']['name']})\nKomissiya: {fee:.2f} USD\nFoyda: {net:.2f} USD\nROI: {roi:.2f}%"
        )

    elif check_mode and CHECKABLE_MIN <= roi < CHECKABLE_MAX:
        await send_telegram_message(
            f"ℹ️ Tekshiruv: {coin_id}\nBuy: {buy_price:.4f} ({buy['market']['name']})\nSell: {sell_price:.4f} ({sell['market']['name']})\nROI: {roi:.2f}%"
        )

# 🔁 Doimiy monitoring
async def monitor_loop():
    async with aiohttp.ClientSession() as session:
        while True:
            print("[INFO] Monitoring boshlanmoqda...")
            for coin_id in COIN_IDS:
                try:
                    await analyze_coin(session, coin_id)
                except Exception as e:
                    print(f"[ERROR] {coin_id}: {e}")
                await asyncio.sleep(2)
            await asyncio.sleep(300)  # 5 daqiqa

# 🟡 Telegram komandalar
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Assalomu alaykum, bot ishga tushdi!")

async def check_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Tekshirish boshlandi...")
    async with aiohttp.ClientSession() as session:
        for coin_id in COIN_IDS:
            try:
                await analyze_coin(session, coin_id, check_mode=True)
            except Exception as e:
                print(f"[ERROR in check]: {e}")
            await asyncio.sleep(2)
    await update.message.reply_text("✅ Tekshiruv tugadi.")

# 🔧 Botni ishga tushirish
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("check", check_handler))

    # Arbitraj monitoringini fon rejimida boshlash
    asyncio.create_task(monitor_loop())

    print("[INFO] Telegram bot ishga tushdi.")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())