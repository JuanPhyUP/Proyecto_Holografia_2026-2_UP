#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from PIL import Image, ImageTk
import TFresnel as tf
import matplotlib.pyplot as plt
from matplotlib.image import imsave
import cv2

ruta_holo=""
ruta_recons = "/home/juan/Proyecto_holo/Proyecto_Holografia_2026-2_UP/figures/reconstruccion.bmp"
camara_actual = None
camara_encendida = False

def detectar_camaras():
    camaras = []

    for indice in range(10):
        camara = cv2.VideoCapture(indice)

        if camara.isOpened():
            camaras.append(str(indice))
            camara.release()
    return camaras

def iniciar_camara():
    global camara_actual, camara_encendida

    if camara_actual is not None:
        camara_actual.release()

    indice = int(dispositivos.get())

    camara_actual = cv2.VideoCapture(indice)

    if not camara_actual.isOpened():
        print(f"No se pudo abrir la cámara {indice}")
        camara_actual = None
        camara_encendida = False
        return

    print(f"camara {indice} iniciada")

    camara_encendida= True

    actualizar_camara()


def actualizar_camara():
    global camara_encendida


    if not camara_encendida or camara_actual is None:
        return

    ret, frame = camara_actual.read()

    if ret:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        imagen = Image.fromarray(frame)
        imagen = imagen.resize((400,250))

        imagen_tk = ImageTk.PhotoImage(imagen)

        camara.configure(image=imagen_tk)
        camara.image = imagen_tk

    ventana.after(30, actualizar_camara)


def apagar_camara():
    global camara_actual, camara_encendida

    camara_encendida = False

    if camara_actual is not None:
        camara_actual.release()
        camara_actual = None

    # Volvemos a mostrar la imagen inicial
    camara.configure(image=image_tk1)
    camara.image = image_tk1
    print("Cámara apagada")



def mostrar_img_holo(ruta):
    for widget in holograma_frame.winfo_children():
        widget.destroy()

    image_pil2 = Image.open(ruta)
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
    holograma.image = image_tk2



def abrir_holograma():
    global ruta_holo
    ruta_holo = filedialog.askopenfilename(
        title="Selecciona una imagen",
        filetypes=[
            ("Imágenes","*.png *.jpg *.jpeg *.bmp"),
            ("Todos los archivos","*.*")
        ]
    )
    mostrar_img_holo(ruta_holo)


def mostrar_img_recons(ruta):
    for widget in reconstruccion_frame.winfo_children():
        widget.destroy()

    image_pil3 = Image.open(ruta)
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

    reconstruccion.image = image_tk3

def Apli_transF(dx,dy,λ,z):
    m_trans = tf.TFresnel(ruta_holo,1,λ*1e-9,dx*1e-6,dy*1e-6,z*1e-2)

    imsave(
        ruta_recons,
        m_trans,
        cmap="gray"
    )

    mostrar_img_recons(ruta_recons)

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
    text="Cámara off",
    command = apagar_camara
).pack(
    padx=10,
    pady=(1,1)
)

tk.Button(
    panel_derecho,
    text="Cámara on",
    command = lambda : iniciar_camara()
    ).pack(
        padx=10,
        pady=(1,1)
    )

tk.Label(
    panel_derecho,
    text="Dispositivos IDs"
).pack(
    anchor="w",
    padx=10,
    pady=(1,1)
)

dispositivos= ttk.Combobox(
    panel_derecho,
    state = "readonly"
)


dispositivos.pack(
    fill="x",
    padx=10,
    pady=1
)

camaras = detectar_camaras()

if camaras:
    dispositivos["values"] = camaras
    dispositivos.current(0)
    dispositivos.bind("<<ComboboxSelected>>", lambda event: iniciar_camara())

    iniciar_camara()
else:
    dispositivos["values"] = ["No hay cámaras"]
    dispositivos.current(0)
# Formato

