"""
Utilidades compartidas para el análisis semántico:
- Búsqueda jerárquica de tipos en la pila de ámbitos.
- Parseo de listas de parámetros de funciones.
- Helpers para obtener el tipo de un token.
"""


def buscar_tipo_en_pila(pila, nombre):
    """Busca un tipo en la pila de ámbitos: local → padre → global."""
    for ambito in reversed(pila):
        if nombre in ambito:
            return ambito[nombre]
    return None


def tipo_de_token(token, pila):
    """Devuelve el tipo semántico de un token, o None."""
    if token.tipo == "full":
        return "full"
    if token.tipo == "royal":
        return "royal"
    if token.tipo == "chain":
        return "chain"
    if token.tipo == "id":
        return buscar_tipo_en_pila(pila, token.lexema)
    return None


def parse_parametros(tokens, k, n):
    """
    A partir de k (justo después del '(' de una función), extrae los
    parámetros como (tipo, token_id) y retorna (params, k) donde k
    queda apuntando justo después del ')' que cierra.
    """
    params = []
    profundidad = 1
    while k < n and profundidad > 0:
        t = tokens[k]
        if t.tipo == "delim" and t.lexema == "(":
            profundidad += 1
            k += 1
            continue
        if t.tipo == "delim" and t.lexema == ")":
            profundidad -= 1
            k += 1
            continue
        if profundidad == 1 and t.tipo == "reservada" and t.lexema in ("full", "royal", "chain"):
            if k + 1 < n and tokens[k + 1].tipo == "id":
                params.append((t.lexema, tokens[k + 1]))
                k += 2
                continue
        k += 1
    return params, k


def asignacion_valida(tipo_var, tipo_exp):
    """Aplica las reglas de asignación del PDF."""
    if tipo_var == "full" and tipo_exp == "full":
        return True
    if tipo_var == "royal" and tipo_exp in ("full", "royal"):
        return True
    if tipo_var == "chain" and tipo_exp == "chain":
        return True
    return False