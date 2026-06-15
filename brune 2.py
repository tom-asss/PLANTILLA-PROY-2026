import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import webbrowser
import pyttsx3
import threading
import unicodedata
import whisper as _whisper
import numpy as _np
import sounddevice as _sd
import json
import datetime
import random
import os
from google import genai

# ==========================================
# CARPETA DE DATOS — siempre con permisos
# ==========================================
import pathlib

CARPETA_DATOS = pathlib.Path.home() / "AppData" / "Local" / "BRUNE"
CARPETA_DATOS.mkdir(parents=True, exist_ok=True)

# ==========================================
# CONFIGURACIÓN GEMINI
# Pega tu API key de aistudio.google.com aquí:
# ==========================================
GEMINI_API_KEY = "PEGA_TU_API_KEY_AQUI"
cliente_gemini = genai.Client(api_key=GEMINI_API_KEY)
MODELO_GEMINI = "gemini-2.5-flash"

# ==========================================
# FLAGS GLOBALES
# ==========================================
escuchando_activo = False
ramo_activo_sesion = None      # ramo que está abierto actualmente
entorno_abierto_sesion = False # si ya se abrieron spotify y links de estudio

# ==========================================
# 1. FUNCIONES DE VOZ DE BRUNE
# ==========================================
def decir_texto(texto):
    try:
        motor_voz = pyttsx3.init()
        motor_voz.setProperty('rate', 150)
        motor_voz.say(texto)
        motor_voz.runAndWait()
    except Exception as e:
        print(f"[BRUNE] Error de voz: {e}")

def hablar_brune(texto):
    hilo_voz = threading.Thread(target=decir_texto, args=(texto,), daemon=True)
    hilo_voz.start()

# ==========================================
# UTILIDADES THREAD-SAFE
# ==========================================

def actualizar_label(texto):
    """Actualiza el area de estado desde cualquier hilo de forma segura."""
    def _actualizar():
        label_ia.config(state="normal")
        label_ia.delete("1.0", tk.END)
        label_ia.insert(tk.END, "BRUNE: " + texto)
        label_ia.config(state="disabled")
        label_ia.see(tk.END)
    ventana.after(0, _actualizar)

def set_boton_microfono(habilitado):
    estado = "normal" if habilitado else "disabled"
    ventana.after(0, lambda: btn_mic.config(state=estado))

def normalizar(texto):
    return "".join(
        c for c in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(c) != "Mn"
    )

# Whisper se carga en segundo plano para no congelar la interfaz
# REQUISITO PREVIO: ejecutar en terminal antes de iniciar BRUNE:
#   python -c "import whisper; whisper.load_model('base')"
_modelo_whisper = None
_whisper_listo = threading.Event()

def _cargar_whisper():
    global _modelo_whisper
    print("[BRUNE] Cargando modelo Whisper base...")
    try:
        _modelo_whisper = _whisper.load_model("base")
        print("[BRUNE] Whisper listo - ya puedes hablar!")
    except FileNotFoundError:
        _modelo_whisper = None
        print("[BRUNE] Modelo Whisper no encontrado.")
        print('[BRUNE] Ejecuta primero: python -c "import whisper; whisper.load_model(\"base\")"')
    except Exception as _e:
        _modelo_whisper = None
        print(f"[BRUNE] Error cargando Whisper: {_e}")
    finally:
        _whisper_listo.set()

threading.Thread(target=_cargar_whisper, daemon=True).start()

def microfono_disponible():
    try:
        dispositivos = _sd.query_devices()
        return any(d["max_input_channels"] > 0 for d in dispositivos)
    except Exception:
        return False

# ==========================================
# 2. LÓGICA PARA ABRIR MATERIAL
# ==========================================

# Links por ramo: Drive (material propio) + Almacén Camello (material externo)
def obtener_material_ramos():
    """Construye el diccionario de ramos con los links fijos de Drive."""
    return {
        "Álgebra y geometría": {
            "drive":   "https://drive.google.com/drive/folders/1iRYBqLJ0pKhOKUNHOyjvYBYhXqFPBORi?usp=drive_link",
            "camello": "https://onedrive.live.com/?redeem=aHR0cHM6Ly8xZHJ2Lm1zL2YvYy9EODlGNTIzNzVERkExRTg0L0VsQXRVRUpSUEQ1RXRfVWRZQ2xsTTJrQnhHb0c4V1l3bkgxMC0wQmZuRWczbnc&id=D89F52375DFA1E84%21s6d8e8a2b983240cabdbdbf0abcfb028e&cid=D89F52375DFA1E84&sb=name&sd=1",
        },
        "Introducción a la física": {
            "drive":   "https://drive.google.com/drive/folders/1igTlAcTwjtgWZA693qS_4Q2pXesMhsSO?usp=drive_link",
            "camello": "https://onedrive.live.com/?redeem=aHR0cHM6Ly8xZHJ2Lm1zL2YvYy9EODlGNTIzNzVERkExRTg0L0VsQXRVRUpSUEQ1RXRfVWRZQ2xsTTJrQnhHb0c4V1l3bkgxMC0wQmZuRWczbnc&id=D89F52375DFA1E84%21s7515b26d4e8043198ee882235da16afb&cid=D89F52375DFA1E84&sb=name&sd=1",
        },
        "Introducción al cálculo": {
            "drive":   "https://drive.google.com/drive/folders/1h8uoFqdqXByQZeiqBhPPlZxP6o3lw8SF?usp=drive_link",
            "camello": "https://onedrive.live.com/?redeem=aHR0cHM6Ly8xZHJ2Lm1zL2YvYy9EODlGNTIzNzVERkExRTg0L0VsQXRVRUpSUEQ1RXRfVWRZQ2xsTTJrQnhHb0c4V1l3bkgxMC0wQmZuRWczbnc&id=D89F52375DFA1E84%21sf365a72a8fa3456383e26862b61b3265&cid=D89F52375DFA1E84&sb=name&sd=1",
        },
        "Proyecto inicial": {
            "drive":   "https://drive.google.com/drive/folders/10EubrON_mBkQBM9ROq-MeEq0_9445paM?usp=drive_link",
            "camello": None,
        },
    }

def abrir_material(ramo_nombre):
    global ramo_activo_sesion, entorno_abierto_sesion

    if ramo_nombre == "Selecciona el ramo" or not ramo_nombre.strip():
        actualizar_label("Primero selecciona un ramo del menú.")
        hablar_brune("Por favor selecciona un ramo primero.")
        return

    ramo = obtener_material_ramos().get(ramo_nombre)

    if ramo:
        mismo_ramo = (ramo_nombre == ramo_activo_sesion)

        if mismo_ramo:
            # Ya está abierto este ramo — no abrir nada
            actualizar_label(f"El material de {ramo_nombre} ya está abierto.")
            hablar_brune(f"El material de {ramo_nombre} ya está abierto.")
            return

        # Ramo nuevo o diferente — abrir Drive y Camello siempre
        mensaje = f"Abriendo material de {ramo_nombre}"
        actualizar_label(mensaje)
        hablar_brune(mensaje)
        webbrowser.open(ramo["drive"])
        if ramo["camello"]:
            webbrowser.open(ramo["camello"])

        # Spotify y links de estudio solo si no están abiertos en esta sesión
        if not entorno_abierto_sesion:
            hablar_brune("Preparando tu entorno de estudio. Aquí tienes tu playlist.")
            cfg = cargar_config()
            webbrowser.open(cfg.get("playlist_spotify", CONFIG_DEFAULT["playlist_spotify"]))
            for link in cfg.get("links_estudio", CONFIG_DEFAULT["links_estudio"]):
                if link.get("url"):
                    webbrowser.open(link["url"])
            entorno_abierto_sesion = True
        else:
            hablar_brune(f"Cambiando a {ramo_nombre}.")

        ramo_activo_sesion = ramo_nombre

    else:
        msg = f"No tengo información de {ramo_nombre}."
        actualizar_label(msg)
        hablar_brune(msg)

