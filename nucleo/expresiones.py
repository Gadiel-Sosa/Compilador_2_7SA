"""
Evaluación de expresiones aritméticas y determinación de culpables.
"""

from nucleo.reglas import REGLAS_ARITMETICAS, REGLAS
from nucleo.contexto import tipo_de_token


def evaluar_expresion(analizador, expresion, tipo_variable, pila):
    """Recorre la expresión y reporta TODOS los errores (sin duplicados)."""
    if not expresion:
        return None

    errores_reportados = set()

    operando_actual_tok = expresion[0]
    tipo_actual = tipo_de_token(operando_actual_tok, pila)
    if tipo_actual is None:
        return None

    i = 1
    while i < len(expresion):
        operador = expresion[i]
        if operador.tipo != "op":
            i += 1
            continue
        if i + 1 >= len(expresion):
            return tipo_actual

        operando_derecho_tok = expresion[i + 1]
        tipo_derecho = tipo_de_token(operando_derecho_tok, pila)
        if tipo_derecho is None:
            i += 2
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
            i += 2
            continue

        tipo_actual = tipo_resultado
        operando_actual_tok = operando_derecho_tok
        i += 2

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