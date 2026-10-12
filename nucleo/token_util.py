"""
Clasifica un token en una categoría del catálogo:
  - IDE  → identificador
  - CE   → constante (entera, real, cadena)
  - OA   → operador aritmético
  - OR   → operador relacional
  - OL   → operador lógico
  - ORAS → asignación
  - None → no aplica (reservadas, delimitadores, etc.)
"""

OPERADORES_ARITMETICOS = {"+", "-", "*", "/"}
OPERADORES_RELACIONALES = {"<", ">", "<=", ">=", "==", "!="}
OPERADORES_LOGICOS = {"&&", "||"}


def clasificar_token(tok):
    """Devuelve la categoría del token o None si no aplica."""
    if tok.tipo == "id":
        return "IDE"

    if tok.tipo in ("full", "royal", "chain"):
        # Son literales (enteros, reales, cadenas)
        return "CE"

    if tok.tipo == "op":
        if tok.lexema == "=":
            return "ORAS"
        if tok.lexema in OPERADORES_ARITMETICOS:
            return "OA"
        if tok.lexema in OPERADORES_RELACIONALES:
            return "OR"
        if tok.lexema in OPERADORES_LOGICOS:
            return "OL"

    return None