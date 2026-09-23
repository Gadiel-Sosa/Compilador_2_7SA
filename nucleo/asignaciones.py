"""
Fase 4: verifica asignaciones (id = expresión ;).
"""

from nucleo.contexto import (
    buscar_tipo_en_pila,
    tipo_de_token,
    parse_parametros,
    asignacion_valida,
)
from nucleo.expresiones import evaluar_expresion


def verificar_asignaciones(analizador):
    tokens = analizador.tokens
    n = len(tokens)

    pila_ambitos = [{}]
    i = 0
    while i < n:
        tok = tokens[i]

        # Actualizar pila de ámbitos
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

                # Función
                if k < n and tokens[k].tipo == "delim" and tokens[k].lexema == "(":
                    if nombre not in pila_ambitos[-1]:
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
                    # Variables
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
                        if var not in pila_ambitos[-1]:
                            pila_ambitos[-1][var] = tipo_decl
                    i = m
                    continue

        # Detectar asignación
        if (tok.tipo == "id"
            and i + 1 < n
            and tokens[i + 1].tipo == "op"
            and tokens[i + 1].lexema == "="):

            identificador = tok.lexema
            tipo_variable = buscar_tipo_en_pila(pila_ambitos, identificador)

            if tipo_variable is None:
                i += 2
                continue

            if i + 2 < n:
                j = i + 2
                expresion = []
                while j < n and tokens[j].lexema != ";":
                    expresion.append(tokens[j])
                    j += 1

                if len(expresion) == 1:
                    tokk = expresion[0]
                    tipo_expresion = tipo_de_token(tokk, pila_ambitos)
                    if tipo_expresion is not None and \
                            not asignacion_valida(tipo_variable, tipo_expresion):
                        errores_reportados = set()
                        analizador._insertar_error(
                            tokk,
                            f"Incompatibilidad de tipos, {tipo_variable}",
                            errores_reportados
                        )
                else:
                    nombre_fn_llamada = _es_llamada_completa(expresion)
                    if nombre_fn_llamada is not None and \
                            nombre_fn_llamada in analizador.tipos_retorno_funciones:
                        tipo_retorno = analizador.tipos_retorno_funciones[nombre_fn_llamada]
                        if not asignacion_valida(tipo_variable, tipo_retorno):
                            errores_reportados = set()
                            analizador._insertar_error(
                                expresion[0],
                                f"Incompatibilidad de tipos, {tipo_variable}",
                                errores_reportados
                            )
                    else:
                        evaluar_expresion(analizador, expresion, tipo_variable, pila_ambitos)

            i += 2
            continue

        i += 1
        
        
def _es_llamada_completa(expresion):
    """Devuelve el nombre de función si expresion es exactamente id '(' ... ')'."""
    if len(expresion) < 3:
        return None
    if expresion[0].tipo != "id":
        return None
    if not (expresion[1].tipo == "delim" and expresion[1].lexema == "("):
        return None
    if not (expresion[-1].tipo == "delim" and expresion[-1].lexema == ")"):
        return None
    profundidad = 0
    for tok in expresion[1:]:
        if tok.tipo == "delim" and tok.lexema == "(":
            profundidad += 1
        elif tok.tipo == "delim" and tok.lexema == ")":
            profundidad -= 1
            if profundidad == 0 and tok is not expresion[-1]:
                return None
    return expresion[0].lexema