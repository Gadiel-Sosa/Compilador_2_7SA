"""
Fase 1: recorre los tokens registrando tipos de variables, funciones
y parámetros en la pila de ámbitos.
"""

from nucleo.contexto import parse_parametros


def inferir_tipos_declarados(analizador):
    tokens = analizador.tokens
    n = len(tokens)
    i = 0
    while i < n:
        tok = tokens[i]

        # Apertura / cierre de bloque
        if tok.tipo == "delim" and tok.lexema == "{":
            analizador.pila_tipos.append({})
            i += 1
            continue
        if tok.tipo == "delim" and tok.lexema == "}":
            if len(analizador.pila_tipos) > 1:
                analizador.pila_tipos.pop()
            i += 1
            continue

        # Declaración de tipo
        if tok.tipo == "reservada" and tok.lexema in ("full", "royal", "chain", "void"):
            tipo_decl = tok.lexema
            renglon_decl = tok.renglon
            j = i + 1

            if j < n and tokens[j].tipo == "id":
                nombre = tokens[j].lexema
                k = j + 1

                # Función
                if k < n and tokens[k].tipo == "delim" and tokens[k].lexema == "(":
                    if nombre not in analizador.pila_tipos[-1]:
                        analizador.pila_tipos[-1][nombre] = tipo_decl
                        if nombre not in analizador.simbolos_globales:
                            analizador.simbolos_globales[nombre] = tipo_decl

                    params, k = parse_parametros(tokens, k + 1, n)
                    analizador.firmas_funciones[nombre] = [tipo_p for tipo_p, _ in params]

                    if k < n and tokens[k].tipo == "delim" and tokens[k].lexema == "{":
                        analizador.pila_tipos.append({})
                        for tipo_p, tok_p in params:
                            nombre_p = tok_p.lexema
                            analizador.pila_tipos[-1][nombre_p] = tipo_p
                            if nombre_p not in analizador.simbolos_globales:
                                analizador.simbolos_globales[nombre_p] = tipo_p
                        k += 1
                    i = k
                    continue

                # Variables
                else:
                    ids_declarados = [nombre]
                    m = k
                    while m < n:
                        if tokens[m].renglon != renglon_decl:
                            break
                        if tokens[m].tipo == "delim" and tokens[m].lexema == ";":
                            break
                        if tokens[m].tipo == "id":
                            ids_declarados.append(tokens[m].lexema)
                        m += 1
                    for var in ids_declarados:
                        if var not in analizador.pila_tipos[-1]:
                            analizador.pila_tipos[-1][var] = tipo_decl
                            if var not in analizador.simbolos_globales:
                                analizador.simbolos_globales[var] = tipo_decl
                    i = m
                    continue
        i += 1