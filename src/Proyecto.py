#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk


# Crear la ventana principal
ventana = tk.Tk()
ventana.title("HDFresnel_GOM")
ventana.geometry("1200x700")
ventana.resizable(False,False)

barra_menu = tk.Menu(ventana)

menu_archivo = tk.Menu(barra_menu, tearoff=0)
menu_archivo.add_command(label="Abrir")
menu_archivo.add_command(label="Guardar")
menu_archivo.add_separator()
menu_archivo.add_command(label="Salir", command=ventana.destroy)

barra_menu.add_cascade(label="Archivo", menu=menu_archivo)

menu_herramientas = tk.Menu(barra_menu, tearoff=0)
menu_herramientas.add_command(label="Configuración")

barra_menu.add_cascade(
    label="Herramientas",
    menu=menu_herramientas
)

menu_ayuda = tk.Menu(barra_menu,tearoff=0)
menu_ayuda.add_command(label="Acerca de")

barra_menu.add_cascade(
    label= "Ayuda",
    menu=menu_ayuda
)

ventana.config(menu=barra_menu)

barra_herramientas = tk.Frame(
    ventana,
    bg='#eeeeee',
    height=35,
)

barra_herramientas.grid(
    row=0,
    column=0,
    sticky="eew"
)

tk.Button(
    barra_herramientas,
    text="📁"
).pack(side="left", padx=3)

tk.Button(
    barra_herramientas,
    text="💾"
).pack(side="left", padx=3)

tk.Button(
    barra_herramientas,
    text="🔍"
).pack(side="left",padx=3)

contenido = tk.Frame(ventana)

contenido.grid(
    row=1,
    column=0,
    padx=10,
    pady=10
)

ventana.rowconfigure(1,weight=1)
ventana.columnconfigure(0,weight=1)

contenido.rowconfigure(0,weight=1)


contenido.columnconfigure(0,weight=1)
contenido.columnconfigure(1,weight=0)


panel_izquierdo = tk.Frame(
    contenido,
    relief = "sunken",
    borderwidth=1
)

panel_izquierdo.grid(
    row=0,
    column=0,
    sticky="nsew",
    padx=(0,10)
)

panel_izquierdo.rowconfigure(0,weight=1)
panel_izquierdo.rowconfigure(1, weight=1)
panel_izquierdo.columnconfigure(0, weight=1)
panel_izquierdo.columnconfigure(1, weight=1)

# Cuadro 1

camara_frame = tk.LabelFrame(
    panel_izquierdo,
    text="CÁMARA"
)

camara_frame.grid(
    row=0,
    column=0,sticky="nsew",
    padx=5,
    pady=5
)

camara_frame.rowconfigure(0, weight=1)
camara_frame.columnconfigure(0, weight=1)

image_pil1 = Image.open("/home/juan/Proyecto_holo/Proyecto_Holografia_2026-2_UP/figures/profile.jpg")
image_pil1=image_pil1.resize((400,250))
image_tk1 = ImageTk.PhotoImage(image_pil1)

camara = tk.Label(
    camara_frame,
    image=image_tk1
)

camara.grid(
    row=0,
    column=0,
    sticky="nsew",
    padx=10,
    pady=10
)



# Cuadro 2

holograma_frame = tk.LabelFrame(
    panel_izquierdo,
    text="HOLOGRAMA"
)

holograma_frame.grid(
    row=0,
    column=1,
    sticky="nsew",
    padx=5,
    pady=5
)

holograma_frame.rowconfigure(0,weight=1)
holograma_frame.columnconfigure(0,weight=1)

image_pil2 = Image.open("/home/juan/Proyecto_holo/Proyecto_Holografia_2026-2_UP/figures/Holograma.bmp")
image_pil2 = image_pil2.resize((400,250))
image_tk2 = ImageTk.PhotoImage(image_pil2)

holograma= tk.Label(
    holograma_frame,
    image = image_tk2
    
)

holograma.grid(
    row=0,
    column=0,
    sticky="nsew",
    padx=10,
    pady=10
)

# Cuadro 3

