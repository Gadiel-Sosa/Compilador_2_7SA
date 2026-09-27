"""
Fase 7: verifica los tipos usados en la condición de un if.
"""

from nucleo.contexto import parse_parametros, asignacion_valida
from nucleo.expresiones import _leer_operando

OPERADORES_CONDICION = {"<", ">", "<=", ">=", "==", "!=", "&&", "||"}


def verificar_condiciones_if(analizador):
    tokens = analizador.tokens
    n = len(tokens)
    pila_ambitos = [{}]
    errores_reportados = set()
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

        # Registrar declaraciones (variables, funciones y parámetros)
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

        # Detectar "if ("
        if tok.tipo == "reservada" and tok.lexema == "if":
            if i + 1 < n and tokens[i + 1].tipo == "delim" and tokens[i + 1].lexema == "(":
                condicion = []
                k = i + 2
                profundidad = 1
                while k < n and profundidad > 0:
                    t = tokens[k]
                    if t.tipo == "delim" and t.lexema == "(":
                        profundidad += 1
                    elif t.tipo == "delim" and t.lexema == ")":
                        profundidad -= 1
                        if profundidad == 0:
                            k += 1
                            break
                    condicion.append(t)
                    k += 1

                _verificar_condicion(analizador, condicion, pila_ambitos, errores_reportados)
                i = k
                continue

        i += 1


def _verificar_condicion(analizador, condicion, pila, errores_reportados):
    if not condicion:
        return

    tipo_actual, tok_actual, idx = _leer_operando(analizador, condicion, 0, pila)
    if tipo_actual is None:
        return

    while idx < len(condicion):
        operador = condicion[idx]
        if operador.tipo != "op" or operador.lexema not in OPERADORES_CONDICION:
            idx += 1
            continue
        if idx + 1 >= len(condicion):
            return

        tipo_der, tok_der, siguiente_idx = _leer_operando(analizador, condicion, idx + 1, pila)
        if tipo_der is None:
            idx = siguiente_idx
            continue

        if not (asignacion_valida(tipo_actual, tipo_der) or asignacion_valida(tipo_der, tipo_actual)):
            analizador._insertar_error(
                tok_der,
                f"Incompatibilidad de tipos, {tipo_actual}",
                errores_reportados
            )

        tipo_actual = tipo_der
        tok_actual = tok_der
        idx = siguiente_idx