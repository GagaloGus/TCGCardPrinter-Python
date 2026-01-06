from enum import Enum
import sys
from PIL import Image
import os
import requests
from urllib.request import urlopen

#Añade el directorio de arriba en el path para usar scripts fuera de la carpeta
sys.path.insert(1, "/".join(os.path.realpath(__file__).split("/")[0:-2]))
from basicFunctions import *

# ---------------- CACHE GLOBAL ----------------
SCRYFALL_URL_CACHE = {}          # cache por URL / Guarda el JSON entero de Scryfall para cada url
ORACLE_LANG_CACHE = {}           # cache por oracle_id + lang / Guarda el JSON por Oracle ID + Idioma

SESSION = requests.Session()     # reutiliza conexiones HTTP

def cached_get(url: str):
    if url in SCRYFALL_URL_CACHE:
        return SCRYFALL_URL_CACHE[url]

    response = SESSION.get(url)
    data = response.json()
    SCRYFALL_URL_CACHE[url] = data
    return data

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

class CardClass:
    def __init__(self, quantity:int, scryfall_url:str, lang:str = "orig", base_jsonData=None):       
        self.quantity = quantity
        self.scryfall_url = scryfall_url
        self.lang = lang
        
        self.oracle_id = ""
        self.layout = ""
        self.altLang = False
        
        self.cardMainName = ""
        self.cardNames = []       
        self.cardTypeText = []
        self.img_urls = []
        
        # ---------- BASE JSON (SIEMPRE HACE 1 REQUEST SI NO SE LE HA PASADO EL PARAMETRO) ----------
        self.jsonData = self._fetch_base_json() if base_jsonData == None else base_jsonData
        
        # ---------- IDIOMA ALTERNATIVO (USANDO CACHE) ----------
        if self.lang != "orig":
            self.jsonData, self.altLang = self._fetch_altLang_json()    
             
        # ---------- PARSEO DE DATOS ----------   
        self.layout = self._get_card_layout()
        self.oracle_id = self._get_oracle_id()
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
    
    def _fetch_base_json(self):
        return cached_get(self.scryfall_url)
    
    def _fetch_altLang_json(self):       
        cache_key = f"{self.oracle_id}:{self.lang}"
        
        # ----- [1] MIRA SI EXISTE YA EN LA CACHE -----
        if cache_key in ORACLE_LANG_CACHE:
            return ORACLE_LANG_CACHE[cache_key]
        
        # ----- [2] BUSCA EN EL MISMO SET -----
        #data = cached_get(f"{self.scryfall_url}/{self.lang}")
        #if data.get("object") != "error":
        #    result = (data, True, self._get_card_layout(data))
        #    ORACLE_LANG_CACHE[cache_key] = result
        #    return result
            
        # ----- [3] BUSCA EN OTRO SET USANDO ORACLE -----
        url = f"https://api.scryfall.com/cards/search?q=oracleid:{self.oracle_id}+lang:{self.lang}"
        data = cached_get(url)
        
        if data.get("object") == "list" and data["total_cards"] >= 1:
            card = data["data"][0]
            result = (card, True)
            ORACLE_LANG_CACHE[cache_key] = result
            return result
            
        # ----- [4] FALLBACK EN IDIOMA ORIGINAL -----
        result = (self.jsonData, False)
        ORACLE_LANG_CACHE[cache_key] = result
        return result
     
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
                    
    def _get_card_layout(self) -> str:            
        # Carta con otra carta por atras
        if "card_faces" in self.jsonData:
            name1 = str(self.jsonData["card_faces"][0]["name"])
            name2 = str(self.jsonData["card_faces"][1]["name"])
            #misma carta por ambas caras, diferente arte
            if name1 == name2:
                return "reversible"
            # dos cartas diferentes
            else:
                return "double"
        # Cartas unicas
        else:
            return "single"    
           
    def _get_oracle_id(self) -> str:
        if self.layout == "":
            self.layout = self._get_card_layout()
        
        if self.layout == "reversible":
            oracle_id = self.jsonData["card_faces"][0]["oracle_id"]
        else:
            oracle_id = self.jsonData["oracle_id"]   
        return oracle_id 
    
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
