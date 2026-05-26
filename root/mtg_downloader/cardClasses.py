"""Archivo principal para definir la clase CardClass, que representa una carta de Magic con sus datos y métodos para descargar imágenes. También incluye la clase CardScraper para obtener los datos de las cartas desde URLs, con manejo de cache para optimizar el proceso."""
import asyncio
from enum import Enum
import sys, os, requests, json, time, ctypes
from PIL import Image
from urllib.request import urlopen

from mtg_downloader.scraper import scrape_json as url_scraper
from packages.basicFunctions import *

# ---------------- CACHE GLOBAL ----------------
SCRYFALL_URL_CACHE = {}          # cache por URL / Guarda el JSON entero de Scryfall para cada url
ORACLE_URL_CACHE = {}           # cache por oracle_id + lang / Guarda el JSON por Oracle ID + Idiom
CACHE_LIFETIME_SEC = 3 * 24 * 60 * 60 # Tres dias
MAX_REQ_PER_SEC = 5

#Doble cara necesaria: transform, modal_dfc
#Doble cara innecesaria: reversible
#Solo una cara: (el resto)
DOUBLE_LAYOUTS = ["transform", "modal_dfc"]


class CardType(Enum):
    """Enumeración de tipos de cartas de Magic: The Gathering. Incluye tipos comunes como Criatura, Instantáneo, Encantamiento, así como categorías especiales como Commander y Token. El método __str__ permite obtener una representación legible del tipo en diferentes idiomas, con un fallback al inglés si el idioma no es reconocido."""
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
    COMMANDER = 18
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
                    CardType.COMMANDER: "Commader",
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
    """Clase principal para obtener los datos de las cartas desde URLs. Toma una lista de URLs y un idioma, y maneja el proceso de scrappeo con cache para optimizar la obtención de datos. El método run inicia el proceso, que incluye scrappear las URLs, parsear los datos y guardar los resultados en la propiedad finishedJsons. Maneja errores y limita la cantidad de solicitudes por segundo para evitar bloqueos."""
   
    def __init__(self, urls: list, lang: str):
        self.urls = urls
        self.lang = lang
        self.altLang = lang != "orig"
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
            for (url, json, scryUrl) in self.rawJsons:
                scryfall_json_dict[url] = json
                
            print(f"\033[33mSe cachearon todas las cartas de \033[36mSCRYFALL\033[33m! ({len(self.rawJsons)} cartas)\033[0m")
            
        #-- Si es el idioma original, ya esta
        if not self.altLang:
            self.finishedJsons = self.rawJsons.copy()

        #-- Si se pide otro idioma, se usan los oracle_id
        else:
            #-- Scrapea para otro idioma usando oracle_id
            oracle_url_pairs = {}
            oracle_url_json_pairs = []

            #-- Filtra por si ya hay algo en cache de oracle
            print("\033[33minicio filtrado de oracle_id\033[0m\033[0m")
            for (url, json, scryUrl) in self.rawJsons:
                # por si acaso no tiene oracle_id O es un token se usa el original de scryfall
                oracle_id = _get_card_oracle_id(json)
                if not oracle_id or json.get("layout", "") == "token":
                    self.finishedJsons.append((url, json, scryUrl))
                    continue
                
                oracle_url = f"https://api.scryfall.com/cards/search?q=oracleid:{oracle_id}+lang:{self.lang}"

                if oracle_url in ORACLE_URL_CACHE:
                    self.finishedJsons.append((oracle_url, ORACLE_URL_CACHE[oracle_url], scryUrl))
                else:
                    oracle_url_pairs[oracle_url] = scryUrl

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
        """Guarda las caches globales SCRYFALL_URL_CACHE y ORACLE_URL_CACHE en archivos JSON dentro de la carpeta de cache. Crea la carpeta si no existe y la oculta. Antes de guardar, elimina los archivos de cache que sean más antiguos que CACHE_LIFETIME_SEC para evitar acumular datos obsoletos. Maneja errores al guardar e imprime mensajes informativos sobre el proceso."""
        global SCRYFALL_URL_CACHE, ORACLE_URL_CACHE
        with open(self.cacheFileNames[0], "w", encoding="utf-8") as f:
            json.dump(SCRYFALL_URL_CACHE, f, ensure_ascii=False, indent=2)  
        with open(self.cacheFileNames[1], "w", encoding="utf-8") as f:
            json.dump(ORACLE_URL_CACHE, f, ensure_ascii=False, indent=2)  
        
    def _load_json_cache(self):
        """Carga las caches globales SCRYFALL_URL_CACHE y ORACLE_URL_CACHE desde archivos JSON dentro de la carpeta de cache. Crea la carpeta si no existe y la oculta. Antes de cargar, elimina los archivos de cache que sean más antiguos que CACHE_LIFETIME_SEC para evitar usar datos obsoletos. Maneja errores al cargar e imprime mensajes informativos sobre el proceso."""
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
                SCRYFALL_URL_CACHE.update(json.load(f))
                print("cache de url obtenida")
        except Exception as e:
            print(f"no se pudo obtener la cache de url // {e}")
        #Cache ORACLE
        try:
            with open(self.cacheFileNames[1], "r", encoding="utf-8") as f:
                ORACLE_URL_CACHE.update(json.load(f))
                print("cache de oracle obtenida")
        except Exception as e:
            print(f"no se pudo obtener la cache de oracle // {e}")

