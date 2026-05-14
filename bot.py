import requests
import time
import os
import asyncio
import sys
import re
from collections import deque
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════════════════
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

if not TELEGRAM_TOKEN:
    raise EnvironmentError("TELEGRAM_TOKEN manquant.")
if not TELEGRAM_CHAT_ID:
    raise EnvironmentError("TELEGRAM_CHAT_ID manquant.")

# ══════════════════════════════════════════════════════════════════════════════
#  BASE DE DONNÉES DE MARQUES (VERSION PRO)
# ══════════════════════════════════════════════════════════════════════════════

BRANDS = [
    "Corteiz","Hellstar","Broken Planet","Stussy","Supreme","Palace","Carhartt","Dickies",
    "Off-White","Essentials","Fear of God","Trapstar","Represent","Bape","Kith",
    "Chrome Hearts","Amiri","Pleasures","Daily Paper","Hoodrich","CPFM",
    "Rhude","Palm Angels","Stone Island","The North Face","Arc'teryx",
    "Aime Leon Dore","Patta","Obey","Thrasher","Anti Social Social Club",
    "Nike","Adidas","Puma","Reebok","New Balance","Asics","Under Armour",
    "Jordan","Converse","Vans","Salomon","Mizuno","Champion","Fila",
    "Hoka","On Running","Columbia","Patagonia",
    "Louis Vuitton","Gucci","Prada","Balenciaga","Dior","Chanel","Burberry",
    "Givenchy","Moncler","YSL","Versace","Kenzo","Celine","Loewe","Margiela",
    "Rick Owens","Vetements","Acne Studios","Jacquemus","Ami Paris",
    "Valentino","Bottega Veneta","Hermes","Lanvin","Moschino",
    "Acronym","Mammut","Helly Hansen","Montbell","Millet","Haglofs","Carinthia",
    "Ralph Lauren","Tommy Hilfiger","Lacoste","Levi's","Wrangler",
    "Timberland","Nautica","Kappa","Ellesse","Fred Perry","Benetton","Napapijri",
    "Ugg","Lululemon","Gallery Dept","Sp5der",
]

VARIANTS = {
    "crt": "Corteiz", "crtz": "Corteiz", "stoney": "Stone Island",
    "bp": "Broken Planet", "tnf": "The North Face", "fog": "Fear of God",
    "tech fleece": "Nike Tech Fleece", "nb": "New Balance", "rl": "Ralph Lauren",
}

CATEGORIES = {
    "Corteiz": "streetwear", "Hellstar": "streetwear", "Broken Planet": "streetwear",
    "Stussy": "streetwear", "Supreme": "streetwear", "Palace": "streetwear",
    "Carhartt": "streetwear", "Dickies": "streetwear",
    "Off-White": "streetwear", "Essentials": "streetwear", "Fear of God": "streetwear",
    "Trapstar": "streetwear", "Represent": "streetwear", "Bape": "streetwear",
    "Kith": "streetwear", "Chrome Hearts": "streetwear", "Amiri": "streetwear",
    "Pleasures": "streetwear", "Daily Paper": "streetwear", "Hoodrich": "streetwear",
    "CPFM": "streetwear", "Rhude": "streetwear", "Palm Angels": "streetwear",
    "Stone Island": "streetwear", "The North Face": "streetwear", "Arc'teryx": "techwear",
    "Aime Leon Dore": "streetwear", "Patta": "streetwear", "Obey": "streetwear",
    "Thrasher": "streetwear", "Anti Social Social Club": "streetwear",
    "Gallery Dept": "streetwear", "Sp5der": "streetwear",
    "Nike": "sportswear", "Adidas": "sportswear", "Puma": "sportswear",
    "Reebok": "sportswear", "New Balance": "sportswear", "Asics": "sportswear",
    "Under Armour": "sportswear", "Jordan": "sportswear", "Converse": "sportswear",
    "Vans": "sportswear", "Salomon": "sportswear", "Mizuno": "sportswear",
    "Champion": "sportswear", "Fila": "sportswear", "Hoka": "sportswear",
    "On Running": "sportswear", "Columbia": "sportswear", "Patagonia": "sportswear",
    "Louis Vuitton": "luxe", "Gucci": "luxe", "Prada": "luxe",
    "Balenciaga": "luxe", "Dior": "luxe", "Chanel": "luxe", "Burberry": "luxe",
    "Givenchy": "luxe", "Moncler": "luxe", "YSL": "luxe", "Versace": "luxe",
    "Kenzo": "luxe", "Celine": "luxe", "Loewe": "luxe", "Margiela": "luxe",
    "Rick Owens": "luxe", "Vetements": "luxe", "Acne Studios": "luxe",
    "Jacquemus": "luxe", "Ami Paris": "luxe", "Valentino": "luxe",
    "Bottega Veneta": "luxe", "Hermes": "luxe", "Lanvin": "luxe", "Moschino": "luxe",
    "Acronym": "techwear", "Mammut": "techwear", "Helly Hansen": "techwear",
    "Montbell": "techwear", "Millet": "techwear", "Haglofs": "techwear",
    "Carinthia": "techwear",
    "Ralph Lauren": "vintage", "Tommy Hilfiger": "vintage", "Lacoste": "vintage",
    "Levi's": "vintage", "Wrangler": "vintage", "Timberland": "vintage",
    "Nautica": "vintage", "Kappa": "vintage", "Ellesse": "vintage",
    "Fred Perry": "vintage", "Benetton": "vintage", "Napapijri": "vintage",
    "Ugg": "tendance", "Lululemon": "tendance",
}

