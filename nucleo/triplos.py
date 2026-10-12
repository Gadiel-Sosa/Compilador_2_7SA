"""
Genera la tabla de triplos a partir de los tokens.

Reglas:
  - Notación postfija.
  - Jerarquía: ( ) > * / > + - > =
  - Reutilización de temporales: se usa T1 por defecto, y solo se crean
    T2, T3... cuando hay dos subexpresiones vivas simultáneamente.
  - Toda asignación termina con `VAR T# ORAS` (el resultado regresa a la variable).
"""

from nucleo.token_util import clasificar_token


class Fila:
    """Representa una fila del triplo."""
    def __init__(self, numero, objeto, fuente, operador, descripcion, tipo_fila):
        self.numero = numero
        self.objeto = objeto
        self.fuente = fuente
        self.operador = operador
        self.descripcion = descripcion
        self.tipo_fila = tipo_fila   # "asignacion", "aritmetica", "relacional",
                                     # "logico", "salto_cond", "salto_incond"


class GeneradorTriplos:
    def __init__(self, tokens, catalogo):
        self.tokens = tokens
        self.catalogo = catalogo
        self.filas = []
        self.contador_filas = 0

        # Pila de temporales: maneja cuántos están en uso
        self.temporales_en_uso = []

    # ==========================================================
    # API pública
    # ==========================================================
    def generar(self):
        """Recorre los tokens y genera la tabla de triplos."""
        i = 0
        n = len(self.tokens)
        while i < n:
            tok = self.tokens[i]

            # Detectar if
            if tok.tipo == "reservada" and tok.lexema == "if":
                i = self._procesar_if(i)
                continue

            # Detectar asignación: id = ...
            if (tok.tipo == "id"
                    and i + 1 < n
                    and self.tokens[i + 1].tipo == "op"
                    and self.tokens[i + 1].lexema == "="):
                i = self._procesar_asignacion(i)
                continue

            i += 1

        return self.filas

    # ==========================================================
    # Asignación: id = expresión ;
    # ==========================================================
    def _procesar_asignacion(self, i):
        tok_id = self.tokens[i]
        # i + 1 = '='
        # i + 2 = inicio de la expresión
        # Buscar el ';'
        j = i + 2
        expresion = []
        while j < len(self.tokens) and self.tokens[j].lexema != ";":
            expresion.append(self.tokens[j])
            j += 1

        id_var = self.catalogo.id_de(tok_id.lexema)
        self._generar_expresion_asignacion(id_var, expresion)

        return j + 1   # saltar el ';'

    # ==========================================================
    # Expresión con asignación final a una variable
    # ==========================================================
    def _generar_expresion_asignacion(self, id_var, expresion):
        """Genera los triplos para `id_var = expresión`."""
        if not expresion:
            return

        # Postfijo de la expresión
        postfijo = self._a_postfijo(expresion)

        # Generar filas
        temporal_final = self._evaluar_postfijo(postfijo)

        # Fila de asignación final: VAR T# ORAS
        self._emitir(
            objeto=id_var,
            fuente=temporal_final,
            operador="ORAS",
            descripcion=f"{id_var} = {temporal_final}",
            tipo="asignacion"
        )

    # ==========================================================
    # Postfijo (shunting-yard)
    # ==========================================================
    def _a_postfijo(self, expresion):
        """Convierte una expresión infija (lista de tokens) a postfijo."""
        precedencia = {
            "||": 1,
            "&&": 2,
            "==": 3, "!=": 3,
            "<": 4, ">": 4, "<=": 4, ">=": 4,
            "+": 5, "-": 5,
            "*": 6, "/": 6,
        }

        salida = []
        pila = []

        for tok in expresion:
            # Operando
            if tok.tipo in ("id", "full", "royal", "chain"):
                salida.append(tok)
                continue

            # Paréntesis izquierdo
            if tok.tipo == "delim" and tok.lexema == "(":
                pila.append(tok)
                continue

            # Paréntesis derecho
            if tok.tipo == "delim" and tok.lexema == ")":
                while pila and not (pila[-1].tipo == "delim" and pila[-1].lexema == "("):
                    salida.append(pila.pop())
                if pila:
                    pila.pop()  # quitar el '('
                continue

            # Operador
            if tok.tipo == "op":
                prec_actual = precedencia.get(tok.lexema, 0)
                while pila:
                    tope = pila[-1]
                    if tope.tipo == "delim" and tope.lexema == "(":
                        break
                    if tope.tipo != "op":
                        break
                    prec_tope = precedencia.get(tope.lexema, 0)
                    # Asociatividad izquierda: <=
                    if prec_tope >= prec_actual:
                        salida.append(pila.pop())
                    else:
                        break
                pila.append(tok)
                continue

        while pila:
            salida.append(pila.pop())

        return salida

    # ==========================================================
    # Evaluar postfijo y emitir filas
    # ==========================================================
    def _evaluar_postfijo(self, postfijo):
        """
        Recorre el postfijo y emite filas de triplos.

        Devuelve el temporal (o lexema) que contiene el resultado final.
        """
        pila = []   # cada elemento: (id_simbolico, es_temporal)

        for tok in postfijo:
            # Operando: id o constante
            if tok.tipo in ("id", "full", "royal", "chain"):
                id_sim = self.catalogo.id_de(tok.lexema)
                pila.append((id_sim, False))
                continue

            # Operador binario
            if tok.tipo == "op":
                der, der_es_temp = pila.pop()
                izq, izq_es_temp = pila.pop()

                op_id = self.catalogo.id_de(tok.lexema)

                # Decidir el temporal destino
                if izq_es_temp:
                    t = izq   # reutilizar temporal del izquierdo
                elif der_es_temp:
                    t = der   # reutilizar temporal del derecho
                else:
                    t = self.catalogo.nuevo_temporal()
                    # Fila: T# = izq
                    self._emitir(
                        objeto=t,
                        fuente=izq,
                        operador="ORAS",
                        descripcion=f"{t} = {izq}",
                        tipo="asignacion"
                    )

                # Fila de la operación: T# = T# op der
                self._emitir(
                    objeto=t,
                    fuente=der,
                    operador=op_id,
                    descripcion=f"{t} = {t} {tok.lexema} {der}",
                    tipo=self._tipo_fila_de_operador(tok.lexema)
                )

                pila.append((t, True))

        if not pila:
            return None
        return pila[-1][0]

    # ==========================================================
    # Detectar tipo de fila según operador
    # ==========================================================
    def _tipo_fila_de_operador(self, lexema):
        if lexema in ("+", "-", "*", "/"):
            return "aritmetica"
        if lexema in ("<", ">", "<=", ">=", "==", "!="):
            return "relacional"
        if lexema in ("&&", "||"):
            return "logico"
        return "otro"

    # ==========================================================
    # Emitir fila
    # ==========================================================
    def _emitir(self, objeto, fuente, operador, descripcion, tipo):
        self.contador_filas += 1
        self.filas.append(Fila(
            numero=self.contador_filas,
            objeto=objeto,
            fuente=fuente,
            operador=operador,
            descripcion=descripcion,
            tipo_fila=tipo
        ))

    # ==========================================================
    # IF (pendiente de implementar aquí)
    # ==========================================================
    def _procesar_if(self, i):
        # TODO: implementar generación de if / if-else con backpatching
        # Por ahora, saltamos el if para no romper.
        return i + 1


# ==========================================================
def generar_triplos(analizador):
    """Punto de entrada: construye el catálogo y genera la tabla."""
    from nucleo.catalogo_tokens import construir_catalogo
    catalogo = construir_catalogo(analizador.tokens)
    gen = GeneradorTriplos(analizador.tokens, catalogo)
    filas = gen.generar()
    return filas, catalogo