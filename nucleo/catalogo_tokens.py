"""
Catálogo de temporales usados en la generación de triplos.
Ya no traduce lexemas a IDs simbólicos: los triplos usan el lexema
crudo directamente (variable, constante u operador).
"""


class CatalogoTokens:
    def __init__(self):
        self.contador_temporal = 0

    def nuevo_temporal(self):
        """Crea un nuevo temporal (T1, T2, ...) y devuelve su nombre."""
        self.contador_temporal += 1
        return f"T{self.contador_temporal}"

    def reiniciar_temporales(self):
        self.contador_temporal = 0


def construir_catalogo(tokens):
    """Punto de entrada: ya no necesita recorrer tokens."""
    return CatalogoTokens()