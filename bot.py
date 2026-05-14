diff --git a/bot.py b/bot.py
index 272c391ffbbb6589efb987196d2521444e0133bd..c6147ad465c2fe91fd6f7dbcf7d854910571ca03 100644
--- a/bot.py
+++ b/bot.py
@@ -1,30 +1,32 @@
 import requests
 import time
 import os
 import asyncio
 import sys
+import re
+import html
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
 TOUTES_LES_MARQUES = {
     "chrome hearts", "hellstar", "denim tears", "gallery dept", "gallery dept.",
     "rick owens", "drkshdw", "broken planet", "minus two", "no faith studios",
     "corteiz", "crtz", "syna world", "trapstar", "vicinity", "represent",
     "fear of god", "essentials", "off-white", "palm angels", "misbhv",
     "a-cold-wall", "a cold wall", "vivienne westwood",
     "nike", "adidas", "new balance", "stone island", "cp company", "c.p. company",
@@ -107,102 +109,119 @@ PRIX_MARCHE = {
     "stone island": 200, "cp company": 150, "arc'teryx": 250,
     "north face": 80, "nike": 80, "adidas": 70, "new balance": 90,
     "ralph lauren": 60, "lacoste": 50, "carhartt": 60,
     "ami paris": 130, "jacquemus": 150, "sandro": 100,
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
     "msg_cooldown":     1,       # secondes entre chaque message Telegram
     "prix_min":         3.0,
     "prix_max":         200.0,
     "score_min":        60,      # score /100 minimum pour alerter
+    "mode_flux":        False,   # False = un message par article (défaut), True = flux continu
     "marques":          set(TOUTES_LES_MARQUES),
     # sous-menus panel
     "menu_actif":       "main",  # main | scan | budget | score | marques | historique | favoris
 }
 
+selected_brands: set = set(TOUTES_LES_MARQUES)
+brand_panel_state = {"page": 0, "search": ""}
+
 seen_ids: set = set()
 historique_alertes: deque = deque(maxlen=50)  # 50 dernières alertes
 favoris: list = []  # annonces mises en favoris
 
 # ══════════════════════════════════════════════════════════════════════════════
 #  SCRAPER
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
 
-def _fetch_sync(query: str) -> list:
+def _api_get(path: str, params: dict | None = None) -> dict:
+    """Appel JSON Vinted robuste, avec refresh de session si nécessaire."""
     global _session
     headers = {
         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
         "Accept": "application/json, text/plain, */*",
         "Accept-Language": "fr-FR,fr;q=0.9",
         "Referer": "https://www.vinted.fr/catalog",
         "X-Requested-With": "XMLHttpRequest",
     }
-    url = (
-        f"https://www.vinted.fr/api/v2/catalog/items"
-        f"?search_text={requests.utils.quote(query)}&per_page=20&order=newest_first"
-    )
+    url = f"https://www.vinted.fr{path}"
+    resp = _session.get(url, headers=headers, params=params or {}, timeout=15)
+    if resp.status_code in (401, 403):
+        _session = _make_session()
+        resp = _session.get(url, headers=headers, params=params or {}, timeout=15)
+    if resp.status_code != 200:
+        return {}
+    return resp.json()
+
+def _fetch_sync(query: str = "", per_page: int = 20) -> list:
+    """Scraping intelligent sur /api/v2/catalog/items?order=newest_first."""
+    params = {"order": "newest_first", "per_page": max(1, min(per_page, 96))}
+    if query:
+        params["search_text"] = query
     try:
-        resp = _session.get(url, headers=headers, timeout=15)
-        if resp.status_code == 401:
-            _session = _make_session()
-            resp = _session.get(url, headers=headers, timeout=15)
-        if resp.status_code != 200:
-            return []
-        return resp.json().get("items", [])
+        return _api_get("/api/v2/catalog/items", params).get("items", [])
     except Exception as e:
         print(f"❌ fetch '{query}': {e}")
         return []
 
+def _fetch_item_by_id(item_id: str | int) -> dict | None:
+    try:
+        data = _api_get(f"/api/v2/items/{item_id}")
+        return data.get("item") or data.get("items") or None
+    except Exception as e:
+        print(f"❌ item '{item_id}': {e}")
+        return None
+
 # ══════════════════════════════════════════════════════════════════════════════
 #  SCORE /100 INTELLIGENT
 # ══════════════════════════════════════════════════════════════════════════════
 def calculer_score(prix: float, revente: float, marge: float,
                    marque: str, titre: str, taille: str, etat: str) -> int:
     """
     Score /100 basé sur :
     - ratio marge/prix          → 0-35 pts
     - marge absolue             → 0-20 pts
     - comparaison prix marché   → 0-10 pts
     - bonus marque hype         → 0-15 pts
     - bonus keywords hype       → 0-8  pts
     - bonus sous-côte extrême   → 0-6  pts
     - bonus état (neuf/TBE)     → 0-4  pts
     - bonus taille rare         → 0-2  pts
     """
     t = titre.lower()
     score = 0
 
     # 1. Ratio marge/prix
     ratio = marge / prix if prix > 0 else 0
     score += min(35, int(ratio * 55))
 
     # 2. Marge absolue
     if   marge >= 100: score += 20
@@ -238,275 +257,460 @@ def calculer_score(prix: float, revente: float, marge: float,
         score += 4
 
     # 8. Bonus taille rare
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
 #  FILTRAGE & ANALYSE
 # ══════════════════════════════════════════════════════════════════════════════
 def extraire_prix(item: dict) -> float | None:
     try:
         raw = item.get("price", {})
         return float(raw.get("amount", 0) if isinstance(raw, dict) else raw)
     except (TypeError, ValueError):
         return None
 
+def _item_url(item: dict) -> str:
+    return item.get("url") or f"https://www.vinted.fr/items/{item.get('id')}"
+
+def _photo_url(item: dict) -> str | None:
+    photo = item.get("photo") or {}
+    if isinstance(photo, dict):
+        return photo.get("url") or photo.get("full_size_url") or photo.get("high_resolution", {}).get("url")
+    photos = item.get("photos") or []
+    if photos and isinstance(photos[0], dict):
+        return photos[0].get("url") or photos[0].get("full_size_url")
+    return None
+
+def _normaliser_texte(valeur: str) -> str:
+    return re.sub(r"\s+", " ", (valeur or "").lower()).strip()
+
 def detecter_marque(titre: str, marque_vinted: str) -> str | None:
-    t = titre.lower()
-    m = marque_vinted.lower().strip()
-    for marque in config["marques"]:
+    t = _normaliser_texte(titre)
+    m = _normaliser_texte(marque_vinted)
+    for marque in sorted(selected_brands, key=len, reverse=True):
         if marque in m or marque in t:
             return marque
     return None
 
-def analyser(item: dict) -> tuple[bool, dict]:
-    titre      = item.get("title", "") or ""
+def _modele_depuis_titre(titre: str, marque: str | None = None) -> str:
+    texte = _normaliser_texte(titre)
+    if marque:
+        texte = texte.replace(marque, " ")
+    mots_vides = {
+        "homme", "femme", "unisexe", "taille", "size", "veste", "pull", "tee", "shirt",
+        "tshirt", "t-shirt", "sweat", "hoodie", "pantalon", "jean", "chaussure", "paire",
+        "neuf", "avec", "sans", "etiquette", "étiquette", "etat", "état", "bon", "tres", "très",
+    }
+    tokens = [m for m in re.findall(r"[a-z0-9'’.-]+", texte) if len(m) > 1 and m not in mots_vides]
+    return " ".join(tokens[:4])
+
+def _signature_item(item: dict) -> dict:
+    titre = item.get("title", "") or ""
     marque_raw = item.get("brand_title", "") or ""
-    taille     = item.get("size_title", "?") or "?"
-    etat       = item.get("status", "") or ""
-    prix       = extraire_prix(item)
-    item_id    = item.get("id")
-    t          = titre.lower()
+    marque = detecter_marque(titre, marque_raw)
+    return {
+        "titre": titre,
+        "marque_raw": marque_raw,
+        "marque": marque,
+        "modele": _modele_depuis_titre(titre, marque or marque_raw.lower()),
+        "taille": item.get("size_title", "?") or "?",
+        "etat": item.get("status", "") or "",
+        "prix": extraire_prix(item),
+        "id": item.get("id"),
+        "url": _item_url(item),
+        "photo": _photo_url(item),
+    }
 
+def _est_similaire(base: dict, candidat: dict) -> bool:
+    b = _signature_item(base)
+    c = _signature_item(candidat)
+    if not c["prix"] or b["id"] == c["id"]:
+        return False
+    if b["marque"] and c["marque"] and b["marque"] != c["marque"]:
+        return False
+    if b["taille"] != "?" and c["taille"] != "?" and b["taille"].lower() != c["taille"].lower():
+        return False
+    b_tokens = set(b["modele"].split())
+    c_tokens = set(c["modele"].split())
+    return not b_tokens or not c_tokens or bool(b_tokens & c_tokens)
+
+def trouver_similaires(item: dict, minimum: int = 3, maximum: int = 10) -> list:
+    sig = _signature_item(item)
+    requetes = []
+    if sig["marque"] and sig["modele"]:
+        requetes.append(f"{sig['marque']} {sig['modele']}")
+    if sig["marque_raw"] and sig["modele"]:
+        requetes.append(f"{sig['marque_raw']} {sig['modele']}")
+    if sig["marque"]:
+        requetes.append(sig["marque"])
+    if sig["modele"]:
+        requetes.append(sig["modele"])
+
+    vus = {sig["id"]}
+    similaires = []
+    for requete in dict.fromkeys(q for q in requetes if q):
+        for candidat in _fetch_sync(requete, per_page=30):
+            cid = candidat.get("id")
+            if not cid or cid in vus or not _est_similaire(item, candidat):
+                continue
+            vus.add(cid)
+            similaires.append(candidat)
+            if len(similaires) >= maximum:
+                return similaires
+        if len(similaires) >= minimum:
+            break
+    return similaires[:maximum]
+
+def _deal_depuis_item(item: dict, similaires: list) -> dict | None:
+    sig = _signature_item(item)
+    prix = sig["prix"]
     if prix is None or prix < config["prix_min"] or prix > config["prix_max"]:
-        return False, {}
-    if any(mot in t for mot in KEYWORDS_EXCLUS):
-        return False, {}
+        return None
+    if any(mot in sig["titre"].lower() for mot in KEYWORDS_EXCLUS):
+        return None
+    if sig["marque"] is None:
+        if not any(k in sig["titre"].lower() for k in KEYWORDS_HYPE):
+            return None
+        sig["marque"] = "_defaut"
+
+    prix_similaires = [extraire_prix(s) for s in similaires]
+    prix_similaires = [p for p in prix_similaires if p is not None and p > 0]
+    if len(prix_similaires) < 3:
+        return None
 
-    marque = detecter_marque(titre, marque_raw)
-    if marque is None:
-        if not any(k in t for k in KEYWORDS_HYPE):
-            return False, {}
-        marque = "_defaut"
-
-    coef, marge_min = REGLES_MARGE.get(marque, REGLES_MARGE["_defaut"])
-    revente = round(prix * coef, 2)
-    marge   = round(revente * 0.90 - prix, 2)
+    prix_moyen = round(sum(prix_similaires) / len(prix_similaires), 2)
+    marge = round(prix_moyen - prix, 2)
+    _, marge_min = REGLES_MARGE.get(sig["marque"], REGLES_MARGE["_defaut"])
     if marge < marge_min:
-        return False, {}
+        return None
 
-    score = calculer_score(prix, revente, marge, marque, titre, taille, etat)
+    score = calculer_score(prix, prix_moyen, marge, sig["marque"], sig["titre"], sig["taille"], sig["etat"])
     if score < config["score_min"]:
-        return False, {}
-
-    data = {
-        "id":      item_id,
-        "titre":   titre,
-        "marque":  marque_raw or marque,
-        "taille":  taille,
-        "etat":    etat,
-        "prix":    prix,
-        "revente": revente,
-        "marge":   marge,
-        "score":   score,
-        "niveau":  niveau_affaire(score),
-        "url":     f"https://www.vinted.fr/items/{item_id}",
-        "heure":   time.strftime("%H:%M:%S"),
+        return None
+
+    compares = []
+    for s in similaires[:10]:
+        ss = _signature_item(s)
+        if ss["prix"] is None:
+            continue
+        compares.append({
+            "id": ss["id"],
+            "titre": ss["titre"],
+            "prix": ss["prix"],
+            "url": ss["url"],
+        })
+
+    return {
+        "id": sig["id"],
+        "titre": sig["titre"],
+        "marque": sig["marque_raw"] or sig["marque"],
+        "marque_detectee": sig["marque"],
+        "modele": sig["modele"] or "Non détecté",
+        "taille": sig["taille"],
+        "etat": sig["etat"],
+        "prix": prix,
+        "prix_moyen": prix_moyen,
+        "revente": prix_moyen,
+        "prix_conseille": prix_moyen,
+        "marge": marge,
+        "score": score,
+        "niveau": niveau_affaire(score),
+        "url": sig["url"],
+        "photo": sig["photo"],
+        "compares": compares,
+        "heure": time.strftime("%H:%M:%S"),
     }
-    return True, data
+
+def analyser(item: dict) -> tuple[bool, dict]:
+    """Analyse un article par prix moyen réel des similaires avec propagation."""
+    deal = _analyse_item_propagation(item)
+    return (deal is not None), (deal or {})
+
+def _analyse_item_propagation(item: dict, profondeur_max: int = 3) -> dict | None:
+    principal = item
+    meilleur_deal = None
+    vus = set()
+
+    for _ in range(profondeur_max):
+        item_id = principal.get("id")
+        if item_id in vus:
+            break
+        vus.add(item_id)
+
+        similaires = trouver_similaires(principal, minimum=3, maximum=10)
+        deal = _deal_depuis_item(principal, similaires)
+        if deal and (meilleur_deal is None or deal["score"] > meilleur_deal["score"] or deal["marge"] > meilleur_deal["marge"]):
+            meilleur_deal = deal
+
+        candidats = [principal] + similaires
+        candidats = [c for c in candidats if extraire_prix(c) is not None]
+        if not candidats:
+            break
+        meilleur_prix = min(candidats, key=lambda c: extraire_prix(c) or 10**9)
+        if meilleur_prix.get("id") == principal.get("id"):
+            break
+        principal = meilleur_prix
+
+    return meilleur_deal
+
+def _item_id_depuis_url(url: str) -> str | None:
+    match = re.search(r"/items/(\d+)", url or "") or re.search(r"(?:^|[^0-9])(\d{6,})(?:[^0-9]|$)", url or "")
+    return match.group(1) if match else None
+
+def analyse_propagation(url: str) -> dict | None:
+    """Analyse manuelle d'une URL Vinted avec similaires, marge réelle et propagation."""
+    item_id = _item_id_depuis_url(url)
+    if not item_id:
+        raise ValueError("URL Vinted invalide : impossible de détecter l'identifiant de l'article.")
+    item = _fetch_item_by_id(item_id)
+    if not item:
+        raise ValueError("Article introuvable ou API Vinted indisponible.")
+    return _analyse_item_propagation(item)
 
 # ══════════════════════════════════════════════════════════════════════════════
 #  MESSAGE TELEGRAM
 # ══════════════════════════════════════════════════════════════════════════════
 def formater_alerte(d: dict, idx: int | None = None) -> str:
-    fav_btn_hint = f"\n<i>💾 Utilise /bot → Favoris pour sauvegarder</i>" if idx is None else ""
+    compares = d.get("compares", [])[:10]
+    lignes_compares = []
+    for i, c in enumerate(compares, 1):
+        titre = html.escape((c.get("titre") or "Comparé")[:38])
+        lignes_compares.append(f"{i}. {c.get('prix')}€ — <a href='{c.get('url')}'> {titre}</a>")
+    bloc_compares = "\n".join(lignes_compares) if lignes_compares else "Aucun comparable fiable."
     return (
         f"{d['niveau']} — <b>{d['score']}/100</b>\n\n"
-        f"👕 <b>{d['titre']}</b>\n"
-        f"🏷️ Marque : {d['marque']}\n"
-        f"📐 Taille : {d['taille']}\n"
-        f"✨ État : {d['etat'] or 'Non précisé'}\n"
+        f"👕 <b>{html.escape(d['titre'])}</b>\n"
+        f"🏷️ Marque : {html.escape(str(d['marque']))}\n"
+        f"🧩 Modèle : {html.escape(str(d.get('modele', 'Non détecté')))}\n"
+        f"📐 Taille : {html.escape(str(d['taille']))}\n"
+        f"✨ État : {html.escape(d['etat'] or 'Non précisé')}\n"
         f"💶 Prix achat : <b>{d['prix']}€</b>\n"
-        f"📈 Revente estimée : ~{d['revente']}€\n"
-        f"💰 Marge nette : ~<b>{d['marge']}€</b>\n"
+        f"📊 Prix moyen comparés : <b>{d.get('prix_moyen', d['revente'])}€</b>\n"
+        f"📈 Prix conseillé revente : ~<b>{d.get('prix_conseille', d['revente'])}€</b>\n"
+        f"💰 Marge réelle : ~<b>{d['marge']}€</b>\n"
         f"🕐 {d['heure']}\n\n"
-        f"🔗 <a href='{d['url']}'>Voir l'annonce</a>"
-        f"{fav_btn_hint}"
+        f"🔗 <a href='{d['url']}'>Lien principal</a>\n\n"
+        f"📋 <b>Comparés ({len(compares)})</b>\n{bloc_compares}"
     )
 
-def build_alerte_keyboard(item_id) -> InlineKeyboardMarkup:
-    return InlineKeyboardMarkup([[
-        InlineKeyboardButton("⭐ Ajouter aux favoris", callback_data=f"fav_add_{item_id}"),
-    ]])
+def build_alerte_keyboard(item_id, url: str | None = None) -> InlineKeyboardMarkup:
+    buttons = [[
+        InlineKeyboardButton("⏭️ Skip", callback_data="skip_alert"),
+        InlineKeyboardButton("⭐ Favoris", callback_data=f"fav_add_{item_id}"),
+    ]]
+    if url:
+        buttons[0].append(InlineKeyboardButton("🛒 Acheter", url=url))
+    return InlineKeyboardMarkup(buttons)
+
+async def envoyer_deal(bot, chat_id, deal: dict):
+    msg = formater_alerte(deal)
+    markup = build_alerte_keyboard(deal["id"], deal.get("url"))
+    photo = deal.get("photo")
+    if photo:
+        caption = (
+            f"{deal['niveau']} — <b>{deal['score']}/100</b>\n"
+            f"👕 <b>{html.escape(deal['titre'][:120])}</b>\n"
+            f"💶 Achat : <b>{deal['prix']}€</b> | 📈 Revente : <b>{deal.get('prix_conseille', deal['revente'])}€</b>\n"
+            f"💰 Marge réelle : <b>{deal['marge']}€</b>"
+        )
+        await bot.send_photo(
+            chat_id=chat_id,
+            photo=photo,
+            caption=caption,
+            parse_mode="HTML",
+            reply_markup=markup,
+        )
+        await bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML", disable_web_page_preview=True)
+    else:
+        await bot.send_message(
+            chat_id=chat_id,
+            text=msg,
+            parse_mode="HTML",
+            disable_web_page_preview=False,
+            reply_markup=markup,
+        )
 
 # ══════════════════════════════════════════════════════════════════════════════
 #  BOUCLE DE SCAN (scan continu, cooldown uniquement entre messages)
 # ══════════════════════════════════════════════════════════════════════════════
 async def boucle_scan(app: Application):
     loop = asyncio.get_event_loop()
-    # File d'attente pour les alertes à envoyer
     alert_queue: asyncio.Queue = asyncio.Queue()
 
-    # Tâche expéditrice : envoie les messages avec cooldown
     async def expediteur():
         while True:
             d = await alert_queue.get()
-            msg    = formater_alerte(d)
-            markup = build_alerte_keyboard(d["id"])
             try:
-                await app.bot.send_message(
-                    chat_id=TELEGRAM_CHAT_ID,
-                    text=msg,
-                    parse_mode="HTML",
-                    disable_web_page_preview=False,
-                    reply_markup=markup,
-                )
+                await envoyer_deal(app.bot, TELEGRAM_CHAT_ID, d)
             except Exception as e:
                 print(f"❌ Telegram: {e}")
-            # Cooldown adaptatif : augmente si la file est longue
             qs = alert_queue.qsize()
             delay = config["msg_cooldown"] * (1 + qs // 5)
             await asyncio.sleep(min(delay, 5))
 
     asyncio.create_task(expediteur())
 
     while True:
         if not config["actif"]:
             await asyncio.sleep(3)
             continue
 
-        print(f"\n🔍 Scan — {time.strftime('%H:%M:%S')}")
+        print(f"\n🔍 Scan intelligent — {time.strftime('%H:%M:%S')}")
         alertes = 0
+        queries = sorted(selected_brands) if selected_brands else [""]
+        if config.get("mode_flux"):
+            queries = [""] + queries
 
-        for query in SEARCH_QUERIES:
+        for query in queries:
             if not config["actif"]:
                 break
             try:
-                items = await loop.run_in_executor(None, _fetch_sync, query)
+                items = await loop.run_in_executor(None, _fetch_sync, query, 20)
             except Exception as e:
                 print(f"❌ Executor: {e}")
                 items = []
 
             for item in items:
                 item_id = item.get("id")
                 if not item_id or item_id in seen_ids:
                     continue
                 seen_ids.add(item_id)
 
                 if len(seen_ids) > 50_000:
-                    # Garde les 25 000 plus récents
                     seen_ids.difference_update(list(seen_ids)[:25_000])
 
-                ok, d = analyser(item)
+                try:
+                    ok, d = await loop.run_in_executor(None, analyser, item)
+                except Exception as e:
+                    print(f"❌ Analyse: {e}")
+                    continue
                 if not ok:
                     continue
 
                 alertes += 1
                 historique_alertes.appendleft(d)
                 await alert_queue.put(d)
-                print(f"  🚨 {d['titre'][:45]} | score {d['score']}/100 | ~{d['marge']}€")
+                print(f"  🚨 {d['titre'][:45]} | score {d['score']}/100 | marge réelle ~{d['marge']}€")
 
-            # Petit délai entre requêtes pour ne pas spammer l'API
             await asyncio.sleep(1)
 
-        print(f"✅ Cycle terminé — {alertes} nouvelles alertes")
-        # Scan continu : pas de cooldown entre cycles, seulement 1s de respiration
+        print(f"✅ Cycle terminé — {alertes} nouvelles pépites")
         await asyncio.sleep(1)
 
 # ══════════════════════════════════════════════════════════════════════════════
 #  PANEL /bot — MENU PRINCIPAL
 # ══════════════════════════════════════════════════════════════════════════════
 def build_main_text() -> str:
     etat = "✅ Actif" if config["actif"] else "⏸ En pause"
     nb_fav = len(favoris)
     nb_hist = len(historique_alertes)
     return (
         f"🤖 <b>Vinted Bot — Panel de contrôle</b>\n"
         f"{'─' * 32}\n"
         f"{'🟢' if config['actif'] else '🔴'} État          : <b>{etat}</b>\n"
         f"📨 Cooldown msg : <b>{config['msg_cooldown']}s</b>\n"
         f"💶 Budget        : <b>{config['prix_min']}€ – {config['prix_max']}€</b>\n"
         f"🎯 Score min     : <b>{config['score_min']}/100</b>\n"
-        f"🏷️ Marques        : <b>{len(config['marques'])}</b>\n"
+        f"🏷️ Marques        : <b>{len(selected_brands)}</b> actives\n"
+        f"📨 Mode messages : <b>{'Flux continu' if config['mode_flux'] else '1/article'}</b>\n"
         f"📋 Historique    : <b>{nb_hist}</b> alertes\n"
         f"⭐ Favoris       : <b>{nb_fav}</b> annonces\n"
         f"{'─' * 32}\n"
         f"<i>Choisis une catégorie ci-dessous :</i>"
     )
 
 def build_main_keyboard() -> InlineKeyboardMarkup:
     etat_btn = "⏸ Pause" if config["actif"] else "▶️ Démarrer"
     etat_cb  = "panel_pause" if config["actif"] else "panel_start"
     return InlineKeyboardMarkup([
         [
             InlineKeyboardButton(etat_btn, callback_data=etat_cb),
             InlineKeyboardButton("⏹ Arrêter", callback_data="panel_stop"),
         ],
         [
             InlineKeyboardButton("📡 Scan",         callback_data="menu_scan"),
             InlineKeyboardButton("💶 Budget",        callback_data="menu_budget"),
             InlineKeyboardButton("🎯 Score",         callback_data="menu_score"),
         ],
         [
             InlineKeyboardButton("🏷️ Marques",        callback_data="menu_marques"),
             InlineKeyboardButton("📋 Historique",    callback_data="menu_historique"),
             InlineKeyboardButton("⭐ Favoris",       callback_data="menu_favoris"),
         ],
         [
             InlineKeyboardButton("🔁 Reset config",  callback_data="panel_reset"),
             InlineKeyboardButton("🔄 Actualiser",    callback_data="menu_main"),
         ],
     ])
 
 # ══════════════════════════════════════════════════════════════════════════════
 #  SOUS-MENU : SCAN (cooldown messages)
 # ══════════════════════════════════════════════════════════════════════════════
 def build_scan_text() -> str:
+    mode = "Flux continu" if config["mode_flux"] else "Un message par article"
     return (
-        f"📡 <b>Paramètres de scan</b>\n"
+        f"📡 <b>Paramètres de scan intelligent</b>\n"
         f"{'─' * 30}\n"
-        f"⚡ Le scan tourne en <b>continu</b> (pas de cooldown entre cycles)\n\n"
-        f"📨 Cooldown entre messages : <b>{config['msg_cooldown']}s</b>\n"
-        f"   <i>(augmente automatiquement si trop d'alertes)</i>\n"
+        f"⚡ Endpoint : <code>/api/v2/catalog/items?order=newest_first</code>\n"
+        f"🧠 Analyse : 3 à 10 similaires + propagation\n"
+        f"📨 Mode : <b>{mode}</b>\n\n"
+        f"⏱️ Cooldown entre messages : <b>{config['msg_cooldown']}s</b>\n"
         f"{'─' * 30}\n"
-        f"<i>Choisis le délai entre messages :</i>"
+        f"<i>Choisis le délai ou le mode d'envoi :</i>"
     )
 
 def build_scan_keyboard() -> InlineKeyboardMarkup:
     cd = config["msg_cooldown"]
     def mark(v): return f"✅ {v}s" if cd == v else f"{v}s"
+    mode_label = "✅ Flux continu" if config["mode_flux"] else "Flux continu"
+    single_label = "✅ 1/article" if not config["mode_flux"] else "1/article"
     return InlineKeyboardMarkup([
         [
             InlineKeyboardButton(mark(1),  callback_data="msgcd_1"),
             InlineKeyboardButton(mark(2),  callback_data="msgcd_2"),
             InlineKeyboardButton(mark(3),  callback_data="msgcd_3"),
         ],
         [
             InlineKeyboardButton(mark(5),  callback_data="msgcd_5"),
             InlineKeyboardButton(mark(10), callback_data="msgcd_10"),
             InlineKeyboardButton(mark(30), callback_data="msgcd_30"),
         ],
+        [
+            InlineKeyboardButton(single_label, callback_data="mode_single"),
+            InlineKeyboardButton(mode_label, callback_data="mode_flux"),
+        ],
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
         [
             InlineKeyboardButton(mark(3,  30),  callback_data="budget_3_30"),
             InlineKeyboardButton(mark(3,  50),  callback_data="budget_3_50"),
             InlineKeyboardButton(mark(5,  50),  callback_data="budget_5_50"),
         ],
         [
@@ -547,67 +751,105 @@ def build_score_keyboard() -> InlineKeyboardMarkup:
     def mark(v): return f"✅ {v}" if s == v else str(v)
     return InlineKeyboardMarkup([
         [
             InlineKeyboardButton(mark(40), callback_data="score_set_40"),
             InlineKeyboardButton(mark(50), callback_data="score_set_50"),
             InlineKeyboardButton(mark(55), callback_data="score_set_55"),
             InlineKeyboardButton(mark(60), callback_data="score_set_60"),
         ],
         [
             InlineKeyboardButton(mark(65), callback_data="score_set_65"),
             InlineKeyboardButton(mark(70), callback_data="score_set_70"),
             InlineKeyboardButton(mark(75), callback_data="score_set_75"),
             InlineKeyboardButton(mark(80), callback_data="score_set_80"),
         ],
         [
             InlineKeyboardButton("▼ -5", callback_data="score_down"),
             InlineKeyboardButton(f"  {s}/100  ", callback_data="noop"),
             InlineKeyboardButton("▲ +5", callback_data="score_up"),
         ],
         [InlineKeyboardButton("◀️ Retour", callback_data="menu_main")],
     ])
 
 # ══════════════════════════════════════════════════════════════════════════════
 #  SOUS-MENU : MARQUES
 # ══════════════════════════════════════════════════════════════════════════════
+def _marques_filtrees() -> list:
+    recherche = brand_panel_state.get("search", "").lower().strip()
+    marques = sorted(TOUTES_LES_MARQUES)
+    if recherche:
+        marques = [m for m in marques if recherche in m]
+    return marques
+
 def build_marques_text() -> str:
-    nb = len(config["marques"])
+    marques = _marques_filtrees()
     total = len(TOUTES_LES_MARQUES)
+    page = brand_panel_state.get("page", 0)
+    pages = max(1, (len(marques) + 7) // 8)
+    recherche = brand_panel_state.get("search", "") or "Aucune"
     return (
         f"🏷️ <b>Gestion des marques</b>\n"
         f"{'─' * 30}\n"
-        f"Actives : <b>{nb}/{total}</b> marques\n"
+        f"Actives : <b>{len(selected_brands)}/{total}</b> marques\n"
+        f"Recherche : <b>{html.escape(recherche)}</b>\n"
+        f"Page : <b>{min(page + 1, pages)}/{pages}</b>\n"
         f"{'─' * 30}\n"
-        f"<i>Utilise /marque add &lt;nom&gt; ou /marque remove &lt;nom&gt; pour modifier.\n"
-        f"/marque list pour voir la liste complète.</i>"
+        f"<i>Clique une marque pour la sélectionner/désélectionner. "
+        f"Recherche simulée : /marque search &lt;texte&gt; ou boutons rapides.</i>"
     )
 
 def build_marques_keyboard() -> InlineKeyboardMarkup:
-    return InlineKeyboardMarkup([
-        [InlineKeyboardButton("🔁 Réinitialiser toutes les marques", callback_data="marques_reset")],
-        [InlineKeyboardButton("◀️ Retour", callback_data="menu_main")],
+    marques = _marques_filtrees()
+    page = brand_panel_state.get("page", 0)
+    pages = max(1, (len(marques) + 7) // 8)
+    brand_panel_state["page"] = min(page, pages - 1)
+    debut = brand_panel_state["page"] * 8
+    courant = marques[debut:debut + 8]
+    buttons = []
+    for marque in courant:
+        prefix = "✔ " if marque in selected_brands else "▫️ "
+        buttons.append([InlineKeyboardButton(prefix + marque[:35], callback_data=f"brand_toggle_{marque}")])
+    buttons.append([
+        InlineKeyboardButton("⬅️", callback_data="brand_prev"),
+        InlineKeyboardButton(f"{brand_panel_state['page'] + 1}/{pages}", callback_data="noop"),
+        InlineKeyboardButton("➡️", callback_data="brand_next"),
     ])
+    buttons.append([
+        InlineKeyboardButton("🔎 Nike", callback_data="brand_search_nike"),
+        InlineKeyboardButton("🔎 Jordan", callback_data="brand_search_jordan"),
+        InlineKeyboardButton("🔎 Luxe", callback_data="brand_search_luxe"),
+        InlineKeyboardButton("🧹 Recherche", callback_data="brand_search_clear"),
+    ])
+    buttons.append([
+        InlineKeyboardButton("✅ Tout sélectionner", callback_data="brand_all"),
+        InlineKeyboardButton("🚫 Tout désélectionner", callback_data="brand_none"),
+    ])
+    buttons.append([
+        InlineKeyboardButton("💾 Valider", callback_data="brand_validate"),
+        InlineKeyboardButton("◀️ Retour", callback_data="menu_main"),
+    ])
+    return InlineKeyboardMarkup(buttons)
 
 # ══════════════════════════════════════════════════════════════════════════════
 #  SOUS-MENU : HISTORIQUE
 # ══════════════════════════════════════════════════════════════════════════════
 def build_historique_text() -> str:
     if not historique_alertes:
         return "📋 <b>Historique des alertes</b>\n\nAucune alerte pour le moment."
     lines = [f"📋 <b>Historique — {len(historique_alertes)} dernières alertes</b>\n{'─' * 30}"]
     for i, d in enumerate(list(historique_alertes)[:10], 1):
         lines.append(
             f"\n<b>{i}.</b> {d['niveau']} <b>{d['score']}/100</b>\n"
             f"   {d['titre'][:35]} | {d['prix']}€ → ~{d['marge']}€ marge\n"
             f"   🕐 {d['heure']} — <a href='{d['url']}'>Voir</a>"
         )
     if len(historique_alertes) > 10:
         lines.append(f"\n<i>... et {len(historique_alertes) - 10} de plus</i>")
     return "\n".join(lines)
 
 def build_historique_keyboard() -> InlineKeyboardMarkup:
     return InlineKeyboardMarkup([
         [InlineKeyboardButton("🗑️ Vider l'historique", callback_data="historique_clear")],
         [InlineKeyboardButton("◀️ Retour", callback_data="menu_main")],
     ])
 
 # ══════════════════════════════════════════════════════════════════════════════
@@ -673,194 +915,294 @@ async def cmd_bot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
     )
 
 async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
     config["actif"] = True
     await update.message.reply_text("✅ <b>Scan activé !</b>", parse_mode="HTML")
 
 async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
     config["actif"] = False
     await update.message.reply_text("⏸ <b>Scan mis en pause.</b>\nTape /start pour relancer.", parse_mode="HTML")
 
 async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
     await update.message.reply_text(
         build_main_text() + "\n\n👉 Tape /bot pour le panel interactif",
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
 
+async def cmd_analyse(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
+    if not ctx.args:
+        await update.message.reply_text("❌ Usage : /analyse &lt;url Vinted&gt;")
+        return
+    url = " ".join(ctx.args).strip()
+    await update.message.reply_text("🔎 Analyse propagation en cours…", disable_web_page_preview=True)
+    loop = asyncio.get_event_loop()
+    try:
+        deal = await loop.run_in_executor(None, analyse_propagation, url)
+        if not deal:
+            await update.message.reply_text(
+                "❌ Aucune pépite détectée : pas assez de similaires fiables, marge trop faible ou score sous le seuil."
+            )
+            return
+        historique_alertes.appendleft(deal)
+        await envoyer_deal(ctx.bot, update.effective_chat.id, deal)
+    except Exception as e:
+        await update.message.reply_text(f"❌ Analyse impossible : {html.escape(str(e))}", parse_mode="HTML")
+
 async def cmd_marque(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
+    global selected_brands
     try:
         action = ctx.args[0].lower()
     except IndexError:
-        await update.message.reply_text("Usage :\n/marque add &lt;nom&gt;\n/marque remove &lt;nom&gt;\n/marque reset\n/marque list")
+        await update.message.reply_text(
+            "Usage :\n"
+            "/marque search &lt;texte&gt;\n"
+            "/marque add &lt;nom&gt;\n"
+            "/marque remove &lt;nom&gt;\n"
+            "/marque reset\n"
+            "/marque list\n\n"
+            "Le panel /bot → Marques permet aussi la sélection paginée."
+        )
         return
 
     if action == "reset":
-        config["marques"] = set(TOUTES_LES_MARQUES)
-        await update.message.reply_text(f"✅ {len(config['marques'])} marques réactivées.")
+        selected_brands = set(TOUTES_LES_MARQUES)
+        config["marques"] = selected_brands
+        brand_panel_state.update({"page": 0, "search": ""})
+        await update.message.reply_text(f"✅ {len(selected_brands)} marques réactivées.")
     elif action == "list":
-        texte = "🏷️ <b>Marques actives :</b>\n" + ", ".join(sorted(config["marques"]))
+        texte = "🏷️ <b>Marques actives :</b>\n" + ", ".join(sorted(selected_brands))
         await update.message.reply_text(texte[:4000], parse_mode="HTML")
+    elif action == "search":
+        recherche = " ".join(ctx.args[1:]).lower().strip()
+        brand_panel_state.update({"page": 0, "search": recherche})
+        await update.message.reply_text(
+            f"🔎 Recherche marques : <b>{html.escape(recherche or 'Aucune')}</b>\nOuvre /bot → Marques pour voir le filtre.",
+            parse_mode="HTML",
+        )
     elif action in ("add", "remove"):
         nom = " ".join(ctx.args[1:]).lower().strip()
         if not nom:
             await update.message.reply_text(f"❌ Usage : /marque {action} &lt;nom&gt;")
             return
         if action == "add":
-            config["marques"].add(nom)
-            await update.message.reply_text(f"✅ Ajouté : <b>{nom}</b>", parse_mode="HTML")
+            selected_brands.add(nom)
+            config["marques"] = selected_brands
+            await update.message.reply_text(f"✅ Ajouté : <b>{html.escape(nom)}</b>", parse_mode="HTML")
         else:
-            config["marques"].discard(nom)
-            await update.message.reply_text(f"🗑️ Retiré : <b>{nom}</b>", parse_mode="HTML")
+            selected_brands.discard(nom)
+            config["marques"] = selected_brands
+            await update.message.reply_text(f"🗑️ Retiré : <b>{html.escape(nom)}</b>", parse_mode="HTML")
     else:
-        await update.message.reply_text("❌ Action inconnue : add / remove / reset / list")
+        await update.message.reply_text("❌ Action inconnue : add / remove / reset / list / search")
 
 # ══════════════════════════════════════════════════════════════════════════════
 #  CALLBACK HANDLER
 # ══════════════════════════════════════════════════════════════════════════════
 async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
     query = update.callback_query
-    await query.answer()
     data = query.data
 
     # ── Navigation menus ──────────────────────────────────────
     if data.startswith("menu_"):
         menu = data.split("_", 1)[1]
         await afficher_menu(query, menu)
         return
 
     # ── Contrôle scan ─────────────────────────────────────────
     if data == "panel_start":
         config["actif"] = True
     elif data == "panel_pause":
         config["actif"] = False
     elif data == "panel_stop":
         config["actif"] = False
         await query.edit_message_text("⛔ Bot arrêté. Railway va le redémarrer automatiquement.")
         sys.exit(0)
     elif data == "panel_reset":
+        selected_brands.clear()
+        selected_brands.update(TOUTES_LES_MARQUES)
+        brand_panel_state.update({"page": 0, "search": ""})
         config.update({
             "msg_cooldown": 1,
             "prix_min": 3.0,
             "prix_max": 200.0,
             "score_min": 60,
-            "marques": set(TOUTES_LES_MARQUES),
+            "mode_flux": False,
+            "marques": selected_brands,
         })
 
     # ── Cooldown messages ─────────────────────────────────────
     elif data.startswith("msgcd_"):
         config["msg_cooldown"] = int(data.split("_")[1])
         await afficher_menu(query, "scan")
         return
+    elif data == "mode_single":
+        config["mode_flux"] = False
+        await afficher_menu(query, "scan")
+        return
+    elif data == "mode_flux":
+        config["mode_flux"] = True
+        await afficher_menu(query, "scan")
+        return
 
     # ── Budget ────────────────────────────────────────────────
     elif data.startswith("budget_"):
         _, pmin, pmax = data.split("_")
         config["prix_min"] = float(pmin)
         config["prix_max"] = float(pmax)
         await afficher_menu(query, "budget")
         return
 
     # ── Score ─────────────────────────────────────────────────
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
 
     # ── Marques ───────────────────────────────────────────────
+    elif data.startswith("brand_toggle_"):
+        marque = data.split("_", 2)[2]
+        if marque in selected_brands:
+            selected_brands.remove(marque)
+        else:
+            selected_brands.add(marque)
+        config["marques"] = selected_brands
+        await afficher_menu(query, "marques")
+        return
+    elif data == "brand_prev":
+        brand_panel_state["page"] = max(0, brand_panel_state.get("page", 0) - 1)
+        await afficher_menu(query, "marques")
+        return
+    elif data == "brand_next":
+        brand_panel_state["page"] = brand_panel_state.get("page", 0) + 1
+        await afficher_menu(query, "marques")
+        return
+    elif data == "brand_all":
+        selected_brands.clear()
+        selected_brands.update(TOUTES_LES_MARQUES)
+        config["marques"] = selected_brands
+        await afficher_menu(query, "marques")
+        return
+    elif data == "brand_none":
+        selected_brands.clear()
+        config["marques"] = selected_brands
+        await afficher_menu(query, "marques")
+        return
+    elif data == "brand_validate":
+        config["marques"] = selected_brands
+        await query.answer(f"✅ {len(selected_brands)} marques validées", show_alert=True)
+        await afficher_menu(query, "main")
+        return
+    elif data.startswith("brand_search_"):
+        valeur = data.split("_", 2)[2]
+        recherches = {"clear": "", "luxe": "gu"}
+        brand_panel_state.update({"page": 0, "search": recherches.get(valeur, valeur)})
+        await afficher_menu(query, "marques")
+        return
     elif data == "marques_reset":
-        config["marques"] = set(TOUTES_LES_MARQUES)
+        selected_brands.clear()
+        selected_brands.update(TOUTES_LES_MARQUES)
+        config["marques"] = selected_brands
         await afficher_menu(query, "marques")
         return
 
     # ── Historique ────────────────────────────────────────────
     elif data == "historique_clear":
         historique_alertes.clear()
         await afficher_menu(query, "historique")
         return
 
     # ── Favoris ───────────────────────────────────────────────
     elif data.startswith("fav_add_"):
         item_id_str = data.split("_", 2)[2]
         # Cherche dans l'historique
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
         await afficher_menu(query, "favoris")
         return
     elif data == "fav_clear":
         favoris.clear()
         await afficher_menu(query, "favoris")
         return
 
+    elif data == "skip_alert":
+        try:
+            await query.delete_message()
+        except Exception:
+            pass
+        return
+
     elif data == "noop":
         return
 
     # ── Rafraîchissement du panel principal ───────────────────
     await afficher_menu(query, "main")
 
 # ══════════════════════════════════════════════════════════════════════════════
 #  DÉMARRAGE
 # ══════════════════════════════════════════════════════════════════════════════
 async def post_init(app: Application):
     asyncio.create_task(boucle_scan(app))
     await app.bot.send_message(
         chat_id=TELEGRAM_CHAT_ID,
         text=(
             "🤖 <b>Bot Vinted prêt !</b>\n\n"
-            f"🏷️ {len(config['marques'])} marques chargées\n"
+            f"🏷️ {len(selected_brands)} marques chargées\n"
             f"📨 Cooldown messages : {config['msg_cooldown']}s\n"
             f"💶 Budget : {config['prix_min']}€ – {config['prix_max']}€\n"
             f"🎯 Score min : {config['score_min']}/100\n"
-            f"⚡ Scan continu activé\n\n"
+            f"⚡ Scan intelligent + propagation activé\n"
+            "🔎 /analyse &lt;url&gt; disponible\n\n"
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
     app.add_handler(CommandHandler("bot",     cmd_bot))
     app.add_handler(CommandHandler("start",   cmd_start))
     app.add_handler(CommandHandler("stop",    cmd_stop))
     app.add_handler(CommandHandler("budget",  cmd_budget))
+    app.add_handler(CommandHandler("analyse", cmd_analyse))
     app.add_handler(CommandHandler("marque",  cmd_marque))
     app.add_handler(CommandHandler("status",  cmd_status))
     app.add_handler(CallbackQueryHandler(handle_callback))
 
     print("📡 Bot en écoute…")
     app.run_polling(drop_pending_updates=True)
 
 if __name__ == "__main__":
     main()
