import requests
import time
import os
import asyncio
import sys
from collections import deque
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════════════════
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

if not TELEGRAM_TOKEN:
    raise EnvironmentError("❌ TELEGRAM_TOKEN manquant.")
if not TELEGRAM_CHAT_ID:
    raise EnvironmentError("❌ TELEGRAM_CHAT_ID manquant.")

# ══════════════════════════════════════════════════════════════════════════════
#  MARQUES & RÈGLES
# ══════════════════════════════════════════════════════════════════════════════
TOUTES_LES_MARQUES = sorted({
    "chrome hearts", "hellstar", "denim tears", "gallery dept", "gallery dept.",
    "rick owens", "drkshdw", "broken planet", "minus two", "no faith studios",
    "corteiz", "crtz", "syna world", "trapstar", "vicinity", "represent",
    "fear of god", "essentials", "off-white", "palm angels", "misbhv",
    "a-cold-wall", "a cold wall", "vivienne westwood",
    "nike", "adidas", "new balance", "stone island", "cp company", "c.p. company",
    "north face", "the north face", "ralph lauren", "polo ralph lauren",
    "lacoste", "carhartt", "levi's", "levis", "moncler", "stussy", "stüssy",
    "arc'teryx", "arcteryx", "patagonia", "supreme", "palace", "jordan",
    "air jordan", "yeezy", "bape", "a bathing ape", "kith",
    "zara", "h&m", "mango", "massimo dutti", "sandro", "maje",
    "ami paris", "jacquemus", "diesel", "calvin klein", "tommy hilfiger",
    "dickies", "uniqlo", "birkenstock", "asics", "sezane", "sézane",
    "puma", "reebok", "converse", "vans", "saucony", "salomon",
    "canada goose", "napapijri", "columbia", "balenciaga", "gucci",
    "burberry", "prada", "dior", "louis vuitton", "acne studios",
    "a.p.c", "apc", "fred perry", "hugo boss",
})

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
    "chrome hearts", "hellstar", "gallery dept", "gallery dept.",
    "rick owens", "drkshdw", "corteiz", "crtz", "supreme", "palace",
    "off-white", "fear of god", "trapstar", "broken planet", "syna world",
    "yeezy", "bape", "jordan", "air jordan", "represent", "minus two",
}

TAILLES_RARES   = {"xxs", "xs", "3xl", "4xl", "5xl", "xxl", "xxxl", "6", "6.5", "13", "14", "15"}
ETATS_PREMIUM   = {"neuf avec étiquette", "neuf sans étiquette", "très bon état"}

REGLES_MARGE = {
    "chrome hearts":     (2.5, 30), "hellstar":          (2.5, 25),
    "gallery dept":      (2.3, 25), "gallery dept.":     (2.3, 25),
    "rick owens":        (2.2, 25), "drkshdw":           (2.2, 25),
    "denim tears":       (2.2, 20), "broken planet":     (2.0, 20),
    "minus two":         (2.0, 20), "trapstar":          (2.0, 20),
    "represent":         (1.9, 18), "fear of god":       (1.9, 20),
    "essentials":        (1.8, 15), "off-white":         (2.0, 25),
    "palm angels":       (1.9, 20), "misbhv":            (1.8, 15),
    "a-cold-wall":       (1.8, 15), "a cold wall":       (1.8, 15),
    "vivienne westwood": (1.9, 20), "corteiz":           (2.2, 20),
    "crtz":              (2.2, 20), "syna world":        (2.0, 18),
    "vicinity":          (1.9, 15), "no faith studios":  (2.0, 15),
    "supreme":           (2.5, 20), "palace":            (2.2, 20),
    "jordan":            (1.8, 15), "air jordan":        (1.8, 15),
    "stone island":      (1.7, 15), "cp company":        (1.7, 15),
    "c.p. company":      (1.7, 15), "balenciaga":        (1.7, 20),
    "arc'teryx":         (1.7, 20), "arcteryx":          (1.7, 20),
    "moncler":           (1.7, 25), "canada goose":      (1.6, 20),
    "north face":        (1.5, 10), "the north face":    (1.5, 10),
    "napapijri":         (1.5, 10), "nike":              (1.5, 10),
    "adidas":            (1.5, 10), "new balance":       (1.5, 10),
    "ralph lauren":      (1.5, 10), "jacquemus":         (1.6, 12),
    "ami paris":         (1.5, 12), "sandro":            (1.5, 10),
    "maje":              (1.4,  8), "lacoste":           (1.4,  8),
    "tommy hilfiger":    (1.4,  8), "carhartt":          (1.4,  8),
    "levi's":            (1.3,  8), "levis":             (1.3,  8),
    "diesel":            (1.4,  8), "calvin klein":      (1.3,  6),
    "birkenstock":       (1.4,  8), "asics":             (1.4,  8),
    "zara":              (1.3,  5), "uniqlo":            (1.3,  5),
    "_defaut":           (1.4,  8),
}

PRIX_MARCHE = {
    "chrome hearts": 400, "hellstar": 120, "gallery dept": 250,
    "rick owens": 350,    "drkshdw": 200,  "supreme": 150,
    "palace": 100,        "off-white": 200,"yeezy": 180,
    "jordan": 120,        "air jordan": 120,"balenciaga": 400,
    "moncler": 600,       "canada goose": 400,"stone island": 200,
    "cp company": 150,    "arc'teryx": 250,"north face": 80,
    "nike": 80,           "adidas": 70,    "new balance": 90,
    "ralph lauren": 60,   "lacoste": 50,   "carhartt": 60,
    "ami paris": 130,     "jacquemus": 150,"sandro": 100,
}

SEARCH_QUERIES = [
    "nike", "adidas", "jordan", "new balance", "stone island",
    "lacoste", "ralph lauren", "tommy hilfiger", "supreme", "palace",
    "corteiz", "north face", "carhartt", "stussy", "yeezy",
    "arc'teryx", "moncler", "cp company", "napapijri", "hellstar",
    "chrome hearts", "rick owens", "broken planet", "trapstar",
    "represent", "fear of god", "off-white", "palm angels",
    "gallery dept", "vivienne westwood", "syna world", "minus two",
]

# ══════════════════════════════════════════════════════════════════════════════
#  ÉTAT GLOBAL
# ══════════════════════════════════════════════════════════════════════════════
config = {
    "actif":        False,
    "msg_cooldown": 1,
    "prix_min":     3.0,
    "prix_max":     200.0,
    "score_min":    60,
    "marques":      set(TOUTES_LES_MARQUES),
}

