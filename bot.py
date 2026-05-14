cat > /home/claude/vinted-bot/bot.py << 'ENDOFFILE'
import requests
import time
import os
import asyncio
import sys
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
TOUTES_LES_MARQUES = {
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
}

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

# Bonus état article
ETAT_BONUS = {
    "neuf avec étiquettes": 12,
    "neuf sans étiquettes": 10,
    "très bon état":         6,
    "bon état":              2,
    "satisfaisant":         -3,
}

# Tailles courantes = plus liquides = bonus
TAILLES_POPULAIRES = {"s", "m", "l", "xl", "42", "44", "38", "40", "36"}

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
    "actif":            False,
    "msg_cooldown":     1,      # délai entre messages Telegram (secondes)
    "prix_min":         3.0,
    "prix_max":         200.0,
    "score_min":        60,
    "marques":          set(TOUTES_LES_MARQUES),
}

seen_ids: set       = set()
favoris: list       = []          # stockage en mémoire
historique: list    = []          # dernières alertes (max 20)
stats = {"scans": 0, "alertes": 0, "filtres": 0}

# Vue active du panel : "main" | "cooldown" | "budget" | "score" | "favoris" | "historique"
panel_view: dict = {}   # message_id → vue active

# ══════════════════════════════════════════════════════════════════════════════
#  SCRAPER
# ══════════════════════════════════════════════════════════════════════════════
def _make_session():
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

def _fetch_sync(query: str) -> list:
    global _session
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "fr-FR,fr;q=0.9",
        "Referer": "https://www.vinted.fr/catalog",
        "X-Requested-With": "XMLHttpRequest",
    }
    url = (
        f"https://www.vinted.fr/api/v2/catalog/items"
        f"?search_text={requests.utils.quote(query)}&per_page=20&order=newest_first"
    )
    try:
        resp = _session.get(url, headers=headers, timeout=15)
        if resp.status_code == 401:
            _session = _make_session()
            resp = _session.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return []
        return resp.json().get("items", [])
    except Exception as e:
        print(f"❌ fetch '{query}': {e}")
        return []

# ══════════════════════════════════════════════════════════════════════════════
#  SCORE /100 INTELLIGENT
# ══════════════════════════════════════════════════════════════════════════════
def calculer_score(prix, revente, marge, marque, titre, etat, taille) -> int:
    t     = titre.lower()
    score = 0

    # 1. Ratio marge/prix — cœur du score (0-40 pts)
    ratio = marge / prix if prix > 0 else 0
    score += min(40, int(ratio * 65))

    # 2. Marge absolue (0-20 pts)
    if   marge >= 150: score += 20
    elif marge >= 100: score += 16
    elif marge >= 50:  score += 12
    elif marge >= 30:  score += 8
    elif marge >= 15:  score += 4

    # 3. Bonus marque hype (0-15 pts)
    if marque in MARQUES_HYPE_BONUS:
        score += 15
    elif marque in REGLES_MARGE and REGLES_MARGE[marque][0] >= 1.8:
        score += 8

    # 4. Bonus keywords hype dans titre (0-10 pts)
    score += min(10, sum(1 for k in KEYWORDS_HYPE if k in t) * 4)

    # 5. Bonus sous-côte extrême (0-8 pts)
    if   revente > prix * 3.5: score += 8
    elif revente > prix * 3.0: score += 6
    elif revente > prix * 2.5: score += 3

    # 6. Bonus état article (0-12 pts)
    etat_lower = (etat or "").lower()
    for k, v in ETAT_BONUS.items():
        if k in etat_lower:
            score += v
            break

    # 7. Bonus taille populaire (+3 pts)
    if taille and taille.lower().strip() in TAILLES_POPULAIRES:
        score += 3

    return max(0, min(100, score))

def niveau_affaire(score: int) -> str:
    if score >= 90: return "💎 PÉPITE EXTRÊME"
    if score >= 78: return "🔥🔥🔥 ÉNORME AFFAIRE"
    if score >= 65: return "🔥🔥 TRÈS BONNE AFFAIRE"
    if score >= 50: return "🔥 BONNE AFFAIRE"
    return "👍 AFFAIRE CORRECTE"

# ══════════════════════════════════════════════════════════════════════════════
#  FILTRAGE & ANALYSE
# ══════════════════════════════════════════════════════════════════════════════
def extraire_prix(item):
    try:
        raw = item.get("price", {})
        return float(raw.get("amount", 0) if isinstance(raw, dict) else raw)
    except (TypeError, ValueError):
        return None

