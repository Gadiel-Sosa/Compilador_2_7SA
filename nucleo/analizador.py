"""
Analizador semántico con manejo de ámbitos (scopes).

- Pila de diccionarios para tipos declarados.
- Búsqueda jerárquica: local → padre → global.
- Detección de duplicados en el mismo ámbito.
- Detección de variables/funciones indefinidas.
"""

from nucleo.reglas import REGLAS_ARITMETICAS, REGLAS


class Resultado:
    def __init__(self):
        self.simbolos = []    # (lexema, tipo)
        self.errores = []     # (token, lexema, renglon, descripcion)
        

class Analizador:
    def __init__(self, tokens):
        self.tokens = tokens
        self.resultado = Resultado()
        self.contador_errores = 0

        # Pila de ámbitos: cada nivel es {nombre: tipo}
        self.pila_tipos = [{}]

        # Para la tabla de símbolos: cada nombre con su tipo "global" (el primero encontrado)
        self.simbolos_globales = {}

        self.firmas_funciones = {}  # nombre_función: [tipo_param1, tipo_param2, ...]

    # =========================================================
    # API pública
    # =========================================================
    def analizar(self):
        self._inferir_tipos_declarados()
        self._verificar_duplicados()
        self._llenar_tabla_simbolos()
        self._verificar_variables_indefinidas()
        self._verificar_asignaciones()
        self._verificar_llamadas_funciones()
        self._verificar_returns()

        # Ordenar errores por renglón
        self.resultado.errores.sort(key=lambda e: e[2])

        # Reasignar tokens secuencialmente
        errores_renumerados = []
        for idx, (_, lexema, renglon, descripcion) in enumerate(self.resultado.errores, start=1):
            errores_renumerados.append((f"ErrSem{idx}", lexema, renglon, descripcion))
        self.resultado.errores = errores_renumerados

        return self.resultado

    # =========================================================
    # Búsqueda jerárquica de tipos
    # =========================================================
    def _buscar_tipo(self, nombre):
        """Busca un tipo en la pila de ámbitos: local → padre → global."""
        for ambito in reversed(self.pila_tipos):
            if nombre in ambito:
                return ambito[nombre]
        return None

    # =========================================================
    # Fase 1: inferir tipos declarados
    # =========================================================
    def _inferir_tipos_declarados(self):
        tokens = self.tokens
        n = len(tokens)
        i = 0
        while i < n:
            tok = tokens[i]

            # --- Apertura / cierre de bloque ---
            if tok.tipo == "delim" and tok.lexema == "{":
                self.pila_tipos.append({})
                i += 1
                continue
            if tok.tipo == "delim" and tok.lexema == "}":
                if len(self.pila_tipos) > 1:
                    self.pila_tipos.pop()
                i += 1
                continue

            # --- Declaración de tipo ---
            if tok.tipo == "reservada" and tok.lexema in ("full", "royal", "chain", "void"):
                tipo_decl = tok.lexema
                renglon_decl = tok.renglon
                j = i + 1

                if j < n and tokens[j].tipo == "id":
                    nombre = tokens[j].lexema
                    k = j + 1

                    # Función: tipo nombre ( ... )

                    if k < n and tokens[k].tipo == "delim" and tokens[k].lexema == "(":
                        if nombre not in self.pila_tipos[-1]:
                            self.pila_tipos[-1][nombre] = tipo_decl
                            if nombre not in self.simbolos_globales:
                                self.simbolos_globales[nombre] = tipo_decl
                        params, k = self._parse_parametros(tokens, k + 1, n)
                        self.firmas_funciones[nombre] = [tipo_p for tipo_p, _ in params]
                        if k < n and tokens[k].tipo == "delim" and tokens[k].lexema == "{":
                            self.pila_tipos.append({})
                            for tipo_p, tok_p in params:
                                nombre_p = tok_p.lexema
                                self.pila_tipos[-1][nombre_p] = tipo_p
                                if nombre_p not in self.simbolos_globales:
                                    self.simbolos_globales[nombre_p] = tipo_p
                            k += 1
                        i = k
                        continue    
                    
                    else:
                        # Variables — declaración normal
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
                            if var not in self.pila_tipos[-1]:
                                self.pila_tipos[-1][var] = tipo_decl
                                if var not in self.simbolos_globales:
                                    self.simbolos_globales[var] = tipo_decl
                        i = m
                        continue
            i += 1

    # =========================================================
    # Fase 1.5: verificar duplicados (por ámbito)
    # =========================================================
    def _verificar_duplicados(self):
        """
        Detecta declaraciones duplicadas en el mismo ámbito.
        Reinicia la pila de ámbitos para recorrer de nuevo.
        """
        tokens = self.tokens
        n = len(tokens)
        errores_reportados = set()

        pila_ambitos = [{}]

        i = 0
        while i < n:
            tok = tokens[i]

            if tok.tipo == "delim" and tok.lexema == "{":
                pila_ambitos.append({})
                i += 1
                continue
            if tok.tipo == "delim" and tok.lexema == "}":
                if len(pila_ambitos) > 1:
                    pila_ambitos.pop()
                i += 1
                continue

            if tok.tipo == "reservada" and tok.lexema in ("full", "royal", "chain", "void"):
                renglon_decl = tok.renglon
                j = i + 1

                if j < n and tokens[j].tipo == "id":
                    nombre = tokens[j].lexema
                    ambito_actual = pila_ambitos[-1]

                    if nombre in ambito_actual:
                        clave = (nombre, tokens[j].renglon)
                        if clave not in errores_reportados:
                            errores_reportados.add(clave)
                            self.contador_errores += 1
                            self.resultado.errores.append(
                                (f"ErrSem{self.contador_errores}",
                                 nombre,
                                 tokens[j].renglon,
                                 "Declaración duplicada")
                            )
                    else:
                        ambito_actual[nombre] = True

                    k = j + 1

                    # Función: saltar paréntesis

                    if k < n and tokens[k].tipo == "delim" and tokens[k].lexema == "(":
                        params, k = self._parse_parametros(tokens, k + 1, n)
                        if k < n and tokens[k].tipo == "delim" and tokens[k].lexema == "{":
                            pila_ambitos.append({})
                            nuevo_ambito = pila_ambitos[-1]
                            for tipo_p, tok_p in params:
                                nombre_p = tok_p.lexema
                                if nombre_p in nuevo_ambito:
                                    clave = (nombre_p, tok_p.renglon)
                                    if clave not in errores_reportados:
                                        errores_reportados.add(clave)
                                        self.contador_errores += 1
                                        self.resultado.errores.append(
                                            (f"ErrSem{self.contador_errores}", nombre_p, tok_p.renglon, "Declaración duplicada")
                                        )
                                else:
                                    nuevo_ambito[nombre_p] = True
                            k += 1
                        i = k
                        continue

                    # Variables — declaración normal
                    m = k
                    while m < n:
                        if tokens[m].renglon != renglon_decl:
                            break
                        if tokens[m].tipo == "delim" and tokens[m].lexema == ";":
                            break
                        if tokens[m].tipo == "id":
                            otro_nombre = tokens[m].lexema
                            if otro_nombre in ambito_actual:
                                clave = (otro_nombre, tokens[m].renglon)
                                if clave not in errores_reportados:
                                    errores_reportados.add(clave)
                                    self.contador_errores += 1
                                    self.resultado.errores.append(
                                        (f"ErrSem{self.contador_errores}",
                                         otro_nombre,
                                         tokens[m].renglon,
                                         "Declaración duplicada")
                                    )
                            else:
                                ambito_actual[otro_nombre] = True
                        m += 1
                    i = m
                    continue
            i += 1

    # =========================================================
    # Fase 2: llenar la tabla de símbolos
    # =========================================================
    def _llenar_tabla_simbolos(self):
        lexemas_insertados = set()

        for tok in self.tokens:
            if tok.tipo == "reservada":
                if tok.lexema not in lexemas_insertados:
                    self.resultado.simbolos.append((tok.lexema, ""))
                    lexemas_insertados.add(tok.lexema)
                continue

            if tok.tipo in ("op", "delim"):
                if tok.lexema in lexemas_insertados:
                    continue
                self.resultado.simbolos.append((tok.lexema, ""))
                lexemas_insertados.add(tok.lexema)
                continue

            if tok.tipo not in ("id", "full", "royal", "chain"):
                continue

            if tok.lexema in lexemas_insertados:
                continue

            if tok.tipo == "id":
                # Tipo de la primera declaración encontrada
                tipo_tabla = self.simbolos_globales.get(tok.lexema, "")
            else:
                tipo_tabla = tok.tipo

            self.resultado.simbolos.append((tok.lexema, tipo_tabla))
            lexemas_insertados.add(tok.lexema)

    # =========================================================
    # Fase 3: verificar variables y funciones indefinidas
    # =========================================================
    def _verificar_variables_indefinidas(self):
        """
        Recorre los tokens con una pila de ámbitos paralela.
        Verifica que cada id esté declarado en algún ámbito accesible.
        """
        tokens = self.tokens
        n = len(tokens)
        errores_reportados = set()

        pila_ambitos = [{}]

        i = 0
        while i < n:
            tok = tokens[i]

            # Apertura / cierre de bloque
            if tok.tipo == "delim" and tok.lexema == "{":
                pila_ambitos.append({})
                i += 1
                continue
            if tok.tipo == "delim" and tok.lexema == "}":
                if len(pila_ambitos) > 1:
                    pila_ambitos.pop()
                i += 1
                continue

            # Registrar declaraciones para esta pasada
            if tok.tipo == "reservada" and tok.lexema in ("full", "royal", "chain", "void"):
                renglon_decl = tok.renglon
                j = i + 1
                if j < n and tokens[j].tipo == "id":
                    nombre = tokens[j].lexema
                    k = j + 1

                    # ¿Es función? (id seguido de '(')
                    if k < n and tokens[k].tipo == "delim" and tokens[k].lexema == "(":
                        pila_ambitos[-1][nombre] = True
                        params, k = self._parse_parametros(tokens, k + 1, n)
                        if k < n and tokens[k].tipo == "delim" and tokens[k].lexema == "{":
                            pila_ambitos.append({})
                            for tipo_p, tok_p in params:
                                pila_ambitos[-1][tok_p.lexema] = True
                            k += 1
                        i = k
                        continue
                    else:
                        # Variables: registrar TODAS las separadas por comas
                        pila_ambitos[-1][nombre] = True
                        m = k
                        while m < n:
                            if tokens[m].renglon != renglon_decl:
                                break
                            if tokens[m].tipo == "delim" and tokens[m].lexema == ";":
                                break
                            if tokens[m].tipo == "id":
                                pila_ambitos[-1][tokens[m].lexema] = True
                            m += 1
                        i = m
                        continue
                i += 1
                continue

            # Verificar uso de id
            if tok.tipo == "id":
                esta_declarado = any(tok.lexema in ambito for ambito in pila_ambitos)

                if not esta_declarado:
                    es_funcion = (
                        i + 1 < n
                        and tokens[i + 1].tipo == "delim"
                        and tokens[i + 1].lexema == "("
                    )
                    descripcion = "Función indefinida" if es_funcion else "Variable indefinida"

                    clave = (tok.lexema, tok.renglon)
                    if clave not in errores_reportados:
                        errores_reportados.add(clave)
                        self.contador_errores += 1
                        self.resultado.errores.append(
                            (f"ErrSem{self.contador_errores}",
                             tok.lexema,
                             tok.renglon,
                             descripcion)
                        )

            i += 1

    # =========================================================
    # Fase 4: verificar asignaciones
    # =========================================================
    def _verificar_asignaciones(self):
        """
        Recorre los tokens buscando el patrón id = expresión ;
        y evalúa el tipo usando la pila de ámbitos.
        """
        tokens = self.tokens
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
                        params, k = self._parse_parametros(tokens, k + 1, n)
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
                tipo_variable = self._buscar_tipo_en_pila(pila_ambitos, identificador)

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
                        tipo_expresion = self._tipo_de_token(tokk, pila_ambitos)
                        if tipo_expresion is not None and \
                                not self._asignacion_valida(tipo_variable, tipo_expresion):
                            errores_reportados = set()
                            self._insertar_error(
                                tokk,
                                f"Incompatibilidad de tipos, {tipo_variable}",
                                errores_reportados
                            )
                    else:
                        self._evaluar_expresion(expresion, tipo_variable, pila_ambitos)

                i += 2
                continue

            i += 1

    # =========================================================
    # Búsqueda de tipo en la pila (para la fase 4)
    # =========================================================
    def _buscar_tipo_en_pila(self, pila, nombre):
        for ambito in reversed(pila):
            if nombre in ambito:
                return ambito[nombre]
        return None

    def _tipo_de_token(self, token, pila):
        if token.tipo == "full":
            return "full"
        if token.tipo == "royal":
            return "royal"
        if token.tipo == "chain":
            return "chain"
        if token.tipo == "id":
            return self._buscar_tipo_en_pila(pila, token.lexema)
        return None

    # =========================================================
    # Utilidades
    # =========================================================
    def _asignacion_valida(self, tipo_var, tipo_exp):
        if tipo_var == "full" and tipo_exp == "full":
            return True
        if tipo_var == "royal" and tipo_exp in ("full", "royal"):
            return True
        if tipo_var == "chain" and tipo_exp == "chain":
            return True
        return False

    def _insertar_error(self, tok, descripcion, errores_reportados):
        clave = (tok.lexema, tok.renglon)
        if clave in errores_reportados:
            return
        errores_reportados.add(clave)

        self.contador_errores += 1
        self.resultado.errores.append(
            (f"ErrSem{self.contador_errores}", tok.lexema, tok.renglon, descripcion)
        )

    # =========================================================
    # Evaluación de expresiones
    # =========================================================
    def _evaluar_expresion(self, expresion, tipo_variable, pila):
        if not expresion:
            return None

        errores_reportados = set()

        operando_actual_tok = expresion[0]
        tipo_actual = self._tipo_de_token(operando_actual_tok, pila)
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
            tipo_derecho = self._tipo_de_token(operando_derecho_tok, pila)
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

    def _evaluar_operacion(self, variable, izq, op, der):
        clave = (variable, izq, op, der)
        if clave in REGLAS_ARITMETICAS:
            return True, REGLAS_ARITMETICAS[clave], []

        culpables = self._determinar_culpables(variable, izq, op, der)
        return False, None, culpables

    def _determinar_culpables(self, variable, izq, op, der):
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

    def _parse_parametros(self, tokens, k, n):
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
            if profundidad == 1 and t.tipo == "reservada" and t.lexema in ("full", "royal", "chain", "void"):
                if k + 1 < n and tokens[k + 1].tipo == "id":
                    params.append((t.lexema, tokens[k + 1]))
                    k += 2
                    continue
            k += 1
        return params, k


    def _verificar_llamadas_funciones(self):
        tokens = self.tokens
        n = len(tokens)
        pila_ambitos = [{}]
        errores_reportados = set()
        i = 0
        while i < n:
            tok = tokens[i]

            if tok.tipo == "delim" and tok.lexema == "{":
                pila_ambitos.append({})
                i += 1
                continue
            if tok.tipo == "delim" and tok.lexema == "}":
                if len(pila_ambitos) > 1:
                    pila_ambitos.pop()
                i += 1
                continue

            # Registrar declaraciones (variables, funciones y sus parámetros)
            if tok.tipo == "reservada" and tok.lexema in ("full", "royal", "chain", "void"):
                tipo_decl = tok.lexema
                renglon_decl = tok.renglon
                j = i + 1
                if j < n and tokens[j].tipo == "id":
                    nombre = tokens[j].lexema
                    k = j + 1
                    if k < n and tokens[k].tipo == "delim" and tokens[k].lexema == "(":
                        pila_ambitos[-1][nombre] = tipo_decl
                        params, k = self._parse_parametros(tokens, k + 1, n)
                        if k < n and tokens[k].tipo == "delim" and tokens[k].lexema == "{":
                            pila_ambitos.append({})
                            for tipo_p, tok_p in params:
                                pila_ambitos[-1][tok_p.lexema] = tipo_p
                            k += 1
                        i = k
                        continue
                    else:
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
                            pila_ambitos[-1][var] = tipo_decl
                        i = m
                        continue
                i += 1
                continue

            # Detectar llamada: id '(' que NO sea una declaración (ya filtrada arriba)
            if (tok.tipo == "id" and i + 1 < n
                    and tokens[i + 1].tipo == "delim" and tokens[i + 1].lexema == "("):
                nombre_fn = tok.lexema
                args = []
                arg_actual = []
                k = i + 2
                profundidad = 1
                while k < n and profundidad > 0:
                    t = tokens[k]
                    if t.tipo == "delim" and t.lexema == "(":
                        profundidad += 1
                        arg_actual.append(t)
                        k += 1
                        continue
                    if t.tipo == "delim" and t.lexema == ")":
                        profundidad -= 1
                        if profundidad == 0:
                            if arg_actual:
                                args.append(arg_actual)
                            k += 1
                            break
                        arg_actual.append(t)
                        k += 1
                        continue
                    if t.tipo == "delim" and t.lexema == "," and profundidad == 1:
                        args.append(arg_actual)
                        arg_actual = []
                        k += 1
                        continue
                    arg_actual.append(t)
                    k += 1

                if nombre_fn in self.firmas_funciones:
                    firma = self.firmas_funciones[nombre_fn]
                    if len(args) != len(firma):
                        self._insertar_error(tok, "Número de argumentos incorrecto", errores_reportados)
                    else:
                        for tipo_param, arg_tokens in zip(firma, args):
                            if len(arg_tokens) == 1:
                                tipo_arg = self._tipo_de_token(arg_tokens[0], pila_ambitos)
                                if tipo_arg is not None and not self._asignacion_valida(tipo_param, tipo_arg):
                                    self._insertar_error(
                                        arg_tokens[0],
                                        f"Incompatibilidad de tipos, {tipo_param}",
                                        errores_reportados
                                    )
                            elif arg_tokens:
                                self._evaluar_expresion(arg_tokens, tipo_param, pila_ambitos)
                i = k
                continue

            i += 1


    def _verificar_returns(self):
        tokens = self.tokens
        n = len(tokens)
        pila_ambitos = [{}]
        pila_funcion_actual = [None]  # tipo de retorno de la función en cada nivel de {}
        errores_reportados = set()
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
                        pila_ambitos[-1][nombre] = tipo_decl
                        params, k = self._parse_parametros(tokens, k + 1, n)
                        if k < n and tokens[k].tipo == "delim" and tokens[k].lexema == "{":
                            pila_ambitos.append({})
                            for tipo_p, tok_p in params:
                                pila_ambitos[-1][tok_p.lexema] = tipo_p
                            pila_funcion_actual.append(tipo_decl)
                            k += 1
                        i = k
                        continue
                    else:
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
                            pila_ambitos[-1][var] = tipo_decl
                        i = m
                        continue
                i += 1
                continue

            if tok.tipo == "delim" and tok.lexema == "{":
                pila_ambitos.append({})
                pila_funcion_actual.append(pila_funcion_actual[-1])
                i += 1
                continue
            if tok.tipo == "delim" and tok.lexema == "}":
                if len(pila_ambitos) > 1:
                    pila_ambitos.pop()
                    pila_funcion_actual.pop()
                i += 1
                continue

            if tok.tipo == "reservada" and tok.lexema == "return":
                tipo_funcion = pila_funcion_actual[-1]

                j = i + 1
                expresion = []
                while j < n and tokens[j].lexema != ";":
                    expresion.append(tokens[j])
                    j += 1

                if tipo_funcion is None:
                    self._insertar_error(tok, "Return fuera de una función", errores_reportados)
                    i = j + 1
                    continue

                if not expresion:
                    if tipo_funcion != "void":
                        self._insertar_error(
                            tok,
                            f"Error semántico, no hubo retorno tipo {tipo_funcion}",
                            errores_reportados
                        )
                    i = j + 1
                    continue

                if tipo_funcion == "void":
                    self._insertar_error(
                        tok,
                        f"Error semántico, no hubo retorno tipo {tipo_funcion}",
                        errores_reportados
                    )
                    i = j + 1
                    continue

                if len(expresion) == 1:
                    tipo_exp = self._tipo_de_token(expresion[0], pila_ambitos)
                    if tipo_exp is not None and not self._asignacion_valida(tipo_funcion, tipo_exp):
                        self._insertar_error(
                            expresion[0],
                            f"Error semántico, no hubo retorno tipo {tipo_funcion}",
                            errores_reportados
                        )
                else:
                    self._evaluar_expresion(expresion, tipo_funcion, pila_ambitos)

                i = j + 1
                continue

            i += 1