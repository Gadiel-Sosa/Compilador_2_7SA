"""
Fase 5: verifica llamadas a funciones (número y tipo de argumentos).
"""

from nucleo.contexto import (
    tipo_de_token,
    parse_parametros,
    asignacion_valida,
)
from nucleo.expresiones import evaluar_expresion


def verificar_llamadas(analizador):
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

        # Registrar declaraciones
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

        # Detectar llamada: id '('
        if (tok.tipo == "id" and i + 1 < n
                and tokens[i + 1].tipo == "delim" and tokens[i + 1].lexema == "("):
            nombre_fn = tok.lexema
            args = []
            arg_actual = []
            k = i + 2
            profundidad = 1
            while k < n and profundidad > 0:
                t = tokens[k]
                if t.tipo == "delim" and t.lexema == "(":
                    profundidad += 1
                    arg_actual.append(t)
                    k += 1
                    continue
                if t.tipo == "delim" and t.lexema == ")":
                    profundidad -= 1
                    if profundidad == 0:
                        if arg_actual:
                            args.append(arg_actual)
                        k += 1
                        break
                    arg_actual.append(t)
                    k += 1
                    continue
                if t.tipo == "delim" and t.lexema == "," and profundidad == 1:
                    args.append(arg_actual)
                    arg_actual = []
                    k += 1
                    continue
                arg_actual.append(t)
                k += 1

            if nombre_fn in analizador.firmas_funciones:
                firma = analizador.firmas_funciones[nombre_fn]
                if len(args) != len(firma):
                    analizador._insertar_error(
                        tok, "Número de argumentos incorrecto", errores_reportados
                    )
                else:
                    for tipo_param, arg_tokens in zip(firma, args):
                        if len(arg_tokens) == 1:
                            tipo_arg = tipo_de_token(arg_tokens[0], pila_ambitos)
                            if tipo_arg is not None and not asignacion_valida(tipo_param, tipo_arg):
                                analizador._insertar_error(
                                    arg_tokens[0],
                                    f"Incompatibilidad de tipos, {tipo_param}",
                                    errores_reportados
                                )
                        elif arg_tokens:
                            evaluar_expresion(analizador, arg_tokens, tipo_param, pila_ambitos)
            i = k
            continue

        i += 1