class CardClass:
    """Clase que representa una carta de Magic: The Gathering con sus datos y métodos para descargar imágenes. Toma un JSON de Scryfall, la cantidad de copias, el idioma, la URL original de Scryfall y si es commander. Parsea los datos relevantes como el nombre, tipo, layout y URLs de imagen. El método downloadImages permite descargar las imágenes de la carta a una carpeta especificada, generando nombres únicos para evitar sobrescribir archivos. El método showImage devuelve las imágenes como objetos PIL para visualización."""
    def __init__(self, jsonData, quantity:int, lang:str, scryfall_url:str, isCommander:bool):       
        self.jsonData = jsonData
        self.quantity = quantity
        self.scryfall_url = scryfall_url
        self.lang = lang
        self.altLang = False
        self.isCommander = isCommander
        
        self.oracle_id = ""
        self.layout = ""
        
        self.cardMainName = ""
        self.cardNames = []       
        self.cardTypeText = []
        self.img_urls = []
                 
        # ---------- PARSEO DE DATOS ----------   
        self.layout = _get_card_layout(self.jsonData)
        self.oracle_id = _get_card_oracle_id(self.jsonData)
        self._parse_card_data()
        self.cardTypes = self._get_cardType()
        self.quantity = 1 if CardType.TOKEN in self.cardTypes else self.quantity #Cambia la cantidad a 1 si es un token
           
        # ---------- IMAGENES ----------
        if "image_uris" in self.jsonData:
            self.img_urls.append(self.jsonData["image_uris"]["border_crop"])
        elif "card_faces" in self.jsonData:
            for card_face in self.jsonData["card_faces"]:
                self.img_urls.append(card_face["image_uris"]["border_crop"])
        else:
            raise ValueError(f"No hay imagen para {self.cardMainName} / {self.scryfall_url}") 
        
        # ---------- LOG IMPRESO POR CONSOLA ----------
        print(f"\033[33m[+]\033[0m Datos cargados: ({self.quantity}) ", end="")
        if len(self.cardNames) == 1:
            print(f"{self.cardNames[0]} \033[33m({self.cardTypes[0].__str__(self.lang)})\033[0m")
        else:
            for i in range(len(self.cardNames)):
                print(
                    f"{self.cardNames[i]} \033[33m({self.cardTypes[i].__str__(self.lang)})\033[0m", 
                    end=" // " if i < len(self.cardNames) - 1 else "\n")
            
    def _parse_card_data(self):
        """Parsea los datos relevantes del JSON de Scryfall para obtener el nombre, tipo, layout y URLs de imagen de la carta. Maneja diferentes layouts como single, reversible y double, y extrae la información correspondiente según el formato del JSON. Si no se encuentra la información esperada, lanza errores con mensajes informativos."""
        self.altLang = "printed_name" in self.jsonData

        if self.layout == "single":
            self.cardMainName = self.jsonData["printed_name" if self.altLang else "name"].strip()
            self.cardNames = [self.cardMainName]
            self.cardTypeText.append(self.jsonData["type_line"])
        elif self.layout == "reversible":
            if "card_faces" in self.jsonData and len(self.jsonData["card_faces"]) > 0:
                self.cardMainName = self.jsonData["card_faces"][0]["printed_name" if self.altLang else "name"].strip()
                self.cardNames = [self.cardMainName]
                self.cardTypeText.append(self.jsonData["card_faces"][0]["type_line"])
            else:
                raise ValueError(f"Tarjeta reversible sin card_faces válidas: {self.scryfall_url}")
        else:
            if "card_faces" in self.jsonData and len(self.jsonData["card_faces"]) >= 2:
                name1 = str(self.jsonData["card_faces"][0]["printed_name" if self.altLang else "name"].strip())
                name2 = str(self.jsonData["card_faces"][1]["printed_name" if self.altLang else "name"].strip())
                self.cardMainName = f"{name1} // {name2}"
                self.cardNames = [name1, name2]
                self.cardTypeText += self.jsonData["type_line"].split("//")
            else:
                raise ValueError(f"Tarjeta doble cara sin card_faces válidas: {self.scryfall_url}") 
  
    def showImage(self) -> list:
        """Devuelve las imágenes de la carta como objetos PIL para visualización. Descarga las imágenes desde las URLs obtenidas y las abre con PIL. Si no se encuentra una imagen o hay un error al descargar, lanza errores con mensajes informativos."""
        imgs = []
        for i in range(len(self.cardNames)):
            url = self.img_urls[i]
            imgs.append(Image.open(urlopen(url)))
        return imgs
            
    def downloadImages(self, folder_path:str):       
        """Descarga las imágenes de la carta a una carpeta especificada, generando nombres únicos para evitar sobrescribir archivos. Para cada imagen, genera un nombre basado en el tipo de carta y el nombre, y si ya existe un archivo con ese nombre, agrega un índice para hacerlo único. Descarga la imagen desde la URL y la guarda en la carpeta. Imprime mensajes informativos sobre el proceso de descarga.""" 
        for i in range(len(self.cardNames)):
            url = self.img_urls[i]
            img = requests.get(url).content
            
            for q in range(self.quantity):
                # Generar nombre único de archivo
                base_name = f"{self.cardTypeText[i].lower()}_{self.cardNames[i].lower()}".strip()
                index = q
                while True:
                    filename = f"{base_name}_{index}.jpg"
                    filepath = os.path.join(folder_path, filename)
                    if not os.path.exists(filepath):
                        break
                    index += 1

                open(filepath, "wb").write(img)
                print(f"\033[32m[Y]\033[0m Imagen descargada: {filepath}")  
                
    def _get_cardType(self) -> list[CardType]:
        """Determina el tipo de carta basado en el texto del tipo obtenido del JSON. Si la carta es un commander, asigna el tipo Commander. Para otras cartas, compara el texto del tipo con una lista de tipos preferidos (Token, Criatura, Planeswalker) y luego con el resto de tipos definidos en la enumeración CardType. Si no se encuentra un tipo coincidente, asigna el tipo Other. Devuelve una lista de tipos encontrados para la carta."""
        allTypes = []
        if self.isCommander:
            for t in self.cardTypeText:
                allTypes.append(CardType.COMMANDER)
        else: 
            preference = [CardType.TOKEN, CardType.CREATURE, CardType.PLANESWALKER]
            for ty in CardType: #Añade el resto de tipos detras del resto
                if ty not in preference:
                    preference.append(ty)   

            for t in self.cardTypeText:
                text_type = t.lower()
                found_type = False
                for ty in preference: #Criba por cada tipo 
                    card_type = ty.name.lower()
                    if card_type in text_type:
                        allTypes.append(ty)
                        found_type = True
                        break
                    
                if not found_type:
                    allTypes.append(CardType.OTHER)
                
        return allTypes               
    
    def __str__(self):
        return f"{self.cardMainName} (Idioma original: {self.altLang}) ({self.quantity}) -> {self.scryfall_url}"
    
def _get_card_layout(jsonData) -> str: 
    """Determina el layout de la carta basado en el campo "layout" del JSON de Scryfall. Si el layout es uno de los definidos en DOUBLE_LAYOUTS, devuelve "double". Si el layout es "reversible_card", devuelve "reversible". Para cualquier otro layout, devuelve "single". Este método ayuda a clasificar las cartas según su formato para un manejo adecuado en otras partes del código."""
    if jsonData["layout"] in DOUBLE_LAYOUTS:
        return "double"
    elif jsonData["layout"] == "reversible_card":
        return "reversible"
    else:
        return "single"    
        
def _get_card_oracle_id(jsonData) -> str|None:   
    """Obtiene el oracle_id de la carta desde el JSON de Scryfall. Intenta obtenerlo directamente del campo "oracle_id". Si no está presente, intenta obtenerlo del primer card_face en caso de que sea una carta doble. Si no se encuentra un oracle_id válido, devuelve None. Este método es útil para identificar cartas de manera única y para obtener datos en diferentes idiomas usando el oracle_id."""
    try:
        return jsonData["oracle_id"]
    except (KeyError, TypeError):
        try:
            return jsonData["card_faces"][0]["oracle_id"]
        except (KeyError, IndexError, TypeError):
            return None