PRIORITE = {
    "streetwear": 3, "luxe": 3, "techwear": 3,
    "sportswear": 2, "vintage": 2, "tendance": 2, "fast_fashion": 0,
}

# ── Legacy constants ────────────────────────────────────────────────────────
TOUTES_LES_MARQUES = set(b.lower() for b in BRANDS)

KEYWORDS_HYPE = {
    "vintage", "deadstock", "ds", "vnds", "rare", "limited", "collab",
    "og", "retro", "dunk", "air max", "air force", "jordan 1", "jordan 4",
    "jordan 11", "350", "990", "2002r", "550", "travis", "sacai", "fragment",
}

KEYWORDS_EXCLUS = {
    "lot de", "pack", "déguisement", "costume", "bébé", "enfant",
    "fille", "garçon", "chaussettes", "sous-vêtement",
}

MARQUES_HYPE_BONUS = {
    "chrome hearts", "hellstar", "gallery dept", "rick owens",
    "corteiz", "crtz", "supreme", "palace", "off-white",
    "fear of god", "trapstar", "broken planet", "yeezy",
    "bape", "jordan", "air jordan", "represent",
}

TAILLES_RARES = {"xxs", "xs", "3xl", "4xl", "5xl", "xxl", "xxxl", "6", "6.5", "13", "14", "15"}
ETATS_PREMIUM = {"neuf avec étiquette", "neuf sans étiquette", "très bon état"}

# ══════════════════════════════════════════════════════════════════════════════
#  ÉTAT GLOBAL
# ══════════════════════════════════════════════════════════════════════════════

selected_brands: set = set(b.lower() for b in BRANDS)

config = {
    "actif":     False,
    "mode_flux": False,
    "prix_min":  3.0,
    "prix_max":  200.0,
    "score_min": 60,
}

seen_ids: set = set()
historique_alertes: deque = deque(maxlen=50)
favoris: list = []
pending_search: dict = {}
interaction_count: int = 0  # utilisé pour le mode "un message par article"

# ══════════════════════════════════════════════════════════════════════════════
#  SESSION HTTP
# ══════════════════════════════════════════════════════════════════════════════

def _make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9",
    })
    try:
        s.get("https://www.vinted.fr", timeout=10)
    except Exception:
        pass
    return s

_session = _make_session()

def _api_get(url: str):
    global _session
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "fr-FR,fr;q=0.9",
        "Referer": "https://www.vinted.fr/catalog",
        "X-Requested-With": "XMLHttpRequest",
    }
    try:
        resp = _session.get(url, headers=headers, timeout=15)
        if resp.status_code == 401:
            _session = _make_session()
            resp = _session.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception as e:
        print(f" API GET {url[:60]}: {e}")
        return None

def fetch_items(search_text: str = "", per_page: int = 20) -> list:
    params = f"per_page={per_page}&order=newest_first"
    if search_text:
        params += f"&search_text={requests.utils.quote(search_text)}"
    url = f"https://www.vinted.fr/api/v2/catalog/items?{params}"
    data = _api_get(url)
    if not data:
        return []
    return data.get("items", [])

def fetch_item_by_id(item_id: int):
    url = f"https://www.vinted.fr/api/v2/items/{item_id}"
    data = _api_get(url)
    if not data:
        return None
    return data.get("item", data)

# ══════════════════════════════════════════════════════════════════════════════
#  DÉTECTION INTELLIGENTE
# ══════════════════════════════════════════════════════════════════════════════

def detecter_marque(titre: str):
    t = titre.lower()
    for b in selected_brands:
        if b in t:
            return b
    for variant, canonical in VARIANTS.items():
        if variant in t:
            c = canonical.lower()
            if c in selected_brands:
                return c
            return c
    return None

def get_categorie(marque: str) -> str:
    return CATEGORIES.get(marque.title(), "tendance")

def get_priorite(categorie: str) -> int:
    return PRIORITE.get(categorie, 1)

def extraire_prix(item: dict):
    try:
        raw = item.get("price", {})
        return float(raw.get("amount", 0) if isinstance(raw, dict) else raw)
    except (TypeError, ValueError):
        return None

def extraire_photo(item: dict):
    photo = item.get("photo")
    if not photo:
        return None
    if isinstance(photo, dict):
        return photo.get("full_url") or photo.get("url")
    if isinstance(photo, str):
        return photo
    return None

def extraire_item_id(url: str):
    m = re.search(r'/items/(\d+)', url)
    if m:
        return int(m.group(1))
    return None

