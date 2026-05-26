import customtkinter as gui
from tkinter import filedialog
import os, threading
from urllib.request import urlopen
from PIL import Image
import mtg_downloader.mtg_descargar_cartas as mtg_descargar_cartas
from mtg_downloader.cardClasses import CardClass

BASE_MAGIC_DIMS = (63, 88)
IMG_SIZE_MULT = 4

LANGUAGES = {
    "orig":"Original (Mejor calidad)",
    "en":"English",
    "es":"Español"
}

DIR_PATH = os.path.dirname(os.path.abspath(__file__))
CARD_BACK_PATH = os.path.join(DIR_PATH, "img", "card_back.png")

def get_mtg_dims(mult:float = IMG_SIZE_MULT) -> tuple:
    return (mult*BASE_MAGIC_DIMS[0], mult*BASE_MAGIC_DIMS[1])

def get_img_by_url(url:str):
    # guarda imagenes en memoria, no en el disco duro
    return Image.open(urlopen(url)).convert("RGBA")

def get_img_by_path(path:str):
    # guarda imagenes en memoria, no en el disco duro
    return Image.open(path).convert("RGBA")

class FolderPicker(gui.CTkFrame):
    def __init__(self, master, placeholder:str):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)

        self.entry = gui.CTkEntry(self, placeholder_text=placeholder)
        self.entry.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="we")

        self.btn = gui.CTkButton(self, text="📂", width=40, command=self.select_folder)
        self.btn.grid(row=0, column=1, padx=(0, 10), pady=10)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.entry.delete(0, "end")
            self.entry.insert(0, folder)
            
    def get(self):
        return self.entry.get()


class DeckInputFrame(gui.CTkFrame):
    def __init__(self, master, on_deck_loaded):
        super().__init__(master)
        self.on_deck_loaded = on_deck_loaded
        self.grid_columnconfigure(0, weight=1)

        self.url_entry = gui.CTkEntry(self, placeholder_text="Url del mazo...")
        self.url_entry.grid(row=0, column=0, padx=10, pady=5, sticky="we")

        self.lang_var = gui.StringVar(value="orig")
        for i, (k, v) in enumerate(LANGUAGES.items()):
            gui.CTkRadioButton(self, text=v, value=k, variable=self.lang_var)\
                .grid(row=1+i, column=0, sticky="w", padx=10)

        self.tokens_var = gui.BooleanVar(value=False)
        gui.CTkCheckBox(self, text="Incluir tokens", variable=self.tokens_var)\
            .grid(row=4, column=0, sticky="w", padx=10, pady=5)

        self.load_btn = gui.CTkButton(self, text="Cargar mazo", command=self.load_deck)
        self.load_btn.grid(row=5, column=0, padx=10, pady=10, sticky="we")

        self.status = gui.CTkLabel(self, text="", justify="left")
        self.status.grid(row=6, column=0, padx=10, sticky="w")

    def load_deck(self):
        self.load_btn.configure(state="disabled")
        self.status.configure(text="Cargando mazo...")

        url = self.url_entry.get()
        lang = self.lang_var.get()
        tokens = self.tokens_var.get()
        platform, deck_id = mtg_descargar_cartas.get_platform_and_id(url)

        threading.Thread(
            target=self._thread_load,
            args=(platform, deck_id, tokens, lang),
            daemon=True
        ).start()

    def _thread_load(self, platform, deck_id, tokens, lang):
        deck = mtg_descargar_cartas.load_deck(platform, deck_id, tokens, lang)
        self.after(0, lambda: self._done(deck))

    def _done(self, deck):
        self.load_btn.configure(state="normal")
        self.status.configure(text=f"Mazo cargado: {len(deck)} cartas")
        self.on_deck_loaded(deck)
        
