"""
Fase de optimización (Unidad III).

Se aplica sobre el código fuente, en este orden:
  1. Mirilla (funciones intermediarias).
  2. Instrucciones que se repiten sin modificación (Opción 1).

El resultado es el código optimizado como texto limpio, del cual
se genera después el triplo.
"""

from nucleo.optimizacion.arbol import parsear
from nucleo.optimizacion.impresion import imprimir
from nucleo.optimizacion.mirilla import aplicar_mirilla
from nucleo.optimizacion.repetidas import aplicar_repetidas
from nucleo.optimizacion.resultado import Cambio, ResultadoOptimizacion


def optimizar(tokens):
    programa = parsear(tokens)
    cambios = []
    aplicar_mirilla(programa, cambios)
    aplicar_repetidas(programa, cambios)
    cambios.sort(key=lambda c: c.renglon)
    return ResultadoOptimizacion(imprimir(programa), cambios)
