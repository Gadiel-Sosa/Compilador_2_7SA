"""
Fase 3: detecta variables y funciones indefinidas.
"""

from nucleo.contexto import parse_parametros


def verificar_indefinidos(analizador):
    tokens = analizador.tokens
    n = len(tokens)
    errores_reportados = set()

    pila_ambitos = [{}]

    i = 0
    while i < n:
        tok = tokens[i]

        # Apertura / cierre de bloque
        if tok.tipo == "delim" and tok.lexema == "{":
            pila_ambitos.append({})
            i += 1
            continue
        if tok.tipo == "delim" and tok.lexema == "}":
            if len(pila_ambitos) > 1:
                pila_ambitos.pop()
            i += 1
            continue

        # Registrar declaraciones
        if tok.tipo == "reservada" and tok.lexema in ("full", "royal", "chain", "void"):
            renglon_decl = tok.renglon
            j = i + 1
            if j < n and tokens[j].tipo == "id":
                nombre = tokens[j].lexema
                k = j + 1

                # Función
                if k < n and tokens[k].tipo == "delim" and tokens[k].lexema == "(":
                    pila_ambitos[-1][nombre] = True
                    params, k = parse_parametros(tokens, k + 1, n)
                    if k < n and tokens[k].tipo == "delim" and tokens[k].lexema == "{":
                        pila_ambitos.append({})
                        for tipo_p, tok_p in params:
                            pila_ambitos[-1][tok_p.lexema] = True
                        k += 1
                    i = k
                    continue
                else:
                    # Variables: registrar TODAS las separadas por comas
                    pila_ambitos[-1][nombre] = True
                    m = k
                    while m < n:
                        if tokens[m].renglon != renglon_decl:
                            break
                        if tokens[m].tipo == "delim" and tokens[m].lexema == ";":
                            break
                        if tokens[m].tipo == "id":
                            pila_ambitos[-1][tokens[m].lexema] = True
                        m += 1
                    i = m
                    continue
            i += 1
            continue

        # Verificar uso de id
        if tok.tipo == "id":
            esta_declarado = any(tok.lexema in ambito for ambito in pila_ambitos)

            if not esta_declarado:
                es_funcion = (
                    i + 1 < n
                    and tokens[i + 1].tipo == "delim"
                    and tokens[i + 1].lexema == "("
                )
                descripcion = "Función indefinida" if es_funcion else "Variable indefinida"

                clave = (tok.lexema, tok.renglon)
                if clave not in errores_reportados:
                    errores_reportados.add(clave)
                    analizador.contador_errores += 1
                    analizador.resultado.errores.append(
                        (f"ErrSem{analizador.contador_errores}",
                         tok.lexema,
                         tok.renglon,
                         descripcion)
                    )

        i += 1