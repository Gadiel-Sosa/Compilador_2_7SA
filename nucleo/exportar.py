"""
Exporta la tabla de triplos a CSV.
"""

import csv


def exportar_csv(filas, catalogo, ruta_csv):
    """Genera un archivo CSV con la tabla del triplo."""
    with open(ruta_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["#", "Dato Objeto", "Dato Fuente", "Operador"])
        for fila in filas:
            writer.writerow([
                fila.numero,
                fila.objeto or "",
                fila.fuente or "",
                fila.operador or ""
            ])