# ══════════════════════════════════════════════════════════════════════════════
#  ANALYSE AVEC PROPAGATION
# ══════════════════════════════════════════════════════════════════════════════

def fetch_similaires(marque: str, categorie: str, taille: str, exclude_id: int, max_items: int = 10) -> list:
    query = marque
    if categorie in ("streetwear", "luxe", "techwear"):
        query += f" {categorie}"
    items = fetch_items(search_text=query, per_page=max_items + 5)
    result = []
    for item in items:
        if item.get("id") == exclude_id:
            continue
        if not item.get("title"):
            continue
        result.append(item)
        if len(result) >= max_items:
            break
    return result

def analyse_propagation(url: str, max_depth: int = 3) -> dict:
    item_id = extraire_item_id(url)
    if not item_id:
        return {"erreur": "URL invalide. Utilise un lien Vinted valide."}

    visited = set()
    best_data = None
    all_similaires = []
    depth = 0
    current_id = item_id

    while depth < max_depth:
        if current_id in visited:
            break
        visited.add(current_id)

        item = fetch_item_by_id(current_id)
        if not item:
            break

        titre = item.get("title", "") or ""
        prix = extraire_prix(item)
        if prix is None or prix <= 0:
            break

        marque = detecter_marque(titre)
        if not marque:
            if depth == 0:
                return {"erreur": "Impossible de détecter la marque."}
            break

        categorie = get_categorie(marque)
        taille = item.get("size_title", "") or ""

        similaires = fetch_similaires(marque, categorie, taille, current_id, 10)

        prix_list = []
        prix_min = float("inf")
        cheapest_item = None

        for s in similaires:
            sp = extraire_prix(s)
            if sp and sp > 0:
                prix_list.append(sp)
                if sp < prix_min:
                    prix_min = sp
                    cheapest_item = s

        prix_moyen = round(sum(prix_list) / len(prix_list), 2) if prix_list else 0

        if depth == 0 or prix < best_data["prix_achat"]:
            best_data = {
                "item": item,
                "prix_achat": prix,
                "marque": marque,
                "categorie": categorie,
                "taille": taille,
            }

        all_similaires.extend([s for s in similaires if extraire_prix(s) is not None])

        if cheapest_item and prix_min < prix and len(prix_list) >= 3:
            cid = cheapest_item.get("id")
            if cid and cid not in visited:
                current_id = cid
                depth += 1
                continue

        break

    if not best_data:
        return {"erreur": "Aucun article trouvé."}

    all_prices = [extraire_prix(s) for s in all_similaires if extraire_prix(s) is not None]
    prix_moyen_final = round(sum(all_prices) / len(all_prices), 2) if all_prices else 0
    marge = round(prix_moyen_final - best_data["prix_achat"], 2) if prix_moyen_final > 0 else 0
    score = calculer_score(best_data["prix_achat"], prix_moyen_final, marge,
                           best_data["marque"], best_data["item"].get("title", ""),
                           best_data["taille"], best_data["item"].get("status", ""))

    return {
        "item":       best_data["item"],
        "prix_achat": best_data["prix_achat"],
        "prix_moyen": prix_moyen_final,
        "marge":      marge,
        "score":      min(100, score),
        "marque":     best_data["marque"],
        "categorie":  best_data["categorie"],
        "taille":     best_data["taille"],
        "similaires": [(s, extraire_prix(s)) for s in all_similaires if extraire_prix(s) is not None],
        "url":        url,
    }

# ══════════════════════════════════════════════════════════════════════════════
#  SCORE /100
# ══════════════════════════════════════════════════════════════════════════════

def calculer_score(prix: float, revente: float, marge: float,
                   marque: str, titre: str, taille: str, etat: str) -> int:
    t = titre.lower()
    score = 0

    ratio = marge / prix if prix > 0 else 0
    score += min(35, int(ratio * 55))

    if   marge >= 100: score += 20
    elif marge >= 50:  score += 15
    elif marge >= 30:  score += 10
    elif marge >= 20:  score += 7
    elif marge >= 10:  score += 4

    if revente > 0:
        ratio_marche = prix / revente
        if   ratio_marche <= 0.20: score += 10
        elif ratio_marche <= 0.35: score += 7
        elif ratio_marche <= 0.50: score += 4

    if marque in MARQUES_HYPE_BONUS:
        score += 15

    hype_count = sum(1 for k in KEYWORDS_HYPE if k in t)
    score += min(8, hype_count * 3)

    if   revente > prix * 3.0: score += 6
    elif revente > prix * 2.5: score += 4

    if etat.lower() in ETATS_PREMIUM:
        score += 4

    if taille.lower().strip() in TAILLES_RARES:
        score += 2

    return min(100, score)

def niveau_affaire(score: int) -> str:
    if score >= 90: return "PÉPITE EXTRÊME"
    if score >= 78: return "ÉNORME AFFAIRE"
    if score >= 65: return "TRÈS BONNE AFFAIRE"
    if score >= 50: return "BONNE AFFAIRE"
    return "AFFAIRE CORRECTE"

