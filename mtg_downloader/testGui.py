import customtkinter as gui
from tkinter import filedialog
import os, threading
from urllib.request import urlopen
from PIL import Image
import mtg_descargar_cartas

DIR_PATH = os.path.dirname(os.path.abspath(__file__))
IMG_PIPA_PATH = os.path.join(DIR_PATH, "img", "jeje.png")
ICON_PATH = os.path.join(DIR_PATH, "img", "pipa.ico")

gui.set_appearance_mode("dark")
gui.set_default_color_theme("green")

BASE_MAGIC_DIMS = (63, 88)
IMG_SIZE_MULT = 4

def get_mtg_dims(mult:float = IMG_SIZE_MULT) -> tuple:
    return (mult*BASE_MAGIC_DIMS[0], mult*BASE_MAGIC_DIMS[1])

def get_img_by_url(url:str):
    # guarda imagenes en memoria, no en el disco duro
    return Image.open(urlopen(url))

class MyCheckboxFrame(gui.CTkFrame):
    def __init__(self, master, values:list[str], title = ""):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        #self.grid_rowconfigure(tuple(range(len(values))), weight=1)
        
        startCol = 0
        self.values = values
        self.checkboxes = []
        
        # Añade un titulo si se puso uno en los parametros
        if title != "":
            self.title = gui.CTkLabel(self, text=title, fg_color="gray30", corner_radius=6)
            self.title.grid(row= 0, column = 0, padx = 10, pady = (10,0), sticky="we")
            startCol += 1
        
        # Crea las checkboxes
        for i, value in enumerate(values):
            padY = (10, 0) if i < len(values)-1 else 10       
            c = gui.CTkCheckBox(self, text=value)
            c.grid(row= i+startCol, column = 0, padx = 10, pady = padY, sticky="w")
            self.checkboxes.append(c)
        
    def get(self):
        # Añade a la lista el texto de las checkboxes que estan marcadas
        checked = []
        for b in self.checkboxes:
            if b.get() == 1:
                checked.append(b.cget("text"))
        return checked

class MyRadioButtonFrame(gui.CTkFrame):
    def __init__(self, master, values:list[str], title = ""):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        
        startCol = 0
        self.values = values
        self.radioButtons = []
        self.variable = gui.StringVar(value="")
        
        # Añade un titulo si se puso uno en los parametros
        if title != "":
            self.title = gui.CTkLabel(self, text=title, fg_color="gray30", corner_radius=6)
            self.title.grid(row= 0, column = 0, padx = 10, pady = (10,0), sticky="we")
            startCol += 1
        
        # Crea los botons
        for i, value in enumerate(values):
            padY = (10, 0) if i < len(values)-1 else 10       
            c = gui.CTkRadioButton(self, text=value, value=value, variable=self.variable)
            c.grid(row= i+startCol, column = 0, padx = 10, pady = padY, sticky="w")
            self.radioButtons.append(c)
        
    def get(self):
        return self.variable.get()
    
    def set(self, value):
        self.variable.set(value)

class FolderPicker(gui.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)

        self.entry = gui.CTkEntry(self, placeholder_text="Selecciona una carpeta...")
        self.entry.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="we")

        self.btn = gui.CTkButton(self, text="📂", width=40, command=self.select_folder)
        self.btn.grid(row=0, column=1, padx=(0, 10), pady=10)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.entry.delete(0, "end")
            self.entry.insert(0, folder)

