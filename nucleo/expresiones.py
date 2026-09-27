"""
Evaluación de expresiones aritméticas y determinación de culpables.
"""

from nucleo.reglas import REGLAS_ARITMETICAS, REGLAS
from nucleo.contexto import tipo_de_token

def _leer_operando(analizador, expresion, idx, pila):
    """
    Lee el operando que comienza en expresion[idx].
    Si es una llamada a función (id '(' ... ')'), salta hasta su ')' de cierre
    y resuelve el tipo con el tipo de retorno de la función.
    Devuelve (tipo, token_representativo, siguiente_idx).
    """
    tok = expresion[idx]
    if (tok.tipo == "id" and idx + 1 < len(expresion)
            and expresion[idx + 1].tipo == "delim" and expresion[idx + 1].lexema == "("):
        nombre_fn = tok.lexema
        j = idx + 1
        profundidad = 0
        while j < len(expresion):
            t = expresion[j]
            if t.tipo == "delim" and t.lexema == "(":
                profundidad += 1
            elif t.tipo == "delim" and t.lexema == ")":
                profundidad -= 1
                if profundidad == 0:
                    j += 1
                    break
            j += 1
        tipo = analizador.tipos_retorno_funciones.get(nombre_fn)
        return tipo, tok, j
    else:
        tipo = tipo_de_token(tok, pila)
        return tipo, tok, idx + 1

def evaluar_expresion(analizador, expresion, tipo_variable, pila):
    """Recorre la expresión y reporta TODOS los errores (sin duplicados)."""
    if not expresion:
        return None

    errores_reportados = set()

    tipo_actual, operando_actual_tok, i = _leer_operando(analizador, expresion, 0, pila)
    if tipo_actual is None:
        return None

    while i < len(expresion):
        operador = expresion[i]
        if operador.tipo != "op":
            i += 1
            continue
        if i + 1 >= len(expresion):
            return tipo_actual

        tipo_derecho, operando_derecho_tok, siguiente_i = _leer_operando(analizador, expresion, i + 1, pila)
        if tipo_derecho is None:
            i = siguiente_i
            continue

        es_valida, tipo_resultado, culpables = evaluar_operacion(
            tipo_variable, tipo_actual, operador.lexema, tipo_derecho
        )

        if not es_valida:
            for culpable in culpables:
                if culpable == "op":
                    tok_culpable = operador
                elif culpable == "izq":
                    tok_culpable = operando_actual_tok
                else:
                    tok_culpable = operando_derecho_tok

                analizador._insertar_error(
                    tok_culpable,
                    f"Incompatibilidad de tipos, {tipo_variable}",
                    errores_reportados
                )

            tipo_actual = tipo_variable
            operando_actual_tok = operando_derecho_tok
            i = siguiente_i
            continue

        tipo_actual = tipo_resultado
        operando_actual_tok = operando_derecho_tok
        i = siguiente_i

    return tipo_actual


def evaluar_operacion(variable, izq, op, der):
    """Consulta la tabla de reglas semánticas."""
    clave = (variable, izq, op, der)
    if clave in REGLAS_ARITMETICAS:
        return True, REGLAS_ARITMETICAS[clave], []

    culpables = determinar_culpables(variable, izq, op, der)
    return False, None, culpables


def determinar_culpables(variable, izq, op, der):
    """Determina los culpables cuando una operación no es válida."""
    regla = REGLAS.get(variable)
    if regla is None:
        return []

    culpables = []
    if izq not in regla["operandos"]:
        culpables.append("izq")
    if op not in regla["operadores"]:
        culpables.append("op")
    if der not in regla["operandos"]:
        culpables.append("der")
    return culpables