class CardViewerFrame(gui.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.interiorDiv = gui.CTkFrame(self, fg_color="blue")
        self.interiorDiv.grid(row=0, column=0, sticky="nswe", padx=20, pady=20)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.card = None

        self.img = gui.CTkImage(get_img_by_path(CARD_BACK_PATH), size=get_mtg_dims(4))
        self.img_label = gui.CTkLabel(self.interiorDiv, text="", image=self.img)
        self.tree = CardTreeFrame(self.interiorDiv, self.show_card)
        
        self.img_label.grid(row=0, column=0, sticky="nws", padx=(0, 60))
        self.tree.grid(row=0, column=1, sticky="nes")

    def show_card(self, card: CardClass):
        self.card = card
        img = card.showImage()[0]
        self.img = gui.CTkImage(img, size=get_mtg_dims(4))
        self.img_label.configure(image=self.img)
        
class CardTypeGroup(gui.CTkFrame):
    def __init__(self, master, title, cards, on_select):
        super().__init__(master)
        self.open = False
        self.cards = cards
        self.on_select = on_select

        self.header = gui.CTkLabel(self, text=f"> {title} - {len(cards)}", cursor="hand2")
        self.header.pack(anchor="w", padx=5)
        self.header.bind("<Button-1>", self.toggle)

        self.body = gui.CTkFrame(self)

        for c in cards:
            lbl = gui.CTkLabel(self.body, text=f"  - {c.cardNames[0]}", cursor="hand2")
            lbl.pack(anchor="w", padx=20)
            lbl.bind("<Button-1>", lambda e, card=c: on_select(card))

    def toggle(self, _):
        self.open = not self.open
        self.header.configure(text=("v" if self.open else ">") + self.header.cget("text")[1:])
        if self.open:
            self.body.pack(anchor="w")
        else:
            self.body.pack_forget()
            
class CardTreeFrame(gui.CTkScrollableFrame):
    def __init__(self, master, on_select):
        super().__init__(master)
        self.on_select = on_select

    def load_deck(self, deck):
        for w in self.winfo_children():
            w.destroy()

        by_type = {}
        for card in deck:
            t = card.cardTypes[0]
            by_type.setdefault(t, []).append(card)

        for t, cards in by_type.items():
            grp = CardTypeGroup(self, t.name.title(), cards, self.on_select)
            grp.pack(fill="x", pady=5)

class OtherPrintsFrame(gui.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        
        
class ExportFrame(gui.CTkFrame):
    def __init__(self, master, get_deck):
        super().__init__(master)
        self.get_deck = get_deck

        self.grid_columnconfigure(0, weight=1)

        self.download_folder = FolderPicker(self, "Carpeta de descarga")
        self.download_folder.grid(row=0, column=0, sticky="we", padx = 5, pady=5)

        gui.CTkButton(
            self, text="Descargar cartas", command=self.download
        ).grid(row=1, column=0, padx = 5, pady=5, sticky="we")

        self.export_folder = FolderPicker(self, "Carpeta del PDF")
        self.export_folder.grid(row=2, column=0, sticky="we", padx = 5, pady=5)

        gui.CTkButton(
            self, text="Exportar PDF", command=self.export_pdf
        ).grid(row=3, column=0, padx = 5, pady=5, sticky="we")


    def download(self):
        path = self.download_folder.get() if self.download_folder.get() != "" else "cartas"
        
        os.makedirs(path, exist_ok=True)
        mtg_descargar_cartas.download_deck(self.get_deck(), path)

    def export_pdf(self):
        print("Exportar PDF (pendiente)")

class App(gui.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("1200x700")
        self.deck = []

        # Deck Input
        self.input = DeckInputFrame(self, self.on_deck_loaded)
        self.input.configure(width=300, height=250)
        self.input.place(relx=10, rely=10)

        # Card Viewer
        self.viewer = CardViewerFrame(self)
        self.viewer.configure(width=650, height=600)
        self.viewer.place(relx=320, rely=10)

        # Other Prints
        self.otherPrints = OtherPrintsFrame(self)
        self.otherPrints.configure(width=200, height=600)
        self.otherPrints.place(x=980, y=10)

        # Export Frame
        self.export = ExportFrame(self, lambda: self.deck)
        self.export.configure(width=650, height=70)
        self.export.place(x=320, y=620)


    def on_deck_loaded(self, deck):
        self.deck = deck
        self.viewer.show_card(deck[0])
        self.viewer.tree.load_deck(deck)


# PRINTS
# cada carta contiene [prints_search_uri] que es un query para buscar todas las versiones de la carta

if __name__ == "__main__":
    gui.set_appearance_mode("dark")
    gui.set_default_color_theme("green")
    
    app = App()
    app.mainloop()