def detecter_marque(titre, marque_vinted):
    t = titre.lower()
    m = marque_vinted.lower().strip()
    for marque in config["marques"]:
        if marque in m or marque in t:
            return marque
    return None

def analyser(item):
    titre      = item.get("title", "") or ""
    marque_raw = item.get("brand_title", "") or ""
    taille     = item.get("size_title", "?")
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
    revente = round(prix * coef, 2)
    marge   = round(revente * 0.90 - prix, 2)
    if marge < marge_min:
        return False, {}

    score = calculer_score(prix, revente, marge, marque, titre, etat, taille)
    if score < config["score_min"]:
        return False, {}

    return True, {
        "titre":    titre,
        "marque":   marque_raw or marque,
        "taille":   taille,
        "etat":     etat,
        "prix":     prix,
        "revente":  revente,
        "marge":    marge,
        "score":    score,
        "niveau":   niveau_affaire(score),
        "url":      f"https://www.vinted.fr/items/{item_id}",
        "item_id":  item_id,
    }

# ══════════════════════════════════════════════════════════════════════════════
#  BOUCLE DE SCAN — continu, sans cooldown global
# ══════════════════════════════════════════════════════════════════════════════
async def boucle_scan(app: Application):
    loop = asyncio.get_event_loop()

    while True:
        if not config["actif"]:
            await asyncio.sleep(3)
            continue

        stats["scans"] += 1
        print(f"\n🔍 Scan #{stats['scans']} — {time.strftime('%H:%M:%S')}")
        alertes_scan = 0

        for query in SEARCH_QUERIES:
            if not config["actif"]:
                break
            try:
                items = await loop.run_in_executor(None, _fetch_sync, query)
            except Exception as e:
                print(f"❌ Executor: {e}")
                items = []

            for item in items:
                item_id = item.get("id")
                if not item_id or item_id in seen_ids:
                    continue
                seen_ids.add(item_id)
                if len(seen_ids) > 50000:
                    seen_ids.clear()

                stats["filtres"] += 1
                ok, d = analyser(item)
                if not ok:
                    continue

                alertes_scan     += 1
                stats["alertes"] += 1

                # Historique (max 20)
                historique.insert(0, d)
                if len(historique) > 20:
                    historique.pop()

                msg = (
                    f"{d['niveau']} — <b>{d['score']}/100</b>\n\n"
                    f"👕 <b>{d['titre']}</b>\n"
                    f"🏷️ Marque : {d['marque']}\n"
                    f"📐 Taille : {d['taille']}  |  🏅 État : {d['etat']}\n"
                    f"💶 Prix achat : <b>{d['prix']}€</b>\n"
                    f"📈 Revente estimée : ~<b>{d['revente']}€</b>\n"
                    f"💰 Marge nette : ~<b>{d['marge']}€</b>\n\n"
                    f"🔗 <a href='{d['url']}'>Voir l'annonce</a>"
                )
                print(f"  🚨 {d['titre'][:45]} | {d['score']}/100 | marge ~{d['marge']}€")
                try:
                    sent = await app.bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text=msg,
                        parse_mode="HTML",
                        disable_web_page_preview=False,
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("⭐ Ajouter aux favoris", callback_data=f"fav_add_{item_id}")
                        ]])
                    )
                except Exception as e:
                    print(f"❌ Telegram: {e}")

                # Cooldown entre messages uniquement
                await asyncio.sleep(config["msg_cooldown"])

            await asyncio.sleep(2)  # pause polie entre requêtes Vinted

        print(f"✅ Scan #{stats['scans']} terminé — {alertes_scan} alertes")

# ══════════════════════════════════════════════════════════════════════════════
#  PANEL /bot — VUES MULTIPLES
# ══════════════════════════════════════════════════════════════════════════════
def _fmt_cooldown(s):
    return f"{s}s" if s < 60 else f"{s//60}min"

def panel_main_text():
    etat    = "✅ EN COURS" if config["actif"] else "⏸ EN PAUSE"
    uptime  = f"Scan #{stats['scans']} | {stats['alertes']} alertes envoyées"
    return (
        f"╔══════════════════════╗\n"
        f"║   🤖  VINTED BOT     ║\n"
        f"╚══════════════════════╝\n\n"
        f"<b>État :</b> {etat}\n"
        f"<b>📊</b> {uptime}\n\n"
        f"<b>⏱ Cooldown msg :</b> {_fmt_cooldown(config['msg_cooldown'])}\n"
        f"<b>💶 Budget :</b> {config['prix_min']}€ – {config['prix_max']}€\n"
        f"<b>🎯 Score min :</b> {config['score_min']}/100\n"
        f"<b>🏷️ Marques :</b> {len(config['marques'])} actives\n"
        f"<b>⭐ Favoris :</b> {len(favoris)}\n\n"
        f"<i>Sélectionne une section :</i>"
    )

