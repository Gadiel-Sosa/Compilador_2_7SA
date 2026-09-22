"""
Fase 1.5: detecta declaraciones duplicadas en el mismo ámbito.
"""

from nucleo.contexto import parse_parametros


def verificar_duplicados(analizador):
    tokens = analizador.tokens
    n = len(tokens)
    errores_reportados = set()

    pila_ambitos = [{}]

    i = 0
    while i < n:
        tok = tokens[i]

        if tok.tipo == "delim" and tok.lexema == "{":
            pila_ambitos.append({})
            i += 1
            continue
        if tok.tipo == "delim" and tok.lexema == "}":
            if len(pila_ambitos) > 1:
                pila_ambitos.pop()
            i += 1
            continue

        if tok.tipo == "reservada" and tok.lexema in ("full", "royal", "chain", "void"):
            renglon_decl = tok.renglon
            j = i + 1

            if j < n and tokens[j].tipo == "id":
                nombre = tokens[j].lexema
                ambito_actual = pila_ambitos[-1]

                if nombre in ambito_actual:
                    _registrar_duplicado(analizador, nombre, tokens[j].renglon, errores_reportados)
                else:
                    ambito_actual[nombre] = True

                k = j + 1

                # Función
                if k < n and tokens[k].tipo == "delim" and tokens[k].lexema == "(":
                    params, k = parse_parametros(tokens, k + 1, n)
                    if k < n and tokens[k].tipo == "delim" and tokens[k].lexema == "{":
                        pila_ambitos.append({})
                        nuevo_ambito = pila_ambitos[-1]
                        for tipo_p, tok_p in params:
                            nombre_p = tok_p.lexema
                            if nombre_p in nuevo_ambito:
                                _registrar_duplicado(analizador, nombre_p, tok_p.renglon, errores_reportados)
                            else:
                                nuevo_ambito[nombre_p] = True
                        k += 1
                    i = k
                    continue

                # Variables
                m = k
                while m < n:
                    if tokens[m].renglon != renglon_decl:
                        break
                    if tokens[m].tipo == "delim" and tokens[m].lexema == ";":
                        break
                    if tokens[m].tipo == "id":
                        otro_nombre = tokens[m].lexema
                        if otro_nombre in ambito_actual:
                            _registrar_duplicado(analizador, otro_nombre, tokens[m].renglon, errores_reportados)
                        else:
                            ambito_actual[otro_nombre] = True
                    m += 1
                i = m
                continue
        i += 1


def _registrar_duplicado(analizador, nombre, renglon, errores_reportados):
    clave = (nombre, renglon)
    if clave in errores_reportados:
        return
    errores_reportados.add(clave)
    analizador.contador_errores += 1
    analizador.resultado.errores.append(
        (f"ErrSem{analizador.contador_errores}", nombre, renglon, "Declaración duplicada")
    )