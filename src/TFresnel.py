#!/usr/bin/env python3

import cv2
import numpy as np


def TFresnel_array(imagen, Onda_ref, Lambda, deltax0, deltay0, Z0):
    """Reconstruye un holograma 2D con propagación de Fresnel de una FFT.

    Devuelve la magnitud normalizada del campo con la corrección de cuarta
    raíz usada por la aplicación para visualizar el resultado.
    """
    imagen = np.asarray(imagen)
    if imagen.ndim != 2 or imagen.size == 0:
        raise ValueError("El holograma debe ser una matriz 2D no vacía")
    if not np.isfinite(imagen).all():
        raise ValueError("El holograma contiene valores no finitos")
    if not np.isfinite([Lambda, deltax0, deltay0, Z0]).all():
        raise ValueError("Los parámetros de Fresnel deben ser finitos")
    if Lambda == 0 or deltax0 == 0 or deltay0 == 0 or Z0 == 0:
        raise ValueError("Lambda, dx, dy y z deben ser distintos de cero")

    N, M = imagen.shape
    # Coordenadas centradas de longitud exacta N y M, incluso en tamaños impares.
    x = np.arange(M) - M // 2
    y = np.arange(N) - N // 2
    X, Y = np.meshgrid(x, y)

    r1 = (X * (Lambda * Z0) / (M * deltax0)) ** 2 + (Y * (Lambda * Z0) / (N * deltay0)) ** 2
    P = (
        (1 / (1j * Lambda * Z0))
        * np.exp(1j * 2 * np.pi * Z0 / Lambda)
        * np.exp((1j * np.pi / (Lambda * Z0)) * r1)
    )
    r2 = (X * deltax0) ** 2 + (Y * deltay0) ** 2
    H = np.exp((1j * np.pi / (Lambda * Z0)) * r2)

    campo = P * np.fft.fftshift(np.fft.ifft2(imagen * Onda_ref * H))
    magnitud = np.abs(campo)
    maximo = np.max(magnitud)
    if maximo > 0:
        magnitud = magnitud / maximo
    return magnitud ** 0.25


def TFresnel(Imagen, Onda_ref, Lambda, deltax0, deltay0, Z0):
    """Lee una imagen en escala de grises y la reconstruye con Fresnel."""
    imagen = cv2.imread(str(Imagen), cv2.IMREAD_GRAYSCALE)
    if imagen is None:
        raise ValueError(f"No se pudo leer el holograma: {Imagen}")
    return TFresnel_array(imagen, Onda_ref, Lambda, deltax0, deltay0, Z0)
