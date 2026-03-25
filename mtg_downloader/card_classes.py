import asyncio
import sys
import os
import json
import time
import ctypes
from urllib.request import urlopen
from enum import Enum
from PIL import Image
import requests

#Añade el directorio de arriba en el path para usar scripts fuera de la carpeta
sys.path.insert(1, "/".join(os.path.realpath(__file__).split("/")[0:-2]))
from basic_functions import *
from scraper import scrape_json as url_scraper

# ---------------- CACHE GLOBAL ----------------
SCRYFALL_URL_CACHE = {}          # cache por URL / Guarda el JSON entero de Scryfall para cada url
ORACLE_URL_CACHE = {}           # cache por oracle_id + lang / Guarda el JSON por Oracle ID + Idiom
CACHE_LIFETIME_SEC = 24 * 60 * 60 # Un dia
MAX_REQ_PER_SEC = 5
print("el guevo mio")


class CardType(Enum):
    ARTIFACT = 0
    BATTLE = 1
    CONSPIRACY = 2
    CREATURE = 3
    DUNGEON = 4
    EMBLEM = 5
    ENCHANTMENT = 6
    HERO = 7
    INSTANT = 8
    KINDRED = 9
    LAND = 10
    PHENOMENON = 11
    PLANE = 12
    PLANESWALKER = 13
    SCHEME = 14
    SORCERY = 15
    TOKEN = 16
    VANGUARD = 17
    OTHER = 99

    def __str__(self, lang:str = "orig") -> str:
        if lang not in ["orig", "en"]:
            dic = {}
            if lang == "es":
                dic = {
                    CardType.ARTIFACT: "Artefacto",
                    CardType.BATTLE: "Batalla",
                    CardType.CONSPIRACY: "Conspiración",
                    CardType.CREATURE: "Criatura",
                    CardType.DUNGEON: "Mazmorra",
                    CardType.EMBLEM: "Emblema",
                    CardType.ENCHANTMENT: "Encantamiento",
                    CardType.HERO: "Héroe",
                    CardType.INSTANT: "Instantánea",
                    CardType.KINDRED: "Afín",
                    CardType.LAND: "Tierra",
                    CardType.PHENOMENON: "Fenómeno",
                    CardType.PLANE: "Plano",
                    CardType.PLANESWALKER: "Planeswalker",
                    CardType.SCHEME: "Intriga",
                    CardType.SORCERY: "Conjuro",
                    CardType.TOKEN: "Ficha",
                    CardType.VANGUARD: "Vanguardia",
                    CardType.OTHER: "Otro",
                }
            #Si pusieron otro idioma no reconocido, pone el original
            else:
                return self.name.capitalize()

            # Fallback al "Other", si ese falla tambien, lo imprime en el idioma original
            return dic.get(self, dic.get(CardType.OTHER, "Other"))

        #Si no sale ninguno, devuelve en ingles
        return self.name.capitalize()

