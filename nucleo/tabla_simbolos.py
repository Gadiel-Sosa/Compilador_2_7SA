"""
Fase 2: llena la tabla de símbolos sin duplicados.
"""


def llenar_tabla_simbolos(analizador):
    lexemas_insertados = set()

    for tok in analizador.tokens:
        # Palabras reservadas
        if tok.tipo == "reservada":
            if tok.lexema not in lexemas_insertados:
                analizador.resultado.simbolos.append((tok.lexema, ""))
                lexemas_insertados.add(tok.lexema)
            continue

        # Operadores y delimitadores
        if tok.tipo in ("op", "delim"):
            if tok.lexema in lexemas_insertados:
                continue
            analizador.resultado.simbolos.append((tok.lexema, ""))
            lexemas_insertados.add(tok.lexema)
            continue

        # Solo id y literales
        if tok.tipo not in ("id", "full", "royal", "chain"):
            continue

        if tok.lexema in lexemas_insertados:
            continue

        if tok.tipo == "id":
            tipo_tabla = analizador.simbolos_globales.get(tok.lexema, "")
        else:
            tipo_tabla = tok.tipo

        analizador.resultado.simbolos.append((tok.lexema, tipo_tabla))
        lexemas_insertados.add(tok.lexema)