"""
Genera la tabla de triplos a partir de los tokens.

Reglas:
  - Notación postfija para expresiones aritméticas y relacionales.
  - Jerarquía: ( ) > * / > + - > < > <= >= == != > && > || > =
  - Reutilización de temporales.
  - Backpatching para if / if-else con saltos TRUE/FALSE y JMP.
  - Funciones: JMP de salto al definir, JMP de retorno, asignación
    de argumentos a parámetros y recepción del valor retornado.
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

    def __repr__(self):
        return f"Fila({self.numero}, obj={self.objeto!r}, fte={self.fuente!r}, op={self.operador!r})"


class GeneradorTriplos:
    def __init__(self, tokens, catalogo):
        self.tokens = tokens
        self.catalogo = catalogo
        self.filas = []
        self.contador_filas = 0
        # nombre -> {"inicio_cuerpo", "jmp_retorno", "var_retorno", "jmp_salida"}
        self.funciones = {}

    # ==========================================================
    # API pública
    # ==========================================================
    def generar(self):
        i = 0
        n = len(self.tokens)
        while i < n:
            tok = self.tokens[i]

            # Definición de función: tipo id ( ... ) { ... }
            if self._es_definicion_funcion(i):
                i = self._procesar_definicion_funcion(i)
                continue

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
    # Detección de definición de función
    # ==========================================================
    def _es_definicion_funcion(self, i):
        toks = self.tokens
        n = len(toks)
        if i >= n:
            return False
        if not (toks[i].tipo == "reservada" and toks[i].lexema in ("full", "royal", "chain", "void")):
            return False
        if i + 1 >= n or toks[i + 1].tipo != "id":
            return False
        # El nombre no debe estar en medio de una llamada (id seguido de '=')
        if i + 2 >= n or not (toks[i + 2].tipo == "delim" and toks[i + 2].lexema == "("):
            return False
        # Descartar declaraciones con inicialización: tipo id = ...
        return True

    def _procesar_definicion_funcion(self, i):
        """
        Genera:
          fila JMP  -> salto sobre el cuerpo (al final de la función)
          [cuerpo de la función]
          fila JMP  -> retorno (parchada al final del cuerpo)
        Guarda metadatos en self.funciones.
        """
        tokens = self.tokens
        n = len(tokens)

        tipo_retorno = tokens[i].lexema
        nombre_fn = tokens[i + 1].lexema

        # 1) JMP de salto sobre la función (se parcha luego)
        fila_jmp_salida = self._emitir(
            objeto="", fuente=None, operador="JMP",
            descripcion="", tipo="salto_incond"
        )

        # 2) Saltar parámetros hasta ')' que cierra la firma
        k = i + 2  # apunta a '('
        params = []
        profundidad = 0
        while k < n:
            t = tokens[k]
            if t.tipo == "delim" and t.lexema == "(":
                profundidad += 1
            elif t.tipo == "delim" and t.lexema == ")":
                profundidad -= 1
                if profundidad == 0:
                    k += 1
                    break
            elif profundidad == 1 and t.tipo == "reservada" and t.lexema in ("full", "royal", "chain"):
                if k + 1 < n and tokens[k + 1].tipo == "id":
                    params.append(tokens[k + 1].lexema)
            k += 1

        # 3) Cuerpo de la función
        inicio_cuerpo = self.contador_filas + 1
        if k < n and tokens[k].tipo == "delim" and tokens[k].lexema == "{":
            k = self._generar_bloque(k + 1)
        # (k apunta al token después del '}' de cierre)

        # 4) JMP de retorno (vuelve a la instrucción siguiente a la llamada)
        fila_jmp_retorno = self._emitir(
            objeto="", fuente=None, operador="JMP",
            descripcion="", tipo="salto_incond"
        )

        # 5) Registrar metadatos de la función
        self.funciones[nombre_fn] = {
            "inicio_cuerpo": inicio_cuerpo,
            "jmp_retorno": fila_jmp_retorno,
            "jmp_salida": fila_jmp_salida,
            "params": params,
            "tipo_retorno": tipo_retorno,
            "var_retorno": None,   # se rellena cuando aparece 'return'
        }

        # Parchar el JMP de salida: ir a la primera fila después de la función
        fila_jmp_salida.fuente = str(self.contador_filas + 1)

        return k

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

        # ¿Es una llamada a función en el lado derecho?
        nombre_fn = self._es_llamada_completa(expresion)
        if nombre_fn is not None and nombre_fn in self.funciones:
            self._generar_llamada(tok_id.lexema, nombre_fn, expresion)
            return j + 1

        self._generar_expresion_asignacion(tok_id.lexema, expresion)
        return j + 1

    def _es_llamada_completa(self, expresion):
        """Devuelve el nombre de función si expresion es exactamente id ( ... )."""
        if len(expresion) < 3:
            return None
        if expresion[0].tipo != "id":
            return None
        if not (expresion[1].tipo == "delim" and expresion[1].lexema == "("):
            return None
        if not (expresion[-1].tipo == "delim" and expresion[-1].lexema == ")"):
            return None
        profundidad = 0
        for idx, tok in enumerate(expresion[1:], start=1):
            if tok.tipo == "delim" and tok.lexema == "(":
                profundidad += 1
            elif tok.tipo == "delim" and tok.lexema == ")":
                profundidad -= 1
                if profundidad == 0 and idx != len(expresion) - 1:
                    return None
        return expresion[0].lexema

    # ==========================================================
    # Llamada a función con parámetros
    # ==========================================================
    def _generar_llamada(self, id_asignacion, nombre_fn, expresion):
        """
        Genera (siguiendo el PDF):
          - Asignación de cada argumento a su parámetro: param = arg
          - JMP al inicio del cuerpo de la función
          - [backpatch: JMP de retorno salta aquí]
          - T# = var_retorno
          - id = T#
        """
        meta = self.funciones[nombre_fn]
        params = meta["params"]

        # 1) Parsear argumentos
        args = self._parsear_argumentos(expresion)

        # 2) Asignar cada argumento a su parámetro (antes del JMP)
        for idx, arg_tokens in enumerate(args):
            if idx >= len(params):
                break
            nombre_param = params[idx]
            # Evaluar expresión del argumento en temporales
            self._generar_expresion_asignacion(nombre_param, arg_tokens)

        # 3) JMP al inicio del cuerpo de la función
        self._emitir(
            objeto="", fuente=str(meta["inicio_cuerpo"]), operador="JMP",
            descripcion="", tipo="salto_incond"
        )

        # 4) Aquí regresa la función: parchar su JMP de retorno
        meta["jmp_retorno"].fuente = str(self.contador_filas + 1)

        # 5) T# = var_retorno  (recibe el valor retornado)
        var_retorno = meta["var_retorno"] or "?"
        t = self.catalogo.nuevo_temporal()
        self._emitir(
            objeto=t, fuente=var_retorno, operador="=",
            descripcion=f"{t} = {var_retorno}", tipo="asignacion"
        )

        # 6) id = T#
        self._emitir(
            objeto=id_asignacion, fuente=t, operador="=",
            descripcion=f"{id_asignacion} = {t}", tipo="asignacion"
        )

        self.catalogo.reiniciar_temporales()

    def _parsear_argumentos(self, expresion):
        """Divide los tokens entre '(' ... ')' de una llamada en argumentos."""
        # expresion = [ id, '(', ..., ')' ]
        args = []
        actual = []
        profundidad = 0
        for idx, tok in enumerate(expresion):
            if idx == 0:
                continue
            if tok.tipo == "delim" and tok.lexema == "(":
                profundidad += 1
                if profundidad == 1:
                    continue
            if tok.tipo == "delim" and tok.lexema == ")":
                profundidad -= 1
                if profundidad == 0:
                    if actual:
                        args.append(actual)
                    break
            if tok.tipo == "delim" and tok.lexema == "," and profundidad == 1:
                args.append(actual)
                actual = []
                continue
            actual.append(tok)
        return args

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
    # Evaluar postfijo
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
                        objeto=t, fuente=der, operador=tok.lexema,
                        descripcion=f"{t} = {t} {tok.lexema} {der}",
                        tipo=self._tipo_fila_de_operador(tok.lexema)
                    )
                else:
                    t = self.catalogo.nuevo_temporal()
                    self._emitir(
                        objeto=t, fuente=izq, operador="=",
                        descripcion=f"{t} = {izq}", tipo="asignacion"
                    )
                    self._emitir(
                        objeto=t, fuente=der, operador=tok.lexema,
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
            objeto=objeto, fuente=fuente, operador=operador,
            descripcion=descripcion, tipo_fila=tipo
        )
        self.filas.append(fila)
        return fila

    def _reservar_fila(self):
        self.contador_filas += 1
        return self.contador_filas

    def _parchar(self, lista_filas, destino):
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
    # Condición con backpatching
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

            # Sub-función anidada (no permitida, pero por seguridad)
            if self._es_definicion_funcion(j):
                j = self._procesar_definicion_funcion(j)
                continue

            # return
            if tok.tipo == "reservada" and tok.lexema == "return":
                j = self._procesar_return(j)
                continue

            if tok.tipo == "reservada" and tok.lexema == "if":
                j = self._procesar_if(j)
                continue

            if (tok.tipo == "id" and j + 1 < n
                    and tokens[j + 1].tipo == "op" and tokens[j + 1].lexema == "="):
                j = self._procesar_asignacion(j)
                continue

            # Llamada como sentencia: id ( ... ) ;
            if (tok.tipo == "id" and j + 1 < n
                    and tokens[j + 1].tipo == "delim" and tokens[j + 1].lexema == "("
                    and tok.lexema in self.funciones):
                j = self._procesar_llamada_como_sentencia(j)
                continue

            j += 1
        return j

    # ==========================================================
    # Sentencia return
    # ==========================================================
    def _procesar_return(self, i):
        tokens = self.tokens
        n = len(tokens)
        j = i + 1
        expresion = []
        while j < n and tokens[j].lexema != ";":
            expresion.append(tokens[j])
            j += 1

        # ¿A qué función pertenece este return?
        nombre_fn = self._funcion_actual()
        if nombre_fn is not None and expresion:
            # Guardamos el nombre de la variable retornada.
            # Si es una sola variable: r1 -> var_retorno = "r1"
            if len(expresion) == 1 and expresion[0].tipo == "id":
                self.funciones[nombre_fn]["var_retorno"] = expresion[0].lexema
            else:
                # Evaluar expresión y guardar el temporal resultado
                postfijo = self._a_postfijo(expresion)
                if len(postfijo) == 1:
                    valor = postfijo[0].lexema
                    t = self.catalogo.nuevo_temporal()
                    self._emitir(
                        objeto=t, fuente=valor, operador="=",
                        descripcion=f"{t} = {valor}", tipo="asignacion"
                    )
                    self.funciones[nombre_fn]["var_retorno"] = t
                else:
                    temporal_final = self._evaluar_postfijo(postfijo)
                    self.funciones[nombre_fn]["var_retorno"] = temporal_final

        return j + 1

    def _funcion_actual(self):
        """Devuelve el nombre de la función 'más reciente' abierta."""
        if not self.funciones:
            return None
        # Asumimos que la última definida es la función actual.
        # (Para código bien estructurado, coincide con la función cuyo
        # cuerpo estamos recorriendo.)
        return list(self.funciones.keys())[-1]

    def _procesar_llamada_como_sentencia(self, i):
        tokens = self.tokens
        n = len(tokens)
        nombre_fn = tokens[i].lexema
        # Encontrar el cierre del ')' de la llamada
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
            k += 1
        expresion = [tokens[i]] + tokens[i + 1:k]
        self._generar_llamada("_", nombre_fn, expresion)
        return k + 1 if k < n and tokens[k].lexema == ";" else k

    # ==========================================================
    # IF / IF-ELSE con backpatching
    # ==========================================================
    def _procesar_if(self, i):
        tokens = self.tokens
        n = len(tokens)

        j = i + 2
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