class CardShowcaseFrame(gui.CTkFrame):
    def __init__(self, master, platform:str, deck_id:str):
        super().__init__(master)
        self.grid_columnconfigure((0,1), weight=1)
        
        self.cards = mtg_descargar_cartas.load_deck(platform, deck_id, False, "orig")
        self.card_index = 0
        
        self.card_imgs = []
        for c in self.cards:
            self.card_imgs.append(c.showImage()[0])

        self.label_name = gui.CTkLabel(self, text=f"{self.cards[0].cardNames[0]}")
        self.label_name.grid(row= 0, column = 0, padx = 10, pady = 10, sticky="we", columnspan=2)

        # Carga la primera imagen de la lista
        self.img = gui.CTkImage(self.card_imgs[0], size=get_mtg_dims(3))     
        self.img_label = gui.CTkLabel(self, text="", image=self.img)
        self.img_label.grid(row= 1, column = 0, padx = 10, pady = 10, sticky="we", columnspan=2)
        
        self.cardCounter = gui.CTkLabel(self, text=f"1 / {len(self.cards)}")
        self.cardCounter.grid(row= 2, column = 0, padx = 10, pady = 0, sticky="we", columnspan=2)  
        
        self.btn_prev = gui.CTkButton(self, text="<", command=self.prev_card, font=("Arial", 20, "bold"))
        self.btn_prev.grid(row= 3, column = 0, padx = 10, pady = 10, sticky="we")  
        
        self.btn_next = gui.CTkButton(self, text=">", command=self.next_card, font=("Arial", 20, "bold"))
        self.btn_next.grid(row= 3, column = 1, padx = 10, pady = 10, sticky="we")  
    
    def change_image(self):

        self.label_name.configure(text=f"{self.cards[self.card_index].cardNames[0]}")

        img = self.card_imgs[self.card_index]
        self.img = gui.CTkImage(img, size=get_mtg_dims(3))
          
        self.img_label.configure(image=self.img)
        self.cardCounter.configure(text=f"{self.card_index+1} / {len(self.cards)}")
        
    def next_card(self):
        if self.card_index >= len(self.cards)-1:
            self.card_index = 0
        else:
            self.card_index += 1  
        self.change_image()
    
    def prev_card(self):
        if self.card_index == 0:
            self.card_index = len(self.cards)-1
        else:
            self.card_index -= 1
        self.change_image()  

class LanguageChooseFrame(gui.CTkFrame):
    def __init__(self, master, values:dict):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)

        startCol = 0
        self.values = values
        self.radioButtons = []
        self.radioVar = gui.StringVar(value="lang")

        for i, (key, val) in enumerate(values.items()):
            padY = (10, 0) if i < len(values)-1 else 10 
            c = gui.CTkRadioButton(self, text=val, value=key, variable=self.radioVar)
            c.grid(row= i+startCol, column = 0, padx = 10, pady = padY, sticky="w")
            self.radioButtons.append(c)

    def get(self):
        return self.radioVar.get()
    
    def set(self, value):
        self.radioVar.set(value)
        
class DeckLoaderFrame(gui.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)

        self.deck = []

        self.input_url = gui.CTkEntry(self, placeholder_text="Url del mazo...")
        self.input_url.grid(row= 0, column = 0, padx = 10, pady = (10, 0), sticky="nswe")

        self.langFrame = LanguageChooseFrame(self, LANGUAGES)
        self.langFrame.grid(row= 1, column = 0, padx = 10, pady = (10, 0), sticky="nswe")

        self.btn_search = gui.CTkButton(self, text="Comprobar datos de mazo", command=self.comprobar_datos)
        self.btn_search.grid(row= 2, column = 0, padx = 10, pady = (10, 0), sticky="nswe")
        
        self.folder_input = FolderPicker(self)
        self.folder_input.grid(row= 3, column = 0, padx = 10, pady = (10, 0), sticky="nswe")

        self.debugText = gui.CTkLabel(self, text=f"aloooo", anchor="nw", justify="left")
        self.debugText.grid(row= 4, column = 0, padx = 10, pady = (5, 0), sticky="w")  
    
    def get_deck_data(self):
        url = self.input_url.get()
        platform, id = mtg_descargar_cartas.get_platform_and_id(url)
        deckName = mtg_descargar_cartas.get_json(platform, id)["name"]
        lang = self.langFrame.get()
        return (platform, id, lang, deckName)
    
    def comprobar_datos(self):
        try:
            self.btn_search.configure(True, state="disabled")
            platform, id, lang, deckName = self.get_deck_data()

            self.debugText.configure(text=f"====== DATOS DEL MAZO ======\n\n[ {deckName} ]\nPlataforma: {platform}\nID: {id}\nIdioma: {LANGUAGES.get(lang, "no se")}")
            self.btn_search.configure(True, state="normal")
        except Exception as e:
            self.btn_search.configure(True, state="normal")
            self.debugText.configure(text=e)    