seen_ids:           set   = set()
historique_alertes: deque = deque(maxlen=50)
favoris:            list  = []

# État sous-panel marques (pagination + recherche)
marques_state = {
    "page":     0,
    "filtre":   "",
    "selected": set(TOUTES_LES_MARQUES),   # miroir de config["marques"]
}
MARQUES_PAR_PAGE = 8

# ══════════════════════════════════════════════════════════════════════════════
#  SESSION HTTP
# ══════════════════════════════════════════════════════════════════════════════
def _make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Accept":          "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9",
    })
    try:
        s.get("https://www.vinted.fr", timeout=10)
    except Exception:
        pass
    return s

_session = _make_session()

_API_HEADERS = {
    "User-Agent":        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept":            "application/json, text/plain, */*",
    "Accept-Language":   "fr-FR,fr;q=0.9",
    "Referer":           "https://www.vinted.fr/catalog",
    "X-Requested-With":  "XMLHttpRequest",
}

# ══════════════════════════════════════════════════════════════════════════════
#  SCRAPING DE BASE
# ══════════════════════════════════════════════════════════════════════════════
def _fetch_sync(query: str, per_page: int = 20) -> list:
    global _session
    url = (
        f"https://www.vinted.fr/api/v2/catalog/items"
        f"?search_text={requests.utils.quote(query)}"
        f"&per_page={per_page}&order=newest_first"
    )
    try:
        resp = _session.get(url, headers=_API_HEADERS, timeout=15)
        if resp.status_code == 401:
            _session = _make_session()
            resp = _session.get(url, headers=_API_HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        return resp.json().get("items", [])
    except Exception as e:
        print(f"❌ fetch '{query}': {e}")
        return []

def _fetch_item_sync(item_id: int) -> dict | None:
    """Récupère un article Vinted par son ID."""
    global _session
    url = f"https://www.vinted.fr/api/v2/items/{item_id}"
    try:
        resp = _session.get(url, headers=_API_HEADERS, timeout=15)
        if resp.status_code == 401:
            _session = _make_session()
            resp = _session.get(url, headers=_API_HEADERS, timeout=15)
        if resp.status_code != 200:
            return None
        return resp.json().get("item")
    except Exception as e:
        print(f"❌ fetch item {item_id}: {e}")
        return None

def _fetch_similaires_sync(marque: str, category_id: int | None, taille: str, per_page: int = 20) -> list:
    """Recherche des articles similaires par marque + catégorie."""
    global _session
    query = marque
    url = (
        f"https://www.vinted.fr/api/v2/catalog/items"
        f"?search_text={requests.utils.quote(query)}"
        f"&per_page={per_page}&order=relevance"
    )
    if category_id:
        url += f"&catalog_ids[]={category_id}"
    try:
        resp = _session.get(url, headers=_API_HEADERS, timeout=15)
        if resp.status_code == 401:
            _session = _make_session()
            resp = _session.get(url, headers=_API_HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        return resp.json().get("items", [])
    except Exception as e:
        print(f"❌ fetch similaires '{marque}': {e}")
        return []

# ══════════════════════════════════════════════════════════════════════════════
#  UTILITAIRES PRIX
# ══════════════════════════════════════════════════════════════════════════════
def extraire_prix(item: dict) -> float | None:
    try:
        raw = item.get("price", {})
        val = raw.get("amount", 0) if isinstance(raw, dict) else raw
        return float(val)
    except (TypeError, ValueError):
        return None

def extraire_photo(item: dict) -> str | None:
    """Retourne l'URL de la première photo de l'article."""
    try:
        photos = item.get("photos") or item.get("photo") or []
        if isinstance(photos, dict):
            return photos.get("url") or photos.get("full_size_url")
        if isinstance(photos, list) and photos:
            p = photos[0]
            return p.get("url") or p.get("full_size_url")
    except Exception:
        pass
    return None

# ══════════════════════════════════════════════════════════════════════════════
#  DÉTECTION MARQUE
# ══════════════════════════════════════════════════════════════════════════════
def detecter_marque(titre: str, marque_vinted: str) -> str | None:
    t = titre.lower()
    m = marque_vinted.lower().strip()
    for marque in config["marques"]:
        if marque in m or marque in t:
            return marque
    return None

# ══════════════════════════════════════════════════════════════════════════════
#  SCORE /100
# ══════════════════════════════════════════════════════════════════════════════
def calculer_score(prix: float, revente: float, marge: float,
                   marque: str, titre: str, taille: str, etat: str) -> int:
    t = titre.lower()
    score = 0

    # 1. Ratio marge/prix (0-35)
    ratio = marge / prix if prix > 0 else 0
    score += min(35, int(ratio * 55))

    # 2. Marge absolue (0-20)
    if   marge >= 100: score += 20
    elif marge >= 50:  score += 15
    elif marge >= 30:  score += 10
    elif marge >= 20:  score += 7
    elif marge >= 10:  score += 4

    # 3. Comparaison prix marché (0-10)
    pm = PRIX_MARCHE.get(marque)
    if pm and pm > 0:
        rm = prix / pm
        if   rm <= 0.20: score += 10
        elif rm <= 0.35: score += 7
        elif rm <= 0.50: score += 4

    # 4. Bonus marque hype (0-15)
    if marque in MARQUES_HYPE_BONUS:
        score += 15
    elif marque in REGLES_MARGE and REGLES_MARGE[marque][0] >= 1.8:
        score += 8

    # 5. Keywords hype (0-8)
    score += min(8, sum(1 for k in KEYWORDS_HYPE if k in t) * 3)

    # 6. Sous-côte extrême (0-6)
    if   revente > prix * 3.0: score += 6
    elif revente > prix * 2.5: score += 4

    # 7. État (0-4)
    if etat.lower() in ETATS_PREMIUM:
        score += 4

    # 8. Taille rare (0-2)
    if taille.lower().strip() in TAILLES_RARES:
        score += 2

    return min(100, score)

def niveau_affaire(score: int) -> str:
    if score >= 90: return "💎 PÉPITE EXTRÊME"
    if score >= 78: return "🔥🔥🔥 ÉNORME AFFAIRE"
    if score >= 65: return "🔥🔥 TRÈS BONNE AFFAIRE"
    if score >= 50: return "🔥 BONNE AFFAIRE"
    return "👍 AFFAIRE CORRECTE"

# ══════════════════════════════════════════════════════════════════════════════
#  ANALYSE D'UN ITEM (sans propagation, filtre de base)
# ══════════════════════════════════════════════════════════════════════════════
def _analyser_item(item: dict, prix_moyen_similaires: float | None = None) -> tuple[bool, dict]:
    """
    Analyse un item Vinted.
    Si prix_moyen_similaires est fourni, la revente estimée = prix_moyen_similaires.
    """
    titre      = item.get("title", "") or ""
    marque_raw = item.get("brand_title", "") or ""
    taille     = item.get("size_title", "?") or "?"
    etat       = item.get("status", "") or ""
    prix       = extraire_prix(item)
    item_id    = item.get("id")
    t          = titre.lower()

    if prix is None or prix < config["prix_min"] or prix > config["prix_max"]:
        return False, {}
    if any(mot in t for mot in KEYWORDS_EXCLUS):
        return False, {}

    marque = detecter_marque(titre, marque_raw)
    if marque is None:
        if not any(k in t for k in KEYWORDS_HYPE):
            return False, {}
        marque = "_defaut"

    coef, marge_min = REGLES_MARGE.get(marque, REGLES_MARGE["_defaut"])

    if prix_moyen_similaires and prix_moyen_similaires > prix:
        revente = round(prix_moyen_similaires, 2)
    else:
        revente = round(prix * coef, 2)

    marge = round(revente * 0.90 - prix, 2)
    if marge < marge_min:
        return False, {}

    score = calculer_score(prix, revente, marge, marque, titre, taille, etat)
    if score < config["score_min"]:
        return False, {}

    photo = extraire_photo(item)
    cat   = item.get("catalog_id") or item.get("category_id")

    data = {
        "id":          item_id,
        "titre":       titre,
        "marque":      marque_raw or marque,
        "marque_key":  marque,
        "taille":      taille,
        "etat":        etat,
        "prix":        prix,
        "revente":     revente,
        "marge":       marge,
        "score":       score,
        "niveau":      niveau_affaire(score),
        "url":         f"https://www.vinted.fr/items/{item_id}",
        "photo":       photo,
        "category_id": cat,
        "heure":       time.strftime("%H:%M:%S"),
        "similaires":  [],
    }
    return True, data

# ══════════════════════════════════════════════════════════════════════════════
#  ANALYSE AVEC PROPAGATION
# ══════════════════════════════════════════════════════════════════════════════
def _trouver_similaires_sync(marque: str, category_id: int | None,
                              taille: str, prix_ref: float,
                              exclure_id: int | None = None) -> list[dict]:
    """
    Cherche 3-10 articles similaires et retourne leurs infos de prix.
    Filtre par taille si possible.
    """
    raw = _fetch_similaires_sync(marque, category_id, taille, per_page=30)
    resultats = []
    for item in raw:
        iid  = item.get("id")
        if iid == exclure_id:
            continue
        prix = extraire_prix(item)
        if prix is None or prix <= 0:
            continue
        # Garde les articles dont le prix est dans ±70% du prix de référence
        if prix < prix_ref * 0.3 or prix > prix_ref * 5:
            continue
        t_sim = (item.get("size_title") or "").lower().strip()
        t_ref = taille.lower().strip()
        taille_match = (not t_ref or t_ref == "?" or t_sim == t_ref or not t_sim)
        resultats.append({
            "id":          iid,
            "prix":        prix,
            "titre":       item.get("title", "")[:40],
            "url":         f"https://www.vinted.fr/items/{iid}",
            "taille_ok":   taille_match,
        })
        if len(resultats) >= 15:
            break

    # Trie par taille correspondante d'abord, puis par prix
    resultats.sort(key=lambda x: (not x["taille_ok"], x["prix"]))
    return resultats[:10]

def analyse_propagation_sync(item: dict, profondeur: int = 0,
                              visites: set | None = None) -> dict | None:
    """
    Analyse un item avec recherche de similaires et propagation.
    Retourne le meilleur deal trouvé (dict enrichi) ou None si pas rentable.
    Profondeur max = 2 pour éviter les boucles.
    """
    if visites is None:
        visites = set()

    item_id = item.get("id")
    if item_id in visites or profondeur > 2:
        return None
    visites.add(item_id)

    titre      = item.get("title", "") or ""
    marque_raw = item.get("brand_title", "") or ""
    taille     = item.get("size_title", "?") or "?"
    prix       = extraire_prix(item)

    if prix is None:
        return None

    marque = detecter_marque(titre, marque_raw)
    if marque is None:
        if not any(k in titre.lower() for k in KEYWORDS_HYPE):
            return None
        marque = "_defaut"

    category_id = item.get("catalog_id") or item.get("category_id")

    # 1. Chercher similaires
    similaires = _trouver_similaires_sync(marque, category_id, taille, prix, exclure_id=item_id)

    if similaires:
        prix_similaires = [s["prix"] for s in similaires]
        prix_moyen      = round(sum(prix_similaires) / len(prix_similaires), 2)
        prix_median     = round(sorted(prix_similaires)[len(prix_similaires) // 2], 2)
        # On prend la médiane pour être conservateur
        prix_revente_reel = prix_median
    else:
        prix_revente_reel = None

    ok, data = _analyser_item(item, prix_moyen_similaires=prix_revente_reel)

    if ok:
        data["similaires"] = similaires[:5]
        if similaires:
            data["prix_moyen_marche"]  = prix_moyen
            data["prix_median_marche"] = prix_median
            data["nb_similaires"]      = len(similaires)
        else:
            data["prix_moyen_marche"]  = data["revente"]
            data["prix_median_marche"] = data["revente"]
            data["nb_similaires"]      = 0

    # 2. Propagation : si un similaire est moins cher → peut-être encore meilleur deal
    meilleur = data if ok else None

    if profondeur < 2 and similaires:
        for sim in similaires[:3]:
            sim_prix = sim["prix"]
            # Propager seulement si le similaire est nettement moins cher
            if sim_prix < prix * 0.85 and sim["id"] not in visites:
                sim_item = _fetch_item_sync(sim["id"])
                if sim_item:
                    candidat = analyse_propagation_sync(sim_item, profondeur + 1, visites)
                    if candidat:
                        if meilleur is None or candidat["score"] > meilleur["score"]:
                            meilleur = candidat

    return meilleur

# ══════════════════════════════════════════════════════════════════════════════
#  ANALYSE DEPUIS UNE URL
# ══════════════════════════════════════════════════════════════════════════════
def _id_depuis_url(url: str) -> int | None:
    """Extrait l'ID Vinted depuis une URL."""
    import re
    m = re.search(r"/items/(\d+)", url)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d{7,})", url)
    if m:
        return int(m.group(1))
    return None

def analyse_depuis_url_sync(url: str) -> dict | None:
    """Point d'entrée pour /analyse <url>."""
    item_id = _id_depuis_url(url)
    if not item_id:
        return None
    item = _fetch_item_sync(item_id)
    if not item:
        return None
    return analyse_propagation_sync(item)

# ══════════════════════════════════════════════════════════════════════════════
#  FORMATAGE MESSAGES TELEGRAM
# ══════════════════════════════════════════════════════════════════════════════
def formater_caption(d: dict) -> str:
    """Caption court pour send_photo (max 1024 chars)."""
    nb_sim = d.get("nb_similaires", 0)
    sim_txt = f"({nb_sim} similaires trouvés)" if nb_sim else ""
    return (
        f"{d['niveau']} — <b>{d['score']}/100</b>\n\n"
        f"👕 <b>{d['titre'][:60]}</b>\n"
        f"🏷️ {d['marque']}  |  📐 {d['taille']}  |  ✨ {d['etat'] or '?'}\n\n"
        f"💶 Achat : <b>{d['prix']}€</b>\n"
        f"📈 Revente : ~<b>{d['revente']}€</b>  {sim_txt}\n"
        f"💰 Marge nette : ~<b>{d['marge']}€</b>\n\n"
        f"🕐 {d['heure']}"
    )

def formater_detail(d: dict) -> str:
    """Message détaillé avec liste des comparés."""
    lines = [f"🔗 <a href='{d['url']}'>Voir l'annonce principale</a>"]

    if d.get("similaires"):
        lines.append("\n📊 <b>Articles comparés :</b>")
        for i, s in enumerate(d["similaires"][:5], 1):
            lines.append(f"  {i}. {s['prix']}€ — <a href='{s['url']}'>{s['titre'][:30]}</a>")

    pm = d.get("prix_moyen_marche")
    pmed = d.get("prix_median_marche")
    if pm:
        lines.append(f"\n📈 Prix moyen marché : <b>{pm}€</b>")
    if pmed and pmed != pm:
        lines.append(f"📉 Prix médian : <b>{pmed}€</b>")

    return "\n".join(lines)

def build_alerte_keyboard(item_id) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⏭ Skip",            callback_data="skip_noop"),
        InlineKeyboardButton("⭐ Favoris",         callback_data=f"fav_add_{item_id}"),
        InlineKeyboardButton("🛒 Acheter",         callback_data=f"acheter_{item_id}"),
    ]])

# ══════════════════════════════════════════════════════════════════════════════
#  ENVOI D'UNE ALERTE (photo + détail)
# ══════════════════════════════════════════════════════════════════════════════
async def envoyer_alerte(app: Application, d: dict):
    markup  = build_alerte_keyboard(d["id"])
    caption = formater_caption(d)
    detail  = formater_detail(d)

    try:
        if d.get("photo"):
            await app.bot.send_photo(
                chat_id=TELEGRAM_CHAT_ID,
                photo=d["photo"],
                caption=caption[:1024],
                parse_mode="HTML",
                reply_markup=markup,
            )
        else:
            await app.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=caption,
                parse_mode="HTML",
                reply_markup=markup,
                disable_web_page_preview=True,
            )

        # Message secondaire avec les comparés
        if detail.strip():
            await app.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=detail,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
    except Exception as e:
        print(f"❌ Telegram envoyer_alerte: {e}")

# ══════════════════════════════════════════════════════════════════════════════
#  BOUCLE DE SCAN INTELLIGENTE
# ══════════════════════════════════════════════════════════════════════════════
async def boucle_scan(app: Application):
    loop = asyncio.get_event_loop()
    alert_queue: asyncio.Queue = asyncio.Queue()

    async def expediteur():
        while True:
            d = await alert_queue.get()
            await envoyer_alerte(app, d)
            qs    = alert_queue.qsize()
            delay = config["msg_cooldown"] * (1 + qs // 5)
            await asyncio.sleep(min(delay, 10))

    asyncio.create_task(expediteur())

    while True:
        if not config["actif"]:
            await asyncio.sleep(3)
            continue

        print(f"\n🔍 Scan — {time.strftime('%H:%M:%S')}")
        alertes = 0

        for query in SEARCH_QUERIES:
            if not config["actif"]:
                break
            try:
                items = await loop.run_in_executor(None, _fetch_sync, query)
            except Exception as e:
                print(f"❌ Executor fetch: {e}")
                items = []

            for item in items:
                item_id = item.get("id")
                if not item_id or item_id in seen_ids:
                    continue
                seen_ids.add(item_id)
                if len(seen_ids) > 50_000:
                    seen_ids.difference_update(list(seen_ids)[:25_000])

                # Pré-filtre rapide avant propagation coûteuse
                titre = item.get("title", "") or ""
                t     = titre.lower()
                if any(mot in t for mot in KEYWORDS_EXCLUS):
                    continue
                marque_raw = item.get("brand_title", "") or ""
                marque     = detecter_marque(titre, marque_raw)
                if marque is None and not any(k in t for k in KEYWORDS_HYPE):
                    continue

                # Analyse complète avec similaires + propagation
                try:
                    d = await loop.run_in_executor(
                        None, analyse_propagation_sync, item, 0, None
                    )
                except Exception as e:
                    print(f"❌ Analyse: {e}")
                    d = None

                if d is None:
                    continue

                alertes += 1
                historique_alertes.appendleft(d)
                await alert_queue.put(d)
                print(f"  🚨 {d['titre'][:45]} | {d['score']}/100 | ~{d['marge']}€ | {d.get('nb_similaires', 0)} similaires")

            await asyncio.sleep(1.5)

        print(f"✅ Cycle terminé — {alertes} alertes")
        await asyncio.sleep(1)

# ══════════════════════════════════════════════════════════════════════════════
#  PANEL PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
def build_main_text() -> str:
    etat = "✅ Actif" if config["actif"] else "⏸ En pause"
    return (
        f"🤖 <b>Vinted Bot — Panel de contrôle</b>\n"
        f"{'─' * 32}\n"
        f"{'🟢' if config['actif'] else '🔴'} État          : <b>{etat}</b>\n"
        f"📨 Cooldown msg : <b>{config['msg_cooldown']}s</b>\n"
        f"💶 Budget        : <b>{config['prix_min']}€ – {config['prix_max']}€</b>\n"
        f"🎯 Score min     : <b>{config['score_min']}/100</b>\n"
        f"🏷️ Marques        : <b>{len(config['marques'])}</b>\n"
        f"📋 Historique    : <b>{len(historique_alertes)}</b> alertes\n"
        f"⭐ Favoris       : <b>{len(favoris)}</b> annonces\n"
        f"{'─' * 32}\n"
        f"<i>Choisis une catégorie :</i>"
    )

def build_main_keyboard() -> InlineKeyboardMarkup:
    etat_btn = "⏸ Pause"    if config["actif"] else "▶️ Démarrer"
    etat_cb  = "panel_pause" if config["actif"] else "panel_start"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(etat_btn,           callback_data=etat_cb),
            InlineKeyboardButton("⏹ Arrêter",         callback_data="panel_stop"),
        ],
        [
            InlineKeyboardButton("📡 Scan",           callback_data="menu_scan"),
            InlineKeyboardButton("💶 Budget",          callback_data="menu_budget"),
            InlineKeyboardButton("🎯 Score",           callback_data="menu_score"),
        ],
        [
            InlineKeyboardButton("🏷️ Marques",         callback_data="menu_marques"),
            InlineKeyboardButton("📋 Historique",      callback_data="menu_historique"),
            InlineKeyboardButton("⭐ Favoris",         callback_data="menu_favoris"),
        ],
        [
            InlineKeyboardButton("🔁 Reset config",    callback_data="panel_reset"),
            InlineKeyboardButton("🔄 Actualiser",      callback_data="menu_main"),
        ],
    ])

# ══════════════════════════════════════════════════════════════════════════════
#  SOUS-MENU : SCAN
# ══════════════════════════════════════════════════════════════════════════════
def build_scan_text() -> str:
    return (
        f"📡 <b>Paramètres de scan</b>\n"
        f"{'─' * 30}\n"
        f"⚡ Scan <b>continu</b> avec analyse similaires + propagation\n\n"
        f"📨 Cooldown entre messages : <b>{config['msg_cooldown']}s</b>\n"
        f"   <i>(augmente auto si trop d'alertes)</i>\n"
        f"{'─' * 30}\n"
        f"<i>Choisis le délai entre messages :</i>"
    )

def build_scan_keyboard() -> InlineKeyboardMarkup:
    cd = config["msg_cooldown"]
    def mark(v): return f"✅ {v}s" if cd == v else f"{v}s"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(mark(1), callback_data="msgcd_1"),
         InlineKeyboardButton(mark(2), callback_data="msgcd_2"),
         InlineKeyboardButton(mark(3), callback_data="msgcd_3")],
        [InlineKeyboardButton(mark(5), callback_data="msgcd_5"),
         InlineKeyboardButton(mark(10), callback_data="msgcd_10"),
         InlineKeyboardButton(mark(30), callback_data="msgcd_30")],
        [InlineKeyboardButton("◀️ Retour", callback_data="menu_main")],
    ])

# ══════════════════════════════════════════════════════════════════════════════
#  SOUS-MENU : BUDGET
# ══════════════════════════════════════════════════════════════════════════════
def build_budget_text() -> str:
    return (
        f"💶 <b>Filtre budget</b>\n"
        f"{'─' * 30}\n"
        f"Actuel : <b>{config['prix_min']}€ – {config['prix_max']}€</b>\n"
        f"{'─' * 30}\n"
        f"<i>Choisis une plage de prix :</i>"
    )

def build_budget_keyboard() -> InlineKeyboardMarkup:
    cur = (config["prix_min"], config["prix_max"])
    def mark(a, b): return f"✅ {a}–{b}€" if cur == (float(a), float(b)) else f"{a}–{b}€"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(mark(3, 30),   callback_data="budget_3_30"),
         InlineKeyboardButton(mark(3, 50),   callback_data="budget_3_50"),
         InlineKeyboardButton(mark(5, 50),   callback_data="budget_5_50")],
        [InlineKeyboardButton(mark(5, 100),  callback_data="budget_5_100"),
         InlineKeyboardButton(mark(5, 150),  callback_data="budget_5_150"),
         InlineKeyboardButton(mark(5, 200),  callback_data="budget_5_200")],
        [InlineKeyboardButton(mark(10, 300), callback_data="budget_10_300"),
         InlineKeyboardButton(mark(10, 500), callback_data="budget_10_500")],
        [InlineKeyboardButton("◀️ Retour",    callback_data="menu_main")],
    ])

# ══════════════════════════════════════════════════════════════════════════════
#  SOUS-MENU : SCORE
# ══════════════════════════════════════════════════════════════════════════════
def build_score_text() -> str:
    s = config["score_min"]
    explication = {
        range(30, 50): "🟡 Mode large — beaucoup d'alertes",
        range(50, 65): "🟠 Mode équilibré — recommandé",
        range(65, 80): "🔴 Mode strict — bonnes affaires sûres",
        range(80, 96): "💎 Mode expert — pépites seulement",
    }
    desc = next((v for k, v in explication.items() if s in k), "")
    return (
        f"🎯 <b>Score minimum</b>\n"
        f"{'─' * 30}\n"
        f"Score actuel : <b>{s}/100</b>\n"
        f"{desc}\n"
        f"{'─' * 30}\n"
        f"<i>Ajuste le seuil :</i>"
    )

def build_score_keyboard() -> InlineKeyboardMarkup:
    s = config["score_min"]
    def mark(v): return f"✅ {v}" if s == v else str(v)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(mark(40), callback_data="score_set_40"),
         InlineKeyboardButton(mark(50), callback_data="score_set_50"),
         InlineKeyboardButton(mark(55), callback_data="score_set_55"),
         InlineKeyboardButton(mark(60), callback_data="score_set_60")],
        [InlineKeyboardButton(mark(65), callback_data="score_set_65"),
         InlineKeyboardButton(mark(70), callback_data="score_set_70"),
         InlineKeyboardButton(mark(75), callback_data="score_set_75"),
         InlineKeyboardButton(mark(80), callback_data="score_set_80")],
        [InlineKeyboardButton("▼ -5",     callback_data="score_down"),
         InlineKeyboardButton(f"  {s}/100  ", callback_data="noop"),
         InlineKeyboardButton("▲ +5",     callback_data="score_up")],
        [InlineKeyboardButton("◀️ Retour", callback_data="menu_main")],
    ])

# ══════════════════════════════════════════════════════════════════════════════
#  SOUS-MENU : MARQUES (pagination + sélection + recherche)
# ══════════════════════════════════════════════════════════════════════════════
def _marques_filtrees() -> list[str]:
    """Retourne la liste triée des marques correspondant au filtre actuel."""
    f = marques_state["filtre"].lower().strip()
    if f:
        return [m for m in TOUTES_LES_MARQUES if f in m]
    return list(TOUTES_LES_MARQUES)

def build_marques_text() -> str:
    total    = len(TOUTES_LES_MARQUES)
    selected = len(marques_state["selected"])
    filtre   = marques_state["filtre"]
    filtrees = _marques_filtrees()
    nb_pages = max(1, (len(filtrees) + MARQUES_PAR_PAGE - 1) // MARQUES_PAR_PAGE)
    page     = marques_state["page"]

    filtre_txt = f"\n🔍 Filtre actif : <b>{filtre}</b>  ({len(filtrees)} résultats)" if filtre else ""
    return (
        f"🏷️ <b>Gestion des marques</b>\n"
        f"{'─' * 30}\n"
        f"Actives : <b>{selected}/{total}</b>{filtre_txt}\n"
        f"Page <b>{page + 1}/{nb_pages}</b>\n"
        f"{'─' * 30}\n"
        f"<i>Coche/décoche les marques. Tape /recherche &lt;mot&gt; pour filtrer.</i>"
    )

def build_marques_keyboard() -> InlineKeyboardMarkup:
    filtrees = _marques_filtrees()
    page     = marques_state["page"]
    selected = marques_state["selected"]
    nb_pages = max(1, (len(filtrees) + MARQUES_PAR_PAGE - 1) // MARQUES_PAR_PAGE)

    debut = page * MARQUES_PAR_PAGE
    tranche = filtrees[debut:debut + MARQUES_PAR_PAGE]

    rows = []
    # Boutons marques (2 par ligne)
    paire = []
    for m in tranche:
        checked = "✅" if m in selected else "☑️"
        label   = f"{checked} {m[:18]}"
        cb      = f"mrq_toggle_{m[:40]}"   # callback_data max 64 chars
        paire.append(InlineKeyboardButton(label, callback_data=cb))
        if len(paire) == 2:
            rows.append(paire)
            paire = []
    if paire:
        rows.append(paire)

    # Navigation pages
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data="mrq_page_prev"))
    nav.append(InlineKeyboardButton(f"{page + 1}/{nb_pages}", callback_data="noop"))
    if page < nb_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data="mrq_page_next"))
    if nav:
        rows.append(nav)

    # Actions globales
    rows.append([
        InlineKeyboardButton("✅ Tout sélectionner",   callback_data="mrq_all"),
        InlineKeyboardButton("☑️ Tout désélectionner", callback_data="mrq_none"),
    ])
    rows.append([
        InlineKeyboardButton("💾 Valider",             callback_data="mrq_valider"),
        InlineKeyboardButton("🔁 Reset",               callback_data="mrq_reset"),
    ])
    rows.append([InlineKeyboardButton("◀️ Retour",     callback_data="menu_main")])
    return InlineKeyboardMarkup(rows)

# ══════════════════════════════════════════════════════════════════════════════
#  SOUS-MENU : HISTORIQUE
# ══════════════════════════════════════════════════════════════════════════════
def build_historique_text() -> str:
    if not historique_alertes:
        return "📋 <b>Historique des alertes</b>\n\nAucune alerte pour le moment."
    lines = [f"📋 <b>Historique — {len(historique_alertes)} dernières alertes</b>\n{'─' * 30}"]
    for i, d in enumerate(list(historique_alertes)[:10], 1):
        nb_sim = d.get("nb_similaires", 0)
        sim_txt = f" ({nb_sim} similaires)" if nb_sim else ""
        lines.append(
            f"\n<b>{i}.</b> {d['niveau']} <b>{d['score']}/100</b>\n"
            f"   {d['titre'][:35]} | {d['prix']}€ → ~{d['marge']}€{sim_txt}\n"
            f"   🕐 {d['heure']} — <a href='{d['url']}'>Voir</a>"
        )
    if len(historique_alertes) > 10:
        lines.append(f"\n<i>... et {len(historique_alertes) - 10} de plus</i>")
    return "\n".join(lines)

def build_historique_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ Vider l'historique", callback_data="historique_clear")],
        [InlineKeyboardButton("◀️ Retour",              callback_data="menu_main")],
    ])

# ══════════════════════════════════════════════════════════════════════════════
#  SOUS-MENU : FAVORIS
# ══════════════════════════════════════════════════════════════════════════════
def build_favoris_text() -> str:
    if not favoris:
        return "⭐ <b>Favoris</b>\n\nAucun favori.\n\n<i>Clique sur ⭐ dans une alerte.</i>"
    lines = [f"⭐ <b>Favoris — {len(favoris)} annonces</b>\n{'─' * 30}"]
    for i, d in enumerate(favoris, 1):
        lines.append(
            f"\n<b>{i}.</b> {d['niveau']} <b>{d['score']}/100</b>\n"
            f"   {d['titre'][:35]}\n"
            f"   💶 {d['prix']}€ | 💰 ~{d['marge']}€ | 🕐 {d['heure']}\n"
            f"   <a href='{d['url']}'>Voir l'annonce</a>"
        )
    return "\n".join(lines)

def build_favoris_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for i, d in enumerate(favoris[:8]):
        buttons.append([InlineKeyboardButton(
            f"🗑️ #{i+1} — {d['titre'][:25]}", callback_data=f"fav_del_{i}"
        )])
    buttons.append([InlineKeyboardButton("🗑️ Vider tous",  callback_data="fav_clear")])
    buttons.append([InlineKeyboardButton("◀️ Retour",       callback_data="menu_main")])
    return InlineKeyboardMarkup(buttons)

# ══════════════════════════════════════════════════════════════════════════════
#  ROUTEUR DE MENUS
# ══════════════════════════════════════════════════════════════════════════════
MENUS = {
    "main":       (build_main_text,       build_main_keyboard),
    "scan":       (build_scan_text,       build_scan_keyboard),
    "budget":     (build_budget_text,     build_budget_keyboard),
    "score":      (build_score_text,      build_score_keyboard),
    "marques":    (build_marques_text,    build_marques_keyboard),
    "historique": (build_historique_text, build_historique_keyboard),
    "favoris":    (build_favoris_text,    build_favoris_keyboard),
}

async def afficher_menu(query, menu: str = "main"):
    text_fn, kb_fn = MENUS.get(menu, MENUS["main"])
    try:
        await query.edit_message_text(
            text_fn(), reply_markup=kb_fn(),
            parse_mode="HTML", disable_web_page_preview=True,
        )
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
#  COMMANDES TELEGRAM
# ══════════════════════════════════════════════════════════════════════════════
async def cmd_bot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text_fn, kb_fn = MENUS["main"]
    await update.message.reply_text(
        text_fn(), reply_markup=kb_fn(),
        parse_mode="HTML", disable_web_page_preview=True,
    )

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config["actif"] = True
    await update.message.reply_text("✅ <b>Scan activé !</b>", parse_mode="HTML")

async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config["actif"] = False
    await update.message.reply_text("⏸ <b>Scan mis en pause.</b>", parse_mode="HTML")

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        build_main_text() + "\n\n👉 /bot pour le panel",
        parse_mode="HTML",
    )

async def cmd_budget(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        pmin, pmax = float(ctx.args[0]), float(ctx.args[1])
        assert pmin >= 0 and pmax > pmin
        config["prix_min"], config["prix_max"] = pmin, pmax
        await update.message.reply_text(f"💶 Budget : <b>{pmin}€ – {pmax}€</b>", parse_mode="HTML")
    except Exception:
        await update.message.reply_text("❌ Usage : /budget &lt;min&gt; &lt;max&gt;  ex: /budget 5 150")

async def cmd_marque(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        action = ctx.args[0].lower()
    except IndexError:
        await update.message.reply_text(
            "Usage :\n/marque add &lt;nom&gt;\n/marque remove &lt;nom&gt;\n"
            "/marque reset\n/marque list"
        )
        return

    if action == "reset":
        config["marques"] = set(TOUTES_LES_MARQUES)
        marques_state["selected"] = set(TOUTES_LES_MARQUES)
        await update.message.reply_text(f"✅ {len(config['marques'])} marques réactivées.")
    elif action == "list":
        texte = "🏷️ <b>Marques actives :</b>\n" + ", ".join(sorted(config["marques"]))
        await update.message.reply_text(texte[:4000], parse_mode="HTML")
    elif action in ("add", "remove"):
        nom = " ".join(ctx.args[1:]).lower().strip()
        if not nom:
            await update.message.reply_text(f"❌ Usage : /marque {action} &lt;nom&gt;")
            return
        if action == "add":
            config["marques"].add(nom)
            marques_state["selected"].add(nom)
            await update.message.reply_text(f"✅ Ajouté : <b>{nom}</b>", parse_mode="HTML")
        else:
            config["marques"].discard(nom)
            marques_state["selected"].discard(nom)
            await update.message.reply_text(f"🗑️ Retiré : <b>{nom}</b>", parse_mode="HTML")
    else:
        await update.message.reply_text("❌ Action inconnue : add / remove / reset / list")

async def cmd_analyse(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Analyse une URL Vinted avec propagation et envoie un rapport complet."""
    if not ctx.args:
        await update.message.reply_text(
            "❌ Usage : /analyse &lt;url_vinted&gt;\n"
            "Ex : /analyse https://www.vinted.fr/items/123456",
            parse_mode="HTML",
        )
        return

    url = ctx.args[0].strip()
    msg_wait = await update.message.reply_text("⏳ Analyse en cours…")

    loop = asyncio.get_event_loop()
    try:
        d = await loop.run_in_executor(None, analyse_depuis_url_sync, url)
    except Exception as e:
        await msg_wait.delete()
        await update.message.reply_text(f"❌ Erreur lors de l'analyse : {e}")
        return

    await msg_wait.delete()

    if d is None:
        await update.message.reply_text(
            "❌ Impossible d'analyser cet article.\n"
            "Vérifie que l'URL est valide et que l'article existe encore.",
            parse_mode="HTML",
        )
        return

    # Ignorer le filtre score_min pour /analyse (analyse manuelle)
    markup  = build_alerte_keyboard(d["id"])
    caption = formater_caption(d)
    detail  = formater_detail(d)

    try:
        if d.get("photo"):
            await update.message.reply_photo(
                photo=d["photo"],
                caption=caption[:1024],
                parse_mode="HTML",
                reply_markup=markup,
            )
        else:
            await update.message.reply_text(
                caption, parse_mode="HTML",
                reply_markup=markup,
                disable_web_page_preview=True,
            )
        if detail.strip():
            await update.message.reply_text(
                detail, parse_mode="HTML", disable_web_page_preview=True,
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur envoi message : {e}")

    # Ajout à l'historique
    historique_alertes.appendleft(d)

async def cmd_recherche(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Filtre la liste des marques dans le sous-panel."""
    filtre = " ".join(ctx.args).lower().strip() if ctx.args else ""
    marques_state["filtre"] = filtre
    marques_state["page"]   = 0
    if filtre:
        nb = len(_marques_filtrees())
        await update.message.reply_text(
            f"🔍 Filtre marques : <b>{filtre}</b> — {nb} résultat(s)\n"
            f"Ouvre /bot → 🏷️ Marques pour voir.",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text("🔍 Filtre réinitialisé.")

# ══════════════════════════════════════════════════════════════════════════════
#  CALLBACK HANDLER
# ══════════════════════════════════════════════════════════════════════════════
async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data  = query.data

    # ── Navigation menus ──────────────────────────────────────
    if data.startswith("menu_"):
        await afficher_menu(query, data[5:])
        return

    # ── Contrôle scan ─────────────────────────────────────────
    if data == "panel_start":
        config["actif"] = True
    elif data == "panel_pause":
        config["actif"] = False
    elif data == "panel_stop":
        config["actif"] = False
        await query.edit_message_text("⛔ Bot arrêté. Railway va le redémarrer.")
        sys.exit(0)
    elif data == "panel_reset":
        config.update({
            "msg_cooldown": 1, "prix_min": 3.0,
            "prix_max": 200.0, "score_min": 60,
            "marques": set(TOUTES_LES_MARQUES),
        })
        marques_state["selected"] = set(TOUTES_LES_MARQUES)

    # ── Cooldown messages ─────────────────────────────────────
    elif data.startswith("msgcd_"):
        config["msg_cooldown"] = int(data.split("_")[1])
        await afficher_menu(query, "scan"); return

    # ── Budget ────────────────────────────────────────────────
    elif data.startswith("budget_"):
        _, pmin, pmax = data.split("_")
        config["prix_min"] = float(pmin)
        config["prix_max"] = float(pmax)
        await afficher_menu(query, "budget"); return

    # ── Score ─────────────────────────────────────────────────
    elif data == "score_up":
        config["score_min"] = min(95, config["score_min"] + 5)
        await afficher_menu(query, "score"); return
    elif data == "score_down":
        config["score_min"] = max(30, config["score_min"] - 5)
        await afficher_menu(query, "score"); return
    elif data.startswith("score_set_"):
        config["score_min"] = int(data.split("_")[2])
        await afficher_menu(query, "score"); return

    # ── Marques : toggle ─────────────────────────────────────
    elif data.startswith("mrq_toggle_"):
        nom = data[len("mrq_toggle_"):]
        # Cherche le nom complet dans TOUTES_LES_MARQUES (cb tronqué à 40 chars)
        correspondance = next(
            (m for m in TOUTES_LES_MARQUES if m[:40] == nom or m == nom), nom
        )
        if correspondance in marques_state["selected"]:
            marques_state["selected"].discard(correspondance)
        else:
            marques_state["selected"].add(correspondance)
        await afficher_menu(query, "marques"); return

    elif data == "mrq_page_prev":
        marques_state["page"] = max(0, marques_state["page"] - 1)
        await afficher_menu(query, "marques"); return

    elif data == "mrq_page_next":
        filtrees = _marques_filtrees()
        nb_pages = max(1, (len(filtrees) + MARQUES_PAR_PAGE - 1) // MARQUES_PAR_PAGE)
        marques_state["page"] = min(nb_pages - 1, marques_state["page"] + 1)
        await afficher_menu(query, "marques"); return

    elif data == "mrq_all":
        filtrees = _marques_filtrees()
        marques_state["selected"].update(filtrees)
        await afficher_menu(query, "marques"); return

    elif data == "mrq_none":
        filtrees = _marques_filtrees()
        marques_state["selected"].difference_update(filtrees)
        await afficher_menu(query, "marques"); return

    elif data == "mrq_valider":
        config["marques"] = set(marques_state["selected"])
        await query.answer(f"✅ {len(config['marques'])} marques actives.", show_alert=True)
        await afficher_menu(query, "marques"); return

    elif data == "mrq_reset":
        marques_state["selected"] = set(TOUTES_LES_MARQUES)
        config["marques"]         = set(TOUTES_LES_MARQUES)
        marques_state["filtre"]   = ""
        marques_state["page"]     = 0
        await afficher_menu(query, "marques"); return

    # ── Historique ────────────────────────────────────────────
    elif data == "historique_clear":
        historique_alertes.clear()
        await afficher_menu(query, "historique"); return

    # ── Favoris ───────────────────────────────────────────────
    elif data.startswith("fav_add_"):
        item_id_str = data.split("_", 2)[2]
        trouve = next((d for d in historique_alertes if str(d.get("id")) == item_id_str), None)
        if trouve and trouve not in favoris:
            favoris.append(trouve)
            await query.answer("⭐ Ajouté aux favoris !", show_alert=True)
        elif trouve in favoris:
            await query.answer("Déjà dans les favoris.", show_alert=True)
        else:
            await query.answer("Introuvable dans l'historique.", show_alert=True)
        return

    elif data.startswith("fav_del_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(favoris):
            favoris.pop(idx)
        await afficher_menu(query, "favoris"); return

    elif data == "fav_clear":
        favoris.clear()
        await afficher_menu(query, "favoris"); return

    # ── Acheter (ouvre le lien — juste un toast) ──────────────
    elif data.startswith("acheter_"):
        item_id_str = data.split("_", 1)[1]
        trouve = next((d for d in historique_alertes if str(d.get("id")) == item_id_str), None)
        if trouve:
            await query.answer(f"🛒 Ouvre : {trouve['url']}", show_alert=True)
        else:
            await query.answer("🛒 Ouvre l'annonce dans le navigateur.", show_alert=True)
        return

    elif data in ("noop", "skip_noop"):
        return

    # ── Rafraîchir main ───────────────────────────────────────
    await afficher_menu(query, "main")

# ══════════════════════════════════════════════════════════════════════════════
#  DÉMARRAGE
# ══════════════════════════════════════════════════════════════════════════════
async def post_init(app: Application):
    asyncio.create_task(boucle_scan(app))
    await app.bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=(
            "🤖 <b>Bot Vinted v2 prêt !</b>\n\n"
            f"🏷️ {len(config['marques'])} marques chargées\n"
            f"📨 Cooldown msgs : {config['msg_cooldown']}s\n"
            f"💶 Budget : {config['prix_min']}€ – {config['prix_max']}€\n"
            f"🎯 Score min : {config['score_min']}/100\n"
            f"⚡ Scraping intelligent + propagation activé\n\n"
            "👉 /bot — panel de contrôle\n"
            "👉 /start — lancer le scan\n"
            "👉 /analyse &lt;url&gt; — analyser une annonce\n"
            "👉 /recherche &lt;mot&gt; — filtrer les marques"
        ),
        parse_mode="HTML",
    )

def main():
    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler("bot",       cmd_bot))
    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("stop",      cmd_stop))
    app.add_handler(CommandHandler("budget",    cmd_budget))
    app.add_handler(CommandHandler("marque",    cmd_marque))
    app.add_handler(CommandHandler("status",    cmd_status))
    app.add_handler(CommandHandler("analyse",   cmd_analyse))
    app.add_handler(CommandHandler("recherche", cmd_recherche))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("📡 Bot v2 en écoute…")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
