"""
Optimización local: instrucciones que se repiten sin haber tenido
modificación alguna en sus valores (PDF Unidad III, Opción 1).

    a = j + 56            a = j + 56
    b = m - 45      ->    b = m - 45
    c = j + 56            w = a + b
    w = a + b             b = a * 4
    b = c * 4

Se conserva la PRIMERA instrucción, se elimina la repetida y los usos
posteriores de su variable se reemplazan por la variable de la primera.

Una expresión deja de estar "disponible" cuando se modifica cualquiera
de sus operandos o la variable que guarda su valor (pág. 10 del PDF).

Además, si se repite exactamente la misma asignación (misma variable,
mismo valor) sin cambios de por medio, la segunda se elimina.

Reglas de seguridad para reemplazar c por a:
    - a y c son del mismo tipo.
    - La expresión no contiene llamadas a función ni arreglos.
    - a no se modifica antes de los usos de c que se reemplazan.
    - Los usos de c se reemplazan hasta que c se vuelve a asignar; si
      eso no ocurre en el mismo bloque, c debe ser local a ese bloque
      (o estar en el nivel global), para no dejar usos fuera sin valor.
    - Ninguna función llamada en medio lee o modifica a ni c.
"""

from nucleo.obtener_tokens import Token
from nucleo.optimizacion.arbol import (
    Simple, Funcion, If, Bloque,
    recorrer, listas_de_tokens, llamadas_en,
    asignaciones_en, declaraciones_en, ids_declarados, es_asignacion_op,
)
from nucleo.optimizacion.impresion import unir
from nucleo.optimizacion.resultado import Cambio

TECNICA = "Instrucción repetida"


def aplicar_repetidas(programa, cambios):
    optimizador = _Repetidas(programa, cambios)
    programa[:] = optimizador.optimizar_lista(programa, {}, es_global=True)