class CardScraper:
    """
        1. Obtiene todas las urls
        2. las pasa por el scraper para obtener todos los jsons
        3. si el idioma es "orig" se devuelven los jsons de scryfall, si no, se obtiene su url con su oracle_id y se scrapean una vez mas
        4. Devuelve una lista de una tupla que contiene:
            la url de donde se obtuvo el JSON
            el JSON
            la url original de scryfall
    """

    def __init__(self, urls: list, lang: str):
        self.urls = urls
        self.lang = lang
        self.alt_lang = lang != "orig"
        self.rawJsons = []
        self.finishedJsons = []

        self.errors = 0
        self.cacheFolderName = "card_cache"
        self.cacheFileNames = [os.path.join(self.cacheFolderName, n) for n in ["scryfall_cache.json", "oracle_cache.json"]]
        self._load_json_cache()

    # ===== INICIO DEL PROGRAMA =====
    def run(self):
        asyncio.run(self._run_async())

    async def _run_async(self):
        await self._scrape_all_urls()
        self._save_json_cache()
    # ======================

    async def _scrape_all_urls(self):
        clean_urls = []
        clean_url_json_pairs = []
        scryfall_json_dict = {}

        #-- Checkea si esta el json original en la cache
        print("\033[33minicio filtrado de urls\033[0m")
        for u in self.urls:
            if u in SCRYFALL_URL_CACHE:
                self.rawJsons.append((u, SCRYFALL_URL_CACHE[u], u))
            else:
                clean_urls.append(u)

        if len(clean_urls) > 0:
            #-- Screapea nuevas urls para obtener sus jsons
            print(f"\033[33minicio scrapeo de url con {len(clean_urls)} resultados // Se cachearon {len(self.rawJsons)} cartas\033[0m")
            await url_scraper(clean_urls, clean_url_json_pairs, MAX_REQ_PER_SEC)

            #-- Parsea y cachea urls de scryfall
            print("\033[33minicio cacheo de urls\033[0m")
            for i, (url, json) in enumerate(clean_url_json_pairs):
                try:
                    SCRYFALL_URL_CACHE[url] = json
                    self.rawJsons.append((url, json, url))
                    scryfall_json_dict[url] = json
                    #print(f"\033[36mAñadido SCRYFALL: \033[0m{url}")
                except Exception as e:
                    print(f"Dio URL error '{url}': {type(e)} // {e}")
                    self.errors += 1

            print(f"\033[33mSe obtuvieron {len(self.rawJsons)} resultados filtrados de URL\033[0m")
        else:
            #-- Mete todas las cartas cacheadas en el diccionario porsiaca
            for (url, json, scry_url) in self.rawJsons:
                scryfall_json_dict[url] = json

            print(f"\033[33mSe cachearon todas las cartas de \033[36mSCRYFALL\033[33m! ({len(self.rawJsons)} cartas)\033[0m")

        #-- Si es el idioma original, ya esta
        if not self.alt_lang:
            self.finishedJsons = self.rawJsons.copy()

        #-- Si se pide otro idioma, se usan los oracle_id
        else:
            #-- Scrapea para otro idioma usando oracle_id
            oracle_url_pairs = {}
            oracle_url_json_pairs = []
            oracle_fallback_url_pairs = {}

            #-- Filtra por si ya hay algo en cache de oracle
            print("\033[33minicio filtrado de oracle_id\033[0m\033[0m")
            for (url, json, scry_url) in self.rawJsons:
                # por si acaso no tiene oracle_id O es un token se usa el original de scryfall
                oracle_id = _get_card_oracle_id(json)
                if not oracle_id or json.get("layout", "") == "token":
                    self.finishedJsons.append((url, json, scry_url))
                    continue

                oracle_url = f"https://api.scryfall.com/cards/search?q=oracleid:{oracle_id}+lang:{self.lang}"

                if oracle_url in ORACLE_URL_CACHE:
                    self.finishedJsons.append((oracle_url, ORACLE_URL_CACHE[oracle_url], scry_url))
                else:
                    oracle_url_pairs[oracle_url] = scry_url

            if len(oracle_url_pairs) > 0:
                #-- Scrapea las urls con su oracle_id
                print(f"\033[33minicio scrapeo de oracle_id con {len(oracle_url_pairs)} resultados // Se cachearon {len(self.finishedJsons)} cartas\033[0m")
                await url_scraper(list(oracle_url_pairs.keys()), oracle_url_json_pairs, MAX_REQ_PER_SEC)

                #-- Parsea y cachea urls
                print("\033[33minicio cacheo de oracle_id\033[0m")
                for i, (url, json) in enumerate(oracle_url_json_pairs):
                    original_scry_url = oracle_url_pairs[url]

                    try:
                        card_json = json["data"][0]
                        ORACLE_URL_CACHE[url] = card_json

                        self.finishedJsons.append((url, card_json, original_scry_url))
                        print(f"\033[32mAñadido ORACLE: \033[0m{url}")
                    except Exception as e:
                        card_json = SCRYFALL_URL_CACHE.get(original_scry_url, None)
                        if not card_json:
                            card_json = scryfall_json_dict[original_scry_url]

                        ORACLE_URL_CACHE[url] = card_json

                        self.finishedJsons.append((original_scry_url, card_json, original_scry_url))
                        print(f"\033[36mUrl original de SCRYFALL: \033[0m{url}")

            else:
                print(f"\033[33mSe cachearon todas las cartas de \033[31mORACLE\033[33m! ({len(self.finishedJsons)} cartas)\033[0m")


        print(f"\033[33mFin // Se obtuvieron {len(self.finishedJsons)} resultados\033[0m")

    def _save_json_cache(self):
        global SCRYFALL_URL_CACHE, ORACLE_URL_CACHE
        with open(self.cacheFileNames[0], "w", encoding="utf-8") as f:
            json.dump(SCRYFALL_URL_CACHE, f, ensure_ascii=False, indent=2)
        with open(self.cacheFileNames[1], "w", encoding="utf-8") as f:
            json.dump(ORACLE_URL_CACHE, f, ensure_ascii=False, indent=2)

    def _load_json_cache(self):
        global SCRYFALL_URL_CACHE, ORACLE_URL_CACHE
        os.makedirs(self.cacheFolderName, exist_ok=True)
        ctypes.windll.kernel32.SetFileAttributesW(self.cacheFolderName, 0x02) #Pone la carpeta de cache oculta

        # Borrar archivos antiguos
        for file in self.cacheFileNames:
            if os.path.exists(file):
                mtime = os.path.getmtime(file)
                age = time.time() - mtime
                if age > CACHE_LIFETIME_SEC:
                    os.remove(file)
        #Cache SCRYFALL
        try:
            with open(self.cacheFileNames[0], "r", encoding="utf-8") as f:
                SCRYFALL_URL_CACHE = json.load(f)
                print("cache de url obtenida")
        except Exception as e:
            print(f"no se pudo obtener la cache de url // {e}")
        #Cache ORACLE
        try:
            with open(self.cacheFileNames[1], "r", encoding="utf-8") as f:
                ORACLE_URL_CACHE = json.load(f)
                print("cache de oracle obtenida")
        except Exception as e:
            print(f"no se pudo obtener la cache de oracle // {e}")