# ==========================================
# 3. CALCULADORA DE NOTAS
# ==========================================
def abrir_calculadora_notas():
    ventana_calc = tk.Toplevel()
    ventana_calc.title("Calculadora de Notas — BRUNE")
    ventana_calc.resizable(False, False)
    ventana_calc.config(bg=C_FONDO)
    ventana_calc.update_idletasks()
    _cx = (ventana_calc.winfo_screenwidth() // 2) - 235
    _cy = (ventana_calc.winfo_screenheight() // 2) - 260
    ventana_calc.geometry(f"470x520+{_cx}+{_cy}")
    # Header
    fh = tk.Frame(ventana_calc, bg=C_AZUL_OSC, height=55)
    fh.pack(fill="x"); fh.pack_propagate(False)
    tk.Label(fh, text="🧮  Calculadora de Notas", bg=C_AZUL_OSC, fg="white",
             font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=18, pady=10)

    ponderaciones_ramos = {
        "Introducción al cálculo (MAT070)": {"Certamen 1": 0.25, "Certamen 2": 0.25, "Certamen 3": 0.25, "Controles": 0.25},
        "Álgebra y geometría (MAT060)": {"Controles": 1.0},
        "Introducción a la física (FIS100)": {"Certamen 1": 0.20, "Certamen 2": 0.20, "Certamen 3": 0.25, "Controles": 0.20, "Tareas": 0.10, "Preclases": 0.05}
    }

    entradas = {}

    tk.Label(ventana_calc, text="Selecciona tu ramo:", bg=C_FONDO, fg=C_TEXTO, font=("Segoe UI", 11, "bold")).pack(pady=(15, 5))

    variable_ramo_calc = tk.StringVar()
    combo_ramos = ttk.Combobox(ventana_calc, textvariable=variable_ramo_calc,
                                values=list(ponderaciones_ramos.keys()), state="readonly", width=30)
    combo_ramos.pack(pady=5)
    combo_ramos.current(0)

    frame_inputs = tk.Frame(ventana_calc, bg=C_FONDO)
    frame_inputs.pack(pady=10)

    lbl_resultado = tk.Label(ventana_calc, text="Nota requerida: --", bg=C_FONDO,
                              fg="#1A7A4A", font=("Segoe UI", 12, "bold"))

    def abrir_ventana_controles(entry_destino, cantidad, borrar_peores, es_algebra=False):
        win_ctrl = tk.Toplevel(ventana_calc)
        win_ctrl.title("Ingreso Detallado")
        win_ctrl.geometry("250x450")
        win_ctrl.config(bg=C_FONDO)

        if es_algebra:
            texto_info = f"Ingresa tus notas.\nMeta: Sumar 330 pts (Mejores {cantidad - borrar_peores})."
        else:
            texto_info = (f"Ingresa tus {cantidad} notas.\nSe borrarán las {borrar_peores} peores."
                          if borrar_peores > 0 else f"Ingresa tus {cantidad} notas.")

        tk.Label(win_ctrl, text=texto_info, bg=C_FONDO, fg=C_TEXTO, font=("Segoe UI", 9)).pack(pady=10)

        entries_ctrl = []
        for i in range(cantidad):
            f_ctrl = tk.Frame(win_ctrl, bg=C_FONDO)
            f_ctrl.pack(pady=2)
            tk.Label(f_ctrl, text=f"Nota {i+1}:", bg=C_FONDO, fg=C_TEXTO, font=("Segoe UI",10), width=8).pack(side=tk.LEFT)
            e = tk.Entry(f_ctrl, width=6, justify="center")
            e.pack(side=tk.LEFT)
            entries_ctrl.append(e)

        def guardar_promedio():
            notas_ingresadas = []
            for e in entries_ctrl:
                val = e.get()
                if val.strip() != "":
                    try:
                        notas_ingresadas.append(float(val))
                    except ValueError:
                        pass

            if len(notas_ingresadas) == 0:
                win_ctrl.destroy()
                return

            entry_destino.notas_crudas = notas_ingresadas
            notas_ordenadas = sorted(notas_ingresadas, reverse=True)
            notas_validas = notas_ordenadas[:cantidad - borrar_peores]
            resultado = sum(notas_validas) if es_algebra else sum(notas_validas) / len(notas_validas)
            entry_destino.delete(0, tk.END)
            entry_destino.insert(0, f"{resultado:.1f}")
            win_ctrl.destroy()

        tk.Button(win_ctrl, text="Guardar", command=guardar_promedio, bg=C_AZUL_MED, fg="white",
                   relief="flat", font=("Segoe UI",10,"bold"), padx=14, pady=7, cursor="hand2").pack(pady=15)

    def actualizar_campos(event=None):
        for widget in frame_inputs.winfo_children():
            widget.destroy()
        entradas.clear()

        ramo_seleccionado = variable_ramo_calc.get()
        pesos_actuales = ponderaciones_ramos[ramo_seleccionado]

        for eval_nombre, peso in pesos_actuales.items():
            frame_fila = tk.Frame(frame_inputs, bg=C_FONDO)
            frame_fila.pack(pady=5, fill="x")

            texto_label = ("Puntos (Meta 330):" if "Álgebra" in ramo_seleccionado and "Controles" in eval_nombre
                           else f"{eval_nombre} ({int(peso*100)}%):")

            tk.Label(frame_fila, text=texto_label, bg=C_FONDO, fg=C_TEXTO, font=("Segoe UI",10), width=22, anchor="w").pack(side=tk.LEFT)
            entry = tk.Entry(frame_fila, width=8, justify="center")
            entry.pack(side=tk.LEFT, padx=10)
            entradas[eval_nombre] = entry

            if "Controles" in eval_nombre:
                if "Álgebra" in ramo_seleccionado:
                    tk.Button(frame_fila, text="⚙️ Ingresar", font=("Arial", 8),
                              command=lambda e=entry: abrir_ventana_controles(e, 8, 2, True)).pack(side=tk.LEFT)
                elif "Cálculo" in ramo_seleccionado or "cálculo" in ramo_seleccionado:
                    tk.Button(frame_fila, text="⚙️ Ingresar", font=("Arial", 8),
                              command=lambda e=entry: abrir_ventana_controles(e, 8, 2, False)).pack(side=tk.LEFT)
                elif "Física" in ramo_seleccionado or "física" in ramo_seleccionado:
                    tk.Button(frame_fila, text="⚙️ Ingresar", font=("Arial", 8),
                              command=lambda e=entry: abrir_ventana_controles(e, 6, 0)).pack(side=tk.LEFT)
            elif "Tareas" in eval_nombre:
                tk.Button(frame_fila, text="⚙️ Ingresar", font=("Arial", 8),
                          command=lambda e=entry: abrir_ventana_controles(e, 5, 0)).pack(side=tk.LEFT)

        lbl_resultado.config(text="Nota requerida: --", fg="#1A7A4A")

    combo_ramos.bind("<<ComboboxSelected>>", actualizar_campos)

    def calcular():
        ramo_seleccionado = variable_ramo_calc.get()

        if "Álgebra" in ramo_seleccionado:
            try:
                valor = entradas["Controles"].get()
                if valor.strip() == "":
                    return
                puntos = float(valor)
                notas = getattr(entradas["Controles"], "notas_crudas", [])

                if len(notas) > 0:
                    rendidos = len(notas)
                    faltantes = 8 - rendidos
                    escenario_ideal = sorted(notas + [100.0] * faltantes, reverse=True)
                    max_posible = sum(escenario_ideal[:6])

                    if puntos >= 330:
                        lbl_resultado.config(text=f"¡Felicidades! Lograste {puntos:.0f} pts. Nota final: {puntos/6:.1f}", fg="#1A7A4A")
                    elif max_posible < 330:
                        lbl_resultado.config(text=f"Está imposible remontar...\nSacando 100 en todo tendrías {max_posible:.0f} pts.", fg="#FF4C4C")
                    elif rendidos == 8 and puntos < 330:
                        lbl_resultado.config(text=f"No lograste los 330 pts (Faltaron {330-puntos:.0f}). Suerte en el otro semestre...", fg="#FF4C4C")
                    else:
                        lbl_resultado.config(text=f"Llevas {puntos:.0f} pts. Te faltan {330-puntos:.0f} para aprobar", fg="#FFD700")
                else:
                    if puntos >= 330:
                        lbl_resultado.config(text=f"¡Felicidades! Lograste pasar con {puntos:.0f} pts", fg="#1A7A4A")
                    else:
                        lbl_resultado.config(text=f"Llevas {puntos:.0f} pts. Te faltan {330-puntos:.0f} para aprobar 🔥", fg="#FFD700")
            except ValueError:
                messagebox.showerror("Error", "Ingresa solo números.")
            return

        pesos_actuales = ponderaciones_ramos[ramo_seleccionado]
        nota_actual = 0.0
        peso_evaluado = 0.0

        try:
            for eval_nombre, entry in entradas.items():
                valor = entry.get()
                if valor.strip() != "":
                    nota = float(valor)
                    nota_actual += nota * pesos_actuales[eval_nombre]
                    peso_evaluado += pesos_actuales[eval_nombre]

            peso_restante = 1.0 - peso_evaluado

            if peso_restante <= 0:
                color = "#1A7A4A" if nota_actual >= 55 else "#FF4C4C"
                texto = (f"¡Felicidades! Pasaste con un {nota_actual:.1f} 🎓🚀" if nota_actual >= 55
                         else f"Promedio final: {nota_actual:.1f}. ¡Suerte en el otro semestre!")
                lbl_resultado.config(text=texto, fg=color)
            else:
                nota_faltante = (55 - nota_actual) / peso_restante
                if nota_faltante > 100:
                    lbl_resultado.config(text=f"¡Está imposible remontar!\nNecesitarías un {nota_faltante:.1f} 💀", fg="#FF4C4C")
                elif nota_faltante <= 0:
                    lbl_resultado.config(text=f"¡Ya aprobaste! Tienes un {nota_actual:.1f} asegurado :)", fg="#1A7A4A")
                else:
                    lbl_resultado.config(text=f"Necesitas un {nota_faltante:.1f} en lo que queda. ¡Dale!", fg="#FFD700")
        except ValueError:
            messagebox.showerror("Error", "Ingresa solo números. Usa punto para los decimales.")

    actualizar_campos()
    frame_btns_calc = tk.Frame(ventana_calc, bg=C_FONDO)
    frame_btns_calc.pack(pady=10)
    tk.Button(frame_btns_calc, text="Calcular →", command=calcular,
              bg=C_AZUL_MED, fg="white", font=("Segoe UI", 11, "bold"),
              relief="flat", padx=18, pady=9, cursor="hand2").pack(side=tk.LEFT, padx=8)
    tk.Button(frame_btns_calc, text="📚 Mis ramos",
              command=abrir_calculadora_custom,
              bg=C_AZUL_OSC, fg="white", font=("Segoe UI", 11),
              relief="flat", padx=14, pady=9, cursor="hand2").pack(side=tk.LEFT, padx=8)
    lbl_resultado.pack(pady=10)


# ==========================================
# 3B. CALCULADORA — RAMOS PERSONALIZADOS
# ==========================================
ARCHIVO_RAMOS = str(CARPETA_DATOS / "brune_ramos.json")

def cargar_ramos_custom():
    try:
        with open(ARCHIVO_RAMOS, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def guardar_ramos_custom(ramos):
    with open(ARCHIVO_RAMOS, "w", encoding="utf-8") as f:
        json.dump(ramos, f, ensure_ascii=False, indent=2)

def abrir_crear_ramo(callback_actualizar, ramo_editar=None):
    """Ventana para crear o editar un ramo personalizado."""
    es_edicion = ramo_editar is not None

    ventana_cr = tk.Toplevel()
    ventana_cr.title("Editar ramo" if es_edicion else "Crear ramo personalizado")
    ventana_cr.config(bg=C_FONDO)
    ventana_cr.resizable(False, False)
    ventana_cr.update_idletasks()
    _cx = (ventana_cr.winfo_screenwidth() // 2) - 250
    _cy = (ventana_cr.winfo_screenheight() // 2) - 320
    ventana_cr.geometry(f"500x640+{_cx}+{_cy}")

    # Header
    fh = tk.Frame(ventana_cr, bg=C_AZUL_OSC, height=55)
    fh.pack(fill="x"); fh.pack_propagate(False)
    tk.Label(fh, text="✏️  " + ("Editar ramo" if es_edicion else "Crear ramo personalizado"),
             bg=C_AZUL_OSC, fg="white", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=18, pady=10)

    # Nombre y código
    frame_info = tk.Frame(ventana_cr, bg=C_FONDO)
    frame_info.pack(fill="x", padx=25, pady=(15, 5))

    tk.Label(frame_info, text="Nombre del ramo:", bg=C_FONDO, fg=C_TEXTO,
             font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=3)
    entry_nombre = tk.Entry(frame_info, font=("Segoe UI", 10), width=28,
                             bg=C_CARD, relief="flat",
                             highlightbackground=C_BORDE, highlightthickness=1)
    entry_nombre.grid(row=0, column=1, padx=10, pady=3, ipady=5)

    tk.Label(frame_info, text="Código (ej: MAT070):", bg=C_FONDO, fg=C_TEXTO,
             font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", pady=3)
    entry_codigo = tk.Entry(frame_info, font=("Segoe UI", 10), width=12,
                             bg=C_CARD, relief="flat",
                             highlightbackground=C_BORDE, highlightthickness=1)
    entry_codigo.grid(row=1, column=1, padx=10, pady=3, ipady=5, sticky="w")

    tk.Label(frame_info, text="Nota meta (ej: 55):", bg=C_FONDO, fg=C_TEXTO,
             font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w", pady=3)
    entry_meta = tk.Entry(frame_info, font=("Segoe UI", 10), width=8,
                           bg=C_CARD, relief="flat",
                           highlightbackground=C_BORDE, highlightthickness=1)
    entry_meta.grid(row=2, column=1, padx=10, pady=3, ipady=5, sticky="w")
    entry_meta.insert(0, "55")

    # Si es edición, llenar datos
    if es_edicion:
        entry_nombre.insert(0, ramo_editar.get("nombre", ""))
        entry_codigo.insert(0, ramo_editar.get("codigo", ""))
        entry_meta.delete(0, tk.END)
        entry_meta.insert(0, str(ramo_editar.get("meta", 55)))

    tk.Frame(ventana_cr, bg=C_BORDE, height=1).pack(fill="x", padx=25, pady=8)

    # Componentes de evaluación
    tk.Label(ventana_cr, text="Componentes de evaluación:",
             bg=C_FONDO, fg=C_TEXTO, font=("Segoe UI", 10, "bold"),
             anchor="w").pack(fill="x", padx=25, pady=(0, 5))

    # Encabezados
    frame_header_comp = tk.Frame(ventana_cr, bg=C_FONDO)
    frame_header_comp.pack(fill="x", padx=25)
    tk.Label(frame_header_comp, text="Nombre", bg=C_FONDO, fg=C_TEXTO_SEC,
             font=("Segoe UI", 8), width=14, anchor="w").pack(side=tk.LEFT)
    tk.Label(frame_header_comp, text="% del total", bg=C_FONDO, fg=C_TEXTO_SEC,
             font=("Segoe UI", 8), width=10).pack(side=tk.LEFT)
    tk.Label(frame_header_comp, text="Cantidad", bg=C_FONDO, fg=C_TEXTO_SEC,
             font=("Segoe UI", 8), width=9).pack(side=tk.LEFT)
    tk.Label(frame_header_comp, text="Borrar peores", bg=C_FONDO, fg=C_TEXTO_SEC,
             font=("Segoe UI", 8), width=13).pack(side=tk.LEFT)

    # Scroll para componentes
    frame_comp_outer = tk.Frame(ventana_cr, bg=C_CARD,
                                 highlightbackground=C_BORDE, highlightthickness=1)
    frame_comp_outer.pack(fill="x", padx=25, pady=(0, 5))

    canvas_comp = tk.Canvas(frame_comp_outer, bg=C_CARD, highlightthickness=0, height=160)
    sb_comp = ttk.Scrollbar(frame_comp_outer, orient="vertical", command=canvas_comp.yview)
    frame_comp = tk.Frame(canvas_comp, bg=C_CARD)
    frame_comp.bind("<Configure>",
        lambda e: canvas_comp.configure(scrollregion=canvas_comp.bbox("all")))
    canvas_comp.create_window((0, 0), window=frame_comp, anchor="nw")
    canvas_comp.configure(yscrollcommand=sb_comp.set)
    canvas_comp.pack(side="left", fill="both", expand=True)
    sb_comp.pack(side="right", fill="y")

    filas_comp = []

    def agregar_componente(nombre="", porcentaje="", cantidad="1", borrar="0"):
        fila = tk.Frame(frame_comp, bg=C_CARD)
        fila.pack(fill="x", padx=5, pady=2)

        e_nom = tk.Entry(fila, width=13, font=("Segoe UI", 9), bg=C_FONDO,
                          relief="flat", highlightbackground=C_BORDE, highlightthickness=1)
        e_nom.pack(side=tk.LEFT, padx=(0,3), ipady=4)
        e_nom.insert(0, nombre)

        e_pct = tk.Entry(fila, width=8, font=("Segoe UI", 9), bg=C_FONDO,
                          justify="center", relief="flat",
                          highlightbackground=C_BORDE, highlightthickness=1)
        e_pct.pack(side=tk.LEFT, padx=3, ipady=4)
        e_pct.insert(0, porcentaje)

        e_cant = tk.Entry(fila, width=7, font=("Segoe UI", 9), bg=C_FONDO,
                           justify="center", relief="flat",
                           highlightbackground=C_BORDE, highlightthickness=1)
        e_cant.pack(side=tk.LEFT, padx=3, ipady=4)
        e_cant.insert(0, cantidad)

        e_borr = tk.Entry(fila, width=7, font=("Segoe UI", 9), bg=C_FONDO,
                           justify="center", relief="flat",
                           highlightbackground=C_BORDE, highlightthickness=1)
        e_borr.pack(side=tk.LEFT, padx=3, ipady=4)
        e_borr.insert(0, borrar)

        def eliminar_fila():
            fila.destroy()
            filas_comp.remove((fila, e_nom, e_pct, e_cant, e_borr))
            actualizar_porcentaje()

        tk.Button(fila, text="✕", command=eliminar_fila,
                  bg=C_CARD, fg="#C0392B", font=("Arial", 9),
                  relief="flat", cursor="hand2").pack(side=tk.LEFT, padx=2)

        filas_comp.append((fila, e_nom, e_pct, e_cant, e_borr))

    # Cargar componentes si es edición
    if es_edicion and ramo_editar.get("componentes"):
        for comp in ramo_editar["componentes"]:
            agregar_componente(
                comp.get("nombre", ""),
                str(int(comp.get("porcentaje", 0) * 100)),
                str(comp.get("cantidad", 1)),
                str(comp.get("borrar", 0))
            )
    else:
        agregar_componente("Certamen 1", "33", "1", "0")
        agregar_componente("Certamen 2", "33", "1", "0")
        agregar_componente("Controles", "34", "5", "1")

    # Indicador de porcentaje total
    lbl_total_pct = tk.Label(ventana_cr, text="Total: 0%", bg=C_FONDO,
                              fg="#C0392B", font=("Segoe UI", 10, "bold"))
    lbl_total_pct.pack(pady=2)

    def actualizar_porcentaje(*args):
        total = 0
        for _, _, e_pct, _, _ in filas_comp:
            try:
                total += float(e_pct.get())
            except ValueError:
                pass
        color = "#1A7A4A" if abs(total - 100) < 0.01 else "#C0392B"
        lbl_total_pct.config(text=f"Total: {total:.0f}% {'✅' if abs(total-100)<0.01 else '❌ debe ser 100%'}",
                              fg=color)

    tk.Button(ventana_cr, text="➕  Agregar componente",
              command=lambda: [agregar_componente(), actualizar_porcentaje()],
              bg=C_FONDO, fg=C_AZUL_MED, font=("Segoe UI", 9, "bold"),
              relief="flat", cursor="hand2").pack(pady=(0, 5))

    lbl_error = tk.Label(ventana_cr, text="", bg=C_FONDO,
                          fg="#C0392B", font=("Segoe UI", 9))
    lbl_error.pack()

    def guardar_ramo():
        nombre = entry_nombre.get().strip()
        codigo = entry_codigo.get().strip()
        try:
            meta = float(entry_meta.get())
        except ValueError:
            lbl_error.config(text="⚠️  La nota meta debe ser un número.")
            return

        if not nombre:
            lbl_error.config(text="⚠️  Ingresa un nombre para el ramo.")
            return

        componentes = []
        total_pct = 0
        for _, e_nom, e_pct, e_cant, e_borr in filas_comp:
            n = e_nom.get().strip()
            try:
                pct = float(e_pct.get())
                cant = int(e_cant.get())
                borr = int(e_borr.get())
            except ValueError:
                lbl_error.config(text="⚠️  Verifica que cantidad y porcentajes sean números.")
                return
            if n and pct > 0:
                componentes.append({
                    "nombre": n,
                    "porcentaje": pct / 100,
                    "cantidad": cant,
                    "borrar": borr
                })
                total_pct += pct

        if not componentes:
            lbl_error.config(text="⚠️  Agrega al menos un componente.")
            return

        if abs(total_pct - 100) > 0.5:
            lbl_error.config(text=f"⚠️  Los porcentajes suman {total_pct:.0f}%, deben sumar 100%.")
            return

        ramos = cargar_ramos_custom()
        nuevo = {"nombre": nombre, "codigo": codigo, "meta": meta, "componentes": componentes}

        if es_edicion:
            idx = ramo_editar.get("_idx", 0)
            ramos[idx] = nuevo
        else:
            ramos.append(nuevo)

        guardar_ramos_custom(ramos)
        callback_actualizar()
        ventana_cr.destroy()
        hablar_brune(f"Ramo {nombre} guardado correctamente.")

    frame_btns_cr = tk.Frame(ventana_cr, bg=C_FONDO)
    frame_btns_cr.pack(pady=8)

    tk.Button(frame_btns_cr, text="💾  Guardar ramo", command=guardar_ramo,
              bg=C_AZUL_MED, fg="white", font=("Segoe UI", 11, "bold"),
              relief="flat", padx=18, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=8)

    tk.Button(frame_btns_cr, text="✖  Cancelar", command=ventana_cr.destroy,
              bg=C_FONDO, fg=C_TEXTO_SEC, font=("Segoe UI", 10),
              relief="flat", padx=14, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=8)

def abrir_calculadora_custom():
    """Calculadora para ramos personalizados."""
    ventana_cc = tk.Toplevel()
    ventana_cc.title("Mis Ramos — BRUNE")
    ventana_cc.config(bg=C_FONDO)
    ventana_cc.resizable(False, False)
    ventana_cc.update_idletasks()
    _cx = (ventana_cc.winfo_screenwidth() // 2) - 250
    _cy = (ventana_cc.winfo_screenheight() // 2) - 280
    ventana_cc.geometry(f"500x560+{_cx}+{_cy}")

    # Header
    fh = tk.Frame(ventana_cc, bg=C_AZUL_OSC, height=55)
    fh.pack(fill="x"); fh.pack_propagate(False)
    tk.Label(fh, text="📚  Mis Ramos Personalizados", bg=C_AZUL_OSC, fg="white",
             font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=18, pady=10)

    frame_lista = tk.Frame(ventana_cc, bg=C_FONDO)
    frame_lista.pack(fill="both", expand=True, padx=20, pady=10)

    def actualizar_lista():
        for w in frame_lista.winfo_children():
            w.destroy()

        ramos = cargar_ramos_custom()
        if not ramos:
            tk.Label(frame_lista,
                     text="No tienes ramos personalizados todavía.\nCrea uno con el botón de abajo.",
                     bg=C_FONDO, fg=C_TEXTO_SEC, font=("Segoe UI", 10),
                     justify="center").pack(expand=True, pady=30)
            return

        for idx, ramo in enumerate(ramos):
            frame_ramo = tk.Frame(frame_lista, bg=C_CARD,
                                   highlightbackground=C_BORDE, highlightthickness=1)
            frame_ramo.pack(fill="x", pady=4)

            frame_ramo_top = tk.Frame(frame_ramo, bg=C_CARD)
            frame_ramo_top.pack(fill="x", padx=12, pady=8)

            nombre_completo = ramo["nombre"]
            if ramo.get("codigo"):
                nombre_completo += f" ({ramo['codigo']})"

            tk.Label(frame_ramo_top, text=nombre_completo,
                     bg=C_CARD, fg=C_TEXTO, font=("Segoe UI", 11, "bold"),
                     anchor="w").pack(side=tk.LEFT)

            tk.Label(frame_ramo_top, text=f"Meta: {ramo.get('meta', 55)}",
                     bg=C_CARD, fg=C_TEXTO_SEC, font=("Segoe UI", 9)).pack(side=tk.RIGHT)

            # Componentes
            comp_txt = "  |  ".join([f"{c['nombre']} {int(c['porcentaje']*100)}%"
                                      for c in ramo.get("componentes", [])])
            tk.Label(frame_ramo, text=comp_txt, bg=C_CARD, fg=C_TEXTO_SEC,
                     font=("Segoe UI", 8), anchor="w").pack(fill="x", padx=12, pady=(0, 8))

            # Botones
            frame_btns_ramo = tk.Frame(frame_ramo, bg=C_CARD)
            frame_btns_ramo.pack(fill="x", padx=12, pady=(0, 8))

            def abrir_calc_ramo(r=ramo):
                abrir_calc_para_ramo(r)

            def editar_ramo(r=ramo, i=idx):
                r["_idx"] = i
                abrir_crear_ramo(actualizar_lista, r)

            def eliminar_ramo(i=idx):
                if messagebox.askyesno("Eliminar", f"¿Eliminar '{ramos[i]['nombre']}'?"):
                    ramos_act = cargar_ramos_custom()
                    ramos_act.pop(i)
                    guardar_ramos_custom(ramos_act)
                    actualizar_lista()

            tk.Button(frame_btns_ramo, text="🧮  Calcular nota",
                      command=abrir_calc_ramo,
                      bg=C_AZUL_MED, fg="white", font=("Segoe UI", 9, "bold"),
                      relief="flat", padx=10, pady=4, cursor="hand2").pack(side=tk.LEFT, padx=(0, 6))

            tk.Button(frame_btns_ramo, text="✏️  Editar",
                      command=editar_ramo,
                      bg=C_FONDO, fg=C_AZUL_MED, font=("Segoe UI", 9),
                      relief="flat", padx=8, pady=4, cursor="hand2").pack(side=tk.LEFT, padx=3)

            tk.Button(frame_btns_ramo, text="🗑  Eliminar",
                      command=eliminar_ramo,
                      bg=C_FONDO, fg="#C0392B", font=("Segoe UI", 9),
                      relief="flat", padx=8, pady=4, cursor="hand2").pack(side=tk.LEFT, padx=3)

    actualizar_lista()

    tk.Frame(ventana_cc, bg=C_BORDE, height=1).pack(fill="x", padx=20)

    tk.Button(ventana_cc, text="➕  Crear nuevo ramo",
              command=lambda: abrir_crear_ramo(actualizar_lista),
              bg=C_AZUL_MED, fg="white", font=("Segoe UI", 11, "bold"),
              relief="flat", padx=18, pady=10, cursor="hand2").pack(pady=12)

def abrir_calc_para_ramo(ramo):
    """Abre la calculadora para un ramo personalizado específico."""
    ventana_cr2 = tk.Toplevel()
    nombre_completo = ramo["nombre"] + (f" ({ramo['codigo']})" if ramo.get("codigo") else "")
    ventana_cr2.title(f"{nombre_completo} — BRUNE")
    ventana_cr2.config(bg=C_FONDO)
    ventana_cr2.resizable(False, False)
    ventana_cr2.update_idletasks()
    _cx = (ventana_cr2.winfo_screenwidth() // 2) - 230
    _cy = (ventana_cr2.winfo_screenheight() // 2) - 260
    ventana_cr2.geometry(f"460x520+{_cx}+{_cy}")

    fh = tk.Frame(ventana_cr2, bg=C_AZUL_OSC, height=55)
    fh.pack(fill="x"); fh.pack_propagate(False)
    tk.Label(fh, text=f"🧮  {nombre_completo}", bg=C_AZUL_OSC, fg="white",
             font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=18, pady=10)

    meta = ramo.get("meta", 55)
    componentes = ramo.get("componentes", [])

    tk.Label(ventana_cr2, text=f"Meta: {meta} pts",
             bg=C_FONDO, fg=C_TEXTO_SEC, font=("Segoe UI", 9)).pack(pady=(10, 5))

    frame_inputs = tk.Frame(ventana_cr2, bg=C_FONDO)
    frame_inputs.pack(padx=25, fill="x")

    entradas = {}
    for comp in componentes:
        fila = tk.Frame(frame_inputs, bg=C_FONDO)
        fila.pack(fill="x", pady=5)

        tk.Label(fila, text=f"{comp['nombre']} ({int(comp['porcentaje']*100)}%):",
                 bg=C_FONDO, fg=C_TEXTO, font=("Segoe UI", 10), width=22, anchor="w").pack(side=tk.LEFT)

        entry = tk.Entry(fila, width=8, justify="center", bg=C_CARD,
                          relief="flat", highlightbackground=C_BORDE, highlightthickness=1)
        entry.pack(side=tk.LEFT, padx=8, ipady=5)

        cant = comp.get("cantidad", 1)
        borrar = comp.get("borrar", 0)
        if cant > 1:
            info = f"{cant} notas"
            if borrar > 0:
                info += f", se borran {borrar} peores"
            tk.Label(fila, text=info, bg=C_FONDO, fg=C_TEXTO_SEC,
                     font=("Segoe UI", 8)).pack(side=tk.LEFT)

        entradas[comp["nombre"]] = (entry, comp)

    tk.Frame(ventana_cr2, bg=C_BORDE, height=1).pack(fill="x", padx=25, pady=12)

    lbl_resultado = tk.Label(ventana_cr2, text="Nota requerida: --",
                              bg=C_FONDO, fg="#1A7A4A", font=("Segoe UI", 12, "bold"))
    lbl_resultado.pack(pady=5)

    def calcular():
        nota_actual = 0.0
        peso_evaluado = 0.0

        try:
            for nom, (entry, comp) in entradas.items():
                val = entry.get().strip()
                if val:
                    notas_raw = [float(x) for x in val.replace(",", " ").split() if x]
                    cant = comp.get("cantidad", 1)
                    borrar = comp.get("borrar", 0)

                    if len(notas_raw) > 1:
                        ordenadas = sorted(notas_raw, reverse=True)
                        utiles = ordenadas[:cant - borrar]
                        nota = sum(utiles) / len(utiles)
                    elif len(notas_raw) == 1:
                        nota = notas_raw[0]
                    else:
                        continue

                    nota_actual += nota * comp["porcentaje"]
                    peso_evaluado += comp["porcentaje"]

            peso_restante = 1.0 - peso_evaluado

            if peso_restante <= 0.001:
                if nota_actual >= meta:
                    lbl_resultado.config(text=f"🎓 ¡Lograste tu meta! Nota final: {nota_actual:.1f}", fg="#1A7A4A")
                else:
                    lbl_resultado.config(text=f"Nota final: {nota_actual:.1f} — No lograste la meta de {meta}", fg="#C0392B")
            else:
                nota_faltante = (meta - nota_actual) / peso_restante
                if nota_faltante > 100:
                    lbl_resultado.config(text=f"Imposible llegar a {meta} 💀\nNecesitarías {nota_faltante:.1f}", fg="#C0392B")
                elif nota_faltante <= 0:
                    lbl_resultado.config(text=f"🎉 ¡Ya aseguraste la meta! Tienes {nota_actual:.1f}", fg="#1A7A4A")
                else:
                    lbl_resultado.config(text=f"Necesitas {nota_faltante:.1f} en lo que falta — ¡tú puedes!", fg=C_AZUL_MED)
        except ValueError:
            messagebox.showerror("Error", "Ingresa solo números. Separa múltiples notas con espacios.")

    tk.Button(ventana_cr2, text="Calcular →", command=calcular,
              bg=C_AZUL_MED, fg="white", font=("Segoe UI", 11, "bold"),
              relief="flat", padx=20, pady=9, cursor="hand2").pack(pady=5)

    tk.Label(ventana_cr2,
             text="💡 Si tienes múltiples notas, sepáralas con espacios (ej: 75 80 90)",
             bg=C_FONDO, fg=C_TEXTO_SEC, font=("Segoe UI", 8),
             wraplength=400).pack(pady=5)

# ==========================================
# 4. VENTANA DE CHAT CON GEMINI
# ==========================================
def abrir_chat_ia():
    ventana_chat = tk.Toplevel()
    ventana_chat.title("Chat con BRUNE IA")
    ventana_chat.config(bg=C_FONDO)
    ventana_chat.resizable(True, True)
    ventana_chat.update_idletasks()
    _cx = (ventana_chat.winfo_screenwidth() // 2) - 280
    _cy = (ventana_chat.winfo_screenheight() // 2) - 310
    ventana_chat.geometry(f"560x620+{_cx}+{_cy}")
    # Header chat
    fhc = tk.Frame(ventana_chat, bg=C_AZUL_OSC, height=55)
    fhc.pack(fill="x"); fhc.pack_propagate(False)
    tk.Label(fhc, text="💬  Chat con BRUNE", bg=C_AZUL_OSC, fg="white",
             font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=18, pady=10)

    ramo_actual = variable_ramo.get()
    texto_contexto = ("Contexto: consulta general" if ramo_actual == "Selecciona el ramo"
                      else f"Contexto: {ramo_actual}")
    tk.Label(ventana_chat, text=texto_contexto, bg=C_FONDO,
             fg=C_TEXTO_SEC, font=("Segoe UI", 9)).pack(pady=(8, 2))

    frame_chat = tk.Frame(ventana_chat, bg=C_FONDO)
    frame_chat.pack(fill="both", expand=True, padx=15)

    area_chat = scrolledtext.ScrolledText(
        frame_chat, wrap=tk.WORD, bg=C_CARD, fg=C_TEXTO,
        font=("Segoe UI", 10), state="disabled", relief="flat", bd=0,
        highlightbackground=C_BORDE, highlightthickness=1
    )
    area_chat.pack(fill="both", expand=True)

    area_chat.tag_config("usuario",  foreground=C_AZUL_OSC, font=("Segoe UI", 10, "bold"))
    area_chat.tag_config("brune",    foreground="#1A7A4A", font=("Segoe UI", 10))
    area_chat.tag_config("error",    foreground="#C0392B", font=("Segoe UI", 10))
    area_chat.tag_config("pensando", foreground=C_AZUL_MED, font=("Segoe UI", 10, "italic"))

    def agregar_mensaje(quien, texto):
        area_chat.config(state="normal")
        if quien == "usuario":
            area_chat.insert(tk.END, f"\nTú: {texto}\n", "usuario")
        elif quien == "brune":
            area_chat.insert(tk.END, f"BRUNE: {texto}\n", "brune")
        elif quien == "error":
            area_chat.insert(tk.END, f"⚠️ {texto}\n", "error")
        elif quien == "pensando":
            area_chat.insert(tk.END, f"{texto}\n", "pensando")
        area_chat.config(state="disabled")
        area_chat.see(tk.END)

    agregar_mensaje("brune", "¡Hola! Soy BRUNE. Puedes preguntarme sobre tus ramos o cualquier cosa. ¿En qué te ayudo?")

    frame_inferior = tk.Frame(ventana_chat, bg=C_FONDO)
    frame_inferior.pack(fill="x", padx=15, pady=10)

    entrada_texto = tk.Entry(frame_inferior, bg=C_CARD, fg=C_TEXTO,
                              font=("Segoe UI", 11), insertbackground=C_AZUL_MED,
                              relief="flat", bd=0,
                              highlightbackground=C_BORDE, highlightthickness=1)
    entrada_texto.pack(side=tk.LEFT, fill="x", expand=True, ipady=6)

    lbl_estado_voz = tk.Label(frame_inferior, text="", bg=C_FONDO,
                               fg=C_AZUL_MED, font=("Segoe UI", 9))

    def construir_prompt(pregunta):
        ramo = variable_ramo.get()
        contexto_ramos = {
            "Introducción a la física": (
                "física universitaria introductoria (cinemática, dinámica, energía, "
                "ondas, termodinámica, electromagnetismo básico)"
            ),
            "Álgebra y geometría": (
                "álgebra lineal y geometría universitaria (vectores, matrices, "
                "determinantes, sistemas de ecuaciones, transformaciones lineales)"
            ),
            "Introducción al cálculo": (
                "cálculo universitario introductorio (límites, derivadas, "
                "integrales, reglas de derivación, aplicaciones)"
            ),
            "Proyecto inicial": (
                "metodología de proyectos de ingeniería y trabajo en equipo universitario"
            ),
        }

        if ramo in contexto_ramos:
            sistema = (
                f"Eres BRUNE, un asistente universitario para estudiantes de ingeniería de la USM Chile. "
                f"El estudiante tiene seleccionado el ramo de {ramo}. "
                f"Si la pregunta es sobre {contexto_ramos[ramo]}, responde con ese contexto en mente, "
                f"con ejemplos claros y apropiados para ese ramo. "
                f"Si la pregunta es general o de otro tema, respóndela igual sin problema. "
                f"Sé conciso, claro y amigable. Responde siempre en español."
            )
        else:
            sistema = (
                "Eres BRUNE, un asistente universitario para estudiantes de ingeniería de la USM Chile. "
                "Responde de forma concisa, clara y amigable. Siempre en español."
            )

        return f"{sistema}\n\nEstudiante pregunta: {pregunta}"

    def quitar_ultimo_mensaje():
        area_chat.config(state="normal")
        area_chat.delete("end-2l", "end-1c")
        area_chat.config(state="disabled")

    def enviar_pregunta(pregunta):
        if not pregunta.strip():
            return

        agregar_mensaje("usuario", pregunta)
        agregar_mensaje("pensando", "BRUNE está pensando...")

        def llamar_gemini():
            try:
                prompt = construir_prompt(pregunta)
                respuesta = cliente_gemini.models.generate_content(
                    model=MODELO_GEMINI,
                    contents=prompt
                )
                texto_respuesta = respuesta.text.strip()

                ventana_chat.after(0, quitar_ultimo_mensaje)
                ventana_chat.after(0, lambda: agregar_mensaje("brune", texto_respuesta))

                voz = texto_respuesta[:300] + ("..." if len(texto_respuesta) > 300 else "")
                hablar_brune(voz)

            except Exception as e:
                ventana_chat.after(0, quitar_ultimo_mensaje)
                ventana_chat.after(0, lambda: agregar_mensaje(
                    "error",
                    f"No pude conectarme a Gemini. Verifica tu API key y conexión.\nDetalle: {e}"
                ))
                print(f"[BRUNE] Error Gemini: {e}")

        threading.Thread(target=llamar_gemini, daemon=True).start()

    def on_enviar(event=None):
        pregunta = entrada_texto.get().strip()
        if pregunta:
            entrada_texto.delete(0, tk.END)
            enviar_pregunta(pregunta)

    entrada_texto.bind("<Return>", on_enviar)

    btn_enviar = tk.Button(frame_inferior, text="Enviar", command=on_enviar,
                            bg=C_AZUL_MED, fg="white", font=("Segoe UI", 10, "bold"),
                            relief="flat", padx=14, pady=6, cursor="hand2")
    btn_enviar.pack(side=tk.LEFT, padx=(8, 0))

    escuchando_chat = {"activo": False}

    def escuchar_en_chat():
        if escuchando_chat["activo"]:
            return
        if not microfono_disponible():
            agregar_mensaje("error", "No encontré micrófono. ¿Está conectado?")
            return

        escuchando_chat["activo"] = True
        btn_voz_chat.config(state="disabled")
        lbl_estado_voz.config(text="Escuchando...")
        lbl_estado_voz.pack(side=tk.LEFT, padx=(8, 0))

        def reconocer():
            def chat_abierto():
                try:
                    return ventana_chat.winfo_exists()
                except Exception:
                    return False

            def ui_safe(func):
                if chat_abierto():
                    ventana_chat.after(0, func)

            try:
                ui_safe(lambda: lbl_estado_voz.config(text="Escuchando..."))
                audio_data, sample_rate = grabar_con_silencio(duracion_max=10)

                if audio_data is None or len(audio_data) < sample_rate * 0.3:
                    ui_safe(lambda: lbl_estado_voz.config(text="No escuché nada."))
                    return

                ui_safe(lambda: lbl_estado_voz.config(text="Procesando..."))
                PROMPT_CHAT = "Pregunta o consulta universitaria en español chileno."
                resultado = _modelo_whisper.transcribe(
                    audio_data,
                    language="es",
                    fp16=False,
                    temperature=0.1,
                    initial_prompt=PROMPT_CHAT,
                    condition_on_previous_text=False,
                    no_speech_threshold=0.5,
                )
                texto = resultado["text"].strip()

                if texto:
                    ui_safe(lambda: entrada_texto.insert(0, texto))
                    ui_safe(lambda: lbl_estado_voz.config(text=""))
                    ui_safe(on_enviar)
                else:
                    ui_safe(lambda: lbl_estado_voz.config(text="No te entendí, repite."))

            except Exception as e:
                ui_safe(lambda: lbl_estado_voz.config(text="Error de micrófono."))
                print(f"[BRUNE] Error voz en chat: {e}")
            finally:
                escuchando_chat["activo"] = False
                ui_safe(lambda: btn_voz_chat.config(state="normal"))

        threading.Thread(target=reconocer, daemon=True).start()

    btn_voz_chat = tk.Button(frame_inferior, text="🎙️", command=escuchar_en_chat,
                              bg=C_FONDO, fg=C_AZUL_MED, font=("Arial", 14),
                              relief="flat", cursor="hand2")
    btn_voz_chat.pack(side=tk.LEFT, padx=(5, 0))
    lbl_estado_voz.pack(side=tk.LEFT, padx=(8, 0))

    entrada_texto.focus()



# ==========================================
# HISTORIAL DE ESTUDIO
# ==========================================
def cargar_historial():
    try:
        with open(ARCHIVO_HISTORIAL, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def guardar_sesion_historial(minutos, ciclos):
    """Guarda una sesión de estudio en el historial."""
    historial = cargar_historial()
    hoy = datetime.date.today().strftime("%d/%m/%Y")
    # Buscar si ya hay una entrada para hoy
    for entrada in historial:
        if entrada["fecha"] == hoy:
            entrada["minutos"] += minutos
            entrada["ciclos"] += ciclos
            break
    else:
        historial.append({"fecha": hoy, "minutos": minutos, "ciclos": ciclos})
    # Mantener solo los últimos 30 días
    historial = historial[-30:]
    with open(ARCHIVO_HISTORIAL, "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False, indent=2)

def abrir_historial_estudio():
    ventana_hist = tk.Toplevel()
    ventana_hist.title("Historial de Estudio — BRUNE")
    ventana_hist.config(bg=C_FONDO)
    ventana_hist.resizable(False, False)
    ventana_hist.update_idletasks()
    _cx = (ventana_hist.winfo_screenwidth() // 2) - 220
    _cy = (ventana_hist.winfo_screenheight() // 2) - 250
    ventana_hist.geometry(f"440x500+{_cx}+{_cy}")

    # Header
    fh = tk.Frame(ventana_hist, bg=C_AZUL_OSC, height=55)
    fh.pack(fill="x"); fh.pack_propagate(False)
    tk.Label(fh, text="📊  Historial de Estudio", bg=C_AZUL_OSC, fg="white",
             font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=18, pady=10)

    historial = cargar_historial()

    if not historial:
        tk.Label(ventana_hist, text="\nAún no hay sesiones registradas.\nCompleta un ciclo del temporizador para empezar.",
                 bg=C_FONDO, fg=C_TEXTO_SEC, font=("Segoe UI", 11),
                 justify="center").pack(expand=True)
        return

    # Estadísticas totales
    total_min = sum(e["minutos"] for e in historial)
    total_ciclos = sum(e["ciclos"] for e in historial)
    total_horas = total_min // 60
    total_min_rest = total_min % 60

    frame_stats = tk.Frame(ventana_hist, bg=C_AZUL_OSC)
    frame_stats.pack(fill="x")

    tk.Label(frame_stats,
             text=f"Total: {total_horas}h {total_min_rest}min  •  {total_ciclos} ciclos completados",
             bg=C_AZUL_OSC, fg=C_AZUL_CLAR, font=("Segoe UI", 10)).pack(pady=6)

    tk.Frame(ventana_hist, bg=C_BORDE, height=1).pack(fill="x")

    # Lista de sesiones (más reciente primero)
    frame_lista = tk.Frame(ventana_hist, bg=C_FONDO)
    frame_lista.pack(fill="both", expand=True, padx=20, pady=10)

    # Máximo de minutos para escalar las barras
    max_min = max(e["minutos"] for e in historial) if historial else 1

    for entrada in reversed(historial[-14:]):  # últimos 14 días
        fecha = entrada["fecha"]
        mins = entrada["minutos"]
        ciclos = entrada["ciclos"]
        horas = mins // 60
        mins_rest = mins % 60

        # Tiempo formateado
        if horas > 0:
            tiempo_str = f"{horas}h {mins_rest}min"
        else:
            tiempo_str = f"{mins_rest}min"

        # Color según tiempo estudiado
        if mins >= 120:
            color_barra = "#1A7A4A"   # verde — más de 2h
        elif mins >= 60:
            color_barra = C_AZUL_MED  # azul — entre 1h y 2h
        elif mins >= 25:
            color_barra = "#E67E22"   # naranja — entre 25min y 1h
        else:
            color_barra = C_TEXTO_SEC # gris — menos de 25min

        fila = tk.Frame(frame_lista, bg=C_FONDO)
        fila.pack(fill="x", pady=4)

        # Fecha
        tk.Label(fila, text=fecha, bg=C_FONDO, fg=C_TEXTO_SEC,
                 font=("Segoe UI", 9), width=12, anchor="w").pack(side=tk.LEFT)

        # Barra de progreso
        ancho_barra = int((mins / max_min) * 160)
        ancho_barra = max(ancho_barra, 4)
        barra_frame = tk.Frame(fila, bg=C_BORDE, height=18, width=160)
        barra_frame.pack(side=tk.LEFT, padx=(0, 8))
        barra_frame.pack_propagate(False)
        tk.Frame(barra_frame, bg=color_barra, height=18, width=ancho_barra).place(x=0, y=0)

        # Tiempo y ciclos
        tk.Label(fila, text=f"{tiempo_str}  ({ciclos} ciclos)",
                 bg=C_FONDO, fg=C_TEXTO, font=("Segoe UI", 9),
                 anchor="w").pack(side=tk.LEFT)

    # Leyenda de colores
    tk.Frame(ventana_hist, bg=C_BORDE, height=1).pack(fill="x", padx=20)
    frame_leyenda = tk.Frame(ventana_hist, bg=C_FONDO)
    frame_leyenda.pack(pady=8)

    leyendas = [
        ("#1A7A4A", "+2h"),
        (C_AZUL_MED, "1-2h"),
        ("#E67E22", "25-60min"),
        (C_TEXTO_SEC, "<25min"),
    ]
    for color, texto in leyendas:
        f = tk.Frame(frame_leyenda, bg=C_FONDO)
        f.pack(side=tk.LEFT, padx=8)
        tk.Frame(f, bg=color, width=14, height=14).pack(side=tk.LEFT, padx=(0, 4))
        tk.Label(f, text=texto, bg=C_FONDO, fg=C_TEXTO_SEC,
                 font=("Segoe UI", 8)).pack(side=tk.LEFT)

# ==========================================
# 5B. POMODORO
# ==========================================
def abrir_pomodoro():
    ventana_pom = tk.Toplevel()
    ventana_pom.title("Temporizador de Estudio — BRUNE")
    ventana_pom.config(bg=C_FONDO)
    ventana_pom.resizable(False, False)
    ventana_pom.update_idletasks()
    _cx = (ventana_pom.winfo_screenwidth() // 2) - 190
    _cy = (ventana_pom.winfo_screenheight() // 2) - 240
    ventana_pom.geometry(f"380x480+{_cx}+{_cy}")
    fhp = tk.Frame(ventana_pom, bg=C_AZUL_OSC, height=55)
    fhp.pack(fill="x"); fhp.pack_propagate(False)
    tk.Label(fhp, text="⏱️  Temporizador de Estudio", bg=C_AZUL_OSC, fg="white",
             font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=18, pady=10)

    # --- Estado interno ---
    estado = {
        "corriendo": False,
        "modo": "estudio",       # "estudio" o "descanso"
        "segundos_restantes": 0,
        "ciclos": 0,
        "job": None,
    }

    # --- Configuración de tiempos ---
    frame_config = tk.Frame(ventana_pom, bg=C_FONDO)
    frame_config.pack(pady=10)

    tk.Label(frame_config, text="Estudio (min):", bg=C_FONDO, fg=C_TEXTO, font=("Segoe UI", 10)).grid(row=0, column=0, padx=8)
    tk.Label(frame_config, text="Descanso (min):", bg=C_FONDO, fg=C_TEXTO, font=("Segoe UI", 10)).grid(row=0, column=1, padx=8)

    entry_estudio  = tk.Entry(frame_config, width=5, justify="center", font=("Arial", 11))
    entry_descanso = tk.Entry(frame_config, width=5, justify="center", font=("Arial", 11))
    entry_estudio.insert(0, "25")
    entry_descanso.insert(0, "5")
    entry_estudio.grid(row=1, column=0, padx=8, pady=4)
    entry_descanso.grid(row=1, column=1, padx=8, pady=4)

    # --- Display del temporizador ---
    lbl_modo = tk.Label(ventana_pom, text="ESTUDIO", bg=C_FONDO, fg=C_AZUL_MED,
                         font=("Segoe UI", 13, "bold"))
    lbl_modo.pack(pady=(10, 0))

    lbl_tiempo = tk.Label(ventana_pom, text="25:00", bg=C_FONDO, fg=C_AZUL_OSC,
                           font=("Segoe UI", 52, "bold"))
    lbl_tiempo.pack()

    lbl_ciclos = tk.Label(ventana_pom, text="Ciclos completados: 0",
                           bg=C_FONDO, fg=C_AZUL_MED, font=("Segoe UI", 10))
    lbl_ciclos.pack(pady=(0, 10))

    # --- Barra de progreso ---
    barra = ttk.Progressbar(ventana_pom, orient="horizontal", length=300, mode="determinate")
    barra.pack(pady=5)

    # --- Botones ---
    frame_btns = tk.Frame(ventana_pom, bg=C_FONDO)
    frame_btns.pack(pady=15)

    def formatear(segundos):
        m, s = divmod(segundos, 60)
        return f"{m:02d}:{s:02d}"

    def tick():
        if not estado["corriendo"]:
            return
        if estado["segundos_restantes"] > 0:
            estado["segundos_restantes"] -= 1
            lbl_tiempo.config(text=formatear(estado["segundos_restantes"]))
            total = (int(entry_estudio.get()) * 60 if estado["modo"] == "estudio"
                     else int(entry_descanso.get()) * 60)
            barra["value"] = ((total - estado["segundos_restantes"]) / total) * 100
            estado["job"] = ventana_pom.after(1000, tick)
        else:
            # Tiempo terminado — cambiar modo
            if estado["modo"] == "estudio":
                estado["ciclos"] += 1
                lbl_ciclos.config(text=f"Ciclos completados: {estado['ciclos']}")
                # Guardar en historial
                try:
                    mins_estudiados = int(entry_estudio.get())
                except ValueError:
                    mins_estudiados = 25
                guardar_sesion_historial(mins_estudiados, 1)
                estado["modo"] = "descanso"
                try:
                    mins = int(entry_descanso.get())
                except ValueError:
                    mins = 5
                estado["segundos_restantes"] = mins * 60
                lbl_modo.config(text="DESCANSO", fg="#1A7A4A")
                hablar_brune(f"¡Muy bien! Completaste el ciclo {estado['ciclos']}. Tómate un descanso de {mins} minutos.")
            else:
                estado["modo"] = "estudio"
                try:
                    mins = int(entry_estudio.get())
                except ValueError:
                    mins = 25
                estado["segundos_restantes"] = mins * 60
                lbl_modo.config(text="ESTUDIO", fg=C_AZUL_MED)
                hablar_brune(f"¡Descanso terminado! A estudiar por {mins} minutos más. ¡Tú puedes!")
            barra["value"] = 0
            lbl_tiempo.config(text=formatear(estado["segundos_restantes"]))
            estado["job"] = ventana_pom.after(1000, tick)

    def iniciar_pausar():
        if estado["corriendo"]:
            # Pausar
            estado["corriendo"] = False
            if estado["job"]:
                ventana_pom.after_cancel(estado["job"])
            btn_iniciar.config(text="▶  Reanudar", bg="#1A7A4A", fg="white")
        else:
            # Iniciar o reanudar
            if estado["segundos_restantes"] == 0:
                # Primer inicio — leer tiempos configurados
                try:
                    mins = int(entry_estudio.get())
                    if mins <= 0: raise ValueError
                except ValueError:
                    messagebox.showerror("Error", "Ingresa minutos válidos de estudio.")
                    return
                estado["segundos_restantes"] = mins * 60
                estado["modo"] = "estudio"
                lbl_modo.config(text="ESTUDIO", fg=C_AZUL_MED)
                hablar_brune(f"Iniciando temporizador. {mins} minutos de estudio. ¡Concéntrate!")
            estado["corriendo"] = True
            btn_iniciar.config(text="⏸  Pausar", bg="#C0392B", fg="white")
            tick()

    def reiniciar():
        estado["corriendo"] = False
        if estado["job"]:
            ventana_pom.after_cancel(estado["job"])
        estado["segundos_restantes"] = 0
        estado["modo"] = "estudio"
        estado["ciclos"] = 0
        lbl_tiempo.config(text="--:--")
        lbl_modo.config(text="ESTUDIO", fg="#90D5FF")
        lbl_ciclos.config(text="Ciclos completados: 0")
        barra["value"] = 0
        btn_iniciar.config(text="▶  Iniciar", bg="#1A7A4A", fg="white")

    btn_iniciar = tk.Button(frame_btns, text="▶  Iniciar", command=iniciar_pausar,
                             bg="#1A7A4A", fg="white", font=("Segoe UI", 11, "bold"),
                             relief="flat", padx=18, pady=9, cursor="hand2")
    btn_iniciar.pack(side=tk.LEFT, padx=8)

    tk.Button(frame_btns, text="↺  Reiniciar", command=reiniciar,
              bg=C_AZUL_MED, fg="white", font=("Segoe UI", 11),
              relief="flat", padx=18, pady=9, cursor="hand2").pack(side=tk.LEFT, padx=8)

    tk.Frame(ventana_pom, bg=C_BORDE, height=1).pack(fill="x", padx=30, pady=(15, 5))

    tk.Button(ventana_pom, text="📊  Ver historial de estudio",
              command=abrir_historial_estudio,
              bg=C_FONDO, fg=C_AZUL_MED, font=("Segoe UI", 10, "bold"),
              relief="flat", cursor="hand2").pack(pady=(0, 15))


# ==========================================
# 5C. RECORDATORIO DE CERTÁMENES
# ==========================================
ARCHIVO_CERTAMENES = str(CARPETA_DATOS / "certamenes.json")

def cargar_certamenes():
    try:
        with open(ARCHIVO_CERTAMENES, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def guardar_certamenes(lista):
    with open(ARCHIVO_CERTAMENES, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)

def dias_restantes(fecha_str):
    try:
        fecha = datetime.datetime.strptime(fecha_str, "%d/%m/%Y").date()
        hoy = datetime.date.today()
        return (fecha - hoy).days
    except Exception:
        return None

def abrir_certamenes():
    ventana_cert = tk.Toplevel()
    ventana_cert.title("Certámenes — BRUNE")
    ventana_cert.config(bg=C_FONDO)
    ventana_cert.update_idletasks()
    _cx = (ventana_cert.winfo_screenwidth() // 2) - 260
    _cy = (ventana_cert.winfo_screenheight() // 2) - 270
    ventana_cert.geometry(f"520x540+{_cx}+{_cy}")
    fhce = tk.Frame(ventana_cert, bg=C_AZUL_OSC, height=55)
    fhce.pack(fill="x"); fhce.pack_propagate(False)
    tk.Label(fhce, text="📅  Mis Certámenes", bg=C_AZUL_OSC, fg="white",
             font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=18, pady=10)

    tk.Label(ventana_cert, text="Haz clic en un certamen para editarlo o eliminarlo",
             bg=C_FONDO, fg=C_TEXTO_SEC, font=("Segoe UI", 9)).pack(pady=(8,2))

    # --- Lista de certámenes ---
    frame_lista = tk.Frame(ventana_cert, bg=C_FONDO)
    frame_lista.pack(fill="both", expand=True, padx=15, pady=10)

    lista_box = tk.Listbox(frame_lista, bg=C_CARD, fg=C_TEXTO, font=("Segoe UI", 10),
                            selectbackground=C_AZUL_CLAR, selectforeground="white",
                            relief="flat", bd=0, highlightthickness=1,
                            highlightbackground=C_BORDE, activestyle="none", height=10)
    lista_box.pack(fill="both", expand=True)

    certamenes = cargar_certamenes()

    def color_dias(dias):
        if dias is None:   return "#888888"
        if dias < 0:       return "#888888"
        if dias <= 3:      return "#FF4C4C"
        if dias <= 7:      return "#FFD700"
        return "#1A7A4A"

    def refrescar_lista():
        lista_box.delete(0, tk.END)
        certamenes_actuales = cargar_certamenes()
        certamenes.clear()
        certamenes.extend(certamenes_actuales)

        # Ordenar por fecha
        def sort_key(c):
            try:
                return datetime.datetime.strptime(c["fecha"], "%d/%m/%Y")
            except Exception:
                return datetime.datetime.max
        certamenes.sort(key=sort_key)

        for c in certamenes:
            dias = dias_restantes(c["fecha"])
            if dias is None:
                texto = f"  {c['ramo']} — {c['nombre']} | {c['fecha']} | fecha inválida"
            elif dias < 0:
                texto = f"  {c['ramo']} — {c['nombre']} | {c['fecha']} | ya pasó"
            elif dias == 0:
                texto = f"  {c['ramo']} — {c['nombre']} | {c['fecha']} | ¡HOY!"
            elif dias == 1:
                texto = f"  {c['ramo']} — {c['nombre']} | {c['fecha']} | ¡mañana!"
            else:
                texto = f"  {c['ramo']} — {c['nombre']} | {c['fecha']} | {dias} días"
            lista_box.insert(tk.END, texto)
            lista_box.itemconfig(tk.END, fg=color_dias(dias))

    refrescar_lista()

    # --- Separador ---
    tk.Frame(ventana_cert, bg=C_BORDE, height=1).pack(fill="x", padx=15)

    # --- Formulario para agregar / editar ---
    tk.Label(ventana_cert, text="Agregar certamen:", bg=C_FONDO, fg=C_AZUL_MED,
             font=("Segoe UI", 10, "bold")).pack(pady=(10, 2))

    frame_form = tk.Frame(ventana_cert, bg=C_FONDO)
    frame_form.pack(padx=15, fill="x")

    # Fila 1
    frame_f1 = tk.Frame(frame_form, bg=C_FONDO)
    frame_f1.pack(fill="x", pady=3)
    tk.Label(frame_f1, text="Ramo:", bg=C_FONDO, fg=C_TEXTO, font=("Segoe UI",10), width=10, anchor="w").pack(side=tk.LEFT)
    combo_ramo_cert = ttk.Combobox(frame_f1, values=[
        "Introducción a la física (FIS100)", "Álgebra y geometría (MAT060)", "Introducción al cálculo (MAT070)", "Proyecto Inicial", "Otro"
    ], state="readonly", width=20)
    combo_ramo_cert.pack(side=tk.LEFT, padx=5)
    combo_ramo_cert.current(0)

    # Fila 2
    frame_f2 = tk.Frame(frame_form, bg=C_FONDO)
    frame_f2.pack(fill="x", pady=3)
    tk.Label(frame_f2, text="Nombre:", bg=C_FONDO, fg=C_TEXTO, font=("Segoe UI",10), width=10, anchor="w").pack(side=tk.LEFT)
    entry_nombre_cert = tk.Entry(frame_f2, width=25, font=("Arial", 10))
    entry_nombre_cert.pack(side=tk.LEFT, padx=5)
    entry_nombre_cert.insert(0, "Certamen 1")

    # Fila 3
    frame_f3 = tk.Frame(frame_form, bg=C_FONDO)
    frame_f3.pack(fill="x", pady=3)
    tk.Label(frame_f3, text="Fecha:", bg=C_FONDO, fg=C_TEXTO, font=("Segoe UI",10), width=10, anchor="w").pack(side=tk.LEFT)
    entry_fecha_cert = tk.Entry(frame_f3, width=12, font=("Arial", 10), justify="center")
    entry_fecha_cert.pack(side=tk.LEFT, padx=5)
    entry_fecha_cert.insert(0, "DD/MM/AAAA")
    tk.Label(frame_f3, text="(DD/MM/AAAA)", bg=C_FONDO, fg=C_TEXTO_SEC, font=("Segoe UI", 8)).pack(side=tk.LEFT)

    indice_editando = {"val": None}

    def limpiar_form():
        combo_ramo_cert.current(0)
        entry_nombre_cert.delete(0, tk.END)
        entry_nombre_cert.insert(0, "Certamen 1")
        entry_fecha_cert.delete(0, tk.END)
        entry_fecha_cert.insert(0, "DD/MM/AAAA")
        indice_editando["val"] = None
        btn_guardar_cert.config(text="➕ Agregar", bg="#1A7A4A", fg="black")

    def guardar_cert():
        ramo  = combo_ramo_cert.get()
        nombre = entry_nombre_cert.get().strip()
        fecha  = entry_fecha_cert.get().strip()

        if not nombre or fecha == "DD/MM/AAAA":
            messagebox.showerror("Error", "Completa el nombre y la fecha.")
            return
        if dias_restantes(fecha) is None:
            messagebox.showerror("Error", "Fecha inválida. Usa el formato DD/MM/AAAA.")
            return

        data = cargar_certamenes()
        nuevo = {"ramo": ramo, "nombre": nombre, "fecha": fecha}

        if indice_editando["val"] is not None:
            data[indice_editando["val"]] = nuevo
        else:
            data.append(nuevo)

        guardar_certamenes(data)
        refrescar_lista()
        limpiar_form()

    def cargar_en_form(event=None):
        sel = lista_box.curselection()
        if not sel:
            return
        idx = sel[0]
        data = cargar_certamenes()
        # Reordenar igual que refrescar_lista
        def sort_key(c):
            try:
                return datetime.datetime.strptime(c["fecha"], "%d/%m/%Y")
            except Exception:
                return datetime.datetime.max
        data.sort(key=sort_key)
        if idx >= len(data):
            return
        c = data[idx]
        combo_ramo_cert.set(c["ramo"])
        entry_nombre_cert.delete(0, tk.END)
        entry_nombre_cert.insert(0, c["nombre"])
        entry_fecha_cert.delete(0, tk.END)
        entry_fecha_cert.insert(0, c["fecha"])
        indice_editando["val"] = idx
        btn_guardar_cert.config(text="💾  Guardar cambios", bg=C_AZUL_MED, fg="white")

    def eliminar_cert():
        sel = lista_box.curselection()
        if not sel:
            messagebox.showinfo("Info", "Selecciona un certamen para eliminar.")
            return
        idx = sel[0]
        data = cargar_certamenes()
        def sort_key(c):
            try:
                return datetime.datetime.strptime(c["fecha"], "%d/%m/%Y")
            except Exception:
                return datetime.datetime.max
        data.sort(key=sort_key)
        if idx >= len(data):
            return
        confirmado = messagebox.askyesno("Eliminar", f"¿Eliminar '{data[idx]['nombre']}'?")
        if confirmado:
            data.pop(idx)
            guardar_certamenes(data)
            refrescar_lista()
            limpiar_form()

    lista_box.bind("<<ListboxSelect>>", cargar_en_form)

    # --- Botones del formulario ---
    frame_btns_cert = tk.Frame(ventana_cert, bg=C_FONDO)
    frame_btns_cert.pack(pady=8)

    btn_guardar_cert = tk.Button(frame_btns_cert, text="➕  Agregar", command=guardar_cert,
                                  bg="#1A7A4A", fg="white", font=("Segoe UI", 10, "bold"),
                                  relief="flat", padx=14, pady=8, cursor="hand2")
    btn_guardar_cert.pack(side=tk.LEFT, padx=6)

    tk.Button(frame_btns_cert, text="🗑  Eliminar", command=eliminar_cert,
              bg="#C0392B", fg="white", font=("Segoe UI", 10),
              relief="flat", padx=14, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=6)

    tk.Button(frame_btns_cert, text="✖  Cancelar", command=limpiar_form,
              bg=C_AZUL_MED, fg="white", font=("Segoe UI", 10),
              relief="flat", padx=14, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=6)


# ==========================================
# 5D. SALUDO INTELIGENTE AL ABRIR
# ==========================================
FRASES_MOTIVACIONALES = [
    "El éxito es la suma de pequeños esfuerzos repetidos día tras día.",
    "No estudies hasta que puedas hacerlo bien. Estudia hasta que no puedas fallar.",
    "Cada hora que estudias hoy es una pregunta menos que temes mañana.",
    "El conocimiento es el único bien que crece cuando se comparte.",
    "La disciplina es elegir entre lo que quieres ahora y lo que más quieres.",
    "No te compares con nadie más. Cada día sé mejor que el tú de ayer.",
    "Los certámenes no evalúan tu inteligencia, evalúan tu preparación.",
    "Pequeños avances diarios llevan a grandes resultados.",
    "Si estudias cuando tienes ganas, serás del montón. Si estudias cuando no tienes ganas, serás extraordinario.",
    "La USM no es fácil, pero tú tampoco.",
]

def obtener_saludo_dia():
    hora = datetime.datetime.now().hour
    if 5 <= hora < 12:
        return "Buenos días"
    elif 12 <= hora < 19:
        return "Buenas tardes"
    else:
        return "Buenas noches"

def obtener_proximo_certamen():
    """Devuelve el certamen más próximo que aún no ha pasado, o None."""
    certamenes = cargar_certamenes()
    proximos = []
    for c in certamenes:
        dias = dias_restantes(c["fecha"])
        if dias is not None and dias >= 0:
            proximos.append((dias, c))
    if not proximos:
        return None
    proximos.sort(key=lambda x: x[0])
    return proximos[0]

def mostrar_saludo():
    """Muestra ventana de bienvenida con fade-in al abrir BRUNE."""
    ventana_saludo = tk.Toplevel()
    ventana_saludo.title("¡Bienvenido!")
    ventana_saludo.geometry("440x340")
    ventana_saludo.config(bg="#F0EDE6")
    ventana_saludo.resizable(False, False)
    ventana_saludo.overrideredirect(True)  # Sin bordes del sistema

    # Centrar la ventana
    ventana_saludo.update_idletasks()
    x = (ventana_saludo.winfo_screenwidth() // 2) - 220
    y = (ventana_saludo.winfo_screenheight() // 2) - 170
    ventana_saludo.geometry(f"440x340+{x}+{y}")

    # Borde redondeado simulado con frame exterior
    tk.Frame(ventana_saludo, bg="#D6E4F0", bd=0).place(relwidth=1, relheight=1)
    frame_inner = tk.Frame(ventana_saludo, bg="#F0EDE6", bd=0)
    frame_inner.place(relx=0.01, rely=0.01, relwidth=0.98, relheight=0.98)

    # Fade-in: empieza transparente y va apareciendo
    ventana_saludo.attributes("-alpha", 0.0)
    def fade_in(alpha=0.0):
        if alpha < 1.0:
            alpha = round(alpha + 0.07, 2)
            ventana_saludo.attributes("-alpha", alpha)
            ventana_saludo.after(20, lambda: fade_in(alpha))
    ventana_saludo.after(50, fade_in)

    ahora = datetime.datetime.now()
    saludo = obtener_saludo_dia()
    hora_str = ahora.strftime("%H:%M")
    fecha_str = ahora.strftime("%A %d de %B").capitalize()
    frase = random.choice(FRASES_MOTIVACIONALES)

    # Saludo y hora
    tk.Label(frame_inner, text=f"{saludo} 👋",
             bg="#F0EDE6", fg="#1A3A5C", font=("Segoe UI", 22, "bold")).pack(pady=(25, 0))

    tk.Label(frame_inner, text=f"{hora_str}  •  {fecha_str}",
             bg="#F0EDE6", fg="#2E6DA4", font=("Segoe UI", 11)).pack(pady=(5, 15))

    # Separador
    tk.Frame(frame_inner, bg="#D6E4F0", height=1).pack(fill="x", padx=30)

    # Próximo certamen
    proximo = obtener_proximo_certamen()
    if proximo:
        dias, cert = proximo
        if dias == 0:
            texto_cert = f"⚠️  ¡HOY tienes {cert['nombre']} de {cert['ramo']}!"
            color_cert = "#FF4C4C"
        elif dias == 1:
            texto_cert = f"⚠️  ¡Mañana tienes {cert['nombre']} de {cert['ramo']}!"
            color_cert = "#FF4C4C"
        elif dias <= 7:
            texto_cert = f"📅  {cert['nombre']} de {cert['ramo']} en {dias} días ({cert['fecha']})"
            color_cert = "#FFD700"
        else:
            texto_cert = f"📅  {cert['nombre']} de {cert['ramo']} en {dias} días ({cert['fecha']})"
            color_cert = "#1A7A4A"

        tk.Label(frame_inner, text="Próximo certamen:",
                 bg="#F0EDE6", fg="#6B7E91", font=("Segoe UI", 9)).pack(pady=(12, 2))
        tk.Label(frame_inner, text=texto_cert, bg="#F0EDE6", fg=color_cert,
                 font=("Segoe UI", 10, "bold"), wraplength=380).pack(padx=20)
    else:
        tk.Label(frame_inner, text="📅  Sin certámenes próximos registrados",
                 bg="#F0EDE6", fg="#6B7E91", font=("Segoe UI", 10)).pack(pady=(15, 0))

    # Botón cerrar
    def cerrar_saludo():
        ventana_saludo.destroy()
        ventana.deiconify()

    btn_cerrar = tk.Button(frame_inner, text="¡A estudiar! →",
              command=cerrar_saludo,
              bg="#2E6DA4", fg="white",
              font=("Segoe UI", 11, "bold"),
              relief="flat", bd=0, padx=20, pady=10,
              cursor="hand2",
              activebackground="#1A3A5C", activeforeground="white")
    btn_cerrar.pack(pady=15)

    # Leer saludo por voz en hilo separado
    def voz_bienvenida():
        mensaje_voz = f"{saludo}. Bienvenido a BRUNE."
        if proximo:
            dias, cert = proximo
            if dias == 0:
                mensaje_voz += f" Atención: hoy tienes {cert['nombre']} de {cert['ramo']}."
            elif dias == 1:
                mensaje_voz += f" Recuerda que mañana tienes {cert['nombre']} de {cert['ramo']}."
            elif dias <= 7:
                mensaje_voz += f" Te recuerdo que tienes {cert['nombre']} de {cert['ramo']} en {dias} días."
        decir_texto(mensaje_voz)

    threading.Thread(target=voz_bienvenida, daemon=True).start()


# ==========================================
# 5E. COMANDOS DE VOZ — SITIOS Y APPS
# ==========================================

SITIOS_WEB = {
    # Búsqueda y productividad
    "youtube":      "https://www.youtube.com",
    "google":       "https://www.google.com",
    "gmail":        "https://mail.google.com",
    "google drive": "https://drive.google.com",
    "google maps":  "https://maps.google.com",
    "wikipedia":    "https://www.wikipedia.org",
    "wolfram":      "https://www.wolframalpha.com",
    # Estudio USM
    "aula":         "https://aula.usm.cl/portada/index.php",
    "usm":          "https://www.usm.cl",
    "gemini":       "https://gemini.google.com/app",
    # Entretenimiento
    "spotify":      "https://open.spotify.com",
    "reddit":       "https://www.reddit.com",
    "twitch":       "https://www.twitch.tv",
    "netflix":      "https://www.netflix.com",
    # Utilidades
    "github":       "https://www.github.com",
    "chatgpt":      "https://chat.openai.com",
    "traductor":    "https://translate.google.com",
}

APPS_SISTEMA = {
    "calculadora":        "calc.exe",
    "bloc de notas":      "notepad.exe",
    "explorador":         "explorer.exe",
    "archivos":           "explorer.exe",
    "paint":              "mspaint.exe",
    "word":               "winword.exe",
    "excel":              "excel.exe",
    "powerpoint":         "powerpnt.exe",
    "vs code":            "code.exe",
    "spotify app":        r"C:\Users\%USERNAME%\AppData\Roaming\Spotify\Spotify.exe",
    "correo":             "outlookforwindows:",
    "camara":             "microsoft.windows.camera:",
    "reloj":              "ms-clock:",
    "configuracion":      "ms-settings:",
}

def abrir_sitio(nombre_normalizado):
    """Busca si el comando de voz coincide con algún sitio web."""
    for clave, url in SITIOS_WEB.items():
        if normalizar(clave) in nombre_normalizado:
            actualizar_label(f"Abriendo {clave}...")
            hablar_brune(f"Abriendo {clave}")
            webbrowser.open(url)
            return True
    return False

def abrir_app(nombre_normalizado):
    """Busca si el comando de voz coincide con alguna app del sistema."""
    import subprocess
    for clave, exe in APPS_SISTEMA.items():
        if normalizar(clave) in nombre_normalizado:
            actualizar_label(f"Abriendo {clave}...")
            hablar_brune(f"Abriendo {clave}")
            try:
                if exe.endswith(":"):
                    # Protocolo de Windows (ms-settings:, ms-clock:, etc.)
                    os.startfile(exe)
                else:
                    subprocess.Popen(exe, shell=True)
            except Exception as e:
                actualizar_label(f"No pude abrir {clave}.")
                print(f"[BRUNE] Error abriendo app: {e}")
            return True
    return False

# ==========================================
# 5G. CONVERSOR DE UNIDADES
# ==========================================
def abrir_conversor():
    ventana_conv = tk.Toplevel()
    ventana_conv.title("Conversor de Unidades — BRUNE")
    ventana_conv.config(bg=C_FONDO)
    ventana_conv.resizable(False, False)
    ventana_conv.update_idletasks()
    _cx = (ventana_conv.winfo_screenwidth() // 2) - 240
    _cy = (ventana_conv.winfo_screenheight() // 2) - 280
    ventana_conv.geometry(f"480x560+{_cx}+{_cy}")

    # Header
    fh = tk.Frame(ventana_conv, bg=C_AZUL_OSC, height=55)
    fh.pack(fill="x"); fh.pack_propagate(False)
    tk.Label(fh, text="🔢  Conversor de Unidades", bg=C_AZUL_OSC, fg="white",
             font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=18, pady=10)

    CATEGORIAS = {
        "📏 Longitud": {
            "Metro (m)":        1.0,
            "Kilómetro (km)":   1e3,
            "Centímetro (cm)":  1e-2,
            "Milímetro (mm)":   1e-3,
            "Milla (mi)":       1609.344,
            "Pie (ft)":         0.3048,
            "Pulgada (in)":     0.0254,
            "Milla náutica":    1852.0,
        },
        "⚖️ Masa": {
            "Kilogramo (kg)":   1.0,
            "Gramo (g)":        1e-3,
            "Miligramo (mg)":   1e-6,
            "Tonelada (t)":     1e3,
            "Libra (lb)":       0.453592,
            "Onza (oz)":        0.0283495,
        },
        "⏱ Tiempo": {
            "Segundo (s)":      1.0,
            "Minuto (min)":     60.0,
            "Hora (h)":         3600.0,
            "Día":              86400.0,
            "Semana":           604800.0,
            "Milisegundo (ms)": 1e-3,
        },
        "⚡ Energía": {
            "Joule (J)":        1.0,
            "Kilojoule (kJ)":   1e3,
            "Caloría (cal)":    4.184,
            "Kilocaloría (kcal)": 4184.0,
            "Watt-hora (Wh)":   3600.0,
            "eV":               1.60218e-19,
        },
        "💨 Velocidad": {
            "m/s":              1.0,
            "km/h":             1/3.6,
            "mph":              0.44704,
            "Nudo (kn)":        0.514444,
            "ft/s":             0.3048,
        },
        "🌡 Temperatura": {
            "Celsius (°C)":     "celsius",
            "Fahrenheit (°F)":  "fahrenheit",
            "Kelvin (K)":       "kelvin",
        },
        "💪 Fuerza": {
            "Newton (N)":       1.0,
            "Kilonewton (kN)":  1e3,
            "Dina (dyn)":       1e-5,
            "Libra-fuerza (lbf)": 4.44822,
        },
        "📐 Área": {
            "Metro² (m²)":      1.0,
            "Kilómetro² (km²)": 1e6,
            "Centímetro² (cm²)":1e-4,
            "Hectárea (ha)":    1e4,
            "Pie² (ft²)":       0.092903,
        },
        "🧪 Presión": {
            "Pascal (Pa)":      1.0,
            "Kilopascal (kPa)": 1e3,
            "Bar":              1e5,
            "Atmósfera (atm)":  101325.0,
            "mmHg":             133.322,
            "PSI":              6894.76,
        },
        "💡 Potencia": {
            "Watt (W)":         1.0,
            "Kilowatt (kW)":    1e3,
            "Megawatt (MW)":    1e6,
            "Caballo (hp)":     745.7,
        },
    }

    # Selector de categoría
    tk.Label(ventana_conv, text="Categoría:", bg=C_FONDO, fg=C_TEXTO,
             font=("Segoe UI", 10, "bold")).pack(pady=(12, 2))

    var_cat = tk.StringVar()
    combo_cat = ttk.Combobox(ventana_conv, textvariable=var_cat,
                              values=list(CATEGORIAS.keys()),
                              state="readonly", width=30, font=("Segoe UI", 10))
    combo_cat.pack()
    combo_cat.current(0)

    # Frame de conversión
    frame_conv = tk.Frame(ventana_conv, bg=C_FONDO)
    frame_conv.pack(pady=12, padx=30, fill="x")

    # De
    tk.Label(frame_conv, text="De:", bg=C_FONDO, fg=C_TEXTO_SEC,
             font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")
    entry_valor = tk.Entry(frame_conv, font=("Segoe UI", 14), width=12,
                            justify="center", bg=C_CARD,
                            highlightbackground=C_BORDE, highlightthickness=1,
                            relief="flat")
    entry_valor.grid(row=1, column=0, padx=(0,8), ipady=6)
    entry_valor.insert(0, "1")

    var_desde = tk.StringVar()
    combo_desde = ttk.Combobox(frame_conv, textvariable=var_desde,
                                state="readonly", width=18, font=("Segoe UI", 10))
    combo_desde.grid(row=1, column=1, padx=4)

    # Flecha
    tk.Label(frame_conv, text="→", bg=C_FONDO, fg=C_AZUL_MED,
             font=("Segoe UI", 18)).grid(row=1, column=2, padx=8)

    # A
    tk.Label(frame_conv, text="A:", bg=C_FONDO, fg=C_TEXTO_SEC,
             font=("Segoe UI", 9)).grid(row=0, column=3, sticky="w")
    var_hasta = tk.StringVar()
    combo_hasta = ttk.Combobox(frame_conv, textvariable=var_hasta,
                                state="readonly", width=18, font=("Segoe UI", 10))
    combo_hasta.grid(row=1, column=3, padx=4)

    # Resultado
    frame_res = tk.Frame(ventana_conv, bg=C_CARD,
                          highlightbackground=C_BORDE, highlightthickness=1)
    frame_res.pack(fill="x", padx=30, pady=8)

    lbl_resultado_conv = tk.Label(frame_res, text="Ingresa un valor y presiona Convertir",
                                   bg=C_CARD, fg=C_TEXTO_SEC,
                                   font=("Segoe UI", 13), pady=14)
    lbl_resultado_conv.pack()

    # Tabla de referencia rápida
    tk.Label(ventana_conv, text="Referencias rápidas:", bg=C_FONDO, fg=C_AZUL_MED,
             font=("Segoe UI", 10, "bold")).pack(pady=(8,2))

    frame_tabla = tk.Frame(ventana_conv, bg=C_CARD,
                            highlightbackground=C_BORDE, highlightthickness=1)
    frame_tabla.pack(fill="x", padx=30, pady=(0,8))

    lbl_tabla = tk.Label(frame_tabla, text="", bg=C_CARD, fg=C_TEXTO,
                          font=("Segoe UI", 9), justify="left", pady=6, padx=10)
    lbl_tabla.pack(anchor="w")

    def actualizar_unidades(event=None):
        cat = var_cat.get()
        unidades = list(CATEGORIAS[cat].keys())
        combo_desde["values"] = unidades
        combo_hasta["values"] = unidades
        combo_desde.current(0)
        combo_hasta.current(1)
        lbl_resultado_conv.config(text="Ingresa un valor y presiona Convertir",
                                   fg=C_TEXTO_SEC)
        # Tabla de referencias reales: 1 unidad base -> todas las demás
        vals = CATEGORIAS[cat]
        unids = list(vals.keys())
        base_nombre = unids[0]
        refs = []
        for u in unids[1:6]:  # mostrar hasta 5 conversiones
            nombre_base = base_nombre.split("(")[0].strip()
            nombre_dest = u.split("(")[0].strip()
            # Temperatura: casos especiales
            if isinstance(vals.get(base_nombre), str):
                if base_nombre == "Celsius (°C)" and u == "Fahrenheit (°F)":
                    res = 1 * 9/5 + 32
                elif base_nombre == "Celsius (°C)" and u == "Kelvin (K)":
                    res = 1 + 273.15
                else:
                    res = 1.0
            else:
                res = vals[base_nombre] / vals[u]
            if abs(res) >= 1e6 or (abs(res) < 1e-3 and res != 0):
                res_str = f"{res:.3e}"
            else:
                res_str = f"{res:,.4f}".rstrip("0").rstrip(".")
            refs.append(f"  1 {nombre_base} = {res_str} {nombre_dest}")
        lbl_tabla.config(text="\n".join(refs) if refs else "")

    combo_cat.bind("<<ComboboxSelected>>", actualizar_unidades)
    actualizar_unidades()

    def convertir(event=None):
        try:
            valor = float(entry_valor.get().replace(",", "."))
        except ValueError:
            lbl_resultado_conv.config(text="⚠️  Ingresa un número válido", fg="#C0392B")
            return

        cat     = var_cat.get()
        desde   = var_desde.get()
        hasta   = var_hasta.get()
        tabla   = CATEGORIAS[cat]

        # Temperatura: conversión especial
        if tabla.get(desde) == "celsius" or isinstance(tabla.get(desde), str):
            if desde == hasta:
                resultado = valor
            elif desde == "Celsius (°C)" and hasta == "Fahrenheit (°F)":
                resultado = valor * 9/5 + 32
            elif desde == "Celsius (°C)" and hasta == "Kelvin (K)":
                resultado = valor + 273.15
            elif desde == "Fahrenheit (°F)" and hasta == "Celsius (°C)":
                resultado = (valor - 32) * 5/9
            elif desde == "Fahrenheit (°F)" and hasta == "Kelvin (K)":
                resultado = (valor - 32) * 5/9 + 273.15
            elif desde == "Kelvin (K)" and hasta == "Celsius (°C)":
                resultado = valor - 273.15
            elif desde == "Kelvin (K)" and hasta == "Fahrenheit (°F)":
                resultado = (valor - 273.15) * 9/5 + 32
            else:
                resultado = valor
        else:
            # Conversión estándar via unidad base
            en_base = valor * tabla[desde]
            resultado = en_base / tabla[hasta]

        # Formatear resultado
        if abs(resultado) >= 1e6 or (abs(resultado) < 1e-4 and resultado != 0):
            texto_res = f"{resultado:.4e}"
        elif resultado == int(resultado):
            texto_res = f"{int(resultado):,}"
        else:
            texto_res = f"{resultado:,.6f}".rstrip("0").rstrip(".")

        nombre_desde = desde.split("(")[0].strip()
        nombre_hasta = hasta.split("(")[0].strip()
        lbl_resultado_conv.config(
            text=f"{valor:g} {nombre_desde}  =  {texto_res} {nombre_hasta}",
            fg=C_AZUL_OSC, font=("Segoe UI", 14, "bold")
        )

    entry_valor.bind("<Return>", convertir)

    tk.Button(ventana_conv, text="Convertir →", command=convertir,
              bg=C_AZUL_MED, fg="white", font=("Segoe UI", 11, "bold"),
              relief="flat", padx=20, pady=9, cursor="hand2").pack(pady=4)


# ==========================================
# 5H. CONFIGURACIÓN PERSONAL
# ==========================================
ARCHIVO_CONFIG = str(CARPETA_DATOS / "brune_config.json")
ARCHIVO_HISTORIAL = str(CARPETA_DATOS / "brune_historial.json")

CONFIG_DEFAULT = {
    "playlist_spotify": "https://open.spotify.com/playlist/6yW6dYt73WjUJMHqHeMqVv?si=db212514120446a6",
    "links_estudio": [
        {"nombre": "Aula USM",  "url": "https://aula.usm.cl/portada/index.php"},
        {"nombre": "Gemini",    "url": "https://gemini.google.com/app"},
    ],
}

def cargar_config():
    try:
        with open(ARCHIVO_CONFIG, "r", encoding="utf-8") as f:
            datos = json.load(f)
            # Asegurarse que tenga todas las claves (por si se agregan nuevas)
            for k, v in CONFIG_DEFAULT.items():
                if k not in datos:
                    datos[k] = v
            return datos
    except Exception:
        return dict(CONFIG_DEFAULT)

def guardar_config(datos):
    with open(ARCHIVO_CONFIG, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

def abrir_configuracion():
    ventana_cfg = tk.Toplevel()
    ventana_cfg.title("Configuración — BRUNE")
    ventana_cfg.config(bg=C_FONDO)
    ventana_cfg.resizable(False, False)
    ventana_cfg.update_idletasks()
    _cx = (ventana_cfg.winfo_screenwidth() // 2) - 250
    _cy = (ventana_cfg.winfo_screenheight() // 2) - 280
    ventana_cfg.geometry(f"500x620+{_cx}+{_cy}")

    # Header
    fh = tk.Frame(ventana_cfg, bg=C_AZUL_OSC, height=55)
    fh.pack(fill="x"); fh.pack_propagate(False)
    tk.Label(fh, text="⚙️  Configuración Personal", bg=C_AZUL_OSC, fg="white",
             font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=18, pady=10)

    config_actual = cargar_config()

    # ── Sección playlist ──────────────────────────
    tk.Label(ventana_cfg, text="🎵  Playlist de Spotify",
             bg=C_FONDO, fg=C_TEXTO, font=("Segoe UI", 10, "bold"),
             anchor="w").pack(fill="x", padx=25, pady=(15, 2))
    tk.Label(ventana_cfg, text="Se abre automáticamente al iniciar sesión de estudio",
             bg=C_FONDO, fg=C_TEXTO_SEC, font=("Segoe UI", 8),
             anchor="w").pack(fill="x", padx=25)

    entry_spotify = tk.Entry(ventana_cfg, font=("Segoe UI", 9),
                              bg=C_CARD, fg=C_TEXTO, relief="flat",
                              highlightbackground=C_BORDE, highlightthickness=1)
    entry_spotify.pack(fill="x", padx=25, ipady=7, pady=(4, 0))
    entry_spotify.insert(0, config_actual.get("playlist_spotify",
                         CONFIG_DEFAULT["playlist_spotify"]))

    tk.Frame(ventana_cfg, bg=C_BORDE, height=1).pack(fill="x", padx=25, pady=12)

    # ── Sección links de estudio ──────────────────
    tk.Label(ventana_cfg, text="🌐  Links del entorno de estudio",
             bg=C_FONDO, fg=C_TEXTO, font=("Segoe UI", 10, "bold"),
             anchor="w").pack(fill="x", padx=25, pady=(0, 2))
    tk.Label(ventana_cfg,
             text="Se abren automáticamente al abrir cualquier ramo. Agrega o elimina los que quieras.",
             bg=C_FONDO, fg=C_TEXTO_SEC, font=("Segoe UI", 8),
             wraplength=430, justify="left", anchor="w").pack(fill="x", padx=25)

    # Botones SIEMPRE visibles al fondo — se empaquetan ANTES que la lista
    tk.Frame(ventana_cfg, bg=C_BORDE, height=1).pack(fill="x", padx=25, pady=5)

    lbl_estado_cfg = tk.Label(ventana_cfg, text="", bg=C_FONDO,
                               fg="#1A7A4A", font=("Segoe UI", 10, "bold"))
    lbl_estado_cfg.pack(pady=3)

    frame_btns_cfg = tk.Frame(ventana_cfg, bg=C_FONDO)
    frame_btns_cfg.pack(pady=5)

    # Frame scrolleable para los links — ocupa el espacio restante
    frame_links_outer = tk.Frame(ventana_cfg, bg=C_CARD,
                                  highlightbackground=C_BORDE, highlightthickness=1)
    frame_links_outer.pack(fill="both", expand=True, padx=25, pady=(0, 5))

    canvas_links = tk.Canvas(frame_links_outer, bg=C_CARD, highlightthickness=0)
    sb_links = ttk.Scrollbar(frame_links_outer, orient="vertical", command=canvas_links.yview)
    frame_links = tk.Frame(canvas_links, bg=C_CARD)
    frame_links.bind("<Configure>",
        lambda e: canvas_links.configure(scrollregion=canvas_links.bbox("all")))
    canvas_links.create_window((0, 0), window=frame_links, anchor="nw")
    canvas_links.configure(yscrollcommand=sb_links.set)
    canvas_links.pack(side="left", fill="both", expand=True)
    sb_links.pack(side="right", fill="y")

    filas_links = []  # lista de (frame, entry_nombre, entry_url)

    def agregar_fila(nombre="", url=""):
        fila = tk.Frame(frame_links, bg=C_CARD)
        fila.pack(fill="x", padx=8, pady=3)

        e_nombre = tk.Entry(fila, width=14, font=("Segoe UI", 9),
                             bg=C_FONDO, fg=C_TEXTO, relief="flat",
                             highlightbackground=C_BORDE, highlightthickness=1)
        e_nombre.pack(side=tk.LEFT, ipady=5, padx=(0, 4))
        e_nombre.insert(0, nombre)

        e_url = tk.Entry(fila, font=("Segoe UI", 9),
                          bg=C_FONDO, fg=C_TEXTO, relief="flat",
                          highlightbackground=C_BORDE, highlightthickness=1)
        e_url.pack(side=tk.LEFT, fill="x", expand=True, ipady=5, padx=(0, 4))
        e_url.insert(0, url)

        def eliminar():
            fila.destroy()
            filas_links.remove((fila, e_nombre, e_url))

        tk.Button(fila, text="✕", command=eliminar,
                  bg=C_CARD, fg="#C0392B", font=("Arial", 10),
                  relief="flat", cursor="hand2", padx=4).pack(side=tk.LEFT)

        filas_links.append((fila, e_nombre, e_url))

    # Cargar links existentes
    for link in config_actual.get("links_estudio", CONFIG_DEFAULT["links_estudio"]):
        agregar_fila(link.get("nombre", ""), link.get("url", ""))

    # Botón agregar nueva fila
    tk.Button(ventana_cfg, text="➕  Agregar link", command=agregar_fila,
              bg=C_FONDO, fg=C_AZUL_MED, font=("Segoe UI", 9, "bold"),
              relief="flat", cursor="hand2").pack(anchor="w", padx=25, pady=(0, 5))

    # ── Funciones guardar/restaurar ───────────────

    def guardar():
        nueva_config = cargar_config()
        # Spotify
        val = entry_spotify.get().strip()
        nueva_config["playlist_spotify"] = val if val else CONFIG_DEFAULT["playlist_spotify"]
        # Links de estudio
        links = []
        for _, e_nom, e_url in filas_links:
            nom = e_nom.get().strip()
            url = e_url.get().strip()
            if url:
                links.append({"nombre": nom if nom else url, "url": url})
        nueva_config["links_estudio"] = links if links else CONFIG_DEFAULT["links_estudio"]
        guardar_config(nueva_config)
        lbl_estado_cfg.config(text="✅  Guardado correctamente", fg="#1A7A4A")
        hablar_brune("Configuración guardada.")

    def restaurar():
        entry_spotify.delete(0, tk.END)
        entry_spotify.insert(0, CONFIG_DEFAULT["playlist_spotify"])
        for fila, _, _ in list(filas_links):
            fila.destroy()
        filas_links.clear()
        for link in CONFIG_DEFAULT["links_estudio"]:
            agregar_fila(link["nombre"], link["url"])
        lbl_estado_cfg.config(text="↺  Valores restaurados", fg=C_AZUL_MED)

    tk.Button(frame_btns_cfg, text="💾  Guardar", command=guardar,
              bg=C_AZUL_MED, fg="white", font=("Segoe UI", 11, "bold"),
              relief="flat", padx=18, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=8)

    tk.Button(frame_btns_cfg, text="↺  Restaurar defaults", command=restaurar,
              bg=C_FONDO, fg=C_TEXTO_SEC, font=("Segoe UI", 10),
              relief="flat", padx=14, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=8)

# ==========================================
# 5. PROCESAMIENTO DE VOZ PRINCIPAL
# ==========================================



# ==========================================
# ACCIONES Y CEREBRO INTELIGENTE DE BRUNE
# ==========================================

ACCIONES_BRUNE = {
    "abrir_fisica":       lambda: abrir_material("Introducción a la física"),
    "abrir_algebra":      lambda: abrir_material("Álgebra y geometría"),
    "abrir_calculo":      lambda: abrir_material("Introducción al cálculo"),
    "abrir_proyecto":     lambda: abrir_material("Proyecto inicial"),
    "abrir_calculadora":  lambda: ventana.after(0, abrir_calculadora_notas),
    "abrir_chat":         lambda: ventana.after(0, abrir_chat_ia),
    "abrir_pomodoro":     lambda: ventana.after(0, abrir_pomodoro),
    "abrir_certamenes":   lambda: ventana.after(0, abrir_certamenes),
    "abrir_conversor":    lambda: ventana.after(0, abrir_conversor),
    "abrir_youtube":      lambda: webbrowser.open("https://www.youtube.com"),
    "abrir_spotify":      lambda: webbrowser.open("https://open.spotify.com"),
    "abrir_google":       lambda: webbrowser.open("https://www.google.com"),
    "abrir_gmail":        lambda: webbrowser.open("https://mail.google.com"),
    "abrir_drive":        lambda: webbrowser.open("https://drive.google.com"),
    "abrir_wikipedia":    lambda: webbrowser.open("https://www.wikipedia.org"),
    "abrir_wolfram":      lambda: webbrowser.open("https://www.wolframalpha.com"),
    "abrir_aula":         lambda: webbrowser.open("https://aula.usm.cl/portada/index.php"),
    "abrir_traductor":    lambda: webbrowser.open("https://translate.google.com"),
    "abrir_gemini":       lambda: webbrowser.open("https://gemini.google.com/app"),
    "abrir_configuracion": lambda: ventana.after(0, abrir_configuracion),
    "ninguna":            None,
}

def obtener_contexto_brune():
    ahora = datetime.datetime.now()
    hora_str = ahora.strftime("%H:%M")
    fecha_str = ahora.strftime("%d/%m/%Y")
    certamenes = cargar_certamenes()
    proximos = []
    for ce in certamenes:
        dias = dias_restantes(ce["fecha"])
        if dias is not None and dias >= 0:
            proximos.append(ce["nombre"] + " de " + ce["ramo"] + " en " + str(dias) + " dias (" + ce["fecha"] + ")")
    cert_texto = "Certamenes proximos: " + "; ".join(proximos[:3]) if proximos else "Sin certamenes proximos."
    ramo_activo = variable_ramo.get()
    if ramo_activo == "Selecciona el ramo":
        ramo_activo = "ninguno seleccionado"
    acciones_str = ", ".join([k for k in ACCIONES_BRUNE.keys()])
    return (
        "Eres BRUNE, asistente universitario personal, inteligente y cercano para estudiantes de ingenieria de la USM Chile. "
        "Hora actual: " + hora_str + " | Fecha: " + fecha_str + " | "
        "Ramo activo: " + ramo_activo + " | " + cert_texto + " | "
        "Ramos: Fisica FIS100, Algebra MAT060, Calculo MAT070, Proyecto Inicial. "
        "Interpreta lo que dijo el estudiante y responde util, calido y directo. Siempre en espanol. "
        "Si quiere abrir algo o ejecutar una funcion, responde SOLO con este JSON sin markdown: "
        '{"accion": "NOMBRE", "mensaje": "Lo que le diras"} '
        "Acciones disponibles: " + acciones_str + ". "
        "Si es conversacional o requiere respuesta larga, usa ninguna como accion y pon la respuesta en mensaje. "
        "Si el mensaje tiene menos de 150 caracteres se lera en voz alta, si es largo solo se mostrara en pantalla."
    )

def brune_inteligente(texto_original):
    import re as _re
    try:
        contexto = obtener_contexto_brune()
        # Limpiar caracteres especiales para evitar error de codec ASCII
        texto_limpio = texto_original.encode("utf-8", errors="ignore").decode("utf-8")
        prompt = contexto + " El estudiante dijo: " + texto_limpio
        respuesta = cliente_gemini.models.generate_content(
            model=MODELO_GEMINI,
            contents=prompt.encode("utf-8", errors="ignore").decode("utf-8")
        )
        texto_resp = respuesta.text.strip() if respuesta.text else ""
        # Intentar parsear JSON
        json_match = _re.search(r'\{.*?\}', texto_resp, _re.DOTALL)
        if json_match:
            datos = json.loads(json_match.group())
            accion  = datos.get("accion", "ninguna")
            mensaje = datos.get("mensaje", "")
        else:
            accion  = "ninguna"
            mensaje = texto_resp
        # Mostrar siempre en pantalla
        actualizar_label(mensaje)
        # Voz solo si es corto
        if len(mensaje) <= 150:
            hablar_brune(mensaje)
        # Ejecutar accion
        if accion in ACCIONES_BRUNE and ACCIONES_BRUNE[accion]:
            ventana.after(500, ACCIONES_BRUNE[accion])
    except Exception as e:
        print("[BRUNE] Error en brune_inteligente: " + str(e))
        actualizar_label("No entendi bien. Intenta de nuevo.")
        hablar_brune("No entendi bien, puedes repetirlo?")

def despachar_comando(cmd, texto_original=""):
    # Comandos directos instantaneos
    if any(p in cmd for p in ["fisica", "fis100", "abrir fisica", "abre fisica"]):
        abrir_material("Introducción a la física"); return True
    if any(p in cmd for p in ["algebra", "geometria", "mat060", "algebra y geometria"]):
        abrir_material("Álgebra y geometría"); return True
    if any(p in cmd for p in ["calculo", "mat070", "abrir calculo", "introduccion al calculo"]):
        abrir_material("Introducción al cálculo"); return True
    if any(p in cmd for p in ["proyecto inicial", "proyecto", "abrir proyecto"]):
        abrir_material("Proyecto inicial"); return True
    if any(p in cmd for p in ["calculadora", "calcular nota"]):
        hablar_brune("Abriendo calculadora"); ventana.after(0, abrir_calculadora_notas); return True
    if any(p in cmd for p in ["chat", "abrir chat", "inteligencia artificial"]):
        hablar_brune("Abriendo el chat"); ventana.after(0, abrir_chat_ia); return True
    if any(p in cmd for p in ["pomodoro", "temporizador", "timer", "cronometro"]):
        hablar_brune("Abriendo el temporizador de estudio"); ventana.after(0, abrir_pomodoro); return True
    if any(p in cmd for p in ["certamen", "certamenes", "fechas"]):
        hablar_brune("Abriendo certámenes"); ventana.after(0, abrir_certamenes); return True
    if any(p in cmd for p in ["conversor", "convertir unidades"]):
        hablar_brune("Abriendo el conversor"); ventana.after(0, abrir_conversor); return True
    if any(p in cmd for p in ["configuracion", "configurar", "ajustes", "playlist", "cambiar playlist"]):
        hablar_brune("Abriendo configuración"); ventana.after(0, abrir_configuracion); return True
    if any(p in cmd for p in ["modo estudio", "activar estudio", "concentracion"]):
        hablar_brune("Abriendo modo estudio"); ventana.after(0, abrir_modo_estudio); return True
    if cmd.startswith("abrir ") or cmd.startswith("abre "):
        nombre = cmd.replace("abrir ", "").replace("abre ", "").strip()
        if abrir_sitio(nombre): return True
        if abrir_app(nombre): return True
    if abrir_sitio(cmd): return True
    if abrir_app(cmd): return True
    # Si no reconocio nada: Gemini decide
    actualizar_label("Pensando...")
    threading.Thread(target=brune_inteligente, args=(texto_original,), daemon=True).start()
    return True

def grabar_audio(duracion=6, sample_rate=16000):
    """Graba audio del micrófono y lo devuelve como array numpy."""
    actualizar_label("Escuchando... habla ahora 🎙️")
    audio = _sd.rec(
        int(duracion * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32"
    )
    _sd.wait()
    return audio.flatten(), sample_rate

def grabar_con_silencio(sample_rate=16000, umbral=0.015, silencio_max=2.0, duracion_max=12):
    """
    Graba hasta detectar silencio prolongado.
    - umbral bajo: capta voces suaves
    - silencio_max 2s: no corta antes de que termines
    - duracion_max 12s: permite frases largas
    """
    CHUNK = 2048  # chunks mas grandes = menos latencia
    grabando = []
    hablando = False
    segundos_silencio = 0.0
    segundos_espera = 0.0
    espera_max = 5.0  # esperar hasta 5s a que empieces a hablar

    actualizar_label("Escuchando... habla ahora 🎙️")

    with _sd.InputStream(samplerate=sample_rate, channels=1,
                         dtype="float32", blocksize=CHUNK) as stream:
        tiempo_total = 0.0
        while tiempo_total < duracion_max:
            chunk, _ = stream.read(CHUNK)
            chunk_flat = chunk.flatten()
            # RMS para mejor deteccion de volumen
            volumen = _np.sqrt(_np.mean(chunk_flat ** 2))

            if volumen > umbral:
                hablando = True
                segundos_silencio = 0.0
                segundos_espera = 0.0
                grabando.append(chunk_flat)
            elif hablando:
                # Ya estaba hablando, contar silencio
                grabando.append(chunk_flat)
                segundos_silencio += CHUNK / sample_rate
                if segundos_silencio >= silencio_max:
                    break
            else:
                # Aun no empieza a hablar
                segundos_espera += CHUNK / sample_rate
                if segundos_espera >= espera_max:
                    break
            tiempo_total += CHUNK / sample_rate

    if not grabando:
        return None, sample_rate

    return _np.concatenate(grabando), sample_rate

def procesar_voz():
    global escuchando_activo

    # Si Whisper aun se esta cargando, avisar y esperar hasta 60 segundos
    if not _whisper_listo.is_set():
        actualizar_label("⏳ Cargando reconocedor de voz... espera un momento")
        _whisper_listo.wait(timeout=60)

    if _modelo_whisper is None:
        actualizar_label(
            "Reconocedor de voz no disponible. "
            "Ejecuta en terminal: python -c import whisper y load_model base. "
            "Luego reinicia BRUNE."
        )
        hablar_brune("El reconocedor de voz no está listo. Revisa la consola para más información.")
        escuchando_activo = False
        set_boton_microfono(True)
        return

    if not microfono_disponible():
        actualizar_label("No encontré micrófono. Verifica que esté conectado.")
        hablar_brune("No encontré ningún micrófono.")
        escuchando_activo = False
        set_boton_microfono(True)
        return

    try:
        audio_data, sample_rate = grabar_con_silencio()

        if audio_data is None or len(audio_data) < sample_rate * 0.5:
            actualizar_label("No escuché nada. ¿Puedes intentarlo de nuevo?")
            hablar_brune("No escuché nada, intenta de nuevo.")
            escuchando_activo = False
            set_boton_microfono(True)
            return

        actualizar_label("Procesando lo que dijiste...")

        # Transcribir con Whisper — prompt con contexto chileno mejora precision
        PROMPT_CONTEXTO = (
            "Asistente universitario USM Chile. Comandos: fisica, algebra, calculo, "
            "proyecto, calculadora, pomodoro, certamen, chat, conversor, modo estudio, "
            "youtube, spotify, google, aula, drive. Acento chileno."
        )
        resultado = _modelo_whisper.transcribe(
            audio_data,
            language="es",
            fp16=False,
            temperature=0.1,       # pequena flexibilidad para ruido de fondo
            initial_prompt=PROMPT_CONTEXTO,
            condition_on_previous_text=False,  # no se confunde con transcripciones anteriores
            no_speech_threshold=0.5,           # menos falsos positivos de silencio
            compression_ratio_threshold=2.4,   # filtra salidas repetitivas
        )
        texto_reconocido = resultado["text"].strip()

        if not texto_reconocido:
            actualizar_label("No entendí nada. ¿Puedes repetirlo más claro?")
            hablar_brune("No te entendí, ¿puedes repetirlo?")
            escuchando_activo = False
            set_boton_microfono(True)
            return

        actualizar_label(f"Dijiste: '{texto_reconocido}'")
        cmd = normalizar(texto_reconocido)
        despachar_comando(cmd, texto_original=texto_reconocido)

    except Exception as e:
        actualizar_label("Ocurrió un error al procesar tu voz.")
        print(f"[BRUNE] Error en procesar_voz: {type(e).__name__}: {e}")
    finally:
        escuchando_activo = False
        set_boton_microfono(True)

def escuchar_hilo():
    global escuchando_activo
    if escuchando_activo:
        actualizar_label("Ya te estoy escuchando, espera un momento...")
        return
    escuchando_activo = True
    set_boton_microfono(False)
    actualizar_label("Iniciando micrófono...")
    threading.Thread(target=procesar_voz, daemon=True).start()


# ==========================================
# 6. INTERFAZ PRINCIPAL — DISEÑO RENOVADO
# ==========================================

# ── Paleta de colores ──────────────────────
C_FONDO       = "#F0EDE6"   # crema suave
C_CARD        = "#FFFFFF"   # blanco puro para cards
C_AZUL_OSC    = "#1A3A5C"   # azul marino oscuro
C_AZUL_MED    = "#2E6DA4"   # azul medio
C_AZUL_CLAR   = "#5BA3D9"   # azul claro / acento
C_TEXTO       = "#1A2A3A"   # texto principal
C_TEXTO_SEC   = "#6B7E91"   # texto secundario
C_BORDE       = "#D6E4F0"   # borde suave
C_EXITO       = "#1A7A4A"   # verde éxito
C_ALERTA      = "#E74C3C"   # rojo alerta

def boton_moderno(parent, texto, comando, color_bg=None, color_fg="white",
                  ancho=None, alto=None, fuente_size=11, bold=False):
    """Botón con bordes redondeados reales usando Canvas."""
    if color_bg is None:
        color_bg = C_AZUL_MED
    peso = "bold" if bold else "normal"
    fuente_tk = ("Segoe UI", fuente_size, peso)

    # Medir el texto para dimensionar el canvas
    tmp = tk.Label(parent, text=texto, font=fuente_tk)
    tmp.update_idletasks()
    tw = tmp.winfo_reqwidth()
    th = tmp.winfo_reqheight()
    tmp.destroy()

    pad_x, pad_y, radio = 22, 10, 14
    w = max(tw + pad_x * 2, (ancho or 0) * 10)
    h = th + pad_y * 2

    canvas = tk.Canvas(parent, width=w, height=h,
                       bg=parent.cget("bg"), highlightthickness=0, cursor="hand2")

    def dibujar(color):
        canvas.delete("all")
        r = radio
        canvas.create_arc(0, 0, 2*r, 2*r, start=90, extent=90, fill=color, outline=color)
        canvas.create_arc(w-2*r, 0, w, 2*r, start=0, extent=90, fill=color, outline=color)
        canvas.create_arc(0, h-2*r, 2*r, h, start=180, extent=90, fill=color, outline=color)
        canvas.create_arc(w-2*r, h-2*r, w, h, start=270, extent=90, fill=color, outline=color)
        canvas.create_rectangle(r, 0, w-r, h, fill=color, outline=color)
        canvas.create_rectangle(0, r, w, h-r, fill=color, outline=color)
        canvas.create_text(w//2, h//2, text=texto, fill=color_fg, font=fuente_tk)

    dibujar(color_bg)

    hover_color = C_AZUL_OSC if color_bg != C_AZUL_OSC else C_AZUL_MED
    canvas.bind("<Enter>",  lambda e: dibujar(hover_color))
    canvas.bind("<Leave>",  lambda e: dibujar(color_bg))
    canvas.bind("<Button-1>", lambda e: [dibujar(hover_color), canvas.after(100, lambda: dibujar(color_bg)), comando()])

    return canvas

ventana = tk.Tk()
ventana.title("B.R.U.N.E.")
ventana.geometry("680x720")
ventana.config(bg=C_FONDO)
ventana.resizable(False, False)

# ── Estilo ttk global ──────────────────────
estilo = ttk.Style()
estilo.theme_use("clam")
estilo.configure("TCombobox",
    fieldbackground=C_CARD,
    background=C_CARD,
    foreground=C_TEXTO,
    bordercolor=C_BORDE,
    arrowcolor=C_AZUL_MED,
    padding=6,
)
estilo.configure("TProgressbar",
    troughcolor=C_BORDE,
    background=C_AZUL_MED,
    thickness=8,
)

# ── Header ────────────────────────────────
frame_header = tk.Frame(ventana, bg=C_AZUL_OSC, height=90)
frame_header.pack(fill="x")
frame_header.pack_propagate(False)

tk.Label(frame_header, text="B.R.U.N.E.",
         bg=C_AZUL_OSC, fg="white",
         font=("Segoe UI", 28, "bold")).pack(pady=(12, 0))

tk.Label(frame_header,
         text="Buen Rendimiento Universitario, No Excusas",
         bg=C_AZUL_OSC, fg=C_AZUL_CLAR,
         font=("Segoe UI", 10)).pack(pady=(0, 10))

# ── Reloj ─────────────────────────────────
frame_reloj = tk.Frame(ventana, bg=C_AZUL_OSC)
frame_reloj.pack(fill="x")

lbl_reloj = tk.Label(frame_reloj, text="", bg=C_AZUL_OSC, fg=C_AZUL_CLAR,
                      font=("Segoe UI", 11))
lbl_reloj.pack(pady=(2, 4))

def actualizar_reloj():
    ahora = datetime.datetime.now()
    dia_semana = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
    meses = ["enero","febrero","marzo","abril","mayo","junio",
             "julio","agosto","septiembre","octubre","noviembre","diciembre"]
    texto = (f"{dia_semana[ahora.weekday()]} {ahora.day} de "
             f"{meses[ahora.month-1]} {ahora.year}  •  "
             f"{ahora.strftime('%H:%M:%S')}")
    lbl_reloj.config(text=texto)
    ventana.after(1000, actualizar_reloj)

actualizar_reloj()

# ── Botón micrófono ────────────────────────
frame_mic = tk.Frame(ventana, bg=C_FONDO)
frame_mic.pack(pady=(25, 5))

btn_mic = tk.Button(
    frame_mic, text="🎙  HABLAR AHORA",
    command=escuchar_hilo,
    bg=C_AZUL_MED, fg="white",
    font=("Segoe UI", 15, "bold"),
    relief="flat", bd=0,
    padx=30, pady=14,
    cursor="hand2",
    activebackground=C_AZUL_OSC,
    activeforeground="white",
)
btn_mic.pack()

def on_enter_mic(e): btn_mic.config(bg=C_AZUL_OSC)
def on_leave_mic(e): btn_mic.config(bg=C_AZUL_MED)
btn_mic.bind("<Enter>", on_enter_mic)
btn_mic.bind("<Leave>", on_leave_mic)

# ── Selector de ramo ──────────────────────
frame_ramo = tk.Frame(ventana, bg=C_FONDO)
frame_ramo.pack(pady=8)

tk.Label(frame_ramo, text="Ramo:", bg=C_FONDO,
         fg=C_TEXTO_SEC, font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0,8))

variable_ramo = tk.StringVar(ventana)
variable_ramo.set("Selecciona el ramo")
opciones = ["Introducción a la física", "Álgebra y geometría", "Introducción al cálculo", "Proyecto inicial"]
selector = ttk.Combobox(frame_ramo, textvariable=variable_ramo,
                         values=opciones, state="readonly", width=28,
                         font=("Segoe UI", 10))
selector.pack(side=tk.LEFT)

# ── Botón abrir material ──────────────────
frame_material = tk.Frame(ventana, bg=C_FONDO)
frame_material.pack(pady=5)

btn_material = boton_moderno(
    frame_material, "🚀  Preparar ambiente de estudio",
    lambda: abrir_material(variable_ramo.get()),
    color_bg=C_AZUL_CLAR, color_fg="white",
    fuente_size=12, bold=True
)
btn_material.pack()

# ── Separador ─────────────────────────────
tk.Frame(ventana, bg=C_BORDE, height=1).pack(fill="x", padx=40, pady=12)

# ── Pomodoro destacado ────────────────────
frame_pom_dest = tk.Frame(ventana, bg=C_AZUL_OSC,
                           highlightbackground=C_AZUL_CLAR, highlightthickness=2)
frame_pom_dest.pack(fill="x", padx=40, pady=(5, 3))
frame_pom_inner = tk.Frame(frame_pom_dest, bg=C_AZUL_OSC)
frame_pom_inner.pack(pady=8)
tk.Label(frame_pom_inner, text="⏱️  Temporizador de Estudio",
         bg=C_AZUL_OSC, fg="white", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT, padx=(0,15))
btn_pom_dest = tk.Button(frame_pom_inner, text="Abrir Temporizador →",
                          command=abrir_pomodoro, bg=C_AZUL_CLAR, fg="white",
                          font=("Segoe UI", 10, "bold"), relief="flat",
                          padx=12, pady=6, cursor="hand2")
btn_pom_dest.pack(side=tk.LEFT)

# ── Grid de botones secundarios — tamaño uniforme ──
frame_grid = tk.Frame(ventana, bg=C_FONDO)
frame_grid.pack(pady=5)

ANCHO_BTN = 18  # ancho fijo para todos los botones

btn_calc = boton_moderno(frame_grid, "🧮  Calculadora de notas", abrir_calculadora_notas,
                          color_bg=C_AZUL_MED, fuente_size=10, ancho=ANCHO_BTN)
btn_calc.grid(row=0, column=0, padx=6, pady=5)

btn_chat = boton_moderno(frame_grid, "💬  Chat con Brune", abrir_chat_ia,
                          color_bg=C_AZUL_OSC, fuente_size=10, ancho=ANCHO_BTN)
btn_chat.grid(row=0, column=1, padx=6, pady=5)

btn_cert = boton_moderno(frame_grid, "📅  Evaluaciones", abrir_certamenes,
                          color_bg=C_AZUL_MED, fuente_size=10, ancho=ANCHO_BTN)
btn_cert.grid(row=1, column=0, padx=6, pady=5)

btn_conv = boton_moderno(frame_grid, "🔢  Conversor de unidades", abrir_conversor,
                          color_bg=C_AZUL_OSC, fuente_size=10, ancho=ANCHO_BTN)
btn_conv.grid(row=1, column=1, padx=6, pady=5)

frame_grid.grid_columnconfigure(0, weight=1)
frame_grid.grid_columnconfigure(1, weight=1)


# ── Separador + botón config sutil ────────
frame_sep2 = tk.Frame(ventana, bg=C_FONDO)
frame_sep2.pack(fill="x", padx=40, pady=(8, 4))
tk.Frame(frame_sep2, bg=C_BORDE, height=1).pack(fill="x", side=tk.LEFT, expand=True, pady=8)
tk.Button(frame_sep2, text="⚙️ playlist y links",
          command=abrir_configuracion,
          bg=C_FONDO, fg=C_TEXTO_SEC, font=("Segoe UI", 8),
          relief="flat", cursor="hand2", padx=4).pack(side=tk.RIGHT)

# ── Área de estado (scrolleable para respuestas largas) ───
frame_status = tk.Frame(ventana, bg=C_CARD,
                         highlightbackground=C_BORDE, highlightthickness=1)
frame_status.pack(fill="both", expand=True, padx=40, pady=(0, 15))

label_ia = scrolledtext.ScrolledText(
    frame_status,
    wrap=tk.WORD,
    bg=C_CARD, fg=C_TEXTO_SEC,
    font=("Segoe UI", 11),
    relief="flat", bd=0,
    padx=15, pady=12,
    height=5,
    state="disabled",
    cursor="arrow",
)
label_ia.pack(fill="both", expand=True)

# ── Centrar y mostrar ─────────────────────
ventana.update_idletasks()
x = (ventana.winfo_screenwidth() // 2) - 340
y = (ventana.winfo_screenheight() // 2) - 430
ventana.geometry(f"680x720+{x}+{y}")
ventana.withdraw()
ventana.after(300, mostrar_saludo)

ventana.mainloop()