# ══════════════════════════════════════════════════════════════════════════════
#  FORMATAGE MESSAGE & KEYBOARDS
# ══════════════════════════════════════════════════════════════════════════════

def formater_message(d: dict) -> str:
    etat = d.get("item", {}).get("status", "Non précisé") or "Non précisé"
    titre = d.get("item", {}).get("title", "") or ""
    niveau = niveau_affaire(d["score"])

    similaires_lines = []
    for s_item, s_prix in d.get("similaires", [])[:10]:
        s_id = s_item.get("id")
        s_url = f"https://www.vinted.fr/items/{s_id}"
        similaires_lines.append(f"{s_prix} - <a href='{s_url}'>Voir</a>")

    similaires_txt = "\n".join(similaires_lines) if similaires_lines else "Aucun similaire trouvé"

    return (
        f"<b>{niveau}</b> — <b>{d['score']}/100</b>\n\n"
        f"👕 <b>{titre[:80]}</b>\n"
        f"🏷️ Marque : {d['marque'].title()}\n"
        f"📐 Taille : {d['taille'] or '?'}\n"
        f"✨ Etat : {etat}\n"
        f"💶 Prix achat : <b>{d['prix_achat']}€</b>\n"
        f"📈 Revente conseille : <b>{d['prix_moyen']}€</b>\n"
        f"💰 Marge reelle : <b>{d['marge']}€</b>\n\n"
        f"🔍 Articles compares ({len(d.get('similaires', []))}) :\n{similaires_txt}\n\n"
        f"🔗 <a href='{d['url']}'>Voir l'annonce originale</a>"
    )

def build_article_keyboard(item_id) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Skip", callback_data=f"skip_{item_id}"),
            InlineKeyboardButton("Favoris", callback_data=f"fav_add_{item_id}"),
            InlineKeyboardButton("Acheter", callback_data=f"buy_{item_id}"),
        ],
    ])

# ══════════════════════════════════════════════════════════════════════════════
#  ANALYSEUR SIMPLIFIÉ POUR LE SCAN
# ══════════════════════════════════════════════════════════════════════════════

def analyser(item: dict) -> tuple:
    titre = item.get("title", "") or ""
    prix = extraire_prix(item)
    if prix is None or prix < config["prix_min"] or prix > config["prix_max"]:
        return False, {}
    if any(mot in titre.lower() for mot in KEYWORDS_EXCLUS):
        return False, {}

    marque = detecter_marque(titre)
    if marque is None:
        return False, {}

    categorie = get_categorie(marque)
    priorite = get_priorite(categorie)
    if priorite == 0:
        return False, {}

    similaires = fetch_similaires(marque, categorie, item.get("size_title", ""), item.get("id"), 5)
    prix_list = [extraire_prix(s) for s in similaires if extraire_prix(s) is not None]
    prix_moyen = round(sum(prix_list) / len(prix_list), 2) if prix_list else prix * 1.4

    marge = round(prix_moyen - prix, 2)
    if marge < 5:
        return False, {}

    score = calculer_score(prix, prix_moyen, marge, marque, titre,
                           item.get("size_title", ""), item.get("status", ""))
    if score < config["score_min"]:
        return False, {}

    data = {
        "id":         item.get("id"),
        "titre":      titre,
        "marque":     marque.title(),
        "taille":     item.get("size_title", "?"),
        "etat":       item.get("status", ""),
        "prix_achat": prix,
        "prix_moyen": prix_moyen,
        "marge":      marge,
        "score":      score,
        "niveau":     niveau_affaire(score),
        "url":        f"https://www.vinted.fr/items/{item.get('id')}",
        "photo":      extraire_photo(item),
        "item":       item,
        "similaires": [(s, extraire_prix(s)) for s in similaires[:10] if extraire_prix(s) is not None],
        "heure":      time.strftime("%H:%M:%S"),
    }
    return True, data

# ══════════════════════════════════════════════════════════════════════════════
#  BOUCLE DE SCAN
# ══════════════════════════════════════════════════════════════════════════════

