#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from PIL import Image, ImageTk
import TFresnel as tf
import matplotlib.pyplot as plt
from matplotlib.image import imsave
import cv2
from pathlib import Path
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
FIGURES_DIR = BASE_DIR / "figures"
DATA_DIR = BASE_DIR / "data"

ruta_holo=""
ruta_recons = FIGURES_DIR / "reconstruccion.bmp"
camara_actual = None
camara_encendida = False

#datos actualizados por el filtro_tipo

hologtama_actual = None
transformada_holo = None
mascara_roi = None
roi_canvas = None
roi_image_tk = None
roi_inicio = None
roi_ventana = None  # ventana aparte para seleccionar el ROI (ya no pisa el holograma)

parametros_fresnel = None

def TFresnel_array(imagen, Onda_ref,Lambda,deltax0,deltay0,Z0):
    if imagen.ndim != 2:
        raise ValueError("El holograma debe ser una matriz 2D")

    N,M = imagen.shape

    x = np.arange(-M // 2, M // 2)
    y = np.arange(-N / 2, N / 2)

    X, Y = np.meshgrid(x, y)

    r1 = (
        (X * (Lambda * Z0) / (M * deltax0)) ** 2
        + (Y * (Lambda * Z0) / (N * deltay0)) ** 2
    )

    P = (
        (1 / (1j * Lambda * Z0))
        * np.exp(1j * 2 * np.pi * Z0 / Lambda)
        * np.exp((1j * np.pi / (Lambda * Z0)) * r1)
    )

    r2 = (X * deltax0) ** 2 + (Y * deltay0) ** 2
    H = np.exp((1j * np.pi / (Lambda * Z0)) * r2)

    TFresnel = P * np.fft.fftshift(
        np.fft.ifft2(imagen * Onda_ref * H)
    )

    maximo = np.max(np.abs(TFresnel))
    if maximo > 0:
        TFresnel = TFresnel / maximo

    TFresnel = np.abs(TFresnel)

    maximo = np.max(TFresnel)
    if maximo > 0:
        TFresnel = TFresnel / maximo

    TFresnel = TFresnel ** 0.25

    return TFresnel


def detectar_camaras():
    camaras = []

    for indice in range(10):
        camara = cv2.VideoCapture(indice,cv2.CAP_V4L2)

        if camara.isOpened():
            ret, frame = camara.read()

            if ret:
                camaras.append(str(indice))

            camara.release()

    return camaras


def iniciar_camara():
    global camara_actual, camara_encendida

    if camara_actual is not None:
        camara_actual.release()
        camara_actual = None

    try:
        indice = int(dispositivos.get())
    except ValueError:
        print("No hay cámara seleccionada")
        return

    camara_actual = cv2.VideoCapture(indice,cv2.CAP_V4L2)

    if not camara_actual.isOpened():
        print(f"No se pudo abrir la cámara {indice}")
        camara_actual = None
        camara_encendida = False

        camara.configure(image=image_tk1)
        camara.image = image_tk1
        return

    ret, frame = camara_actual.read()

    if not ret:
        print(f"La cámara {indice} fue detectada pero no entrega imágenes")

        camara_actual.release()
        camara_actual = None
        camara_encendida = False

        camara.configure(image=image_tk1)
        camara.image = image_tk1
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

def roi_inicio_evento(event):
    global roi_inicio

    roi_inicio = (event.x,event.y)

    roi_canvas.delete("roi")


def roi_movimiento_evento(event):
    if roi_inicio is None:
        return

    x0,y0 = roi_inicio
    x1,y1 = event.x,event.y 

    roi_canvas.delete("roi")

    roi_canvas.create_rectangle(
        x0,
        y0,
        x1,
        y1,
        outline="red",
        width=2,
        tags="roi"
    )


def roi_fin_evento(event):
    global mascara_roi, roi_inicio
    if roi_inicio is None:
        return 

    x0,y0 = roi_inicio 
    x1,y1 = event.x,event.y 

    x_min = min(x0,x1)
    x_max = max(x0,x1)

    y_min = min(y0,y1)
    y_max = max(y0,y1)

    if x_max - x_min < 2 or y_max - y_min < 2:
        print("ROI demasiado pequeña")
        roi_inicio = None
        return

    filas, columnas = transformada_holo.shape

    mascara_roi = np.zeros(
        (filas,columnas),
        dtype = np.float64
    )

    escala_x = columnas/400
    escala_y = filas/250

    ix_min = int(x_min*escala_x)
    ix_max = int(x_max * escala_x)

    iy_min = int(y_min * escala_y)
    iy_max = int(y_max * escala_y)

    # Limitar coordenadas
    ix_min = max(0, min(columnas, ix_min))
    ix_max = max(0, min(columnas, ix_max))

    iy_min = max(0, min(filas, iy_min))
    iy_max = max(0, min(filas, iy_max))

    mascara_roi[
        iy_min:iy_max,
        ix_min:ix_max
    ] = 1

    print(
        f"ROI seleccionada: "
        f"x={ix_min}:{ix_max}, "
        f"y={iy_min}:{iy_max}"
    )

    aplicar_filtro_1()

    roi_inicio = None


def aplicar_filtro_1():
    if transformada_holo is None:
        print("No existe transformada de Fourier")
        return

    if mascara_roi is None:
        print("No existe una ROI")
        return 

    NF = transformada_holo*mascara_roi

    holograma_filtrado = np.fft.ifft2(NF)

    dx = parametros_fresnel["dx"]
    dy = parametros_fresnel["dy"]
    λ = parametros_fresnel["lambda"]
    z = parametros_fresnel["z"]

    reconstruccion_filtrada = TFresnel_array(
        holograma_filtrado,
        1,
        λ,
        dx,
        dy,
        z
    )

    mostrar_img_array(
        filtrado_frame,
        reconstruccion_filtrada
    )
    

def iniciar_filtro_1():
    global roi_canvas
    global roi_image_tk
    global roi_inicio
    global roi_ventana

    if transformada_holo is None:
        print("Primero debe ejecutar Fresnel")
        return

    roi_inicio = None

    espectro = np.log1p(np.abs(transformada_holo))
    # Normalizacion

    espectro = cv2.normalize(
        espectro,
        None,
        0,
        255,
        cv2.NORM_MINMAX
    )

    espectro = espectro.astype(np.uint8)

    imagen = Image.fromarray(espectro)

    imagen = imagen.resize((400,250))

    roi_image_tk = ImageTk.PhotoImage(imagen)

    # Cerramos una ventana de ROI anterior si quedó abierta, en vez de
    # destruir el contenido de holograma_frame (eso era lo que borraba
    # la imagen del holograma).
    if roi_ventana is not None:
        try:
            if roi_ventana.winfo_exists():
                roi_ventana.destroy()
        except tk.TclError:
            pass

    roi_ventana = tk.Toplevel(ventana)
    roi_ventana.title("Seleccione la región del espectro (ROI)")
    roi_ventana.resizable(False, False)

    roi_canvas = tk.Canvas(
        roi_ventana,
        width=400,
        height=250,
        highlightthickness=0
    )

    roi_canvas.pack(
        padx=10,
        pady=10
    )

    roi_canvas.create_image(
        0,
        0,
        anchor="nw",
        image=roi_image_tk
    )

    roi_canvas.bind(
        "<ButtonPress-1>",
        roi_inicio_evento
    )

    roi_canvas.bind(
        "<B1-Motion>",
        roi_movimiento_evento
    )

    roi_canvas.bind(
        "<ButtonRelease-1>",
        roi_fin_evento
    )

    print("Seleccione con el mouse la región del espectro que desea conservar.")


def Apli_transF(dx,dy,λ,z):
    global holograma_actual
    global transformada_holo
    global parametros_fresnel
    global mascara_roi


    if not ruta_holo:
        print("No hay ningún holograma cargado")
        return

    holograma_actual = cv2.imread(
        str(ruta_holo),
        cv2.IMREAD_GRAYSCALE
    )

    if holograma_actual is None:
        print("No se pudo leer el holograma")
        return

    holograma_actual = holograma_actual.astype(np.float64)

    holograma_actual -= np.mean(holograma_actual)

    transformada_holo = np.fft.fftshift(
        np.fft.fft2(holograma_actual)
    )


    parametros_fresnel = {
        "dx":dx*1e-6,
        "dy":dy*1e-6,
        "lambda":λ*1e-9,
        "z":z*1e-2
    }


    m_trans = tf.TFresnel(
        ruta_holo,
        1,
        λ*1e-9,
        dx*1e-6,
        dy*1e-6,
        z*1e-2
    )

    imsave(
        str(ruta_recons),
        m_trans,
        cmap="gray"
    )

    mostrar_img_recons(ruta_recons)

    mascara_roi = None

    if filtro_tipo.get() == "Filtro 1":
        iniciar_filtro_1()


def cambiar_filtro(event=None):
    filtro=filtro_tipo.get()

    if filtro == "Filtro 1":

        if transformada_holo is None:
            print("Primero debe ejecutar Fresnel")
            return 

        iniciar_filtro_1()
    elif filtro == "Filtro 2":
        print("Filtro 2 toadavía no implementado")
    elif filtro == "Filtro 3":
        print("Filtro 3 todavía no implementado")


def mostrar_img_array(frame, imagen):
    """Muestra un array 2D (ya normalizado en [0,1], p.ej. salida de
    TFresnel_array) como imagen dentro de `frame`. No vuelve a aplicar
    corrección gamma porque TFresnel_array ya la aplica; hacerlo de nuevo
    saturaba/lavaba la imagen filtrada."""

    for widget in frame.winfo_children():
        widget.destroy()

    imagen = np.abs(imagen)

    maximo = np.max(imagen)

    if maximo > 0:
        imagen = imagen / maximo

    imagen = (imagen * 255).clip(0, 255).astype(np.uint8)

    imagen_pil = Image.fromarray(imagen)

    imagen_pil = imagen_pil.resize((400, 250))

    imagen_tk = ImageTk.PhotoImage(imagen_pil)

    etiqueta = tk.Label(
        frame,
        image=imagen_tk
    )

    etiqueta.grid(
        row=0,
        column=0,
        sticky="nsew",
        padx=10,
        pady=10
    )

    etiqueta.image = imagen_tk




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

image_pil1 = Image.open(FIGURES_DIR/"profile.jpg")
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
    text="ROI",
    command = iniciar_filtro_1
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

filtro_tipo.bind(
    "<<ComboboxSelected>>",
    cambiar_filtro
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
    FIGURES_DIR/"escudounipamplona.png"
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