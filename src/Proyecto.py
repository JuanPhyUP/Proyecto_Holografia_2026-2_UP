#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
from PIL import Image, ImageTk
import TFresnel as tf
import matplotlib.pyplot as plt
from matplotlib.image import imsave
import cv2
from pathlib import Path
import numpy as np
import traceback
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
FIGURES_DIR = BASE_DIR / "figures"
DATA_DIR = BASE_DIR / "data"
VIDEOS_DIR = BASE_DIR / "videos"

ruta_holo=""
ruta_recons = FIGURES_DIR / "reconstruccion.bmp"
camara_actual = None
camara_encendida = False

#datos actualizados por el filtro_tipo

hologtama_actual = None
transformada_holo = None  # FFT del holograma completo (reservada para futuros Filtro 2/3)
ultima_reconstruccion_completa = None  # reconstrucción completa sin filtrar (uint8), tal como se ve en RECONSTRUCCIÓN
reconstruccion_filtrada_actual = None  # resultado del Filtro 1 sobre TODA la imagen, uint8; el ROI recorta de aquí
roi_canvas = None
roi_image_tk = None
roi_inicio = None
roi_ventana = None  # ventana aparte para seleccionar el ROI (ya no pisa el holograma)

parametros_fresnel = None

# Nombres de los filtros (única fuente de verdad)
FILTRO_PASO_BANDA = "Paso banda (ROI)"        # antes Filtro 1
FILTRO_PLANO = "Plano (sin filtro)"           # antes Filtro 2
FILTRO_LAPLACIANO = "Laplaciano"              # antes Filtro 3
FILTRO_PASO_ALTO = "Paso alto (ROI)"          # antes Filtro 4
FILTROS_CON_ROI = (FILTRO_PASO_BANDA, FILTRO_PASO_ALTO)

# --- Estado para Foto / Vídeo / Guardar ---
ultimo_frame_camara = None          # último frame BGR entregado por la cámara (sin redimensionar)
entrada_frames = None                # Entry con el número de frames a capturar (equivale a 'Frames' del original)
modo_lote = False                    # True durante la grabación de vídeo: evita abrir ventanas de ROI en cada frame
sesion_video = None                  # estado de captura manual de fotogramas

# --- Estado para el botón ROI + radios CAM/HOL (recorte PREVIO al
# procesamiento, distinto del ROI de Filtro 1/4) ---
roi_captura_activo = False
recorte_cam = None       # (ix_min, ix_max, iy_min, iy_max) en píxeles de la cámara, o None
recorte_hol = None       # (ix_min, ix_max, iy_min, iy_max) en píxeles del holograma, o None
ruta_holo_sin_recortar = None  # ruta original del holograma, para restaurar al apagar el ROI en modo HOL
roi_captura_canvas = None
roi_captura_image_tk = None
roi_captura_inicio = None
roi_captura_ventana = None

# Guarda referencia a la última imagen calculada (reconstrucción o filtrada)
# para que "Guardar" sepa qué exportar sin volver a pedirlo.
ultima_imagen_guardable = {"tipo": None, "valor": None}  # tipo: "archivo" | "array"


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
    global camara_encendida, ultimo_frame_camara

    if not camara_encendida or camara_actual is None:
        return

    ret, frame = camara_actual.read()

    if ret:
        # Si hay un recorte de captura activo (botón ROI en modo CAM),
        # se aplica aquí antes de mostrar o de usar el frame para nada.
        if recorte_cam is not None:
            ix_min, ix_max, iy_min, iy_max = recorte_cam
            frame = frame[iy_min:iy_max, ix_min:ix_max]

        # Guardamos el frame (ya recortado si aplica) para Foto/Vídeo,
        # antes de redimensionar para la vista previa.
        ultimo_frame_camara = frame.copy()

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        imagen = Image.fromarray(frame_rgb)
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
    ruta_seleccionada = filedialog.askopenfilename(
        title="Selecciona una imagen",
        filetypes=[
            ("Imágenes","*.png *.jpg *.jpeg *.bmp"),
            ("Todos los archivos","*.*")
        ]
    )

    if not ruta_seleccionada:
        # El usuario canceló el diálogo: no tocamos el holograma actual.
        return

    ruta_holo = ruta_seleccionada
    mostrar_img_holo(ruta_holo)


