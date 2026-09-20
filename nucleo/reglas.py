"""
Tabla de reglas semánticas para las operaciones aritméticas.
Basada en el PDF de la profesora (Unidad I. Análisis Semántico IV).

La clave es una tupla (variable, izq, op, der) donde:
  - variable: tipo de la variable de asignación
  - izq:      tipo del operando izquierdo
  - op:       operador ("+", "-", "*", "/")
  - der:      tipo del operando derecho

El valor es el tipo resultante de la operación.
Si una combinación NO está en esta tabla → error semántico.
"""

REGLAS_ARITMETICAS = {
    # ---------- full ----------
    ("full", "full", "+", "full"): "full",
    ("full", "full", "-", "full"): "full",
    ("full", "full", "*", "full"): "full",

    # ---------- royal = full OPA full ----------
    ("royal", "full", "+", "full"): "royal",
    ("royal", "full", "-", "full"): "royal",
    ("royal", "full", "*", "full"): "royal",
    ("royal", "full", "/", "full"): "royal",

    # ---------- royal = full OPA royal ----------
    ("royal", "full", "+", "royal"): "royal",
    ("royal", "full", "-", "royal"): "royal",
    ("royal", "full", "*", "royal"): "royal",
    ("royal", "full", "/", "royal"): "royal",

    # ---------- royal = royal OPA full ----------
    ("royal", "royal", "+", "full"): "royal",
    ("royal", "royal", "-", "full"): "royal",
    ("royal", "royal", "*", "full"): "royal",
    ("royal", "royal", "/", "full"): "royal",

    # ---------- royal = royal OPA royal ----------
    ("royal", "royal", "+", "royal"): "royal",
    ("royal", "royal", "-", "royal"): "royal",
    ("royal", "royal", "*", "royal"): "royal",
    ("royal", "royal", "/", "royal"): "royal",

    # ---------- chain ----------
    ("chain", "chain", "+", "chain"): "chain",
    ("chain", "chain", "-", "chain"): "chain",
}

REGLAS = {
    "full":  {"operandos": {"full"},          "operadores": {"+", "-", "*"}},
    "royal": {"operandos": {"full", "royal"}, "operadores": {"+", "-", "*", "/"}},
    "chain": {"operandos": {"chain"},         "operadores": {"+", "-"}},
}