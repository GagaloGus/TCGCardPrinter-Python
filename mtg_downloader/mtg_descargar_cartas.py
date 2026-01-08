import sys, os, re, requests, cloudscraper, subprocess, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn

# Añade el directorio de arriba para usar scripts fuera de la carpeta
sys.path.insert(1, "/".join(os.path.realpath(__file__).split("/")[0:-2]))
from basicFunctions import *
from cardClasses import CardClass, CardType, CardScraper

# ---------------- CONFIG ----------------
# -- FILES --
OUTPUT_DIR = ""
DOWNLOAD_LEN = 0
N_ERROR_LOAD = 0
N_ERROR_DOWNLOADS = 0

# ------------------------------------------------------------
# Detecta plataforma e ID del mazo
# ------------------------------------------------------------
def get_platform_and_id(url: str):
    if "archidekt" in url.lower():
        match = re.search(r"decks/(\d+)", url)
        if not match: raise ValueError("\033[31m[!]\033[0m No pude sacar el ID de Archidekt.")
        return "archidekt", match.group(1)
    if "moxfield" in url.lower():
        return "moxfield", url.rstrip("/").split("/")[-1]
    raise ValueError(f"\033[31m[!]\033[0m Plataforma no soportada: '{url}'")

# ------------------------------------------------------------
# Obtiene JSON del mazo
# ------------------------------------------------------------
def get_json(platform: str, deck_id: str):
    if platform == "archidekt":
        resp = requests.get(f"https://archidekt.com/api/decks/{deck_id}/")
        if resp.status_code != 200: 
            raise ValueError(f"\033[31m[!]\033[0m Error API Archidekt {resp.status_code}")
        return resp.json()
    elif platform == "moxfield":
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(f"https://api.moxfield.com/v2/decks/all/{deck_id}")
        if resp.status_code != 200: 
            raise ValueError(f"\033[31m[!]\033[0m Error API Moxfield {resp.status_code}")
        return resp.json()
    else:
        raise ValueError(f"\033[31m[!]\033[0m Plataforma no soportada: '{platform}'")

# ------------------------------------------------------------
# Obtiene la longitud del mazo (sin tokens si no se quieren)
# ------------------------------------------------------------
def get_download_length(platform: str, deck_id: str, prnt_tokens: bool) -> int:
    count = 0
    data = get_json(platform, deck_id)

    if platform == "archidekt":
        skip = ["Maybeboard"] + ([] if prnt_tokens else ["Token"])
        for c in data["cards"]:
            card_types = list(c["categories"]) + list(c["card"]["oracleCard"]["types"])
            if any(x in card_types for x in skip): continue
            count += 1
    elif platform == "moxfield":
        all_cards = {}
        for sec in ["mainboard","commanders","companions","signatureSpells"]:
            if sec in data:
                for c in data[sec].values(): 
                    all_cards[c["card"]["scryfall_id"]] = c
        if prnt_tokens and "tokens" in data:
            for t in data["tokens"]:
                if t.get("layout") == "token": 
                    all_cards[t["scryfall_id"]] = t
        count = len(all_cards)
    return count

# ------------------------------------------------------------
# Carga todas las cartas en paralelo
# ------------------------------------------------------------
def load_deck(platform: str, deck_id: str, prnt_tokens: bool, lang: str) -> list[CardClass]:
    global N_ERROR_LOAD
    data = get_json(platform, deck_id)
    card_infos = []

    if platform == "archidekt":
        skip = ["Maybeboard"] + ([] if prnt_tokens else ["Token"])
        for c in data["cards"]:
            card_types = list(c["categories"]) + list(c["card"]["oracleCard"]["types"])
            if any(x in card_types for x in skip): 
                continue
            quantity = c["quantity"] if "Token" not in card_types else 1
            edition, number = c["card"]["edition"]["editioncode"], c["card"]["collectorNumber"]
            url = f"https://api.scryfall.com/cards/{edition}/{number}"
            card_infos.append((quantity, url))
    else:  # moxfield
        all_cards = []
        for sec in ["mainboard","commanders","companions","signatureSpells"]:
            if sec in data: 
                all_cards.extend(data[sec].values())
        if prnt_tokens and "tokens" in data:
            all_cards.extend([t for t in data["tokens"] if t.get("layout")=="token"])
        for c in all_cards:
            card_data = c.get("card", c)
            quantity = c.get("quantity", 1)
            url = f"https://api.scryfall.com/cards/{card_data['scryfall_id']}"
            card_infos.append((quantity,url))

    cards = []
    qty_map = {url: qty for qty, url in card_infos}
    
    with Progress(
        TextColumn("[bold]Obteniendo cartas..."), BarColumn(), TextColumn("[bold]{task.completed}/{task.total}"), TimeRemainingColumn()
    ) as progress:
        task = progress.add_task("", total=len(card_infos))
        
        # le carga todas las urls
        cardScraper = CardScraper([i[1] for i in card_infos], lang)
        print("Iniciar card scraper..")
        cardScraper.run()
        
        for url, json in cardScraper.finishedJsons:
            quantity = qty_map.get(url, 1) #Default 1 por si acaso
            card = CardClass(json, quantity, lang, url)
            cards.append(card)
            
            progress.update(task, advance=1)
            time.sleep(0.05)

    return sorted(cards, key=lambda c: c.cardTypes[0].value)