def mostrar_img_recons(ruta):
    global ultima_imagen_guardable

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

    # Esta reconstrucción queda como la última imagen exportable
    # hasta que se calcule un filtro sobre ella.
    ultima_imagen_guardable = {"tipo": "archivo", "valor": Path(ruta)}


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
    global roi_inicio

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

    if filtro_tipo.get() in FILTROS_CON_ROI:
        # Fiel al original: para Filtro 1/4, el rectángulo dibujado AQUÍ
        # es el propio mecanismo del filtro (se reutiliza como máscara
        # sobre el espectro del holograma). Se opera en la resolución
        # completa del holograma, no en la del resultado filtrado.
        if holograma_actual is None or parametros_fresnel is None:
            print("Primero debe ejecutar Fresnel")
            roi_inicio = None
            return

        filas, columnas = holograma_actual.shape

        escala_x = columnas/400
        escala_y = filas/250

        ix_min = max(0, min(columnas, int(x_min*escala_x)))
        ix_max = max(0, min(columnas, int(x_max*escala_x)))
        iy_min = max(0, min(filas, int(y_min*escala_y)))
        iy_max = max(0, min(filas, int(y_max*escala_y)))

        print(
            f"ROI ({filtro_tipo.get()}) seleccionada: "
            f"x={ix_min}:{ix_max}, y={iy_min}:{iy_max}"
        )

        try:
            if filtro_tipo.get() == FILTRO_PASO_BANDA:
                filtro_1_roi(ix_min, ix_max, iy_min, iy_max)
            else:
                filtro_4_highpass(ix_min, ix_max, iy_min, iy_max)
        except Exception as error:
            detalle = traceback.format_exc()
            print(detalle)
            messagebox.showerror(
                "Error aplicando el filtro",
                f"Ocurrió un error filtrando y reconstruyendo el ROI:\n\n{error}"
            )
    else:
        # Para los demás filtros, el ROI es solo un recorte de
        # visualización sobre el resultado ya filtrado (no recalcula nada).
        if reconstruccion_filtrada_actual is None:
            roi_inicio = None
            return

        filas, columnas = reconstruccion_filtrada_actual.shape

        escala_x = columnas/400
        escala_y = filas/250

        ix_min = max(0, min(columnas, int(x_min*escala_x)))
        ix_max = max(0, min(columnas, int(x_max*escala_x)))
        iy_min = max(0, min(filas, int(y_min*escala_y)))
        iy_max = max(0, min(filas, int(y_max*escala_y)))

        print(
            f"ROI seleccionada: "
            f"x={ix_min}:{ix_max}, y={iy_min}:{iy_max}"
        )

        recorte = reconstruccion_filtrada_actual[iy_min:iy_max, ix_min:ix_max]
        mostrar_array_uint8(filtrado_frame, recorte)

    roi_inicio = None


def mostrar_array_uint8(frame, array_uint8):
    """Muestra en `frame` un array 2D que YA viene en uint8 (0-255), sin
    volver a normalizar ni aplicar corrección gamma."""
    global ultima_imagen_guardable

    for widget in frame.winfo_children():
        widget.destroy()

    if array_uint8 is None or array_uint8.size == 0:
        print("No hay imagen para mostrar")
        return

    ultima_imagen_guardable = {"tipo": "array", "valor": array_uint8}

    imagen_pil = Image.fromarray(array_uint8)
    imagen_pil = imagen_pil.resize((400, 250))
    imagen_tk = ImageTk.PhotoImage(imagen_pil)

    etiqueta = tk.Label(frame, image=imagen_tk)
    etiqueta.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    etiqueta.image = imagen_tk


def filtro_1_roi(ix_min, ix_max, iy_min, iy_max):
    """Traducción fiel de la opción 1 de 'Filtros' en el MATLAB original
    (button_state==1 de Filtros_Callback): el rectángulo del ROI,
    dibujado sobre la reconstrucción completa, se reutiliza TAL CUAL como
    máscara sobre el espectro de Fourier del holograma —esto es válido
    porque en el método de Fresnel de un solo FFT los índices de píxel
    de la reconstrucción corresponden exactamente a índices de
    frecuencia del holograma—. Se reconstruye de nuevo (con el signo de
    z invertido, igual que el original) y se recorta el resultado al
    mismo rectángulo del ROI."""
    global reconstruccion_filtrada_actual

    filas, columnas = holograma_actual.shape

    mascara = np.zeros((filas, columnas), dtype=np.float64)
    mascara[iy_min:iy_max, ix_min:ix_max] = 1.0

    TFHolograma = np.fft.fftshift(np.fft.fft2(holograma_actual))
    NF = TFHolograma * mascara
    HologramaF = np.fft.fft2(NF)  # sí, otra FFT hacia adelante, tal como en el original

    dx = parametros_fresnel["dx"]
    dy = parametros_fresnel["dy"]
    λ = parametros_fresnel["lambda"]
    z = parametros_fresnel["z"]

    resultado = tf.TFresnel_array(HologramaF, 1, λ, dx, dy, -z)
    resultado = np.fft.fftshift(resultado)

    recorte = resultado[iy_min:iy_max, ix_min:ix_max]
    recorte = np.clip(recorte, 0, 1)

    reconstruccion_filtrada_actual = (recorte * 255).astype(np.uint8)
    mostrar_array_uint8(filtrado_frame, reconstruccion_filtrada_actual)


def filtro_2_plano(imagen_reconstruida):
    """Traducción fiel de la opción 2 (button_state==2): no filtra nada,
    simplemente reutiliza la reconstrucción completa tal cual."""
    return imagen_reconstruida.copy()