tk.Label(
    panel_derecho,
    text="Formato:"
).pack(
    padx=10,
    pady=(1,1)
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
    pady=1
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
    pady=1
)

tk.Button(
    roi,
    text="ROI"
).grid(rowspan=2,column=0,padx=5)

modo2 = tk.StringVar(value="CAM")

tk.Radiobutton(
    roi,
    text="CAM",
    variable=modo2,
    value="CAM"
).grid(row=0,column=1,padx=2)

tk.Radiobutton(
    roi,
    text="HOL",
    variable=modo2,
    value="HOL"
).grid(row=1, column=1,padx=2)

# Parámetros

parametros = tk.LabelFrame(
    panel_derecho,
    text="Parámetros"
)

parametros.pack(
    fill="x",
    padx=10,
    pady=1
)

tk.Label(
    parametros,
    text="δx:"
).grid(row=0,column=0,padx=5,pady=1)

dx = tk.Entry(
    parametros,
    width=8
)

dx.grid(row=0, column=1, padx=5)

tk.Label(
    parametros,
    text="µm"
).grid(row=0, column=2, padx=5)


tk.Label(
    parametros,
    text="δy:"
).grid(row=1,column=0,padx=5,pady=1)

dy = tk.Entry(
    parametros,
    width=8
)
dy.grid(row=1, column=1, padx=5)

tk.Label(
    parametros,
    text="µm"
).grid(row=1, column=2, padx=5)

tk.Label(
    parametros,
    text="λ:"
).grid(row=2,column=0,padx=5,pady=1)

λ= tk.Entry(
    parametros,
    width=8
)
λ.grid(row=2, column=1, padx=5)

tk.Label(
    parametros,
    text="nm"
).grid(row=2, column=2, padx=5)

tk.Label(
    parametros,
    text="z:"
).grid(row=3,column=0,padx=5,pady=1)

z= tk.Entry(
    parametros,
    width=8
    )

z.grid(row=3, column=1, padx=5)

tk.Label(
    parametros,
    text="cm"
).grid(row=3, column=2, padx=5)


#Botones

botones = tk.Frame(
    panel_derecho,
    relief = "sunken",
    borderwidth=1
)

botones.pack(
    fill="x",
    padx=10,
    pady=5
)

tk.Button(
    botones,
    text="Foto"
).grid(row=0,column=0,padx=5)

tk.Button(
    botones,
    text="Vídeo"
).grid(row=0,column=1,padx=5)

tk.Entry(
    botones,
    width=4
).grid(row=0,column=2,padx=5)

tk.Button(
    botones,
    text="Fresnel",
    width=19,
    command = lambda : Apli_transF(float(dx.get()),float(dy.get()),float(λ.get()),float(z.get()))
).grid(row=1,columnspan=3,padx=5)

filtro_tipo = ttk.Combobox(
    botones,
    values=[
        "Filtro 1",
        "Filtro 2",
        "Filtro 3"
    ],
    state = "readonly",
    width=20
)

filtro_tipo.current(0)

filtro_tipo.grid(
    row=2,
    columnspan=3,
    padx=5
)

frame_final = tk.Frame(
    panel_derecho,
    relief = "sunken",
    borderwidth=1
)

frame_final.pack(
    fill="x",
    padx=10,
    pady=1
)

tk.Button(
    frame_final,
    text="Abrir Holograma",
    command = abrir_holograma
).grid(row=0,padx=40)

tk.Button(
    frame_final,
    text="Guardar",
    width=13
).grid(row=1, padx=40)

escudo = Image.open(
    "/home/juan/Proyecto_holo/Proyecto_Holografia_2026-2_UP/figures/escudounipamplona.png"
)

escudo = escudo.resize((50, 50))

escudo_tk = ImageTk.PhotoImage(escudo)

imagen_escudo = tk.Label(
    frame_final,
    image=escudo_tk
)

imagen_escudo.grid(
    row=2,
    column=0,
    padx=40,
    pady=10
)

ventana.mainloop()