class App(gui.CTk):
    def __init__(self):
        super().__init__()
        self.title("Soy homero chino")
        self.iconbitmap(ICON_PATH)
        self.geometry("800x600")
        self.grid_columnconfigure((0,1,2,3,4), weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.titleText = gui.CTkLabel(self, text="Titulo do Aplicação", font=("Arial", 20, "bold"))
        self.titleText.grid(row= 0, column = 0, padx = 0, pady = (10, 0), sticky="we", columnspan = 5)

        self.url_info = DeckLoaderFrame(self)
        self.url_info.grid(row= 1, column = 0, padx = 10, pady = (10, 0), sticky="nswe", columnspan = 2)
        
        self.cardFrame = CardShowcaseFrame(self, "moxfield", "rFMAHnn5EkCVWCtNJQ7CkA")
        self.cardFrame.grid(row= 1, column = 2, padx = 10, pady = (10, 0), sticky="nswe", columnspan = 3)

        #self.checkboxFrame1 = MyCheckboxFrame(self, values=["pito", "pete", "puta", "pato"], title="Check")
        #self.checkboxFrame1.grid(row= 1, column = 4, padx = 10, pady = (10, 0), sticky="nswe")
        
        #self.btn_load_deck = gui.CTkButton(self, text="Cargar imagenes del mazo", command=self.load_deck)
        #self.btn_load_deck.grid(row= 2, column = 0, padx = 20, pady = 20, sticky="we", columnspan=2)
        #
        #self.btn_download_deck = gui.CTkButton(self, text="Descargar imagenes", command=self.btn_callback)
        #self.btn_download_deck.grid(row= 2, column = 2, padx = 20, pady = 20, sticky="we", columnspan=2)
        # 
        #self.btn = gui.CTkButton(self, text="Soy homero", command=self.btn_callback)
        #self.btn.grid(row= 2, column = 4, padx = 20, pady = 20, sticky="we", columnspan=1)

        
    def btn_callback(self):
        print("peo")
        #print(f"Checkboxes marcadas: {self.checkboxFrame1.get()}")
        #mtg_descargar_cartas.callback()
        
    #def load_deck(self):
    #    try:
    #        self.btn_load_deck.configure(True, state="disabled")
    #        platform, id, lang, deckName = self.url_info.get_deck_data()
#
    #        #self.debugText.configure(text=f"Obteniendo cartas...\n\nPlataforma: {platform}\nID: {id}\nIdioma: {LANGUAGES.get(lang, "no se")}")
#
    #        #Usa thread para no colapsar el codigo        
    #        threading.Thread(
    #            target=self._thread_load_deck,
    #            args=(platform, id, lang),
    #            daemon=True # Si se cierra la app, el hilo hace kaput
    #        ).start()
#
    #    except Exception as e:
    #        self.btn_load_deck.configure(True, state="normal")
    #        #self.debugText.configure(text=e)

    def _thread_load_deck(self, platform, id, lang):
        deck = mtg_descargar_cartas.load_deck(platform, id, True, lang)
        
        #Llama a la otra funcion al terminar todo
        self.after(0, lambda: self._on_deck_loaded(deck))
    
    def _on_deck_loaded(self, deck):
        self.deck = deck
        #self.btn_load_deck.configure(True, state="normal")
        #self.debugText.configure(text=f"Cartas obtenidas: {len(self.deck)}")

LANGUAGES = {
    "orig":"Original (Mejor calidad)",
    "en":"English",
    "es":"Español"
}


