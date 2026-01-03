import customtkinter as gui
import os
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

class CardShowcaseFrame(gui.CTkFrame):
    def __init__(self, master, platform:str, deck_id:str):
        super().__init__(master)
        self.grid_columnconfigure((0,1), weight=1)
        
        self.cards = mtg_descargar_cartas.load_deck(platform, deck_id, False)
        self.card_index = 0
        
        self.card_imgs = []
        for c in self.cards:
            self.card_imgs.append(c.showImage()[0])
              
        # Carga la primera imagen de la lista
        self.img = gui.CTkImage(self.card_imgs[0], size=get_mtg_dims(3))     
        self.img_label = gui.CTkLabel(self, text="", image=self.img)
        self.img_label.grid(row= 0, column = 0, padx = 10, pady = 10, sticky="we", columnspan=2)
        
        self.cardCounter = gui.CTkLabel(self, text=f"1 / {len(self.cards)}")
        self.cardCounter.grid(row= 1, column = 0, padx = 10, pady = 0, sticky="we", columnspan=2)  
        
        self.btn_prev = gui.CTkButton(self, text="<", command=self.prev_card, font=("Arial", 20, "bold"))
        self.btn_prev.grid(row= 2, column = 0, padx = 10, pady = 10, sticky="we")  
        
        self.btn_next = gui.CTkButton(self, text=">", command=self.next_card, font=("Arial", 20, "bold"))
        self.btn_next.grid(row= 2, column = 1, padx = 10, pady = 10, sticky="we")  
    
    def change_image(self):
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
        
        
class App(gui.CTk):
    def __init__(self):
        super().__init__()
        self.title("Soy homero chino")
        self.iconbitmap(ICON_PATH)
        self.geometry("600x500")
        self.grid_columnconfigure((0,1,2), weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.titleText = gui.CTkLabel(self, text="Titulo do Aplicação", font=("Arial", 20, "bold"))
        self.titleText.grid(row= 0, column = 0, padx = 0, pady = (10, 0), sticky="we", columnspan = 3)

        self.checkboxFrame1 = MyCheckboxFrame(self, values=["pito", "pete", "puta", "pato"], title="Check")
        self.checkboxFrame1.grid(row= 1, column = 0, padx = 10, pady = (10, 0), sticky="nswe")
        
        self.cardFrame = CardShowcaseFrame(self, "moxfield", "ZZUKS-3qPUCca3z4kaV4FQ")
        self.cardFrame.grid(row= 1, column = 1, padx = 10, pady = (10, 0), sticky="nswe")
        
        self.radioFrame1 = MyRadioButtonFrame(self, values=["el guevo", "Mio"], title="Radio")
        self.radioFrame1.grid(row= 1, column = 2, padx = 10, pady = (10, 0), sticky="nswe")
         
        self.btn = gui.CTkButton(self, text="Soy homero", command=self.btn_callback)
        self.btn.grid(row= 3, column = 0, padx = 20, pady = 20, sticky="we", columnspan=3)
        
    def btn_callback(self):
        print(f"Checkboxes marcadas: {self.checkboxFrame1.get()} + {self.radioFrame1.get()}")
        mtg_descargar_cartas.callback()

app = App()
app.mainloop()