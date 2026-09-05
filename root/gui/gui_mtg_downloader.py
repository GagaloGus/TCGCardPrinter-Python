import os
import sys
import threading
import io
import re
import random
import shutil
import builtins
import string
import time
import tkinter as tk
from tkinter import ttk, filedialog
import customtkinter as ctk
from PIL import Image
import requests

# Importar funciones scripts
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mtg_downloader.cardClasses import CardClass
import mtg_downloader.mtg_descargar_cartas as mtg_descargar_cartas
import card_printers.imprimir_cartas as imprimir_cartas

# --- CONFIGURACION DE LA INTERFAZ ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green") 

# Dimensiones
WINDOW_RESOLUTION = (960,500)
CARD_PREVIEW_RESOLUTION = (250/1.3, 350/1.3)
PRINT_CARD_RESOLUTION = (120, 168)

# Colores personalizados del diseño
BG_COLOR = "#1e1e1e"
PANEL_COLOR = "#2b2b2b"
ACCENT_COLOR = "#6ee2b0"
TEXT_COLOR = "#ffffff"

original_get = requests.get

def patched_get(url, **kwargs):
    headers = kwargs.pop('headers', {})
    # Camuflar peticion como si fuera un usuario desde Chrome
    if 'User-Agent' not in headers:
        headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    kwargs['headers'] = headers
    return original_get(url, **kwargs)

requests.get = patched_get

class ConsoleRedirector:
    """Redirige los prints de la consola a la caja de texto de la UI limpiando formatos raros."""
    def __init__(self, text_widget):
        self.text_widget = text_widget
        # Regex para limpiar códigos ANSI de color (ej. \033[33m)
        self.ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    def write(self, string):
        # Limpiar ANSI y evitar prints raros de barras de progreso (rich)
        clean_string = self.ansi_escape.sub('', string)
        if "━" in clean_string or "Task" in clean_string:
            return  # Ignorar caracteres de barras de carga
        
        if clean_string.strip():
            self.text_widget.configure(state="normal")
            self.text_widget.insert(ctk.END, clean_string + "\n")
            self.text_widget.see(ctk.END)
            self.text_widget.configure(state="disabled")

    def flush(self):
        pass


class MTGDownloaderGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.deckName = ""
        self.did_temp_download = False
        self._temp_download_folder = ""

        self.title("Mtg deck downloader 💎")
        self.geometry(f"{WINDOW_RESOLUTION[0]}x{WINDOW_RESOLUTION[1]}")
        self.resizable(False, False)
        self.configure(fg_color=BG_COLOR)

        # Variables de estado
        self.loaded_cards = []
        self.current_card_index = 0
        self.is_downloaded = False
        
        # Variables de UI
        self.lang_var = ctk.StringVar(value="orig")
        self.tokens_var = ctk.BooleanVar(value=True)
        self.dim_var = ctk.StringVar(value="0") # 0:Magic, 1:Ygo, 2:Normal, 3:Custom
        self.pdf_btn_text = ctk.StringVar(value="Descargar y Exportar PDF")

        self._build_ui()
        self._setup_console()
        self._patch_scripts()

    def _patch_scripts(self):
        """Parchea funciones bloqueantes de los scripts originales para que funcionen en UI."""
        # Evitar que os._exit o sys.exit cierren la UI al terminar el PDF
        os._exit = lambda x: print("Proceso finalizado internamente.")
        sys.exit = lambda x: print("Proceso finalizado internamente.")
        # Evitar que inputs en consola bloqueen el hilo (se autocompletan con enter "")
        builtins.input = lambda prompt="": ""

        import os as _os
        _os.system = lambda cmd: None if "pause" in cmd.lower() else print(f"Sistema ejecutó: {cmd}") # type: ignore
        
        # --- PARCHE PARA BUCLES INFINITOS ---
        import packages.basicFunctions as basicFunctions
        # Responde "No" por defecto a la pregunta del margen entre cartas. 
        basicFunctions.yesNo_CustomChoice = lambda *args: False

    def _setup_console(self):
        sys.stdout = ConsoleRedirector(self.console_text)
        print("Mtg deck downloader iniciado.")

    def _build_ui(self):
        # GRID PRINCIPAL: 3 Columnas, 2 Filas
        self.grid_columnconfigure(0, weight=0, minsize=150)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0, minsize=220)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0, minsize=60) 

        # ================= PANEL IZQUIERDO =================
        self.left_panel = ctk.CTkFrame(self, fg_color=PANEL_COLOR, corner_radius=10)
        self.left_panel.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.url_entry = ctk.CTkEntry(self.left_panel, placeholder_text="Url del mazo...", fg_color="#1e1e1e", border_color="#555")
        self.url_entry.pack(fill="x", padx=10, pady=(10, 5))

        # Idiomas
        self.lang_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.lang_frame.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(self.lang_frame, text="Idioma de las cartas", font=("Roboto", 12, "bold")).pack()
        ctk.CTkRadioButton(self.lang_frame, text="Original", variable=self.lang_var, value="orig").pack(anchor="w", pady=(3,5))
        ctk.CTkRadioButton(self.lang_frame, text="English", variable=self.lang_var, value="en").pack(anchor="w", pady=5)
        ctk.CTkRadioButton(self.lang_frame, text="Español", variable=self.lang_var, value="es").pack(anchor="w", pady=5)

        # Barra horizontal
        ctk.CTkFrame(master=self.left_panel,height=2,fg_color="#555555").pack(fill="x", padx=10, pady=5)

        # Tokens
        self.tokens_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.tokens_frame.pack(fill="x", padx=50)

        ctk.CTkLabel(self.tokens_frame, text="Tokens", font=("Roboto", 12, "bold")).pack()
        ctk.CTkRadioButton(self.tokens_frame, text="Si", variable=self.tokens_var, value=True, width=40).pack(side="left")
        ctk.CTkRadioButton(self.tokens_frame, text="No", variable=self.tokens_var, value=False, width=40).pack(side="right")

        self.btn_cargar = ctk.CTkButton(self.left_panel, text="Cargar mazo", fg_color=ACCENT_COLOR, text_color="black", font=("Roboto", 14, "bold"), command=self._load_deck_thread)
        self.btn_cargar.pack(side="bottom", fill="x", padx=10, pady=10)

        # ================= PANEL CENTRAL =================
        self.center_panel = ctk.CTkFrame(self, fg_color=PANEL_COLOR, corner_radius=10)
        self.center_panel.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="nsew")

        self.center_panel.grid_columnconfigure(0, weight=1)
        self.center_panel.grid_columnconfigure(1, weight=1)
        self.center_panel.grid_rowconfigure(0, weight=1)

        # Imagen Principal
        self.main_img_label = ctk.CTkLabel(self.center_panel, text="> Sin cargar <")
        self.main_img_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Arbol de cartas
        self.tree_frame = ctk.CTkFrame(self.center_panel, fg_color="transparent")
        self.tree_frame.grid(row=0, column=1, pady=(10, 0), sticky="nsew")
        
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#1e1e1e", foreground="white", fieldbackground="#1e1e1e", borderwidth=0)
        style.map('Treeview', background=[('selected', ACCENT_COLOR)], foreground=[('selected', 'black')])

        self.tree = ttk.Treeview(self.tree_frame, show="tree")
        self.tree.column("#0", width=200, stretch=tk.YES)
        self.tree.pack(expand=True, fill="both")
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Navegacion
        self.nav_frame = ctk.CTkFrame(self.center_panel, fg_color="transparent")
        self.nav_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        self.btn_prev = ctk.CTkButton(self.nav_frame, text="<", width=50, fg_color=ACCENT_COLOR, text_color="black", font=("Roboto", 18, "bold"), command=lambda: self._navigate_card(-1))
        self.btn_prev.pack(side="left", padx=10)
        
        self.lbl_counter = ctk.CTkLabel(self.nav_frame, text="0/0", font=("Roboto", 18, "bold"))
        self.lbl_counter.pack(side="left", padx=15)
        
        self.btn_next = ctk.CTkButton(self.nav_frame, text=">", width=50, fg_color=ACCENT_COLOR, text_color="black", font=("Roboto", 18, "bold"), command=lambda: self._navigate_card(1))
        self.btn_next.pack(side="left", padx=10)

        # ================= PANEL DERECHO (Impresiones) =================
        self.right_panel = ctk.CTkFrame(self, fg_color=PANEL_COLOR, corner_radius=10)
        self.right_panel.grid(row=0, column=2, padx=(0, 10), pady=10, sticky="nsew")

        ctk.CTkLabel(self.right_panel, text="Cambiar Impresión", font=("Roboto", 14, "bold")).pack(pady=(10, 5))
        
        self.btn_select_print = ctk.CTkButton(self.right_panel, text="Seleccionar", fg_color=ACCENT_COLOR, text_color="black", font=("Roboto", 12, "bold"))
        self.btn_select_print.pack(side="bottom", padx=10, pady=10)

        self.scroll_prints = ctk.CTkScrollableFrame(self.right_panel, fg_color="#1e1e1e")
        self.scroll_prints.pack(side="top", expand=True, fill="both", padx=10, pady=0)


        # ================= PANEL INFERIOR =================
        self.bottom_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_panel.grid(row=1, column=0, columnspan=3, padx=10, pady=(0, 5), sticky="nsew")
        
        # Dividir en 5 partes: Consola ocupa 3, Exportar ocupa 2
        self.bottom_panel.grid_columnconfigure(0, weight=3)
        self.bottom_panel.grid_columnconfigure(1, weight=1)

        # Consola
        console_container = ctk.CTkFrame(self.bottom_panel, fg_color="transparent")
        console_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ctk.CTkLabel(console_container, text="Consola", font=("Roboto", 12, "bold")).pack(anchor="w")
        self.console_text = ctk.CTkTextbox(console_container, fg_color="#000000", text_color="#00ff00", font=("Consolas", 10), height=80)
        self.console_text.pack(expand=True, fill="both")
        self.console_text.configure(state="disabled")

        # Exportacion
        export_container = ctk.CTkFrame(self.bottom_panel, fg_color=PANEL_COLOR, corner_radius=10)
        export_container.grid(row=0, column=1, sticky="nsew")
        export_container.grid_columnconfigure(0, weight=1)
        export_container.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(export_container, text="Exportar", font=("Roboto", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(2, 2))

        width_btn_exportar = 196
        width_btn_carpeta = 26
        
        # Sub-contenedor Izquierdo (Descarga)
        left_path = ctk.CTkFrame(export_container, fg_color="transparent")
        left_path.grid(row=1, column=0, pady=(0, 2))
        
        self.entry_descarga = ctk.CTkEntry(left_path, placeholder_text="Carpeta de descarga...", width=width_btn_exportar-width_btn_carpeta, height=width_btn_carpeta)
        self.entry_descarga.pack(side="left", padx=2)
        ctk.CTkButton(left_path, text="📁", width=width_btn_carpeta, height=width_btn_carpeta, fg_color="transparent", border_width=1, command=lambda: self._choose_dir(self.entry_descarga)).pack(side="left")

        # Boton Izquierdo 
        self.btn_descargar = ctk.CTkButton(export_container, text="Descargar cartas", fg_color=ACCENT_COLOR, text_color="black", font=("Roboto", 12, "bold"), width=width_btn_exportar, height=26, command=self._download_thread)
        self.btn_descargar.grid(row=2, column=0, pady=5)

        # Sub-contenedor Derecho (PDF)
        right_path = ctk.CTkFrame(export_container, fg_color="transparent")
        right_path.grid(row=1, column=1, pady=(0, 2))
        
        self.entry_pdf = ctk.CTkEntry(right_path, placeholder_text="Carpeta del PDF...", width=width_btn_exportar-width_btn_carpeta, height=width_btn_carpeta)
        self.entry_pdf.pack(side="left", padx=2)
        ctk.CTkButton(right_path, text="📁", width=width_btn_carpeta, height=width_btn_carpeta, fg_color="transparent", border_width=1, command=lambda: self._choose_dir(self.entry_pdf)).pack(side="left")

        # Boton Derecho 
        self.btn_exportar = ctk.CTkButton(export_container, textvariable=self.pdf_btn_text, fg_color=ACCENT_COLOR, text_color="black", font=("Roboto", 12, "bold"), width=width_btn_exportar, height=26, command=self._export_pdf_thread)
        self.btn_exportar.grid(row=2, column=1, pady=5)

        self.lockable_widgets = [
            self.url_entry, self.btn_cargar, self.btn_descargar, self.btn_exportar, 
            self.btn_select_print, self.entry_descarga, self.entry_pdf
        ]
    def _set_ui_state(self, state):
        """Bloquea o desbloquea todo EXCEPTO las flechas de navegación."""
        for w in self.lockable_widgets:
            try:
                w.configure(state=state)
            except:
                pass

    # --- HILOS (THREADING) ---
    def _load_deck_thread(self):
        url = self.url_entry.get().strip()
        if not url:
            print("Error: Pon una URL primero.")
            return
        self._set_ui_state("disabled")
        threading.Thread(target=self._process_load, args=(url,), daemon=True).start()

    def _process_load(self, url):
        try:
            print("Analizando mazo...")
            platform, deck_id = mtg_descargar_cartas.get_platform_and_id(url)
            self.deckName = mtg_descargar_cartas.get_json(platform, deck_id)["name"]
            self.loaded_cards = mtg_descargar_cartas.load_deck(platform, deck_id, self.tokens_var.get(), self.lang_var.get())
            self.is_downloaded = False
            self.pdf_btn_text.set("Descargar y Exportar PDF")
            
            # Actualizar GUI de forma segura
            self.after(0, self._populate_treeview)
            print("Mazo cargado correctamente.")
        except Exception as e:
            print(f"Error cargando: {e}")
        finally:
            self.after(0, lambda: self._set_ui_state("normal"))

    def _download_thread(self):
        if not self.loaded_cards:
            print("No hay mazo cargado.")
            return
        self._set_ui_state("disabled")
        threading.Thread(target=self._process_download, daemon=True).start()

    def _process_download(self):
        try:
            print("Iniciando descarga de imágenes...")
            # Setear carpeta destino en el script original
            if not self.did_temp_download:
                folder = self.entry_descarga.get().strip()
                if not folder:
                    base_folder = os.path.join("cartas", self.deckName)
                    folder = base_folder
                    contador = 1
                
                    while os.path.exists(folder):
                        folder = f"{base_folder}_{contador}"
                        contador += 1
                
                    self.after(0, lambda: self.entry_descarga.insert(0, folder))
            else:
                folder = self._temp_download_folder
                
            os.makedirs(folder, exist_ok=True)
            mtg_descargar_cartas.OUTPUT_DIR = folder
            
            mtg_descargar_cartas.download_deck(self.loaded_cards)
            
            self.is_downloaded = True
            self.after(0, lambda: self.pdf_btn_text.set("Exportar PDF"))
            print(f"Descarga finalizada en: {folder}")
        except Exception as e:
            print(f"Error descargando: {e}")
        finally:
            self.after(0, lambda: self._set_ui_state("normal"))

    def _choose_dir(self, entry_widget):
        folder = filedialog.askdirectory()
        if folder:
            entry_widget.delete(0, ctk.END)
            entry_widget.insert(0, folder)


    def _export_pdf_thread(self):
        if not self.loaded_cards:
            print("No hay mazo cargado.")
            return
            
        self._set_ui_state("disabled")
        
        def run_export():           
            self.did_temp_download = False

            in_folder = self.entry_descarga.get().strip()
            out_folder = self.entry_pdf.get().strip()

            if not self.is_downloaded:
                self.did_temp_download = True
                # Nombre temporal con caracteres aleatorios
                in_folder = "cartas_"+''.join(random.choices(string.ascii_lowercase + string.digits, k=20))
                self._temp_download_folder = in_folder
                self._process_download()
            
            if not out_folder:
                out_folder = f"pdf_{self.deckName}"
                self.after(0, lambda: self.entry_pdf.insert(0, out_folder))
                
            imprimir_cartas.INPUT_DIR = in_folder
            imprimir_cartas.OUTPUT_DIR = out_folder
            
            print("Generando PDF (Esto puede tardar)...")
            try:
                # El "0" indica a imprimir_cartas.py que use dimensiones de Magic
                imprimir_cartas.main(in_folder, "0")
                print("PDF Generado exitosamente.")
            except Exception as e:
                if "Proceso finalizado" not in str(e):
                    print(f"Error exportando PDF: {e}")
            finally:
                if self.did_temp_download:
                    for _ in range(5):
                        try:
                            if os.path.exists(in_folder):
                                shutil.rmtree(in_folder)
                                print(f"Carpeta temporal de imágenes '{in_folder}' eliminada.")
                                break
                        except Exception:
                            time.sleep(0.5)  # Esperar medio segundo y reintentar si sigue ocupado
                
                self.after(0, lambda: self._set_ui_state("normal"))

        threading.Thread(target=run_export, daemon=True).start()

    # --- LOGICA DE ARBOL Y VISUALIZACION ---
    def _populate_treeview(self):
        # Limpiar
        for i in self.tree.get_children():
            self.tree.delete(i)
            
        # Agrupar por tipo (Artefacto, Criatura...)
        grouped = {}
        for idx, card in enumerate(self.loaded_cards):
            tipo = card.cardTypes[0].__str__(self.lang_var.get())
            if tipo not in grouped:
                tipo = card.cardTypes[0].__str__(self.lang_var.get())
            if tipo not in grouped:
                grouped[tipo] = []
            grouped[tipo].append((idx, card))

        # Insertar nodos
        for tipo, cartas in grouped.items():
            total_qty = sum([c.quantity for _, c in cartas])
            padre = self.tree.insert("", "end", text=f" {tipo} - {total_qty}", open=True)
            
            for idx, card in cartas:
                self.tree.insert(padre, "end", text=f" {card.quantity} - {card.cardMainName}", iid=f"card_{idx}")

        self.lbl_counter.configure(text=f"1/{len(self.loaded_cards)}")
        self._show_card_image(0)

    def _on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected: return
        item_id = selected[0]
        
        # Si se hace clic en la categoria principal (padre), se ignora
        if not item_id.startswith("card_"):
            self.tree.selection_remove(item_id)
            return
            
        # Extraer el indice real del iid de la carta
        idx = int(item_id.split("_")[1])
        self.current_card_index = idx
        self.lbl_counter.configure(text=f"{idx+1}/{len(self.loaded_cards)}")
        self._show_card_image(idx)


    def _navigate_card(self, direction):
        if not self.loaded_cards: return

        # Da la vuelta a la lista
        self.current_card_index += direction
        if self.current_card_index < 0:
            self.current_card_index = len(self.loaded_cards) - 1
        elif self.current_card_index >= len(self.loaded_cards):
            self.current_card_index = 0
            
        self.lbl_counter.configure(text=f"{self.current_card_index+1}/{len(self.loaded_cards)}")
        self._show_card_image(self.current_card_index)

    def _show_card_image(self, index):
        """Descarga a la RAM la imagen principal y la muestra. Lanza hilo para buscar impresiones alternativas."""
        card = self.loaded_cards[index]
        url = card.img_urls[0]
        
        # Eliminar el texto anterior si existe
        if hasattr(self, "lbl_card_name"):
            self.lbl_card_name.destroy()

        self.lbl_card_name = ctk.CTkLabel(self.center_panel, text=card.cardMainName, font=("Roboto", 12, "bold"), text_color=ACCENT_COLOR)
        self.lbl_card_name.grid(row=1, column=0, columnspan=2)
        self.nav_frame.grid(row=2, column=0, columnspan=2, pady=(0, 10))

        # Crear un ID unico para la carta actual. Si se cambia rapido de carta, las descargas viejas se abortan
        if not hasattr(self, "current_fetch_id"):
            self.current_fetch_id = 0
        self.current_fetch_id += 1
        current_id = self.current_fetch_id

        def fetch_image():
            try:
                response = requests.get(url)
                img = Image.open(io.BytesIO(response.content))
                img.thumbnail(CARD_PREVIEW_RESOLUTION, Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                # Verifica que seguimos en la misma carta antes de pintarla
                if self.current_fetch_id == current_id:
                    self.after(0, lambda: self.main_img_label.configure(image=ctk_img, text=""))
            except Exception as e:
                print(f"No se pudo cargar imagen: {e}")

        for widget in self.scroll_prints.winfo_children():
            widget.destroy()
        
        threading.Thread(target=fetch_image, daemon=True).start()
        threading.Thread(target=self._fetch_alternative_prints, args=(card, current_id), daemon=True).start()


    def _fetch_alternative_prints(self, card, fetch_id):
        """Busca variaciones en Scryfall usando el oracle_id y las carga controladamente."""
        if not card.oracle_id: return
            
        api_url = f"https://api.scryfall.com/cards/search?order=released&q=oracleid:{card.oracle_id}&unique=prints"
        try:
            resp = requests.get(api_url).json()
            if "data" not in resp or self.current_fetch_id != fetch_id: return
            
            from concurrent.futures import ThreadPoolExecutor

            def process_alt_card(alt_card):
                if self.current_fetch_id != fetch_id: return # Abortar si ya cambiamos de carta
                
                img_url = ""
                if "image_uris" in alt_card:
                    img_url = alt_card["image_uris"].get("border_crop")
                elif "card_faces" in alt_card and "image_uris" in alt_card["card_faces"][0]:
                    img_url = alt_card["card_faces"][0]["image_uris"].get("border_crop")
                
                if not img_url: return
                set_code = alt_card.get("set", "").upper()
                collector_num = alt_card.get("collector_number", "")
                
                self._load_thumbnail(img_url, set_code, collector_num, fetch_id)

            # ThreadPool de 4 trabajadores para evitar congelamientos por exceso de peticiones
            with ThreadPoolExecutor(max_workers=4) as executor:
                for alt_card in resp["data"]:
                    if self.current_fetch_id != fetch_id: break
                    executor.submit(process_alt_card, alt_card)
                    
        except Exception as e:
            pass


    def _load_thumbnail(self, img_url, set_code, col_num, fetch_id):
        if self.current_fetch_id != fetch_id: return
        try:
            response = requests.get(img_url)
            img = Image.open(io.BytesIO(response.content))
            img.thumbnail(PRINT_CARD_RESOLUTION, Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            
            # Ultima comprobacion antes de mandarlo a la interfaz
            if self.current_fetch_id == fetch_id:
                self.after(0, lambda: self._add_thumbnail_to_ui(ctk_img, set_code, col_num, img_url))
        except:
            pass

    def _add_thumbnail_to_ui(self, ctk_img, set_code, col_num, full_url):
        frame = ctk.CTkFrame(self.scroll_prints, fg_color="transparent")
        frame.pack(pady=5)
        
        lbl_img = ctk.CTkLabel(frame, image=ctk_img, text="")
        lbl_img.pack()
        
        lbl_text = ctk.CTkLabel(frame, text=f"{set_code} ({col_num})", font=("Roboto", 10))
        lbl_text.pack()
        
        # Al hacer click, cambia la URL de la carta y actualiza el panel central en alta resolucion
        def select_this():
            if self.loaded_cards:
                self.loaded_cards[self.current_card_index].img_urls[0] = full_url
                print(f"Arte cambiado a: {set_code} {col_num}")
                
                # Obtener y redimensionar la imagen para el visor principal en 2º plano
                def update_main_preview():
                    try:
                        response = requests.get(full_url)
                        img = Image.open(io.BytesIO(response.content))
                        img.thumbnail(CARD_PREVIEW_RESOLUTION, Image.Resampling.LANCZOS)
                        big_ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                        self.after(0, lambda: self.main_img_label.configure(image=big_ctk_img))
                    except Exception as e:
                        print(f"Error cargando arte alternativo: {e}")
                        
                threading.Thread(target=update_main_preview, daemon=True).start()
                
        lbl_img.bind("<Button-1>", lambda e: select_this())


if __name__ == "__main__":
    app = MTGDownloaderGUI()
    app.mainloop()