class CardClass:
    def __init__(self, json_data, quantity:int, lang:str, scryfall_url:str):
        self.json_data = json_data
        self.quantity = quantity
        self.scryfall_url = scryfall_url
        self.lang = lang
        self.alt_lang = False

        self.oracle_id = ""
        self.layout = ""

        self.card_main_name = ""
        self.card_names = []
        self.card_type_text = []
        self.img_urls = []

        # ---------- PARSEO DE DATOS ----------
        self.layout = _get_card_layout(self.json_data)
        self.oracle_id = _get_card_oracle_id(self.json_data, self.layout)
        self._parse_card_data()
        self.cardTypes = self._get_card_type()
        self.quantity = 1 if CardType.TOKEN in self.cardTypes else self.quantity #Cambia la cantidad a 1 si es un token

        # ---------- IMAGENES ----------
        if "image_uris" in self.json_data:
            self.img_urls.append(self.json_data["image_uris"]["border_crop"])
        elif "card_faces" in self.json_data:
            for card_face in self.json_data["card_faces"]:
                self.img_urls.append(card_face["image_uris"]["border_crop"])
        else:
            raise ValueError(f"No hay imagen para {self.card_main_name} / {self.scryfall_url}")

        # ---------- LOG IMPRESO POR CONSOLA ----------
        print(f"\033[33m[+]\033[0m Datos cargados: ({self.quantity}) ", end="")
        if len(self.card_names) == 1:
            print(f"{self.card_names[0]} \033[33m({self.cardTypes[0].__str__(self.lang)})\033[0m")
        else:
            for i in range(len(self.card_names)):
                print(
                    f"{self.card_names[i]} \033[33m({self.cardTypes[i].__str__(self.lang)})\033[0m",
                    end=" // " if i < len(self.card_names) - 1 else "\n")

    def _parse_card_data(self):
        self.alt_lang = "printed_name" in self.json_data
        # Carta con otra carta por atras
        if self.layout != "single":
            name1 = str(self.json_data["card_faces"][0]["printed_name" if self.alt_lang else "name"])
            # misma carta por ambas caras, diferente arte
            if self.layout == "reversible":
                self.card_main_name = name1
                self.card_type_text.append(self.json_data["card_faces"][0]["type_line"])

            # dos cartas diferentes
            else:
                name2 = str(self.json_data["card_faces"][1]["printed_name" if self.alt_lang else "name"])
                self.card_main_name = f"{name1} // {name2}"
                self.card_type_text += self.json_data["type_line"].split("//")

        # Cartas unicas
        else:
            self.card_type_text.append(self.json_data["type_line"])
            self.card_main_name = self.json_data["printed_name" if self.alt_lang else "name"]

        # Divide el nombre de la carta si contiene un "//"
        self.card_main_name = str(self.card_main_name).strip()
        self.card_names = [n.strip() for n in self.card_main_name.split("//")] #Limpia los espacios del principio y fin de cada elemento de la lista



    def showImage(self) -> list:
        imgs = []
        for i in range(len(self.card_names)):
            url = self.img_urls[i]
            imgs.append(Image.open(urlopen(url)))
        return imgs

    def downloadImages(self, folder_path:str):
        for i in range(len(self.card_names)):
            url = self.img_urls[i]
            img = requests.get(url).content

            for q in range(self.quantity):
                filepath = ""
                index = q
                while True:
                    filepath = os.path.join(folder_path, crear_directorio_nuevo(f"{self.card_type_text[i].lower()}_{self.card_names[i].lower()}_{index}.jpg"))
                    if os.path.exists(filepath):
                        index+=1
                    else:
                        break

                open(filepath, "wb").write(img)
                print(f"\033[32m[Y]\033[0m Imagen descargada: {filepath}")

    def _get_card_type(self) -> list[CardType]:
        allTypes = []
        preference = [CardType.TOKEN, CardType.CREATURE]
        for ty in CardType:
            if ty not in preference:
                preference.append(ty)

        for t in self.card_type_text:
            text_type = t.lower()
            found_type = False
            for ty in preference:
                card_type = ty.name.lower()
                if card_type in text_type:
                    allTypes.append(ty)
                    found_type = True
                    break

            if not found_type:
                allTypes.append(CardType.OTHER)

        return allTypes

    def __str__(self):
        return f"{self.card_main_name} (Idioma original: {self.alt_lang}) ({self.quantity}) -> {self.scryfall_url}"

def _get_card_layout(json_data) -> str:
    # Carta con otra carta por atras
    if "card_faces" in json_data:
        name1 = str(json_data["card_faces"][0]["name"])
        name2 = str(json_data["card_faces"][1]["name"])
        #misma carta por ambas caras, diferente arte
        if name1 == name2:
            return "reversible"
        # dos cartas diferentes
        else:
            return "double"
    # Cartas unicas
    else:
        return "single"

def _get_card_oracle_id(json_data, layout="") -> str:
    if layout == "":
        layout = _get_card_layout(json_data)

    if layout == "reversible":
        oracle_id = json_data["card_faces"][0]["oracle_id"]
    else:
        oracle_id = json_data["oracle_id"]
    return oracle_id

if __name__ == "__main__":
    pass