def filtro_3_laplaciano():
    """Traducción fiel de la opción 3 (button_state==3): aplica un filtro
    Laplaciano (equivalente a fspecial('laplacian',0.5) de MATLAB)
    directamente sobre el holograma crudo, antes de reconstruir. Es
    automático, sobre toda la imagen, y no necesita ningún ROI."""
    alpha = 0.5
    kernel = np.array([
        [alpha,     1 - alpha, alpha],
        [1 - alpha, -4,        1 - alpha],
        [alpha,     1 - alpha, alpha]
    ], dtype=np.float64) / (alpha + 1)

    holo_filtrado = cv2.filter2D(
        holograma_actual,
        -1,
        kernel,
        borderType=cv2.BORDER_REPLICATE
    )

    dx = parametros_fresnel["dx"]
    dy = parametros_fresnel["dy"]
    λ = parametros_fresnel["lambda"]
    z = parametros_fresnel["z"]

    resultado = tf.TFresnel_array(holo_filtrado, 1, λ, dx, dy, z)
    resultado = np.clip(resultado, 0, 1)

    return (resultado * 255).astype(np.uint8)


def filtro_4_highpass(ix_min, ix_max, iy_min, iy_max):
    """Traducción fiel de la rama 'else' de Filtros_Callback (equivalente
    a Filtrado_E_P_A, 'Filtrado Espacial Paso Alto') del MATLAB original:
    igual que Filtro 1, pero la máscara del ROI se INVIERTE — se elimina
    la región seleccionada (por ejemplo, el orden cero) en vez de
    conservarla, y se reconstruye con todo lo demás. A diferencia de
    Filtro 1, el original NO recorta el resultado al final: se ve la
    escena completa, ya sin la región eliminada."""
    global reconstruccion_filtrada_actual

    filas, columnas = holograma_actual.shape

    mascara = np.ones((filas, columnas), dtype=np.float64)
    mascara[iy_min:iy_max, ix_min:ix_max] = 0.0

    TFHolograma = np.fft.fftshift(np.fft.fft2(holograma_actual))
    NF = TFHolograma * mascara
    HologramaF = np.fft.fft2(NF)

    dx = parametros_fresnel["dx"]
    dy = parametros_fresnel["dy"]
    λ = parametros_fresnel["lambda"]
    z = parametros_fresnel["z"]

    resultado = tf.TFresnel_array(HologramaF, 1, λ, dx, dy, -z)
    resultado = np.fft.fftshift(resultado)
    resultado = np.clip(resultado, 0, 1)

    reconstruccion_filtrada_actual = (resultado * 255).astype(np.uint8)
    mostrar_array_uint8(filtrado_frame, reconstruccion_filtrada_actual)


def aplicar_filtro_seleccionado(imagen_reconstruida):
    """Aplica el filtro elegido en el combobox, replicando el
    comportamiento de Filtros_Callback del MATLAB original."""
    global reconstruccion_filtrada_actual

    filtro = filtro_tipo.get()

    try:
        if imagen_reconstruida is None:
            print("Primero debe ejecutar Fresnel")
            return

        if filtro in FILTROS_CON_ROI:
            # Igual que el original: Filtro 1 y Filtro 4 necesitan que se
            # dibuje un ROI sobre la reconstrucción. El cálculo real
            # ocurre en roi_fin_evento, al soltar el mouse.
            iniciar_seleccion_roi()
        elif filtro == FILTRO_PLANO:
            reconstruccion_filtrada_actual = filtro_2_plano(imagen_reconstruida)
            mostrar_array_uint8(filtrado_frame, reconstruccion_filtrada_actual)
        elif filtro == FILTRO_LAPLACIANO:
            reconstruccion_filtrada_actual = filtro_3_laplaciano()
            mostrar_array_uint8(filtrado_frame, reconstruccion_filtrada_actual)

    except Exception as error:
        detalle = traceback.format_exc()
        print(detalle)
        messagebox.showerror(
            "Error aplicando el filtro",
            f"Ocurrió un error filtrando la reconstrucción:\n\n{error}"
        )


def iniciar_seleccion_roi():
    """Abre la ventana para dibujar el ROI. Para 'Filtro 1' se dibuja
    sobre la reconstrucción COMPLETA sin filtrar (igual que
    roipoly(handles.TFres) en el original); para los demás filtros, se
    dibuja sobre el resultado ya filtrado, solo para recortar la vista."""
    global roi_canvas
    global roi_image_tk
    global roi_inicio
    global roi_ventana

    if filtro_tipo.get() in FILTROS_CON_ROI:
        imagen_base = ultima_reconstruccion_completa
        titulo = f"Dibuje el ROI sobre la reconstrucción ({filtro_tipo.get()})"
    else:
        imagen_base = reconstruccion_filtrada_actual
        titulo = "Seleccione la parte del resultado filtrado a conservar (ROI)"

    if imagen_base is None:
        print("Primero debe ejecutar Fresnel")
        return

    roi_inicio = None

    vista_previa = cv2.resize(imagen_base, (400, 250))

    imagen = Image.fromarray(vista_previa)

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
    roi_ventana.title(titulo)
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

    # Forzamos que la ventana quede al frente y con foco: en algunos
    # gestores de ventanas de Linux, un Toplevel nuevo puede abrirse
    # detrás de la ventana principal y pasar completamente inadvertido.
    roi_ventana.lift()
    roi_ventana.attributes("-topmost", True)
    roi_ventana.after(200, lambda: roi_ventana.attributes("-topmost", False))
    roi_ventana.focus_force()

    print("Seleccione con el mouse la región deseada.")


