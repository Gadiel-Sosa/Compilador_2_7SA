"""
Árbol de sentencias usado por la fase de optimización.

La optimización trabaja sobre el código fuente (no sobre el triplo):
los tokens se agrupan en sentencias (declaraciones, asignaciones,
return, if, funciones...), se modifican y al final se vuelve a
imprimir el código ya optimizado.
"""

TIPOS_DATO = ("full", "royal", "chain")
TIPOS_FUNCION = ("full", "royal", "chain", "void")
TIPOS_LITERAL = ("full", "royal", "chain")   # tipo de token de las constantes


def es_delim(tok, lexema):
    return tok.tipo == "delim" and tok.lexema == lexema


def es_asignacion_op(tok):
    return tok.tipo == "op" and tok.lexema == "="


# =========================================================
# Nodos
# =========================================================
class Simple:
    """
    Sentencia que termina en ';'.
    clase: 'decl'   -> full QaZ, QbZ ;
           'asig'   -> QaZ = expresión ;
           'return' -> return expresión ;
           'otra'   -> cualquier otra (llamada suelta, arreglos, etc.)
    """

    def __init__(self, clase, tokens):
        self.clase = clase
        self.tokens = tokens

    @property
    def renglon(self):
        return self.tokens[0].renglon

    @property
    def destino(self):
        """Variable asignada (solo para 'asig')."""
        return self.tokens[0].lexema

    def inicio_expresion(self):
        if self.clase == "asig":
            return 2
        if self.clase == "return":
            return 1
        return 0

    def expresion(self):
        fin = len(self.tokens)
        if fin and es_delim(self.tokens[-1], ";"):
            fin -= 1
        return self.tokens[self.inicio_expresion():fin]


class Funcion:
    def __init__(self, tok_tipo, tok_nombre, params, cuerpo):
        self.tok_tipo = tok_tipo
        self.tok_nombre = tok_nombre
        self.params = params        # tokens entre '(' y ')'
        self.cuerpo = cuerpo        # lista de sentencias

    @property
    def tipo(self):
        return self.tok_tipo.lexema

    @property
    def nombre(self):
        return self.tok_nombre.lexema

    @property
    def renglon(self):
        return self.tok_tipo.renglon

    def parametros(self):
        """Lista de (tipo, nombre) de los parámetros."""
        res = []
        for k, t in enumerate(self.params):
            if (t.tipo == "reservada" and t.lexema in TIPOS_DATO
                    and k + 1 < len(self.params) and self.params[k + 1].tipo == "id"):
                res.append((t.lexema, self.params[k + 1].lexema))
        return res


class If:
    def __init__(self, tok_if, cond, entonces, sino):
        self.tok_if = tok_if
        self.cond = cond            # tokens dentro de los paréntesis
        self.entonces = entonces    # lista de sentencias
        self.sino = sino            # lista de sentencias o None

    @property
    def renglon(self):
        return self.tok_if.renglon


class Bloque:
    """Bloque { ... } suelto."""

    def __init__(self, cuerpo):
        self.cuerpo = cuerpo


# =========================================================
# Parser: tokens -> lista de sentencias
# =========================================================
def parsear(tokens):
    sentencias, _ = _parsear_bloque(tokens, 0, False)
    return sentencias


def _parsear_bloque(tokens, i, con_llave):
    sentencias = []
    n = len(tokens)
    while i < n:
        if es_delim(tokens[i], "}"):
            if con_llave:
                return sentencias, i + 1
            # Llave suelta: se conserva tal cual
            sentencias.append(Simple("otra", [tokens[i]]))
            i += 1
            continue
        sentencia, i = _parsear_sentencia(tokens, i)
        sentencias.append(sentencia)
    return sentencias, i


def _es_definicion_funcion(tokens, i):
    return (i + 2 < len(tokens)
            and tokens[i].tipo == "reservada" and tokens[i].lexema in TIPOS_FUNCION
            and tokens[i + 1].tipo == "id"
            and es_delim(tokens[i + 2], "("))


def _cerrar_parentesis(tokens, k):
    """k apunta a '('. Devuelve (tokens internos, índice tras el ')' que cierra)."""
    interior = []
    profundidad = 0
    n = len(tokens)
    while k < n:
        t = tokens[k]
        if es_delim(t, "("):
            profundidad += 1
            if profundidad == 1:
                k += 1
                continue
        elif es_delim(t, ")"):
            profundidad -= 1
            if profundidad == 0:
                return interior, k + 1
        interior.append(t)
        k += 1
    return interior, k


def _parsear_cuerpo(tokens, k):
    """Cuerpo de if/else: bloque con llaves o una sola sentencia."""
    n = len(tokens)
    if k < n and es_delim(tokens[k], "{"):
        return _parsear_bloque(tokens, k + 1, True)
    if k < n and not es_delim(tokens[k], "}"):
        sentencia, k = _parsear_sentencia(tokens, k)
        return [sentencia], k
    return [], k