def panel_main_kb():
    etat_btn = "⏸ Pause" if config["actif"] else "▶️ Start"
    etat_cb  = "panel_pause" if config["actif"] else "panel_start"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(etat_btn,    callback_data=etat_cb),
            InlineKeyboardButton("⏹ Stop",    callback_data="panel_stop"),
        ],
        [
            InlineKeyboardButton("⏱ Cooldown msg",  callback_data="view_cooldown"),
            InlineKeyboardButton("💶 Budget",        callback_data="view_budget"),
        ],
        [
            InlineKeyboardButton("🎯 Score min",     callback_data="view_score"),
            InlineKeyboardButton("🏷️ Marques",      callback_data="view_marques"),
        ],
        [
            InlineKeyboardButton("⭐ Favoris",       callback_data="view_favoris"),
            InlineKeyboardButton("📋 Historique",    callback_data="view_historique"),
        ],
        [
            InlineKeyboardButton("♻️ Reset config",  callback_data="panel_reset"),
            InlineKeyboardButton("🔄 Actualiser",    callback_data="panel_refresh"),
        ],
    ])

def panel_cooldown_text():
    return (
        f"⏱ <b>Cooldown entre messages</b>\n\n"
        f"Actuel : <b>{_fmt_cooldown(config['msg_cooldown'])}</b>\n\n"
        f"Choisir un délai :"
    )

def panel_cooldown_kb():
    options = [1, 2, 3, 5, 10, 30]
    rows = []
    row = []
    for s in options:
        mark = "✅ " if config["msg_cooldown"] == s else ""
        row.append(InlineKeyboardButton(f"{mark}{_fmt_cooldown(s)}", callback_data=f"cd_{s}"))
        if len(row) == 3:
            rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton("◀️ Retour", callback_data="view_main")])
    return InlineKeyboardMarkup(rows)

def panel_budget_text():
    return (
        f"💶 <b>Budget</b>\n\n"
        f"Actuel : <b>{config['prix_min']}€ – {config['prix_max']}€</b>\n\n"
        f"Sélectionner une fourchette :"
    )

def panel_budget_kb():
    presets = [("5–50€", 5, 50), ("5–100€", 5, 100), ("5–150€", 5, 150),
               ("5–200€", 5, 200), ("10–300€", 10, 300), ("3–500€", 3, 500)]
    rows = []
    row  = []
    for label, pmin, pmax in presets:
        mark = "✅ " if config["prix_min"] == pmin and config["prix_max"] == pmax else ""
        row.append(InlineKeyboardButton(f"{mark}{label}", callback_data=f"budget_{pmin}_{pmax}"))
        if len(row) == 3:
            rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton("◀️ Retour", callback_data="view_main")])
    return InlineKeyboardMarkup(rows)

def panel_score_text():
    return (
        f"🎯 <b>Score minimum</b>\n\n"
        f"Actuel : <b>{config['score_min']}/100</b>\n\n"
        f"Plus le score est élevé, moins d'alertes mais plus de qualité.\n\n"
        f"  30 = tout passe\n"
        f"  50 = bonnes affaires\n"
        f"  65 = très bonnes affaires\n"
        f"  78 = énormes affaires seulement\n"
        f"  90 = pépites uniquement"
    )

def panel_score_kb():
    presets = [30, 40, 50, 60, 65, 70, 78, 85, 90]
    rows = []
    row  = []
    for s in presets:
        mark = "✅ " if config["score_min"] == s else ""
        row.append(InlineKeyboardButton(f"{mark}{s}", callback_data=f"score_{s}"))
        if len(row) == 3:
            rows.append(row); row = []
    if row: rows.append(row)
    rows.append([
        InlineKeyboardButton("▼ -5", callback_data="score_down"),
        InlineKeyboardButton("▲ +5", callback_data="score_up"),
        InlineKeyboardButton("◀️ Retour", callback_data="view_main"),
    ])
    return InlineKeyboardMarkup(rows)

