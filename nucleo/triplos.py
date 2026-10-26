"""
Genera la tabla de triplos a partir de los tokens.

Reglas:
  - Notación postfija para expresiones aritméticas y relacionales.
  - Jerarquía: ( ) > * / > + - > < > <= >= == != > && > || > =
  - Reutilización de temporales.
  - Backpatching para if / if-else con saltos TRUE/FALSE y JMP.
"""


class Fila:
    """Representa una fila del triplo."""
    def __init__(self, numero, objeto, fuente, operador, descripcion, tipo_fila):
        self.numero = numero
        self.objeto = objeto
        self.fuente = fuente
        self.operador = operador
        self.descripcion = descripcion
        self.tipo_fila = tipo_fila


class GeneradorTriplos:
    def __init__(self, tokens, catalogo):
        self.tokens = tokens
        self.catalogo = catalogo
        self.filas = []
        self.contador_filas = 0

    # ==========================================================
    # API pública
    # ==========================================================
    def generar(self):
        i = 0
        n = len(self.tokens)
        while i < n:
            tok = self.tokens[i]

            if tok.tipo == "reservada" and tok.lexema == "if":
                i = self._procesar_if(i)
                continue

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
        j = i + 2
        expresion = []
        while j < len(self.tokens) and self.tokens[j].lexema != ";":
            expresion.append(self.tokens[j])
            j += 1

        self._generar_expresion_asignacion(tok_id.lexema, expresion)
        return j + 1

    def _generar_expresion_asignacion(self, id_var, expresion):
        if not expresion:
            return

        postfijo = self._a_postfijo(expresion)

        if len(postfijo) == 1:
            valor = postfijo[0].lexema
            t = self.catalogo.nuevo_temporal()
            self._emitir(
                objeto=t, fuente=valor, operador="=",
                descripcion=f"{t} = {valor}", tipo="asignacion"
            )
            temporal_final = t
        else:
            temporal_final = self._evaluar_postfijo(postfijo)

        self._emitir(
            objeto=id_var,
            fuente=temporal_final,
            operador="=",
            descripcion=f"{id_var} = {temporal_final}",
            tipo="asignacion"
        )
        
        self.catalogo.reiniciar_temporales()

    # ==========================================================
    # Postfijo (shunting-yard)
    # ==========================================================
    def _a_postfijo(self, expresion):
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
            if tok.tipo in ("id", "full", "royal", "chain"):
                salida.append(tok)
                continue

            if tok.tipo == "delim" and tok.lexema == "(":
                pila.append(tok)
                continue

            if tok.tipo == "delim" and tok.lexema == ")":
                while pila and not (pila[-1].tipo == "delim" and pila[-1].lexema == "("):
                    salida.append(pila.pop())
                if pila:
                    pila.pop()
                continue

            if tok.tipo == "op":
                prec_actual = precedencia.get(tok.lexema, 0)
                while pila:
                    tope = pila[-1]
                    if tope.tipo == "delim" and tope.lexema == "(":
                        break
                    if tope.tipo != "op":
                        break
                    prec_tope = precedencia.get(tope.lexema, 0)
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
    # Evaluar postfijo y emitir filas (sirve para aritmética y relacional)
    # ==========================================================
    def _evaluar_postfijo(self, postfijo):
        pila = []

        for tok in postfijo:
            if tok.tipo in ("id", "full", "royal", "chain"):
                pila.append((tok.lexema, False))
                continue

            if tok.tipo == "op":
                der, der_es_temp = pila.pop()
                izq, izq_es_temp = pila.pop()

                if izq_es_temp:
                    t = izq
                    self._emitir(
                        objeto=t,
                        fuente=der,
                        operador=tok.lexema,
                        descripcion=f"{t} = {t} {tok.lexema} {der}",
                        tipo=self._tipo_fila_de_operador(tok.lexema)
                    )
                else:
                    t = self.catalogo.nuevo_temporal()
                    self._emitir(
                        objeto=t,
                        fuente=izq,
                        operador="=",
                        descripcion=f"{t} = {izq}",
                        tipo="asignacion"
                    )
                    self._emitir(
                        objeto=t,
                        fuente=der,
                        operador=tok.lexema,
                        descripcion=f"{t} = {t} {tok.lexema} {der}",
                        tipo=self._tipo_fila_de_operador(tok.lexema)
                    )

                pila.append((t, True))

        if not pila:
            return None
        return pila[-1][0]

    def _tipo_fila_de_operador(self, lexema):
        if lexema in ("+", "-", "*", "/"):
            return "aritmetica"
        if lexema in ("<", ">", "<=", ">=", "==", "!="):
            return "relacional"
        if lexema in ("&&", "||"):
            return "logico"
        return "otro"

    # ==========================================================
    # Emitir / reservar fila
    # ==========================================================
    def _emitir(self, objeto, fuente, operador, descripcion, tipo):
        self.contador_filas += 1
        fila = Fila(
            numero=self.contador_filas,
            objeto=objeto,
            fuente=fuente,
            operador=operador,
            descripcion=descripcion,
            tipo_fila=tipo
        )
        self.filas.append(fila)
        return fila

    def _reservar_fila(self):
        """Reserva un número de fila sin emitirla (if sin else)."""
        self.contador_filas += 1
        return self.contador_filas

    def _parchar(self, lista_filas, destino):
        """Parcha el campo 'operador' (destino del salto) de cada fila TRUE/FALSE."""
        for fila in lista_filas:
            fila.operador = str(destino)

    # ==========================================================
    # Utilidades de parseo de la condición
    # ==========================================================
    def _split_top_level(self, tokens, operador_lexema):
        grupos = []
        actual = []
        profundidad = 0
        for tok in tokens:
            if tok.tipo == "delim" and tok.lexema == "(":
                profundidad += 1
                actual.append(tok)
                continue
            if tok.tipo == "delim" and tok.lexema == ")":
                profundidad -= 1
                actual.append(tok)
                continue
            if profundidad == 0 and tok.tipo == "op" and tok.lexema == operador_lexema:
                grupos.append(actual)
                actual = []
                continue
            actual.append(tok)
        grupos.append(actual)
        return grupos

    def _contiene_top_level(self, tokens, operador_lexema):
        profundidad = 0
        for tok in tokens:
            if tok.tipo == "delim" and tok.lexema == "(":
                profundidad += 1
            elif tok.tipo == "delim" and tok.lexema == ")":
                profundidad -= 1
            elif profundidad == 0 and tok.tipo == "op" and tok.lexema == operador_lexema:
                return True
        return False

    def _parens_cubren_todo(self, tokens):
        if not tokens:
            return False
        if not (tokens[0].tipo == "delim" and tokens[0].lexema == "(" and
                tokens[-1].tipo == "delim" and tokens[-1].lexema == ")"):
            return False
        profundidad = 0
        for idx, tok in enumerate(tokens):
            if tok.tipo == "delim" and tok.lexema == "(":
                profundidad += 1
            elif tok.tipo == "delim" and tok.lexema == ")":
                profundidad -= 1
                if profundidad == 0 and idx != len(tokens) - 1:
                    return False
        return True

    # ==========================================================
    # Condición con backpatching: OR -> AND -> atom
    # ==========================================================
    def _procesar_condicion(self, tokens):
        return self._procesar_or(tokens)

    def _procesar_or(self, tokens):
        terminos = self._split_top_level(tokens, "||")
        if len(terminos) == 1:
            return self._procesar_and(terminos[0])

        truelist, falselist = self._procesar_and(terminos[0])
        for termino in terminos[1:]:
            self._parchar(falselist, self.contador_filas + 1)
            truelist2, falselist2 = self._procesar_and(termino)
            truelist = truelist + truelist2
            falselist = falselist2
        return truelist, falselist

    def _procesar_and(self, tokens):
        terminos = self._split_top_level(tokens, "&&")
        if len(terminos) == 1:
            return self._procesar_atom(terminos[0])

        truelist, falselist = self._procesar_atom(terminos[0])
        for termino in terminos[1:]:
            self._parchar(truelist, self.contador_filas + 1)
            truelist2, falselist2 = self._procesar_atom(termino)
            falselist = falselist + falselist2
            truelist = truelist2
        return truelist, falselist

    def _procesar_atom(self, tokens):
        if self._parens_cubren_todo(tokens):
            interior = tokens[1:-1]
            if self._contiene_top_level(interior, "&&") or self._contiene_top_level(interior, "||"):
                return self._procesar_or(interior)

        postfijo = self._a_postfijo(tokens)
        resultado = self._evaluar_postfijo(postfijo)
        if resultado is None:
            return [], []

        if len(postfijo) == 1:
            # Operando suelto sin operador relacional: forzar T# = operando
            t = self.catalogo.nuevo_temporal()
            self._emitir(
                objeto=t, fuente=resultado, operador="=",
                descripcion=f"{t} = {resultado}", tipo="asignacion"
            )

        fila_true = self._emitir(objeto="", fuente="TRUE", operador=None,
                                   descripcion="", tipo="salto_cond")
        fila_false = self._emitir(objeto="", fuente="FALSE", operador=None,
                                    descripcion="", tipo="salto_cond")
        self.catalogo.reiniciar_temporales()
        return [fila_true], [fila_false]

    # ==========================================================
    # Bloque { ... }
    # ==========================================================
    def _generar_bloque(self, j):
        tokens = self.tokens
        n = len(tokens)
        while j < n:
            tok = tokens[j]
            if tok.tipo == "delim" and tok.lexema == "}":
                return j + 1
            if tok.tipo == "reservada" and tok.lexema == "if":
                j = self._procesar_if(j)
                continue
            if (tok.tipo == "id" and j + 1 < n
                    and tokens[j + 1].tipo == "op" and tokens[j + 1].lexema == "="):
                j = self._procesar_asignacion(j)
                continue
            j += 1
        return j

    # ==========================================================
    # IF / IF-ELSE con backpatching
    # ==========================================================
    def _procesar_if(self, i):
        tokens = self.tokens
        n = len(tokens)

        j = i + 2  # saltar 'if' y '('
        condicion = []
        profundidad = 1
        while j < n and profundidad > 0:
            t = tokens[j]
            if t.tipo == "delim" and t.lexema == "(":
                profundidad += 1
            elif t.tipo == "delim" and t.lexema == ")":
                profundidad -= 1
                if profundidad == 0:
                    j += 1
                    break
            condicion.append(t)
            j += 1

        truelist, falselist = self._procesar_condicion(condicion)
        self._parchar(truelist, self.contador_filas + 1)

        if j < n and tokens[j].tipo == "delim" and tokens[j].lexema == "{":
            j = self._generar_bloque(j + 1)

        if j < n and tokens[j].tipo == "reservada" and tokens[j].lexema == "else":
            fila_jmp = self._emitir(objeto="", fuente=None, operador="JMP",
                                      descripcion="", tipo="salto_incond")
            self._parchar(falselist, self.contador_filas + 1)
            j += 1
            if j < n and tokens[j].tipo == "delim" and tokens[j].lexema == "{":
                j = self._generar_bloque(j + 1)
            fila_jmp.fuente = str(self.contador_filas + 1)
        else:
            self._reservar_fila()
            self._parchar(falselist, self.contador_filas + 1)

        return j


def generar_triplos(analizador):
    from nucleo.catalogo_tokens import construir_catalogo
    catalogo = construir_catalogo(analizador.tokens)
    gen = GeneradorTriplos(analizador.tokens, catalogo)
    filas = gen.generar()
    return filas, catalogo