def _parsear_sentencia(tokens, i):
    n = len(tokens)
    tok = tokens[i]

    # Definición de función: tipo id ( ... ) { ... }
    if _es_definicion_funcion(tokens, i):
        params, k = _cerrar_parentesis(tokens, i + 2)
        if k < n and es_delim(tokens[k], "{"):
            cuerpo, k = _parsear_bloque(tokens, k + 1, True)
            return Funcion(tok, tokens[i + 1], params, cuerpo), k

    # if ( ... ) cuerpo [else cuerpo]
    if (tok.tipo == "reservada" and tok.lexema == "if"
            and i + 1 < n and es_delim(tokens[i + 1], "(")):
        cond, k = _cerrar_parentesis(tokens, i + 1)
        entonces, k = _parsear_cuerpo(tokens, k)
        sino = None
        if k < n and tokens[k].tipo == "reservada" and tokens[k].lexema == "else":
            sino, k = _parsear_cuerpo(tokens, k + 1)
        return If(tok, cond, entonces, sino), k

    # Bloque suelto
    if es_delim(tok, "{"):
        cuerpo, k = _parsear_bloque(tokens, i + 1, True)
        return Bloque(cuerpo), k

    # Sentencia simple: hasta ';'
    j = i
    profundidad = 0
    while j < n:
        t = tokens[j]
        if t.tipo == "delim" and t.lexema in ("(", "["):
            profundidad += 1
        elif t.tipo == "delim" and t.lexema in (")", "]"):
            profundidad -= 1
        elif es_delim(t, ";") and profundidad <= 0:
            j += 1
            break
        elif t.tipo == "delim" and t.lexema in ("{", "}") and profundidad <= 0 and j > i:
            break
        j += 1
    if j == i:
        j = i + 1
    segmento = tokens[i:j]
    return Simple(_clasificar(segmento), segmento), j


def _clasificar(seg):
    t0 = seg[0]
    if t0.tipo == "reservada" and t0.lexema in TIPOS_DATO:
        if len(seg) > 2 and es_delim(seg[2], "("):
            return "otra"
        return "decl"
    if t0.tipo == "reservada" and t0.lexema == "return":
        return "return"
    if t0.tipo == "id" and len(seg) > 1 and es_asignacion_op(seg[1]):
        return "asig"
    return "otra"


# =========================================================
# Recorridos y consultas sobre el árbol
# =========================================================
def hijos(s, entrar_funciones=True):
    if isinstance(s, Funcion):
        return s.cuerpo if entrar_funciones else []
    if isinstance(s, If):
        return s.entonces + (s.sino or [])
    if isinstance(s, Bloque):
        return s.cuerpo
    return []


def recorrer(sentencias, entrar_funciones=True):
    """Recorre todos los nodos en preorden."""
    for s in sentencias:
        yield s
        yield from recorrer(hijos(s, entrar_funciones), entrar_funciones)


def listas_de_tokens(nodo, entrar_funciones=False):
    """
    Listas de tokens (mutables) de un subárbol, en orden de ejecución.
    Por defecto NO entra a definiciones de función, porque definirlas
    no ejecuta su cuerpo.
    """
    for s in recorrer([nodo], entrar_funciones):
        if isinstance(s, Simple):
            yield s.tokens
        elif isinstance(s, If):
            yield s.cond


def funciones_con_padre(sentencias):
    """(lista_que_la_contiene, Funcion) para cada función del programa."""
    for s in sentencias:
        if isinstance(s, Funcion):
            yield sentencias, s
            yield from funciones_con_padre(s.cuerpo)
        elif isinstance(s, If):
            yield from funciones_con_padre(s.entonces)
            if s.sino is not None:
                yield from funciones_con_padre(s.sino)
        elif isinstance(s, Bloque):
            yield from funciones_con_padre(s.cuerpo)


def llamadas_en(tokens):
    """Nombres de las funciones llamadas en una lista de tokens."""
    return {
        t.lexema for k, t in enumerate(tokens)
        if t.tipo == "id" and k + 1 < len(tokens) and es_delim(tokens[k + 1], "(")
    }


def ids_declarados(simple):
    return [t.lexema for t in simple.tokens if t.tipo == "id"]


def asignaciones_en(nodo):
    """Variables asignadas en un subárbol (sin entrar a funciones)."""
    nombres = set()
    for s in recorrer([nodo], entrar_funciones=False):
        if not isinstance(s, Simple):
            continue
        if s.clase == "asig":
            nombres.add(s.destino)
        elif s.clase == "otra" and any(es_asignacion_op(t) for t in s.tokens):
            ids = [t for t in s.tokens if t.tipo == "id"]
            if ids:
                nombres.add(ids[0].lexema)
    return nombres


def declaraciones_en(nodo):
    """Variables declaradas en un subárbol (sin entrar a funciones)."""
    nombres = set()
    for s in recorrer([nodo], entrar_funciones=False):
        if isinstance(s, Simple) and s.clase == "decl":
            nombres.update(ids_declarados(s))
    return nombres


def partir_argumentos(tokens, k):
    """
    k apunta al '(' de una llamada. Devuelve (lista_de_argumentos, índice
    tras el ')'), donde cada argumento es una lista de tokens.
    """
    args = []
    actual = []
    profundidad = 0
    i = k
    while i < len(tokens):
        t = tokens[i]
        if es_delim(t, "("):
            profundidad += 1
            if profundidad == 1:
                i += 1
                continue
        elif es_delim(t, ")"):
            profundidad -= 1
            if profundidad == 0:
                if actual or args:
                    args.append(actual)
                return args, i + 1
        elif es_delim(t, ",") and profundidad == 1:
            args.append(actual)
            actual = []
            i += 1
            continue
        actual.append(t)
        i += 1
    if actual or args:
        args.append(actual)
    return args, i


def nombre_llamada_completa(expresion):
    """Nombre de la función si la expresión es exactamente id ( ... )."""
    if len(expresion) < 3 or expresion[0].tipo != "id":
        return None
    if not es_delim(expresion[1], "(") or not es_delim(expresion[-1], ")"):
        return None
    _, fin = partir_argumentos(expresion, 1)
    if fin != len(expresion):
        return None
    return expresion[0].lexema