# ------------------------------------------------------------
# Script principal
# ------------------------------------------------------------
def main():
    global OUTPUT_DIR, N_ERROR_DOWNLOADS, DOWNLOAD_LEN
    # ---------- SETUP
    
    print("\033[33m======= DESCARGAR CARTAS MAGIC THE GATHERING =======\033[0m")
    print("- Plataformas admitidas: Archidekt, Moxfield\n")

    url = input("Pega la URL del mazo: \033[36m").strip()
    try:
        platform, deck_id = get_platform_and_id(url)
        deckName = get_json(platform, deck_id)["name"]
    except Exception as e:
        print(e)
        os.system("pause")
        return

    borrar_ultimas_lineas(0)
    print(f"\033[33m-- {deckName} --")
    print(f"\033[33mPlataforma: \033[0m{platform.capitalize()}")
    print(f"\033[33mID del mazo: \033[0m'{deck_id}'")

    prnt_tokens = yesNo_CustomChoice("¿Quieres cargar tambien los tokens?", "si", "no")
    borrar_ultimas_lineas(0)
    print(f"\033[33mTokens:\033[0m {'Si' if prnt_tokens else 'No'}")
    card_lang = multiple_CustomChoice("Elige el idioma de las cartas:", ["Original","English","Español"])
    card_lang = ["orig","en","es"][card_lang]

    print("\nObteniendo longitud del mazo...")
    DOWNLOAD_LEN = get_download_length(platform, deck_id, prnt_tokens)
    borrar_ultimas_lineas(0)

    cards = load_deck(platform, deck_id, prnt_tokens, card_lang)
    print("")
    
    customFolderName = crear_directorio_nuevo(input("¿Quieres ponerle un nombre a la carpeta de descarga? (Enter para no): \033[36m"))
    OUTPUT_DIR = os.path.join("cartas", customFolderName if customFolderName else crear_directorio_nuevo(deckName))
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("")
    
    # Descargar imágenes en paralelo
    with Progress(
        TextColumn("[bold]Descargando cartas..."), BarColumn(), TextColumn("[bold]{task.completed}/{task.total}"), TimeRemainingColumn()
    ) as progress:
        task = progress.add_task("", total=len(cards))
        
        def download_card(card:CardClass):
            global N_ERROR_DOWNLOADS
            try:
                card.downloadImages(OUTPUT_DIR)
            except Exception as e:
                N_ERROR_DOWNLOADS += 1
                print(f"\033[31m[!]\033[0m Error descargando {card.cardMainName}: {e}")

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(download_card, c) for c in cards]
            for future in as_completed(futures):
                progress.update(task, advance=1)

    print(f"\n\033[32mListo mi rey, todas las cartas estan en '{OUTPUT_DIR}'\033[0m")
    if N_ERROR_DOWNLOADS + N_ERROR_LOAD > 0:
        print(f"\033[33m[!] No se pudieron procesar {N_ERROR_DOWNLOADS + N_ERROR_LOAD} cartas\033[0m")

    # Preguntar si crear PDF de impresión
    try:
        import imprimir_cartas as modulo_imprimir
        if yesNo_CustomChoice("¿Quieres crear el PDF de las cartas?", "si", "no"):
            modulo_imprimir.main(OUTPUT_DIR, "1")
        else:
            subprocess.Popen(rf'explorer /select,"{OUTPUT_DIR}"')
    except:
        print("\033[31m[!]\033[0m No se pudo abrir el modulo de impresion.\n -> Pasa las imagenes a la carpeta: 'cartas_imprimir' y ejecuta el otro programa")
        subprocess.Popen(rf'explorer /select,"{OUTPUT_DIR}"')

if __name__ == "__main__":
    os.system("cls")
    main()