async def boucle_scan(app: Application):
    loop = asyncio.get_event_loop()
    alert_queue: asyncio.Queue = asyncio.Queue()

    async def expediteur():
        while True:
            d = await alert_queue.get()
            msg_text = formater_message(d)
            markup = build_article_keyboard(d["id"])

            photo_url = d.get("photo")
            try:
                if photo_url:
                    await app.bot.send_photo(
                        chat_id=TELEGRAM_CHAT_ID,
                        photo=photo_url,
                        caption=msg_text,
                        parse_mode="HTML",
                        reply_markup=markup,
                    )
                else:
                    await app.bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text=msg_text,
                        parse_mode="HTML",
                        disable_web_page_preview=False,
                        reply_markup=markup,
                    )
            except Exception as e:
                print(f" Telegram: {e}")

            if not config["mode_flux"]:
                saved = interaction_count
                while interaction_count == saved:
                    await asyncio.sleep(0.5)
            else:
                qs = alert_queue.qsize()
                delay = 1 * (1 + qs // 5)
                await asyncio.sleep(min(delay, 5))

    asyncio.create_task(expediteur())

    brand_list = list(selected_brands)

    while True:
        if not config["actif"]:
            await asyncio.sleep(3)
            continue

        print(f"\nScan {time.strftime('%H:%M:%S')}")
        alertes = 0

        for brand in brand_list:
            if not config["actif"]:
                break
            try:
                items = await loop.run_in_executor(None, fetch_items, brand, 10)
            except Exception as e:
                print(f" Executor: {e}")
                items = []

            for item in items:
                item_id = item.get("id")
                if not item_id or item_id in seen_ids:
                    continue
                seen_ids.add(item_id)
                if len(seen_ids) > 50_000:
                    seen_ids.difference_update(list(seen_ids)[:25_000])

                ok, d = analyser(item)
                if not ok:
                    continue

                alertes += 1
                historique_alertes.appendleft(d)
                await alert_queue.put(d)
                print(f"  {d['titre'][:45]} | {d['score']}/100 | ~{d['marge']}")

            await asyncio.sleep(0.5)

        print(f"Cycle - {alertes} alertes")
        await asyncio.sleep(3)

# ══════════════════════════════════════════════════════════════════════════════
#  COMMANDES TELEGRAM
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_analyse(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage : /analyse &lt;url_vinted&gt;")
        return
    url = ctx.args[0]
    if "vinted" not in url.lower() or "items/" not in url:
        await update.message.reply_text("URL invalide. Doit etre un lien Vinted.")
        return

    msg = await update.message.reply_text("Analyse en cours...")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, analyse_propagation, url)

    if "erreur" in result:
        await msg.edit_text(f"Erreur : {result['erreur']}")
        return

    text = formater_message(result)
    item_id = result.get("item", {}).get("id")
    markup = build_article_keyboard(item_id)

    photo_url = extraire_photo(result.get("item", {}))
    try:
        if photo_url:
            await update.message.reply_photo(
                photo=photo_url, caption=text,
                parse_mode="HTML", reply_markup=markup,
            )
            await msg.delete()
        else:
            await msg.edit_text(
                text, parse_mode="HTML", reply_markup=markup,
                disable_web_page_preview=False,
            )
    except Exception as e:
        print(f" /analyse error: {e}")

async def cmd_bot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        build_main_text(), reply_markup=build_main_keyboard(),
        parse_mode="HTML", disable_web_page_preview=True,
    )

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config["actif"] = True
    await update.message.reply_text("Scan active !", parse_mode="HTML")

async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config["actif"] = False
    await update.message.reply_text("Scan mis en pause.", parse_mode="HTML")

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        build_main_text() + "\n\n/bot pour le panel",
        parse_mode="HTML",
    )

async def cmd_budget(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        pmin, pmax = float(ctx.args[0]), float(ctx.args[1])
        assert pmin >= 0 and pmax > pmin
        config["prix_min"], config["prix_max"] = pmin, pmax
        await update.message.reply_text(f"Budget : {pmin} - {pmax}", parse_mode="HTML")
    except Exception:
        await update.message.reply_text("Usage : /budget <min> <max>  ex: /budget 5 150")

async def cmd_mode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config["mode_flux"] = not config["mode_flux"]
    mode = "flux continu" if config["mode_flux"] else "un message par article"
    await update.message.reply_text(f"Mode : {mode}", parse_mode="HTML")

# ══════════════════════════════════════════════════════════════════════════════
#  PANEL - TEXTE & KEYBOARDS
# ══════════════════════════════════════════════════════════════════════════════

def build_main_text() -> str:
    etat = "Actif" if config["actif"] else "En pause"
    mode = "flux continu" if config["mode_flux"] else "un msg/article"
    return (
        "Vinted Bot Pro - Panel\n"
        + "-" * 30 + "\n"
        f"Etat : {etat}\n"
        f"Mode : {mode}\n"
        f"Budget : {config['prix_min']} - {config['prix_max']}\n"
        f"Score min : {config['score_min']}/100\n"
        f"Marques : {len(selected_brands)} actives\n"
        f"Historique : {len(historique_alertes)}\n"
        f"Favoris : {len(favoris)}\n"
        + "-" * 30 + "\n"
        "Choisis une option :"
    )

def build_main_keyboard() -> InlineKeyboardMarkup:
    etat_btn = "Pause" if config["actif"] else "Demarrer"
    etat_cb = "panel_pause" if config["actif"] else "panel_start"
    mode_btn = "Flux" if config["mode_flux"] else "Un par un"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(etat_btn, callback_data=etat_cb),
         InlineKeyboardButton("Arreter", callback_data="panel_stop")],
        [InlineKeyboardButton("Scan", callback_data="menu_scan"),
         InlineKeyboardButton("Budget", callback_data="menu_budget"),
         InlineKeyboardButton("Score", callback_data="menu_score")],
        [InlineKeyboardButton("Marques", callback_data="menu_marques"),
         InlineKeyboardButton(mode_btn, callback_data="panel_mode")],
        [InlineKeyboardButton("Historique", callback_data="menu_historique"),
         InlineKeyboardButton("Favoris", callback_data="menu_favoris")],
        [InlineKeyboardButton("Reset", callback_data="panel_reset"),
         InlineKeyboardButton("Rafraichir", callback_data="menu_main")],
    ])

