"""
Construye un catálogo de tokens simbólicos a partir de la lista de tokens.

Asigna IDs como:
  - IDE01, IDE02, ...  → identificadores
  - CE01, CE02, ...    → constantes (enteras, reales, cadenas)
  - OA01, OA02, ...    → operadores aritméticos (+, -, *, /)
  - OR01, OR02, ...    → operadores relacionales (<, >, <=, >=, ==, !=)
  - OL01, OL02, ...    → operadores lógicos (&&, ||)
  - ORAS               → operador de asignación (=)  (siempre el mismo)
"""

from nucleo.token_util import clasificar_token


class CatalogoTokens:
    def __init__(self):
        self.lexema_a_id = {}      # "QaZ" -> "IDE01"
        self.id_a_lexema = {}      # "IDE01" -> "QaZ"
        self.contadores = {
            "IDE": 0,
            "CE": 0,
            "OA": 0,
            "OR": 0,
            "OL": 0,
        }
        self.temporales = {}       # "T1" -> None (por ahora)
        self.contador_temporal = 0

    # ------------------------------------------------------
    def registrar(self, lexema, categoria):
        """Registra un lexema y devuelve su ID simbólico."""
        if lexema in self.lexema_a_id:
            return self.lexema_a_id[lexema]

        if categoria == "ORAS":
            self.lexema_a_id[lexema] = "ORAS"
            self.id_a_lexema["ORAS"] = lexema
            return "ORAS"

        self.contadores[categoria] += 1
        id_simbolico = f"{categoria}{self.contadores[categoria]:02d}"
        self.lexema_a_id[lexema] = id_simbolico
        self.id_a_lexema[id_simbolico] = lexema
        return id_simbolico

    # ------------------------------------------------------
    def nuevo_temporal(self):
        """Crea un nuevo temporal (T1, T2, ...) y devuelve su nombre."""
        self.contador_temporal += 1
        nombre = f"T{self.contador_temporal}"
        self.temporales[nombre] = None
        return nombre

    # ------------------------------------------------------
    def reiniciar_temporales(self):
        """Reinicia los temporales (útil entre bloques si se quiere)."""
        self.temporales = {}
        self.contador_temporal = 0

    # ------------------------------------------------------
    def id_de(self, lexema):
        """Devuelve el ID simbólico de un lexema, o None."""
        return self.lexema_a_id.get(lexema)

    # ------------------------------------------------------
    def leyenda(self):
        """Devuelve una lista de tuplas (ID, lexema, categoría) para exportar."""
        resultado = []
        for id_simbolico, lexema in self.id_a_lexema.items():
            if id_simbolico == "ORAS":
                categoria = "Asignación"
            elif id_simbolico.startswith("IDE"):
                categoria = "Identificador"
            elif id_simbolico.startswith("CE"):
                categoria = "Constante"
            elif id_simbolico.startswith("OA"):
                categoria = "Operador aritmético"
            elif id_simbolico.startswith("OR"):
                categoria = "Operador relacional"
            elif id_simbolico.startswith("OL"):
                categoria = "Operador lógico"
            elif id_simbolico.startswith("T"):
                categoria = "Temporal"
            else:
                categoria = "Desconocido"
            resultado.append((id_simbolico, lexema, categoria))

        # Ordenar por categoría y número
        def clave(item):
            prefijo = "".join(c for c in item[0] if c.isalpha())
            numero = "".join(c for c in item[0] if c.isdigit())
            orden_prefijo = {
                "IDE": 1, "CE": 2, "T": 3, "OA": 4, "OR": 5, "OL": 6, "ORAS": 7
            }.get(prefijo, 99)
            return (orden_prefijo, int(numero) if numero else 0)

        return sorted(resultado, key=clave)


# ==========================================================
def construir_catalogo(tokens):
    """
    Recorre la lista de tokens y construye el catálogo.

    Devuelve una instancia de CatalogoTokens con todos los lexemas
    que aparecen en el código fuente.
    """
    catalogo = CatalogoTokens()
    for tok in tokens:
        categoria = clasificar_token(tok)
        if categoria is None:
            continue  # reservadas, delimitadores, etc. no entran
        catalogo.registrar(tok.lexema, categoria)
    return catalogo