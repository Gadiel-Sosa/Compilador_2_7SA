"""
Analizador semántico: recorre los tokens, construye la tabla de símbolos,
y verifica que las asignaciones y operaciones respeten las reglas del PDF.
"""

from nucleo.reglas import REGLAS_ARITMETICAS


class Resultado:
    """Encapsula el resultado del análisis."""

    def __init__(self):
        self.simbolos = []    # lista de (lexema, tipo)
        self.errores = []     # lista de (token, lexema, renglon, descripcion)


class Analizador:
    """Realiza el análisis semántico sobre la lista de tokens."""

    def __init__(self, tokens):
        self.tokens = tokens
        self.tipos_declarados = {}   # {lexema: tipo}
        self.resultado = Resultado()
        self.contador_errores = 0


    def analizar(self):
        """Ejecuta las fases del análisis y devuelve el resultado."""
        self._inferir_tipos_declarados()
        self._llenar_tabla_simbolos()
        self._verificar_asignaciones()
        return self.resultado

    # ---------------------------------------------------------
    # Fase 1: inferir tipos declarados
    # ---------------------------------------------------------
    def _inferir_tipos_declarados(self):
        """Recorre los tokens buscando declaraciones de tipos."""
        tokens = self.tokens
        n = len(tokens)
        i = 0
        while i < n:
            tok = tokens[i]
            if tok.tipo == "reservada" and tok.lexema in ("full", "royal", "chain", "void"):
                tipo_decl = tok.lexema
                renglon_decl = tok.renglon
                j = i + 1

                if j < n and tokens[j].tipo == "id":
                    nombre = tokens[j].lexema
                    k = j + 1

                    if k < n and tokens[k].tipo == "delim" and tokens[k].lexema == "(":
                        # Función
                        self.tipos_declarados[nombre] = tipo_decl
                        profundidad = 1
                        k += 1
                        while k < n and profundidad > 0:
                            if tokens[k].tipo == "delim" and tokens[k].lexema == "(":
                                profundidad += 1
                            elif tokens[k].tipo == "delim" and tokens[k].lexema == ")":
                                profundidad -= 1
                            k += 1
                        i = k
                        continue
                    else:
                        # Declaración de variables (hasta ';' o cambio de línea)
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
                            self.tipos_declarados[var] = tipo_decl
                        i = m
            i += 1

    # ---------------------------------------------------------
    # Fase 2: llenar la tabla de símbolos
    # ---------------------------------------------------------
    def _llenar_tabla_simbolos(self):
        lexemas_insertados = set()

        for tok in self.tokens:
            # Palabras reservadas de tipo
            if tok.tipo == "reservada":
                if tok.lexema in ("full", "royal", "chain", "void"):
                    if tok.lexema not in lexemas_insertados:
                        self.resultado.simbolos.append((tok.lexema, ""))
                        lexemas_insertados.add(tok.lexema)
                continue

            # Operadores y delimitadores (tipo vacío)
            if tok.tipo in ("op", "delim"):
                if tok.lexema in lexemas_insertados:
                    continue
                self.resultado.simbolos.append((tok.lexema, ""))
                lexemas_insertados.add(tok.lexema)
                continue

            # Solo id y literales
            if tok.tipo not in ("id", "full", "royal", "chain"):
                continue

            if tok.lexema in lexemas_insertados:
                continue

            if tok.tipo == "id":
                tipo_tabla = self.tipos_declarados.get(tok.lexema, "")
            else:
                tipo_tabla = tok.tipo

            self.resultado.simbolos.append((tok.lexema, tipo_tabla))
            lexemas_insertados.add(tok.lexema)

    # ---------------------------------------------------------
    # Fase 3: verificar asignaciones
    # ---------------------------------------------------------
    def _verificar_asignaciones(self):
        tokens = self.tokens
        i = 0
        while i < len(tokens):
            token = tokens[i]

            if (
                token.tipo == "id"
                and i + 1 < len(tokens)
                and tokens[i + 1].tipo == "op"
                and tokens[i + 1].lexema == "="
            ):
                identificador = token.lexema
                tipo_variable = self.tipos_declarados.get(identificador)

                if tipo_variable is None:
                    i += 2
                    continue

                if i + 2 < len(tokens):
                    j = i + 2
                    expresion = []
                    while j < len(tokens) and tokens[j].lexema != ";":
                        expresion.append(tokens[j])
                        j += 1

                    if len(expresion) == 1:
                        # Expresión con un solo token
                        tok = expresion[0]
                        tipo_expresion = self._obtener_tipo_token(tok)
                        if tipo_expresion is not None and \
                                not self._asignacion_valida(tipo_variable, tipo_expresion):
                            errores_reportados = set()
                            self._insertar_error(
                                tok.lexema, tok.renglon,
                                f"Incompatibilidad de tipos, {tipo_variable}",
                                errores_reportados
                            )
                    else:
                        # Expresión compleja
                        self._evaluar_expresion(expresion, tipo_variable)

                i += 2
                continue

            i += 1

    # ---------------------------------------------------------
    # Utilidades
    # ---------------------------------------------------------
    def _obtener_tipo_token(self, token):
        if token.tipo == "full":
            return "full"
        if token.tipo == "royal":
            return "royal"
        if token.tipo == "chain":
            return "chain"
        if token.tipo == "id":
            return self.tipos_declarados.get(token.lexema)
        return None

    def _asignacion_valida(self, tipo_var, tipo_exp):
        if tipo_var == "full" and tipo_exp == "full":
            return True
        if tipo_var == "royal" and tipo_exp in ("full", "royal"):
            return True
        if tipo_var == "chain" and tipo_exp == "chain":
            return True
        return False

    def _insertar_error(self, lexema, renglon, descripcion, errores_reportados):
        """
        Inserta un error, evitando duplicados en la misma línea.
        'errores_reportados' es un set con tuplas (lexema, renglon) ya vistas.
        """
        clave = (lexema, renglon)
        if clave in errores_reportados:
            return
        errores_reportados.add(clave)

        self.contador_errores += 1
        self.resultado.errores.append(
            (f"ErrSem{self.contador_errores}", lexema, renglon, descripcion)
        )

    # ---------------------------------------------------------
    # Evaluación de expresiones
    # ---------------------------------------------------------
    def _evaluar_expresion(self, expresion, tipo_variable):
        """Recorre la expresión y reporta TODOS los errores (sin duplicados)."""
        if not expresion:
            return None

        errores_reportados = set()

        operando_actual_tok = expresion[0]
        tipo_actual = self._obtener_tipo_token(operando_actual_tok)
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
            tipo_derecho = self._obtener_tipo_token(operando_derecho_tok)
            if tipo_derecho is None:
                i += 2
                continue

            es_valida, tipo_resultado, culpables = self._evaluar_operacion(
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

                    self._insertar_error(
                        tok_culpable.lexema,
                        tok_culpable.renglon,
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

    def _evaluar_operacion(self, variable, izq, op, der):
        """Consulta la tabla de reglas semánticas."""
        clave = (variable, izq, op, der)
        if clave in REGLAS_ARITMETICAS:
            return True, REGLAS_ARITMETICAS[clave], []

        culpables = self._determinar_culpables(variable, izq, op, der)
        return False, None, culpables

    def _determinar_culpables(self, variable, izq, op, der):
        """Determina los culpables cuando una operación no es válida."""
        culpables = []

        # -------- Caso 1: hay chain --------
        if izq == "chain" or der == "chain":
            # Operador inválido con chain (* o /) → culpable el operador
            if op not in ("+", "-"):
                culpables.append("op")

            # Si la variable NO es chain, el operando chain es culpable
            if variable != "chain":
                if izq == "chain":
                    culpables.append("izq")
                if der == "chain":
                    culpables.append("der")

            return culpables

        # -------- Caso 2: variable full con royal --------
        if variable == "full":
            if izq == "royal":
                culpables.append("izq")
            if der == "royal":
                culpables.append("der")
            if not culpables:
                culpables.append("op")
            return culpables

        # -------- Caso 3: variable chain con numéricos --------
        if variable == "chain":
            if izq in ("full", "royal"):
                culpables.append("izq")
            if der in ("full", "royal"):
                culpables.append("der")
            if not culpables:
                culpables.append("op")
            return culpables

        # -------- Fallback --------
        culpables.append("op")
        return culpables