# ── Scan ──────────────────────────────────────────────────────────────────
def build_scan_text() -> str:
    mode = "flux continu" if config["mode_flux"] else "un message par article"
    return (f"Scan\n{'-' * 30}\n"
            f"Mode : {mode}\n"
            f"Scan base sur {len(selected_brands)} marques.\n"
            f"/mode pour changer.")

def build_scan_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Changer mode", callback_data="panel_mode")],
        [InlineKeyboardButton("Retour", callback_data="menu_main")],
    ])

# ── Budget ────────────────────────────────────────────────────────────────
def build_budget_text() -> str:
    return (f"Filtre budget\n{'-' * 30}\n"
            f"Actuel : {config['prix_min']} - {config['prix_max']}\n"
            f"{'-' * 30}\nChoisis une plage :")

def build_budget_keyboard() -> InlineKeyboardMarkup:
    cur = (config["prix_min"], config["prix_max"])
    def mark(a, b): return f"{a}-{b}" if cur != (float(a), float(b)) else f"{a}-{b} (actif)"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(mark(3, 30), callback_data="budget_3_30"),
         InlineKeyboardButton(mark(3, 50), callback_data="budget_3_50"),
         InlineKeyboardButton(mark(5, 50), callback_data="budget_5_50")],
        [InlineKeyboardButton(mark(5, 100), callback_data="budget_5_100"),
         InlineKeyboardButton(mark(5, 150), callback_data="budget_5_150"),
         InlineKeyboardButton(mark(5, 200), callback_data="budget_5_200")],
        [InlineKeyboardButton(mark(10, 300), callback_data="budget_10_300"),
         InlineKeyboardButton(mark(10, 500), callback_data="budget_10_500")],
        [InlineKeyboardButton("Retour", callback_data="menu_main")],
    ])

# ── Score ─────────────────────────────────────────────────────────────────
def build_score_text() -> str:
    s = config["score_min"]
    descs = {(30,50): "Mode large", (50,65): "Equilibre",
             (65,80): "Strict", (80,96): "Expert"}
    desc = next((v for k,v in descs.items() if k[0] <= s < k[1]), "")
    return (f"Score minimum\n{'-' * 30}\n"
            f"Actuel : {s}/100\n{desc}\n{'-' * 30}\nAjuste :")

def build_score_keyboard() -> InlineKeyboardMarkup:
    s = config["score_min"]
    def mark(v): return f"{v} (actif)" if s == v else str(v)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(mark(40), callback_data="score_set_40"),
         InlineKeyboardButton(mark(50), callback_data="score_set_50"),
         InlineKeyboardButton(mark(55), callback_data="score_set_55"),
         InlineKeyboardButton(mark(60), callback_data="score_set_60")],
        [InlineKeyboardButton(mark(65), callback_data="score_set_65"),
         InlineKeyboardButton(mark(70), callback_data="score_set_70"),
         InlineKeyboardButton(mark(75), callback_data="score_set_75"),
         InlineKeyboardButton(mark(80), callback_data="score_set_80")],
        [InlineKeyboardButton("-5", callback_data="score_down"),
         InlineKeyboardButton(f"  {s}/100  ", callback_data="noop"),
         InlineKeyboardButton("+5", callback_data="score_up")],
        [InlineKeyboardButton("Retour", callback_data="menu_main")],
    ])

# ── Marques (sous-panel avec recherche) ──────────────────────────────────
ITEMS_PER_PAGE = 8

def get_brand_list(search: str = "") -> list:
    if search:
        s = search.lower().strip()
        return [b for b in BRANDS if s in b.lower()]
    return list(BRANDS)

def build_brands_text(page: int = 0, search: str = "") -> str:
    lst = get_brand_list(search)
    total = len(lst)
    start = page * ITEMS_PER_PAGE
    end = min(start + ITEMS_PER_PAGE, total)
    page_total = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

    lines = [f"Gestion des marques\n{'-' * 30}"]
    if search:
        lines.append(f"Recherche : \"{search}\"")
    lines.append(f"Selectionnees : {len(selected_brands)}/{len(BRANDS)}")
    lines.append(f"Page {page + 1}/{page_total}\n{'-' * 30}")

    for i in range(start, end):
        b = lst[i]
        check = "+" if b.lower() in selected_brands else "-"
        lines.append(f"{check} {b}")

    return "\n".join(lines)