reconstruccion_frame = tk.LabelFrame(
    panel_izquierdo,
    text="RECONSTRUCCIÓN"
)

reconstruccion_frame.grid(
    row=1,
    column=0,
    sticky="nsew",
    padx=5,
    pady=5
)

reconstruccion_frame.rowconfigure(0,weight=1)
reconstruccion_frame.columnconfigure(0,weight=1)

image_pil3 = Image.open("/home/juan/Proyecto_holo/Proyecto_Holografia_2026-2_UP/figures/Transformada_de_Fresnel.bmp")
image_pil3 = image_pil3.resize((400,250))
image_tk3 = ImageTk.PhotoImage(image_pil3)

reconstruccion = tk.Label(
    reconstruccion_frame,
    image = image_tk3
)

reconstruccion.grid(
    row=0,
    column=0,
    sticky="nsew",
    padx=10,
    pady=10
)

# Cuadro 4

filtrado_frame= tk.LabelFrame(
    panel_izquierdo,
    text="RECONSTRUCCIÓN FILTRADA"
)

filtrado_frame.grid(
    row=1,
    column=1,
    sticky="nsew",
    padx=5,
    pady=5
)

filtrado_frame.rowconfigure(0,weight=1)
filtrado_frame.columnconfigure(0,weight=1)

image_pil4 = Image.open("/home/juan/Proyecto_holo/Proyecto_Holografia_2026-2_UP/figures/Transformada_de_Fresnel_Filtrado.bmp")
image_pil4 = image_pil4.resize((400,250))
image_tk4 = ImageTk.PhotoImage(image_pil4)

filtrado = tk.Label(
    filtrado_frame,
    image = image_tk4
)

filtrado.grid(
    row=0,
    column=0,
    sticky="nsew",
    padx=10,
    pady=10
)

#Panel Derecho

panel_derecho = tk.LabelFrame(
    contenido,
    text="CONTROLES",
    width=220
)

panel_derecho.grid(
    row=0,
    column=1,
    sticky="ns"
)

panel_derecho.grid_propagate(False)


# Controles

tk.Button(
    panel_derecho,
    text="Cámara off"
).pack(
    padx=10,
    pady=(5,5)
)

tk.Label(
    panel_derecho,
    text="Dispositivos IDs"
).pack(
    anchor="w",
    padx=10,
    pady=(5,5)
)

dispositivos= ttk.Combobox(
    panel_derecho,
    values=["1","2","3"],
    state = "readonly"
)

dispositivos.current(0)

dispositivos.pack(
    fill="x",
    padx=10,
    pady=5
)


# Formato

tk.Label(
    panel_derecho,
    text="Formato:"
).pack(
    padx=10,
    pady=(5,5)
)


formatos = ttk.Combobox(
    panel_derecho,
    values=[
        "RGB24_1280x720",
        "RGB24_640x480",
        "GRAY8_1280x720"
    ],
    state = "readonly"
)

formatos.current(0)

formatos.pack(
    fill="x",
    padx=10
)

# CPU / GPU

procesador = tk.LabelFrame(
    panel_derecho,
    text = "Procesamiento"
)

procesador.pack(
    fill="x",
    padx=10,
    pady=10
)

modo = tk.StringVar(value="CPU")

tk.Radiobutton(
    procesador,
    text="CPU",
    variable=modo,
    value="CPU"
).pack(side="left")


tk.Radiobutton(
    procesador,
    text="GPU",
    variable=modo,
    value="GPU"
).pack(side="right")

# ROI

roi = tk.Frame(
    panel_derecho,
    relief = "sunken",
    borderwidth=1
)

roi.pack(
    fill="x",
    padx=10,
    pady=10
)

tk.Button(
    roi,
    text="ROI"
).pack(side="left", padx=5,pady=5)

modo2 = tk.StringVar(value="CAM")

tk.Radiobutton(
    roi,
    text="CAM",
    variable=modo2,
    value="CAM"
).pack(side="top")

tk.Radiobutton(
    roi,
    text="HOL",
    variable=modo2,
    value="HOL"
).pack(side="bottom")




ventana.mainloop()
