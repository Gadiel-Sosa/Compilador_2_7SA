"""
Estructuras de salida de la fase de optimización.
"""


class Cambio:
    """Una optimización aplicada (para mostrarla en la tabla de la ventana)."""

    def __init__(self, renglon, tecnica, descripcion):
        self.renglon = renglon          # renglón del código ORIGINAL
        self.tecnica = tecnica          # "Mirilla" / "Instrucción repetida"
        self.descripcion = descripcion

    def __repr__(self):
        return f"Cambio({self.renglon}, {self.tecnica!r}, {self.descripcion!r})"


class ResultadoOptimizacion:
    def __init__(self, codigo, cambios):
        self.codigo = codigo            # código optimizado (texto limpio)
        self.cambios = cambios          # lista de Cambio
