from enum import Enum
import sys, os, requests, json, time
from PIL import Image
from urllib.request import urlopen

#Añade el directorio de arriba en el path para usar scripts fuera de la carpeta
sys.path.insert(1, "/".join(os.path.realpath(__file__).split("/")[0:-2]))
from basicFunctions import *
from request_json import run as url_scraper

# ---------------- CACHE GLOBAL ----------------
SCRYFALL_URL_CACHE = {}          # cache por URL / Guarda el JSON entero de Scryfall para cada url
ORACLE_LANG_CACHE = {}           # cache por oracle_id + lang / Guarda el JSON por Oracle ID + Idiom
CACHE_LIFETIME_SEC = 24 * 60 * 60 # Un dia
MAX_REQ_PER_SEC = 5

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
        3. si el idioma es "orig" scrapedJsons sera igual a rawJsons, si no, se obtiene su url con su oracle_id y se scrapean una vez mas
    """
   
    def __init__(self, urls: list, lang: str):
        self.urls = urls
        self.lang = lang
        self.rawJsons = []
        self.finishedJsons = []
        
        self.errors = 0
        self._load_json_cache()
        
    def run(self):
        self._scrape_all_urls()
        
    def _save_json_cache(self):
        global SCRYFALL_URL_CACHE, ORACLE_LANG_CACHE
        with open("scryfall_cache.json", "w", encoding="utf-8") as f:
            json.dump(SCRYFALL_URL_CACHE, f, ensure_ascii=False, indent=2)  
        with open("oracle_cache.json", "w", encoding="utf-8") as f:
            json.dump(ORACLE_LANG_CACHE, f, ensure_ascii=False, indent=2)  
        
    def _load_json_cache(self):
        global SCRYFALL_URL_CACHE, ORACLE_LANG_CACHE
        files = ["scryfall_cache.json", "oracle_cache.json"]
        
        # Borrar archivos antiguos
        for file in files:
            if os.path.exists(file):
                mtime = os.path.getmtime(file)
                age = time.time() - mtime
                if age > CACHE_LIFETIME_SEC:
                    os.remove(file)
        #Cache SCRYFALL
        try:
            with open(files[0], "w", encoding="utf-8") as f:
                SCRYFALL_URL_CACHE = json.load(f)
        except:
            pass
        #Cache ORACLE
        try:
            with open(files[1], "w", encoding="utf-8") as f:
                ORACLE_LANG_CACHE = json.load(f)
        except:
            pass
        
    def _scrape_all_urls(self):
        clean_urls = []
        clean_jsons = []
        
        #-- Checkea si esta el json original en la cache
        print("\033[33minicio filtrado de urls\033[0m")
        for u in self.urls:
            if u in SCRYFALL_URL_CACHE:
                self.rawJsons.append((u, SCRYFALL_URL_CACHE[u]))
            else:
                clean_urls.append(u)
        
        #-- Screapea nuevas urls para obtener sus jsons
        print(f"\033[33minicio scrapeo de url con {len(clean_urls)} resultados\033[0m")
        url_scraper(clean_urls, clean_jsons, MAX_REQ_PER_SEC)     

        print("\033[33minicio cacheo de urls\033[0m")
        for i, json in enumerate(clean_jsons):
            try:
                url = clean_urls[i]
                SCRYFALL_URL_CACHE[url] = json
                self.rawJsons.append((clean_urls[i], json))
            except Exception as e:
                print(f"Dio URL error '{clean_urls[i]}': {e}")
                self.errors += 1
        
        print(f"\033[33mSe obtuvieron {len(self.rawJsons)} resultados filtrados de URL\033[0m")
        
        #-- Si es el idioma original, ya esta
        if self.lang == "orig":
            self.finishedJsons = self.rawJsons.copy()

        #-- Si se pide otro idioma, se usan los oracle_id
        else:
            #-- Scrapea para otro idioma usando oracle_id
            oracle_jsons = []
            oracle_urls = []

            print("\033[33minicio filtrado de oracle_id\033[0m\033[0m")
            for u in self.rawJsons:
                cache_url = f"https://api.scryfall.com/cards/search?q=oracleid:{_get_card_oracle_id(u[1])}+lang:{self.lang}"

                if cache_url in ORACLE_LANG_CACHE:
                    self.finishedJsons.append((cache_url, ORACLE_LANG_CACHE[cache_url]))
                else:
                    oracle_urls.append(cache_url)

            print(f"\033[33minicio scrapeo de oracle_id con {len(clean_urls)} resultados\033[0m")
            url_scraper(oracle_urls, oracle_jsons, MAX_REQ_PER_SEC)

            print("\033[33minicio cacheo de oracle_id\033[0m")
            for i, json in enumerate(oracle_jsons):
                try:
                    url = oracle_urls[i]
                    card = json["data"][0]
                    ORACLE_LANG_CACHE[url] = card
                    self.finishedJsons.append((url, card))
                except Exception as e:
                    print(f"Dio ORACLE error '{oracle_urls[i]}': {e}")   
                    # --- Fallback: usa el json original de rawJsons correspondiente ---
                    original_card = self.rawJsons[i] 
                    ORACLE_LANG_CACHE[original_card[0]] = original_card[1]
                    self.finishedJsons.append((original_card[0], original_card[1]))

                    self.errors += 1
                    
        self._save_json_cache()                         
        print(f"\033[33mFin // Se obtuvieron {len(self.finishedJsons)} resultados\033[0m")                

class CardClass:
    def __init__(self, jsonData, quantity:int, lang:str, scryfall_url:str):       
        self.jsonData = jsonData
        self.quantity = quantity
        self.scryfall_url = scryfall_url
        self.lang = lang
        self.altLang = False
        
        self.oracle_id = ""
        self.layout = ""
        
        self.cardMainName = ""
        self.cardNames = []       
        self.cardTypeText = []
        self.img_urls = []
                 
        # ---------- PARSEO DE DATOS ----------   
        self.layout = _get_card_layout(self.jsonData)
        self.oracle_id = _get_card_oracle_id(self.jsonData, self.layout)
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
        print(f"\033[33m[+]\033[0m Datos cargados: ", end="")
        if len(self.cardNames) == 1:
            print(f"{self.cardNames[0]} \033[33m({self.cardTypes[0].__str__(self.lang)})\033[0m")
        else:
            for i in range(len(self.cardNames)):
                print(
                    f"{self.cardNames[i]} \033[33m({self.cardTypes[i].__str__(self.lang)})\033[0m", 
                    end=" // " if i < len(self.cardNames) - 1 else "\n")
            
    def _parse_card_data(self):
        self.altLang = "printed_name" in self.jsonData
        # Carta con otra carta por atras
        if self.layout != "single":
            name1 = str(self.jsonData["card_faces"][0]["printed_name" if self.altLang else "name"])
            # misma carta por ambas caras, diferente arte
            if self.layout == "reversible":
                self.cardMainName = name1
                self.cardTypeText.append(self.jsonData["card_faces"][0]["type_line"])
            
            # dos cartas diferentes
            else:
                name2 = str(self.jsonData["card_faces"][1]["printed_name" if self.altLang else "name"])
                self.cardMainName = f"{name1} // {name2}"
                self.cardTypeText += self.jsonData["type_line"].split("//") 
        
        # Cartas unicas
        else:
            self.cardTypeText.append(self.jsonData["type_line"])
            self.cardMainName = self.jsonData["printed_name" if self.altLang else "name"]
            
        # Divide el nombre de la carta si contiene un "//"
        self.cardMainName = str(self.cardMainName).strip()
        self.cardNames = [n.strip() for n in self.cardMainName.split("//")] #Limpia los espacios del principio y fin de cada elemento de la lista
    

     
    def showImage(self) -> list:
        imgs = []
        for i in range(len(self.cardNames)):
            url = self.img_urls[i]
            imgs.append(Image.open(urlopen(url)))
        return imgs
            
    def downloadImages(self, folder_path:str):        
        for i in range(len(self.cardNames)):
            url = self.img_urls[i]
            img = requests.get(url).content
            
            for q in range(self.quantity):
                filepath = os.path.join(folder_path, crear_directorio_nuevo(f"{self.cardTypeText[i].lower()}_{self.cardNames[i].lower()}_{q}.jpg"))    
                open(filepath, "wb").write(img)
                print(f"\033[32m[Y]\033[0m Imagen descargada: {filepath}")  
                
    def _get_cardType(self) -> list[CardType]:
        allTypes = []
        preference = [CardType.TOKEN, CardType.CREATURE]
        for ty in CardType:
            if ty not in preference:
                preference.append(ty)   

        for t in self.cardTypeText:
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
        return f"{self.cardMainName} (Idioma original: {self.altLang}) ({self.quantity}) -> {self.scryfall_url}"
    
def _get_card_layout(jsonData) -> str:            
    # Carta con otra carta por atras
    if "card_faces" in jsonData:
        name1 = str(jsonData["card_faces"][0]["name"])
        name2 = str(jsonData["card_faces"][1]["name"])
        #misma carta por ambas caras, diferente arte
        if name1 == name2:
            return "reversible"
        # dos cartas diferentes
        else:
            return "double"
    # Cartas unicas
    else:
        return "single"    
        
def _get_card_oracle_id(jsonData, layout="") -> str:
    if layout == "":
        layout = _get_card_layout(jsonData)
    
    if layout == "reversible":
        oracle_id = jsonData["card_faces"][0]["oracle_id"]
    else:
        oracle_id = jsonData["oracle_id"]   
    return oracle_id 