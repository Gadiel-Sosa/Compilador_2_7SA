"""
Vuelve a escribir el árbol de sentencias como código fuente limpio:
una sentencia por renglón, sangría de 4 espacios y sin comentarios
ni renglones en blanco.
"""

from nucleo.optimizacion.arbol import Simple, Funcion, If, Bloque, es_delim

SANGRIA = "    "
SIN_ESPACIO_ANTES = {",", ";", ")", "]"}
SIN_ESPACIO_DESPUES = {"(", "["}


def unir(tokens):
    """Une tokens en texto con espaciado legible: QaZ = QfZ(QbZ, 2) + 1;"""
    partes = []
    anterior = None
    for t in tokens:
        if anterior is not None:
            pegado = (
                (t.tipo == "delim" and t.lexema in SIN_ESPACIO_ANTES)
                or (anterior.tipo == "delim" and anterior.lexema in SIN_ESPACIO_DESPUES)
                or (t.tipo == "delim" and t.lexema in SIN_ESPACIO_DESPUES
                    and anterior.tipo == "id")
            )
            if not pegado:
                partes.append(" ")
        partes.append(t.lexema)
        anterior = t
    return "".join(partes)


def imprimir(sentencias):
    lineas = []
    _imprimir(sentencias, 0, lineas)
    return "\n".join(lineas)


def _imprimir(sentencias, nivel, lineas):
    sangria = SANGRIA * nivel
    for s in sentencias:
        if isinstance(s, Simple):
            if all(es_delim(t, ";") for t in s.tokens):
                continue  # sentencia vacía
            lineas.append(sangria + unir(s.tokens))

        elif isinstance(s, Funcion):
            lineas.append(f"{sangria}{s.tipo} {s.nombre}({unir(s.params)}) {{")
            _imprimir(s.cuerpo, nivel + 1, lineas)
            lineas.append(sangria + "}")

        elif isinstance(s, If):
            lineas.append(f"{sangria}if ({unir(s.cond)}) {{")
            _imprimir(s.entonces, nivel + 1, lineas)
            if s.sino is not None:
                lineas.append(sangria + "} else {")
                _imprimir(s.sino, nivel + 1, lineas)
            lineas.append(sangria + "}")

        elif isinstance(s, Bloque):
            lineas.append(sangria + "{")
            _imprimir(s.cuerpo, nivel + 1, lineas)
            lineas.append(sangria + "}")