def build_brands_keyboard(page: int = 0, search: str = "") -> InlineKeyboardMarkup:
    lst = get_brand_list(search)
    total = len(lst)
    start = page * ITEMS_PER_PAGE
    end = min(start + ITEMS_PER_PAGE, total)
    page_total = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

    buttons = []
    for i in range(start, end):
        b = lst[i]
        b_lower = b.lower()
        indicator = "+" if b_lower in selected_brands else "-"
        idx_in_all = BRANDS.index(b)
        buttons.append([
            InlineKeyboardButton(f"{indicator} {b}", callback_data=f"brand_toggle_{idx_in_all}")
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("Prec", callback_data=f"brand_page_{search}_{page - 1}"))
    nav.append(InlineKeyboardButton(f"{page + 1}/{page_total}", callback_data="noop"))
    if end < total:
        nav.append(InlineKeyboardButton("Suiv", callback_data=f"brand_page_{search}_{page + 1}"))
    if nav:
        buttons.append(nav)

    actions = [
        InlineKeyboardButton("Rechercher", callback_data="brand_search"),
        InlineKeyboardButton("Tout +", callback_data="brand_select_all"),
        InlineKeyboardButton("Tout -", callback_data="brand_deselect_all"),
        InlineKeyboardButton("Valider", callback_data="brand_validate"),
    ]
    buttons.append(actions)
    buttons.append([InlineKeyboardButton("Retour", callback_data="menu_main")])

    return InlineKeyboardMarkup(buttons)

# ── Historique ───────────────────────────────────────────────────────────
def build_historique_text() -> str:
    if not historique_alertes:
        return "Historique\n\nAucune alerte."
    lines = [f"Historique - {len(historique_alertes)} dernieres\n{'-' * 30}"]
    for i, d in enumerate(list(historique_alertes)[:10], 1):
        lines.append(
            f"\n{i}. {d.get('niveau','')} {d['score']}/100\n"
            f"   {d['titre'][:35]} | {d['prix_achat']} -> ~{d['marge']}\n"
            f"   {d['heure']} - <a href='{d['url']}'>Voir</a>"
        )
    if len(historique_alertes) > 10:
        lines.append(f"\n... et {len(historique_alertes) - 10} de plus")
    return "\n".join(lines)

def build_historique_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Vider", callback_data="historique_clear")],
        [InlineKeyboardButton("Retour", callback_data="menu_main")],
    ])

# ── Favoris ──────────────────────────────────────────────────────────────
def build_favoris_text() -> str:
    if not favoris:
        return "Favoris\n\nAucun favori."
    lines = [f"Favoris - {len(favoris)}\n{'-' * 30}"]
    for i, d in enumerate(favoris, 1):
        lines.append(
            f"\n{i}. {d.get('niveau','')} {d['score']}/100\n"
            f"   {d['titre'][:35]}\n"
            f"   {d['prix_achat']} | ~{d['marge']} | {d['heure']}\n"
            f"   <a href='{d['url']}'>Voir</a>"
        )
    return "\n".join(lines)

def build_favoris_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for i, d in enumerate(favoris[:8]):
        buttons.append([InlineKeyboardButton(
            f"#{i+1} {d['titre'][:25]}",
            callback_data=f"fav_del_{i}"
        )])
    buttons.append([InlineKeyboardButton("Tout vider", callback_data="fav_clear")])
    buttons.append([InlineKeyboardButton("Retour", callback_data="menu_main")])
    return InlineKeyboardMarkup(buttons)

# ══════════════════════════════════════════════════════════════════════════════
#  MENU ROUTER
# ══════════════════════════════════════════════════════════════════════════════

MENUS = {
    "main":       (build_main_text,       build_main_keyboard),
    "scan":       (build_scan_text,        build_scan_keyboard),
    "budget":     (build_budget_text,      build_budget_keyboard),
    "score":      (build_score_text,       build_score_keyboard),
    "historique": (build_historique_text,  build_historique_keyboard),
    "favoris":    (build_favoris_text,     build_favoris_keyboard),
}