def Apli_transF(dx,dy,λ,z):
    global holograma_actual
    global transformada_holo
    global parametros_fresnel
    global ultima_reconstruccion_completa

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

    # Fiel al original: TFHolograma = fftshift(fft2(handles.Holo)), sin
    # ventana de apodización.
    transformada_holo = np.fft.fftshift(
        np.fft.fft2(holograma_actual)
    )


    parametros_fresnel = {
        "dx":dx*1e-6,
        "dy":dy*1e-6,
        "lambda":λ*1e-9,
        "z":z*1e-2
    }


    try:
        m_trans = tf.TFresnel_array(
            holograma_actual,
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

        # El filtro se aplica siempre sobre la reconstrucción COMPLETA
        # (la misma imagen que se ve en 'RECONSTRUCCIÓN'), sin depender de
        # ningún ROI. Releemos con PIL el bitmap recién guardado (mismo
        # método que ya usa mostrar_img_recons y que sabemos funciona).
        ultima_reconstruccion_completa = np.array(Image.open(ruta_recons).convert("L"))

        if not modo_lote:
            aplicar_filtro_seleccionado(ultima_reconstruccion_completa)

    except Exception as error:
        detalle = traceback.format_exc()
        print(detalle)
        messagebox.showerror(
            "Error al aplicar Fresnel",
            f"Ocurrió un error calculando o mostrando la reconstrucción:\n\n{error}"
        )
        return


def cambiar_filtro(event=None):
    if ultima_reconstruccion_completa is None:
        print("Primero debe ejecutar Fresnel")
        return

    aplicar_filtro_seleccionado(ultima_reconstruccion_completa)


def mostrar_img_array(frame, imagen):
    """Muestra un array 2D (ya normalizado en [0,1], p.ej. salida de
    TFresnel_array) como imagen dentro de `frame`. No vuelve a aplicar
    corrección gamma porque TFresnel_array ya la aplica; hacerlo de nuevo
    saturaba/lavaba la imagen filtrada."""
    global ultima_imagen_guardable

    for widget in frame.winfo_children():
        widget.destroy()

    imagen = np.abs(imagen)

    maximo = np.max(imagen)

    if maximo > 0:
        imagen = imagen / maximo

    imagen_uint8 = (imagen * 255).clip(0, 255).astype(np.uint8)

    # Guardamos la versión a resolución completa (antes del resize para
    # la vista previa) como la última imagen exportable.
    ultima_imagen_guardable = {"tipo": "array", "valor": imagen_uint8}

    imagen_pil = Image.fromarray(imagen_uint8)

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


# --- Funciones de Guardar / Foto / Vídeo / Configuración / Acerca de ---

def guardar_actual():
    """Guarda la última imagen calculada (reconstrucción o filtrada).
    Usa lo que haya en `ultima_imagen_guardable`, actualizado cada vez
    que se muestra una reconstrucción nueva."""
    if ultima_imagen_guardable["tipo"] is None:
        messagebox.showinfo(
            "Guardar",
            "Todavía no hay ninguna reconstrucción para guardar.\n"
            "Ejecute Fresnel (y opcionalmente un filtro) primero."
        )
        return

    ruta_destino = filedialog.asksaveasfilename(
        title="Guardar imagen",
        defaultextension=".png",
        filetypes=[
            ("PNG", "*.png"),
            ("JPEG", "*.jpg"),
            ("BMP", "*.bmp"),
            ("Todos los archivos", "*.*")
        ]
    )

    if not ruta_destino:
        return

    if ultima_imagen_guardable["tipo"] == "archivo":
        import shutil
        shutil.copy(str(ultima_imagen_guardable["valor"]), ruta_destino)
    else:
        cv2.imwrite(ruta_destino, ultima_imagen_guardable["valor"])

    print(f"Imagen guardada en {ruta_destino}")


def tomar_foto():
    """Traducción fiel de Foto_Callback/Captura_Callback del original:
    NO es 'guardar una imagen' — toma el frame actual de la cámara, lo
    usa como el holograma nuevo, y lo reconstruye de inmediato con
    Fresnel usando los parámetros δx/δy/λ/z actuales."""
    global ruta_holo

    if ultimo_frame_camara is None:
        messagebox.showinfo(
            "Foto",
            "No hay imagen de cámara disponible. Encienda la cámara primero."
        )
        return

    gris = cv2.cvtColor(ultimo_frame_camara, cv2.COLOR_BGR2GRAY)

    ruta_captura = FIGURES_DIR / "captura_camara.bmp"
    cv2.imwrite(str(ruta_captura), gris)

    ruta_holo = ruta_captura
    mostrar_img_holo(ruta_holo)

    try:
        valor_dx = float(dx.get())
        valor_dy = float(dy.get())
        valor_lambda = float(λ.get())
        valor_z = float(z.get())
    except ValueError:
        messagebox.showerror(
            "Foto",
            "Revise que δx, δy, λ y z tengan valores numéricos válidos."
        )
        return

    Apli_transF(valor_dx, valor_dy, valor_lambda, valor_z)


def grabar_video_holografico():
    """Inicia una sesión de video en la que cada fotograma se toma y acepta
    manualmente antes de añadirse a los archivos."""
    global ruta_holo, modo_lote, sesion_video

    if camara_actual is None or not camara_encendida:
        messagebox.showinfo("Vídeo", "Encienda la cámara antes de grabar un vídeo.")
        return

    if sesion_video is not None:
        messagebox.showinfo("Vídeo", "Ya hay una sesión de captura abierta.")
        return

    texto_frames = entrada_frames.get().strip() if entrada_frames is not None else ""

    try:
        num_frames = int(texto_frames)
        if num_frames <= 0:
            raise ValueError
    except ValueError:
        messagebox.showerror(
            "Vídeo",
            "Indique un número de frames válido (entero positivo) en el "
            "campo junto al botón 'Vídeo' (equivale a 'Frames' del original)."
        )
        return

    try:
        valor_dx = float(dx.get())
        valor_dy = float(dy.get())
        valor_lambda = float(λ.get())
        valor_z = float(z.get())
    except ValueError:
        messagebox.showerror(
            "Vídeo",
            "Revise que δx, δy, λ y z tengan valores numéricos válidos."
        )
        return

    try:
        VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        carpeta_sesion = VIDEOS_DIR / datetime.now().strftime("sesion_%Y%m%d_%H%M%S")
        carpeta_sesion.mkdir()
    except OSError as error:
        messagebox.showerror("Vídeo", f"No se pudo crear la carpeta de salida:\n{error}")
        return

    ruta_previa = ruta_holo
    modo_lote = True
    sesion_video = {
        "total": num_frames,
        "guardados": 0,
        "dx": valor_dx,
        "dy": valor_dy,
        "lambda": valor_lambda,
        "z": valor_z,
        "ruta_previa": ruta_previa,
        "ruta_captura": carpeta_sesion / "fotograma_actual.bmp",
        "ruta_video_holo": carpeta_sesion / "hologramas.avi",
        "ruta_video_recons": carpeta_sesion / "reconstrucciones.avi",
        "writer_holo": None,
        "writer_recons": None,
        "pendiente": None,
        "ventana": None,
        "vista": None,
        "estado": None,
        "boton_tomar": None,
        "boton_guardar": None,
    }

    popup = tk.Toplevel(ventana)
    popup.title("Captura manual de video holográfico")
    popup.resizable(False, False)
    sesion_video["ventana"] = popup

    vista = tk.Label(popup, text="Tome un fotograma para previsualizarlo")
    vista.pack(padx=12, pady=8)
    sesion_video["vista"] = vista

    estado = tk.Label(popup, text=f"Fotogramas aceptados: 0/{num_frames}")
    estado.pack(padx=12, pady=4)
    sesion_video["estado"] = estado

    boton_tomar = tk.Button(
        popup, text="Tomar fotograma", command=tomar_fotograma_video
    )
    boton_tomar.pack(side="left", padx=8, pady=10)
    sesion_video["boton_tomar"] = boton_tomar

    boton_guardar = tk.Button(
        popup, text="Aceptar fotograma", command=guardar_fotograma_video,
        state="disabled"
    )
    boton_guardar.pack(side="left", padx=8, pady=10)
    sesion_video["boton_guardar"] = boton_guardar

    tk.Button(
        popup, text="Finalizar", command=finalizar_video_holografico
    ).pack(side="left", padx=8, pady=10)
    popup.protocol("WM_DELETE_WINDOW", finalizar_video_holografico)
    popup.transient(ventana)
    popup.lift()
    popup.focus_force()
    estado.config(text=f"Salida: {carpeta_sesion} | Aceptados: 0/{num_frames}")


def tomar_fotograma_video():
    """Captura un candidato, calcula su reconstrucción y la deja en revisión."""
    global ruta_holo, ultima_reconstruccion_completa

    if sesion_video is None:
        return
    if camara_actual is None or not camara_encendida:
        messagebox.showerror("Vídeo", "La cámara se apagó. Finalice la sesión o vuelva a encenderla.")
        return
    ret, frame = camara_actual.read()
    if not ret:
        messagebox.showerror("Vídeo", "La cámara no entregó un fotograma. Intente de nuevo.")
        return

    if recorte_cam is not None:
        ix_min, ix_max, iy_min, iy_max = recorte_cam
        frame = frame[iy_min:iy_max, ix_min:ix_max]
    if frame.size == 0:
        messagebox.showerror("Vídeo", "El recorte de cámara no contiene píxeles.")
        return

    gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    ruta_captura = sesion_video["ruta_captura"]
    if not cv2.imwrite(str(ruta_captura), gris):
        messagebox.showerror("Vídeo", f"No se pudo guardar el fotograma temporal:\n{ruta_captura}")
        return

    ruta_holo = ruta_captura
    mostrar_img_holo(ruta_holo)
    ultima_reconstruccion_completa = None
    Apli_transF(
        sesion_video["dx"], sesion_video["dy"],
        sesion_video["lambda"], sesion_video["z"]
    )
    if ultima_reconstruccion_completa is None:
        messagebox.showerror("Vídeo", "No se pudo reconstruir este fotograma. Puede tomarlo de nuevo.")
        return

    vista_previa = cv2.resize(gris, (480, 300))
    imagen_tk = ImageTk.PhotoImage(Image.fromarray(vista_previa))
    sesion_video["vista"].configure(image=imagen_tk, text="")
    sesion_video["vista"].image = imagen_tk
    sesion_video["pendiente"] = {
        "holograma": gris.copy(),
        "reconstruccion": ultima_reconstruccion_completa.copy(),
    }
    sesion_video["boton_guardar"].configure(state="normal")
    sesion_video["estado"].configure(
        text=f"Revise la vista y acepte o tome otra. Aceptados: "
             f"{sesion_video['guardados']}/{sesion_video['total']}"
    )


def guardar_fotograma_video():
    """Añade al video únicamente el candidato que el usuario acepta."""
    sesion = sesion_video
    if sesion is None or sesion["pendiente"] is None:
        return

    holograma = sesion["pendiente"]["holograma"]
    reconstruccion = sesion["pendiente"]["reconstruccion"]
    alto, ancho = holograma.shape
    alto_r, ancho_r = reconstruccion.shape
    fourcc = cv2.VideoWriter_fourcc(*"XVID")

    if sesion["writer_holo"] is None:
        writer_holo = cv2.VideoWriter(
            str(sesion["ruta_video_holo"]), fourcc, 2.0, (ancho, alto), isColor=False
        )
        writer_recons = cv2.VideoWriter(
            str(sesion["ruta_video_recons"]), fourcc, 2.0,
            (ancho_r, alto_r), isColor=False
        )
        if not writer_holo.isOpened() or not writer_recons.isOpened():
            writer_holo.release()
            writer_recons.release()
            messagebox.showerror("Vídeo", "No se pudieron crear los archivos AVI.")
            finalizar_video_holografico()
            return
        sesion["writer_holo"] = writer_holo
        sesion["writer_recons"] = writer_recons

    sesion["writer_holo"].write(holograma)
    sesion["writer_recons"].write(reconstruccion)
    sesion["guardados"] += 1
    sesion["pendiente"] = None
    sesion["boton_guardar"].configure(state="disabled")
    sesion["estado"].configure(
        text=f"Fotogramas aceptados: {sesion['guardados']}/{sesion['total']}"
    )

    if sesion["guardados"] >= sesion["total"]:
        finalizar_video_holografico()


def finalizar_video_holografico():
    """Cierra la sesión y libera los videos, incluso si quedó incompleta."""
    global ruta_holo, modo_lote, sesion_video

    sesion = sesion_video
    if sesion is None:
        return
    if sesion["writer_holo"] is not None:
        sesion["writer_holo"].release()
    if sesion["writer_recons"] is not None:
        sesion["writer_recons"].release()

    ruta_holo = sesion["ruta_previa"]
    modo_lote = False
    popup = sesion["ventana"]
    sesion_video = None
    if popup is not None and popup.winfo_exists():
        popup.destroy()

    if sesion["guardados"]:
        print(
            f"Video guardado en {sesion['ruta_video_holo'].parent}: "
            f"{sesion['guardados']} fotogramas aceptados"
        )
        messagebox.showinfo(
            "Vídeo",
            f"Se guardaron {sesion['guardados']} fotogramas en:\n"
            f"{sesion['ruta_video_holo'].parent}"
        )
    else:
        messagebox.showinfo("Vídeo", "Sesión finalizada sin fotogramas guardados.")


def alternar_roi_captura():
    """Traducción fiel de ROI_Callback del original: NO tiene nada que ver
    con los filtros. Es un recorte PREVIO al procesamiento. En modo HOL
    recorta el holograma ya cargado; en modo CAM define un rectángulo de
    captura sobre la vista en vivo de la cámara."""
    global roi_captura_activo, recorte_cam, recorte_hol, ruta_holo, ruta_holo_sin_recortar

    roi_captura_activo = not roi_captura_activo

    if roi_captura_activo:
        boton_roi.config(text="ROI ON")
        if modo2.get() == "CAM":
            if ultimo_frame_camara is None:
                messagebox.showinfo("ROI", "Encienda la cámara primero.")
                roi_captura_activo = False
                boton_roi.config(text="ROI OFF")
                return
            iniciar_seleccion_roi_captura("camara")
        else:
            if not ruta_holo:
                messagebox.showinfo("ROI", "Abra un holograma primero.")
                roi_captura_activo = False
                boton_roi.config(text="ROI OFF")
                return
            iniciar_seleccion_roi_captura("holograma")
    else:
        boton_roi.config(text="ROI OFF")
        if modo2.get() == "CAM":
            recorte_cam = None
        else:
            recorte_hol = None
            if ruta_holo_sin_recortar is not None:
                ruta_holo = ruta_holo_sin_recortar
                ruta_holo_sin_recortar = None
                mostrar_img_holo(ruta_holo)


def iniciar_seleccion_roi_captura(origen):
    """Abre una ventana para dibujar el rectángulo de recorte previo,
    sobre el frame actual de la cámara (origen='camara') o sobre el
    holograma ya cargado (origen='holograma')."""
    global roi_captura_canvas, roi_captura_image_tk, roi_captura_inicio, roi_captura_ventana

    if origen == "camara":
        imagen_base_bgr = ultimo_frame_camara
        imagen_base = cv2.cvtColor(imagen_base_bgr, cv2.COLOR_BGR2RGB)
        titulo = "Dibuje el recorte de captura sobre la cámara (ROI - CAM)"
    else:
        imagen_base = np.array(Image.open(ruta_holo).convert("L"))
        titulo = "Dibuje el recorte del holograma (ROI - HOL)"

    roi_captura_inicio = None

    vista_previa = cv2.resize(imagen_base, (400, 250))
    imagen = Image.fromarray(vista_previa)
    roi_captura_image_tk = ImageTk.PhotoImage(imagen)

    if roi_captura_ventana is not None:
        try:
            if roi_captura_ventana.winfo_exists():
                roi_captura_ventana.destroy()
        except tk.TclError:
            pass

    roi_captura_ventana = tk.Toplevel(ventana)
    roi_captura_ventana.title(titulo)
    roi_captura_ventana.resizable(False, False)

    roi_captura_canvas = tk.Canvas(roi_captura_ventana, width=400, height=250, highlightthickness=0)
    roi_captura_canvas.pack(padx=10, pady=10)
    roi_captura_canvas.create_image(0, 0, anchor="nw", image=roi_captura_image_tk)

    def inicio(event):
        global roi_captura_inicio
        roi_captura_inicio = (event.x, event.y)
        roi_captura_canvas.delete("roi_captura")

    def movimiento(event):
        if roi_captura_inicio is None:
            return
        x0, y0 = roi_captura_inicio
        roi_captura_canvas.delete("roi_captura")
        roi_captura_canvas.create_rectangle(
            x0, y0, event.x, event.y, outline="yellow", width=2, tags="roi_captura"
        )

    def fin(event):
        finalizar_roi_captura(origen, imagen_base.shape, event)

    roi_captura_canvas.bind("<ButtonPress-1>", inicio)
    roi_captura_canvas.bind("<B1-Motion>", movimiento)
    roi_captura_canvas.bind("<ButtonRelease-1>", fin)

    roi_captura_ventana.lift()
    roi_captura_ventana.attributes("-topmost", True)
    roi_captura_ventana.after(200, lambda: roi_captura_ventana.attributes("-topmost", False))
    roi_captura_ventana.focus_force()

    print("Dibuje con el mouse la región que desea conservar.")


def finalizar_roi_captura(origen, forma_imagen, event):
    global roi_captura_inicio, recorte_cam, recorte_hol, ruta_holo, ruta_holo_sin_recortar

    if roi_captura_inicio is None:
        return

    x0, y0 = roi_captura_inicio
    x1, y1 = event.x, event.y

    x_min, x_max = sorted((x0, x1))
    y_min, y_max = sorted((y0, y1))

    if x_max - x_min < 2 or y_max - y_min < 2:
        print("ROI demasiado pequeña")
        roi_captura_inicio = None
        return

    filas, columnas = forma_imagen[0], forma_imagen[1]
    escala_x = columnas / 400
    escala_y = filas / 250

    ix_min = max(0, min(columnas, int(x_min * escala_x)))
    ix_max = max(0, min(columnas, int(x_max * escala_x)))
    iy_min = max(0, min(filas, int(y_min * escala_y)))
    iy_max = max(0, min(filas, int(y_max * escala_y)))

    if origen == "camara":
        recorte_cam = (ix_min, ix_max, iy_min, iy_max)
        print(f"Recorte de cámara fijado: x={ix_min}:{ix_max}, y={iy_min}:{iy_max}")
    else:
        recorte_hol = (ix_min, ix_max, iy_min, iy_max)

        imagen_completa = np.array(Image.open(ruta_holo).convert("L"))
        recorte = imagen_completa[iy_min:iy_max, ix_min:ix_max]

        ruta_holo_sin_recortar = ruta_holo
        ruta_recortada = FIGURES_DIR / "holograma_recortado.bmp"
        cv2.imwrite(str(ruta_recortada), recorte)
        ruta_holo = ruta_recortada
        mostrar_img_holo(ruta_holo)
        print(f"Holograma recortado: x={ix_min}:{ix_max}, y={iy_min}:{iy_max}")

    roi_captura_inicio = None

    if roi_captura_ventana is not None:
        try:
            roi_captura_ventana.destroy()
        except tk.TclError:
            pass


def abrir_configuracion():
    """Placeholder de la ventana de configuración: de momento solo informa
    qué se planea incluir aquí (cámara por defecto, formato, ruta de
    guardado). Se puede reemplazar por un Toplevel real más adelante."""
    messagebox.showinfo(
        "Configuración",
        "Panel de configuración en construcción.\n\n"
        "Próximamente: cámara y formato por defecto, ruta de guardado "
        "predeterminada y parámetros de Fresnel por defecto."
    )


def mostrar_acerca_de():
    messagebox.showinfo(
        "Acerca de HDFresnel_GOM",
        "Derechos de autor y software: El Dr. Jorge E. Rueda P. y el Fís. "
        "Dudbil O. Pabon R., son los principales autores del software "
        "HDFresnel_GOM_V1. Se prohíbe la distribución sin previa "
        "autorización de los autores."
    )


def corrimiento_de_fase():
    """Traducción fiel de Corrimiento_de_fase_Callback del original:
    se eligen exactamente cuatro hologramas con corrimiento de fase de 0,
    pi/2, pi y 3pi/2 (en ese orden); se combinan en un campo complejo
    Holo = (I1-I3) - 1j*(I2-I4), que elimina orden cero e imagen gemela,
    y se reconstruye con Fresnel. Se muestra en RECONSTRUCCIÓN FILTRADA."""
    global reconstruccion_filtrada_actual

    try:
        valor_dx = float(dx.get()) * 1e-6
        valor_dy = float(dy.get()) * 1e-6
        valor_lambda = float(λ.get()) * 1e-9
        valor_z = float(z.get()) * 1e-2
    except ValueError:
        messagebox.showerror(
            "Corrimiento de fase",
            "Revise que δx, δy, λ y z tengan valores numéricos válidos."
        )
        return

    rutas = filedialog.askopenfilenames(
        title="Seleccione los 4 hologramas (0, π/2, π, 3π/2)",
        filetypes=[
            ("Imágenes", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.gif"),
            ("Todos los archivos", "*.*")
        ]
    )

    if not rutas:
        return

    if len(rutas) != 4:
        messagebox.showerror(
            "Error",
            "Debe elegir una secuencia de cuatro hologramas con corrimiento "
            "de fase entre ellos de 0, pi/2, pi y 3pi/2, respectivamente."
        )
        return

    try:
        # Se ordenan alfabéticamente (el orden en que el diálogo de MATLAB
        # los entrega); nombre los archivos para que ese orden sea 0, π/2, π, 3π/2.
        I1, I2, I3, I4 = [
            cv2.imread(str(ruta), cv2.IMREAD_GRAYSCALE).astype(np.float64)
            for ruta in sorted(rutas)
        ]

        Holo = (I1 - I3) - 1j * (I2 - I4)

        maximo = np.max(np.abs(Holo))
        if maximo > 0:
            Holo = Holo / maximo

        mostrar_array_uint8(
            holograma_frame,
            (np.abs(Holo) / max(np.max(np.abs(Holo)), 1e-12) * 255).astype(np.uint8)
        )

        resultado = tf.TFresnel_array(Holo, 1, valor_lambda, valor_dx, valor_dy, valor_z)
        resultado = np.clip(resultado, 0, 1)

        reconstruccion_filtrada_actual = (resultado * 255).astype(np.uint8)
        mostrar_array_uint8(filtrado_frame, reconstruccion_filtrada_actual)

    except Exception as error:
        print(traceback.format_exc())
        messagebox.showerror(
            "Corrimiento de fase",
            f"Ocurrió un error reconstruyendo los cuatro hologramas:\n\n{error}"
        )


# Crear la ventana principal
ventana = tk.Tk()
ventana.title("HDFresnel_GOM")
ventana.geometry("1200x700")
ventana.resizable(False,False)

barra_menu = tk.Menu(ventana)

menu_archivo = tk.Menu(barra_menu, tearoff=0)
menu_archivo.add_command(label="Abrir", command=abrir_holograma)
menu_archivo.add_command(label="Guardar", command=guardar_actual)
menu_archivo.add_separator()
menu_archivo.add_command(label="Salir", command=ventana.destroy)

barra_menu.add_cascade(label="Archivo", menu=menu_archivo)

menu_herramientas = tk.Menu(barra_menu, tearoff=0)
menu_herramientas.add_command(label="Configuración", command=abrir_configuracion)
menu_herramientas.add_command(label="Corrimiento de fase (4 hologramas)", command=corrimiento_de_fase)

barra_menu.add_cascade(
    label="Herramientas",
    menu=menu_herramientas
)

menu_ayuda = tk.Menu(barra_menu,tearoff=0)
menu_ayuda.add_command(label="Acerca de", command=mostrar_acerca_de)

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
    text="📁",
    command=abrir_holograma
).pack(side="left", padx=3)

tk.Button(
    barra_herramientas,
    text="💾",
    command=guardar_actual
).pack(side="left", padx=3)

tk.Button(
    barra_herramientas,
    text="🔍",
    command=iniciar_seleccion_roi
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

boton_roi = tk.Button(
    roi,
    text="ROI OFF",
    command = alternar_roi_captura
)
boton_roi.grid(rowspan=2,column=0,padx=5)

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
    text="Foto",
    command=tomar_foto
).grid(row=0,column=0,padx=5)

boton_video = tk.Button(
    botones,
    text="Vídeo",
    command=grabar_video_holografico
)
boton_video.grid(row=0,column=1,padx=5)

entrada_frames = tk.Entry(
    botones,
    width=4
)
entrada_frames.insert(0, "10")
entrada_frames.grid(row=0,column=2,padx=5)

tk.Button(
    botones,
    text="Fresnel",
    width=19,
    command = lambda : Apli_transF(float(dx.get()),float(dy.get()),float(λ.get()),float(z.get()))
).grid(row=1,columnspan=3,padx=5)

filtro_tipo = ttk.Combobox(
    botones,
    values=[
    FILTRO_PASO_BANDA,
    FILTRO_PLANO,
    FILTRO_LAPLACIANO,
    FILTRO_PASO_ALTO
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
    width=13,
    command=guardar_actual
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
