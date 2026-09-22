"""
Fase 6: verifica que los return coincidan con el tipo de la función.
"""

from nucleo.contexto import (
    tipo_de_token,
    parse_parametros,
    asignacion_valida,
)
from nucleo.expresiones import evaluar_expresion


def verificar_returns(analizador):
    tokens = analizador.tokens
    n = len(tokens)
    pila_ambitos = [{}]
    pila_funcion_actual = [None]  # tipo de retorno por nivel de bloque
    errores_reportados = set()
    i = 0
    while i < n:
        tok = tokens[i]

        # Declaraciones
        if tok.tipo == "reservada" and tok.lexema in ("full", "royal", "chain", "void"):
            tipo_decl = tok.lexema
            renglon_decl = tok.renglon
            j = i + 1
            if j < n and tokens[j].tipo == "id":
                nombre = tokens[j].lexema
                k = j + 1
                if k < n and tokens[k].tipo == "delim" and tokens[k].lexema == "(":
                    pila_ambitos[-1][nombre] = tipo_decl
                    params, k = parse_parametros(tokens, k + 1, n)
                    if k < n and tokens[k].tipo == "delim" and tokens[k].lexema == "{":
                        pila_ambitos.append({})
                        for tipo_p, tok_p in params:
                            pila_ambitos[-1][tok_p.lexema] = tipo_p
                        pila_funcion_actual.append(tipo_decl)
                        k += 1
                    i = k
                    continue
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
                        pila_ambitos[-1][var] = tipo_decl
                    i = m
                    continue
            i += 1
            continue

        # Bloque anidado (if, while, for)
        if tok.tipo == "delim" and tok.lexema == "{":
            pila_ambitos.append({})
            pila_funcion_actual.append(pila_funcion_actual[-1])
            i += 1
            continue
        if tok.tipo == "delim" and tok.lexema == "}":
            if len(pila_ambitos) > 1:
                pila_ambitos.pop()
                pila_funcion_actual.pop()
            i += 1
            continue

        # Return
        if tok.tipo == "reservada" and tok.lexema == "return":
            tipo_funcion = pila_funcion_actual[-1]

            j = i + 1
            expresion = []
            while j < n and tokens[j].lexema != ";":
                expresion.append(tokens[j])
                j += 1

            if tipo_funcion is None:
                analizador._insertar_error(tok, "Return fuera de una función", errores_reportados)
                i = j + 1
                continue

            if not expresion:
                if tipo_funcion != "void":
                    analizador._insertar_error(
                        tok,
                        f"Error semántico, no hubo retorno tipo {tipo_funcion}",
                        errores_reportados
                    )
                i = j + 1
                continue

            if tipo_funcion == "void":
                analizador._insertar_error(
                    tok,
                    f"Error semántico, no hubo retorno tipo {tipo_funcion}",
                    errores_reportados
                )
                i = j + 1
                continue

            if len(expresion) == 1:
                tipo_exp = tipo_de_token(expresion[0], pila_ambitos)
                if tipo_exp is not None and not asignacion_valida(tipo_funcion, tipo_exp):
                    analizador._insertar_error(
                        expresion[0],
                        f"Error semántico, no hubo retorno tipo {tipo_funcion}",
                        errores_reportados
                    )
            else:
                evaluar_expresion(analizador, expresion, tipo_funcion, pila_ambitos)

            i = j + 1
            continue

        i += 1