class _Repetidas:
    def __init__(self, programa, cambios):
        self.cambios = cambios
        self.refs = _referencias_por_funcion(programa)
        self.ambitos = [{}]     # pila de {nombre: tipo}

    # -----------------------------------------------------
    # Recorrido de una lista de sentencias (un bloque)
    # disponibles: {clave_expresión: (variable_que_la_guarda, sentencia)}
    # -----------------------------------------------------
    def optimizar_lista(self, sentencias, disponibles, es_global):
        resultado = []
        for idx, s in enumerate(sentencias):
            if isinstance(s, Funcion):
                # El cuerpo de una función empieza sin nada conocido
                self.ambitos.append({nombre: tipo for tipo, nombre in s.parametros()})
                s.cuerpo = self.optimizar_lista(s.cuerpo, {}, es_global=False)
                self.ambitos.pop()

            elif isinstance(s, If):
                if llamadas_en(s.cond):
                    disponibles.clear()
                s.entonces = self._optimizar_subbloque(s.entonces, disponibles)
                if s.sino is not None:
                    s.sino = self._optimizar_subbloque(s.sino, disponibles)
                self._despues_de_compuesta(s, disponibles)

            elif isinstance(s, Bloque):
                s.cuerpo = self._optimizar_subbloque(s.cuerpo, disponibles)
                self._despues_de_compuesta(s, disponibles)

            elif s.clase == "decl":
                tipo = s.tokens[0].lexema
                for nombre in ids_declarados(s):
                    self.ambitos[-1][nombre] = tipo
                    _invalidar(disponibles, nombre)

            elif s.clase == "asig":
                if self._procesar_asignacion(s, sentencias, idx, disponibles, es_global):
                    continue  # la instrucción se eliminó

            else:  # return / otra
                if llamadas_en(s.tokens):
                    disponibles.clear()
                elif any(es_asignacion_op(t) for t in s.tokens):
                    for t in s.tokens:
                        if t.tipo == "id":
                            _invalidar(disponibles, t.lexema)

            resultado.append(s)
        return resultado

    def _optimizar_subbloque(self, cuerpo, disponibles):
        # Lo calculado antes del if sigue disponible dentro de él,
        # pero lo calculado dentro no sale (puede no ejecutarse).
        self.ambitos.append({})
        nuevo = self.optimizar_lista(cuerpo, dict(disponibles), es_global=False)
        self.ambitos.pop()
        return nuevo

    def _despues_de_compuesta(self, s, disponibles):
        for nombre in asignaciones_en(s):
            _invalidar(disponibles, nombre)
        if any(llamadas_en(lista) for lista in listas_de_tokens(s)):
            disponibles.clear()

    # -----------------------------------------------------
    # Asignación: x = expresión ;
    # Devuelve True si la instrucción se eliminó.
    # -----------------------------------------------------
    def _procesar_asignacion(self, s, sentencias, idx, disponibles, es_global):
        x = s.destino
        expr = s.expresion()
        if not expr:
            return False

        if llamadas_en(expr):
            disponibles.clear()
            return False
        if any(t.tipo == "delim" and t.lexema in ("[", "]") for t in expr):
            _invalidar(disponibles, x)
            return False

        clave = tuple(t.lexema for t in expr)
        previo = disponibles.get(clave)

        if previo is not None:
            poseedor, sentencia_previa = previo

            # Misma variable, mismo valor: la segunda sobra
            if poseedor == x:
                self.cambios.append(Cambio(
                    s.renglon, TECNICA,
                    f"Se eliminó «{unir(s.tokens)}»: {x} ya tenía ese valor "
                    f"desde el renglón {sentencia_previa.renglon} y no se modificó"
                ))
                return True

            # Otra variable con la misma operación (Opción 1 del PDF)
            if any(t.tipo == "op" for t in expr) and self._mismo_tipo(x, poseedor):
                plan = self._planear_sustitucion(sentencias, idx, x, poseedor, es_global)
                if plan is not None:
                    self._aplicar_sustitucion(s, sentencia_previa, x, poseedor, plan)
                    _invalidar(disponibles, x)
                    return True

        # Instrucción normal: x cambia de valor
        _invalidar(disponibles, x)
        ids_expr = {t.lexema for t in expr if t.tipo == "id"}
        if x not in ids_expr:
            disponibles[clave] = (x, s)
        return False

    def _planear_sustitucion(self, sentencias, idx, x, poseedor, es_global):
        """
        Busca, hacia adelante en el mismo bloque, los usos de x que deben
        cambiarse por 'poseedor'. Devuelve la lista de (lista_tokens, índice)
        o None si no es seguro optimizar.
        """
        plan = []
        involucradas = {x, poseedor}
        poseedor_modificado = False

        for s in sentencias[idx + 1:]:
            if isinstance(s, Funcion):
                continue  # definirla no la ejecuta

            # Una función llamada aquí no debe leer/modificar x ni poseedor
            for lista in listas_de_tokens(s):
                for f in llamadas_en(lista):
                    if self.refs.get(f, set()) & involucradas:
                        return None

            if isinstance(s, Simple):
                if s.clase == "decl":
                    if involucradas & set(ids_declarados(s)):
                        return None
                    continue
                if s.clase == "otra" and asignaciones_en(s) & involucradas:
                    return None

                usos = _usos(s.tokens, x, s.inicio_expresion())
                if usos and poseedor_modificado:
                    return None
                plan.extend(usos)

                if s.clase == "asig":
                    if s.destino == x:
                        return plan          # x recibe nuevo valor: fin
                    if s.destino == poseedor:
                        poseedor_modificado = True
                continue

            # If / Bloque
            if declaraciones_en(s) & involucradas:
                return None
            asignadas = asignaciones_en(s)
            if x in asignadas:
                return None  # x cambiaría solo en algunos caminos
            usos = [u for lista in listas_de_tokens(s) for u in _usos(lista, x, 0)]
            if usos and (poseedor_modificado or poseedor in asignadas):
                return None
            plan.extend(usos)
            if poseedor in asignadas:
                poseedor_modificado = True

        # Fin del bloque sin reasignar x
        if es_global or x in self.ambitos[-1]:
            return plan
        return None

    def _aplicar_sustitucion(self, s, sentencia_previa, x, poseedor, plan):
        texto_eliminado = unir(s.tokens)
        renglones = []
        for lista, i in plan:
            viejo = lista[i]
            lista[i] = Token("id", poseedor, viejo.renglon)
            if viejo.renglon not in renglones:
                renglones.append(viejo.renglon)

        self.cambios.append(Cambio(
            s.renglon, TECNICA,
            f"Se eliminó «{texto_eliminado}»: repite la operación de "
            f"«{unir(sentencia_previa.tokens)}» (renglón {sentencia_previa.renglon})"
        ))
        for r in renglones:
            self.cambios.append(Cambio(r, TECNICA, f"Se usa {poseedor} en lugar de {x}"))

    def _mismo_tipo(self, a, b):
        ta = _buscar_tipo(self.ambitos, a)
        return ta is not None and ta == _buscar_tipo(self.ambitos, b)


# =========================================================
# Utilidades
# =========================================================
def _invalidar(disponibles, nombre):
    """Quita las expresiones que usan 'nombre' o cuyo valor guarda 'nombre'."""
    for clave in list(disponibles):
        poseedor, _ = disponibles[clave]
        if poseedor == nombre or nombre in clave:
            del disponibles[clave]


def _usos(tokens, nombre, desde):
    return [
        (tokens, i) for i in range(desde, len(tokens))
        if tokens[i].tipo == "id" and tokens[i].lexema == nombre
    ]


def _buscar_tipo(ambitos, nombre):
    for ambito in reversed(ambitos):
        if nombre in ambito:
            return ambito[nombre]
    return None


def _referencias_por_funcion(programa):
    """
    {función: identificadores que usa}, incluyendo sus parámetros y,
    de forma transitiva, lo que usan las funciones que llama.
    """
    usados = {}
    llamadas = {}
    for s in recorrer(programa):
        if isinstance(s, Funcion):
            ids = {nombre for _, nombre in s.parametros()}
            llam = set()
            for sub in s.cuerpo:
                for lista in listas_de_tokens(sub, entrar_funciones=True):
                    ids.update(t.lexema for t in lista if t.tipo == "id")
                    llam.update(llamadas_en(lista))
            usados[s.nombre] = ids
            llamadas[s.nombre] = llam

    cambio = True
    while cambio:
        cambio = False
        for f in usados:
            for g in llamadas[f]:
                if g in usados and not usados[g] <= usados[f]:
                    usados[f] |= usados[g]
                    cambio = True
    return usados