def panel_favoris_text():
    if not favoris:
        return "⭐ <b>Favoris</b>\n\nAucun favori pour le moment.\nAjoute des annonces depuis les alertes."
    lines = [f"⭐ <b>Favoris ({len(favoris)})</b>\n"]
    for i, d in enumerate(favoris[:10], 1):
        lines.append(f"{i}. <a href='{d['url']}'>{d['titre'][:35]}</a> — {d['prix']}€ | marge ~{d['marge']}€")
    return "\n".join(lines)

def panel_favoris_kb():
    rows = []
    if favoris:
        rows.append([InlineKeyboardButton("🗑 Vider les favoris", callback_data="fav_clear")])
    rows.append([InlineKeyboardButton("◀️ Retour", callback_data="view_main")])
    return InlineKeyboardMarkup(rows)

def panel_historique_text():
    if not historique:
        return "📋 <b>Historique</b>\n\nAucune alerte pour le moment."
    lines = [f"📋 <b>Dernières alertes ({len(historique)})</b>\n"]
    for d in historique[:10]:
        lines.append(f"• <a href='{d['url']}'>{d['titre'][:30]}</a> — {d['score']}/100 | {d['prix']}€")
    return "\n".join(lines)

def panel_historique_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Retour", callback_data="view_main")]])

def panel_marques_text():
    return (
        f"🏷️ <b>Marques ({len(config['marques'])} actives)</b>\n\n"
        f"Pour modifier : tape une commande\n\n"
        f"/marque add &lt;nom&gt;\n"
        f"/marque remove &lt;nom&gt;\n"
        f"/marque reset — tout réactiver\n"
        f"/marque list — voir toutes"
    )

def panel_marques_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("♻️ Reset marques", callback_data="marques_reset")],
        [InlineKeyboardButton("◀️ Retour",        callback_data="view_main")],
    ])

VIEWS = {
    "main":       (panel_main_text,       panel_main_kb),
    "cooldown":   (panel_cooldown_text,   panel_cooldown_kb),
    "budget":     (panel_budget_text,     panel_budget_kb),
    "score":      (panel_score_text,      panel_score_kb),
    "favoris":    (panel_favoris_text,    panel_favoris_kb),
    "historique": (panel_historique_text, panel_historique_kb),
    "marques":    (panel_marques_text,    panel_marques_kb),
}