async def afficher_menu(query, menu: str = "main", **kwargs):
    if menu == "marques":
        page = kwargs.get("page", 0)
        search = kwargs.get("search", "")
        try:
            await query.edit_message_text(
                build_brands_text(page, search),
                reply_markup=build_brands_keyboard(page, search),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        return

    text_fn, kb_fn = MENUS.get(menu, MENUS["main"])
    try:
        await query.edit_message_text(
            text_fn(),
            reply_markup=kb_fn(),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
#  CALLBACK HANDLER
# ══════════════════════════════════════════════════════════════════════════════

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global interaction_count
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("menu_"):
        menu = data.split("_", 1)[1]
        await afficher_menu(query, menu)
        return

    if data == "panel_start":
        config["actif"] = True
    elif data == "panel_pause":
        config["actif"] = False
    elif data == "panel_stop":
        config["actif"] = False
        await query.edit_message_text("Bot arrete.")
        sys.exit(0)
    elif data == "panel_mode":
        config["mode_flux"] = not config["mode_flux"]
        await afficher_menu(query, "main")
        return
    elif data == "panel_reset":
        config.update({"prix_min": 3.0, "prix_max": 200.0, "score_min": 60, "mode_flux": False})
        selected_brands.clear()
        selected_brands.update(b.lower() for b in BRANDS)

    elif data.startswith("budget_"):
        _, pmin, pmax = data.split("_")
        config["prix_min"] = float(pmin)
        config["prix_max"] = float(pmax)
        await afficher_menu(query, "budget")
        return

    elif data == "score_up":
        config["score_min"] = min(95, config["score_min"] + 5)
        await afficher_menu(query, "score")
        return
    elif data == "score_down":
        config["score_min"] = max(30, config["score_min"] - 5)
        await afficher_menu(query, "score")
        return
    elif data.startswith("score_set_"):
        config["score_min"] = int(data.split("_")[2])
        await afficher_menu(query, "score")
        return

    # ── Marques panel ────────────────────────────────────────────────────
    elif data == "brand_search":
        chat_id = update.effective_chat.id
        pending_search[chat_id] = True
        await query.edit_message_text(
            "Recherche de marque\n\n"
            "Tape le nom (ou partie) de la marque a chercher :\n\n"
            "Ex: cor, nik, lux, stone...",
            parse_mode="HTML",
        )
        return

    elif data.startswith("brand_page_"):
        parts = data.split("_", 3)
        search = parts[2]
        page = int(parts[3])
        await afficher_menu(query, "marques", page=page, search=search)
        return

    elif data.startswith("brand_toggle_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(BRANDS):
            b = BRANDS[idx].lower()
            if b in selected_brands:
                selected_brands.discard(b)
            else:
                selected_brands.add(b)
        await afficher_menu(query, "marques")
        return

    elif data == "brand_select_all":
        selected_brands.clear()
        selected_brands.update(b.lower() for b in BRANDS)
        await afficher_menu(query, "marques")
        return

    elif data == "brand_deselect_all":
        selected_brands.clear()
        await afficher_menu(query, "marques")
        return

    elif data == "brand_validate":
        await query.edit_message_text(
            f"{len(selected_brands)}/{len(BRANDS)} marques selectionnees.\n\n"
            f"Le scan utilise maintenant ces marques.",
            parse_mode="HTML",
        )
        return

    # ── Interactions article ────────────────────────────────────────────
    elif data.startswith("skip_"):
        interaction_count += 1
        await query.edit_message_text("Article ignore.")
        return

    elif data.startswith("fav_add_"):
        interaction_count += 1
        item_id_str = data.split("_", 2)[2]
        trouve = next((d for d in historique_alertes if str(d.get("id")) == item_id_str), None)
        if trouve and trouve not in favoris:
            favoris.append(trouve)
            await query.answer("Ajoute aux favoris !", show_alert=True)
        elif trouve in favoris:
            await query.answer("Deja dans les favoris.", show_alert=True)
        else:
            await query.answer("Introuvable.", show_alert=True)
        return

    elif data.startswith("buy_"):
        interaction_count += 1
        item_id_str = data.split("_", 1)[1]
        url = f"https://www.vinted.fr/items/{item_id_str}"
        await query.edit_message_text(
            f"Acheter - <a href='{url}'>ouvrir l'annonce</a>",
            parse_mode="HTML",
        )
        return

    elif data == "historique_clear":
        historique_alertes.clear()
        await afficher_menu(query, "historique")
        return

    elif data.startswith("fav_del_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(favoris):
            favoris.pop(idx)
        await afficher_menu(query, "favoris")
        return
    elif data == "fav_clear":
        favoris.clear()
        await afficher_menu(query, "favoris")
        return

    elif data == "noop":
        return

    await afficher_menu(query, "main")

# ══════════════════════════════════════════════════════════════════════════════
#  MESSAGE HANDLER (pour la recherche de marques)
# ══════════════════════════════════════════════════════════════════════════════

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if pending_search.get(chat_id):
        text = update.message.text.strip()
        pending_search[chat_id] = False
        lst = get_brand_list(text)
        if not lst:
            await update.message.reply_text("Aucune marque trouvee.")
            return
        await update.message.reply_text(
            build_brands_text(0, text),
            parse_mode="HTML",
            reply_markup=build_brands_keyboard(0, text),
        )

# ══════════════════════════════════════════════════════════════════════════════
#  POST INIT & MAIN
# ══════════════════════════════════════════════════════════════════════════════

async def post_init(app: Application):
    asyncio.create_task(boucle_scan(app))
    try:
        await app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=(
                "Bot Vinted Pro pret !\n\n"
                f"{len(selected_brands)} marques actives\n"
                f"Budget : {config['prix_min']} - {config['prix_max']}\n"
                f"Score min : {config['score_min']}/100\n"
                f"Mode : {'flux continu' if config['mode_flux'] else 'un msg/article'}\n\n"
                "/bot pour le panel\n"
                "/analyse &lt;url&gt; pour analyser un article\n"
                "/start pour lancer le scan"
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        print(f"post_init send_message: {e}")

def main():
    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler("bot",     cmd_bot))
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("stop",    cmd_stop))
    app.add_handler(CommandHandler("mode",    cmd_mode))
    app.add_handler(CommandHandler("budget",  cmd_budget))
    app.add_handler(CommandHandler("status",  cmd_status))
    app.add_handler(CommandHandler("analyse", cmd_analyse))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot Vinted Pro en ecoute...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