async def _render_panel(query, view="main"):
    txt_fn, kb_fn = VIEWS.get(view, VIEWS["main"])
    try:
        await query.edit_message_text(
            txt_fn(), reply_markup=kb_fn(), parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
#  HANDLERS CALLBACKS
# ══════════════════════════════════════════════════════════════════════════════
async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    data = q.data
    await q.answer()

    # Navigation vues
    if data.startswith("view_"):
        view = data[5:]
        await _render_panel(q, view)
        return

    # Contrôle scan
    if data == "panel_start":
        config["actif"] = True
    elif data == "panel_pause":
        config["actif"] = False
    elif data == "panel_stop":
        config["actif"] = False
        await q.edit_message_text("⛔ Bot arrêté. Railway va le redémarrer automatiquement.")
        sys.exit(0)
    elif data == "panel_refresh":
        pass
    elif data == "panel_reset":
        config.update({"msg_cooldown": 1, "prix_min": 3.0, "prix_max": 200.0,
                       "score_min": 60, "marques": set(TOUTES_LES_MARQUES)})

    # Cooldown msg
    elif data.startswith("cd_"):
        config["msg_cooldown"] = int(data.split("_")[1])
        await _render_panel(q, "cooldown"); return

    # Budget
    elif data.startswith("budget_"):
        _, pmin, pmax = data.split("_")
        config["prix_min"] = float(pmin); config["prix_max"] = float(pmax)
        await _render_panel(q, "budget"); return

    # Score
    elif data.startswith("score_"):
        suffix = data[6:]
        if suffix == "up":
            config["score_min"] = min(95, config["score_min"] + 5)
        elif suffix == "down":
            config["score_min"] = max(30, config["score_min"] - 5)
        else:
            config["score_min"] = int(suffix)
        await _render_panel(q, "score"); return

    # Marques
    elif data == "marques_reset":
        config["marques"] = set(TOUTES_LES_MARQUES)
        await _render_panel(q, "marques"); return

    # Favoris
    elif data.startswith("fav_add_"):
        item_id = data[8:]
        match = next((d for d in historique if str(d.get("item_id")) == item_id), None)
        if match and match not in favoris:
            favoris.insert(0, match)
            await q.answer("⭐ Ajouté aux favoris !", show_alert=True)
        else:
            await q.answer("Déjà dans les favoris.", show_alert=True)
        return
    elif data == "fav_clear":
        favoris.clear()
        await _render_panel(q, "favoris"); return

    await _render_panel(q, "main")

# ══════════════════════════════════════════════════════════════════════════════
#  COMMANDES TEXTE
# ══════════════════════════════════════════════════════════════════════════════
async def cmd_bot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt_fn, kb_fn = VIEWS["main"]
    await update.message.reply_text(txt_fn(), reply_markup=kb_fn(), parse_mode="HTML",
                                    disable_web_page_preview=True)

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config["actif"] = True
    await update.message.reply_text("✅ <b>Scan activé !</b>  Tape /bot pour le panel.", parse_mode="HTML")

async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config["actif"] = False
    await update.message.reply_text("⏸ <b>Scan en pause.</b>  Tape /start pour relancer.", parse_mode="HTML")

async def cmd_cooldown(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        s = int(ctx.args[0]); assert s >= 1
        config["msg_cooldown"] = s
        await update.message.reply_text(f"⏱️ Cooldown msg : <b>{s}s</b>", parse_mode="HTML")
    except Exception:
        await update.message.reply_text("❌ Usage : /cooldown &lt;secondes&gt;  ex: /cooldown 2")

async def cmd_budget(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        pmin, pmax = float(ctx.args[0]), float(ctx.args[1])
        assert pmin >= 0 and pmax > pmin
        config["prix_min"], config["prix_max"] = pmin, pmax
        await update.message.reply_text(f"💶 Budget : <b>{pmin}€ – {pmax}€</b>", parse_mode="HTML")
    except Exception:
        await update.message.reply_text("❌ Usage : /budget &lt;min&gt; &lt;max&gt;  ex: /budget 5 150")

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(panel_main_text(), parse_mode="HTML",
                                    reply_markup=panel_main_kb(), disable_web_page_preview=True)

async def cmd_marque(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        action = ctx.args[0].lower()
    except IndexError:
        await update.message.reply_text("Usage :\n/marque add &lt;nom&gt;\n/marque remove &lt;nom&gt;\n/marque reset\n/marque list")
        return
    if action == "reset":
        config["marques"] = set(TOUTES_LES_MARQUES)
        await update.message.reply_text(f"✅ {len(config['marques'])} marques réactivées.")
    elif action == "list":
        await update.message.reply_text(
            "🏷️ <b>Marques actives :</b>\n" + ", ".join(sorted(config["marques"])),
            parse_mode="HTML"
        )
    elif action in ("add", "remove"):
        nom = " ".join(ctx.args[1:]).lower().strip()
        if not nom:
            await update.message.reply_text(f"❌ Usage : /marque {action} &lt;nom&gt;"); return
        if action == "add":
            config["marques"].add(nom)
            await update.message.reply_text(f"✅ Ajouté : <b>{nom}</b>", parse_mode="HTML")
        else:
            config["marques"].discard(nom)
            await update.message.reply_text(f"🗑️ Retiré : <b>{nom}</b>", parse_mode="HTML")
    else:
        await update.message.reply_text("❌ Action inconnue : add / remove / reset / list")

# ══════════════════════════════════════════════════════════════════════════════
#  DÉMARRAGE
# ══════════════════════════════════════════════════════════════════════════════
async def post_init(app: Application):
    asyncio.create_task(boucle_scan(app))
    await app.bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=(
            "🤖 <b>Bot Vinted prêt !</b>\n\n"
            f"🏷️ {len(config['marques'])} marques chargées\n"
            f"⏱️ Cooldown msg : {config['msg_cooldown']}s\n"
            f"💶 Budget : {config['prix_min']}€ – {config['prix_max']}€\n"
            f"🎯 Score min : {config['score_min']}/100\n\n"
            "👉 Tape /bot pour ouvrir le panel\n"
            "👉 Tape /start pour lancer le scan"
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
    app.add_handler(CommandHandler("bot",      cmd_bot))
    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("stop",     cmd_stop))
    app.add_handler(CommandHandler("cooldown", cmd_cooldown))
    app.add_handler(CommandHandler("budget",   cmd_budget))
    app.add_handler(CommandHandler("marque",   cmd_marque))
    app.add_handler(CommandHandler("status",   cmd_status))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("📡 Bot en écoute…")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
ENDOFFILE
