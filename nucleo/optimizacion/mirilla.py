"""
Optimización de mirilla (solo funciones).

Detecta rutinas intermediarias: funciones cuyo único trabajo es llamar
a otra función y regresar su resultado. Se elimina la intermediaria y
cada llamada a ella se redirige directamente a la función real
(PDF Unidad III, pág. 32):

    RUTINA CALCULA(C,D)          ->  (se elimina)
      Z = SUMA(C,D)
      REGRESA Z
    Y = CALCULA(A,B)             ->  Y = SUMA(A,B)

Formas reconocidas del cuerpo de la intermediaria F:
    return G(args);
    tipo t;  t = G(args);  return t;      (t declarada dentro de F)

Condiciones:
    - G existe, es distinta de F y regresa el mismo tipo que F.
    - Cada argumento de G es un parámetro de F o una constante.
    - Cada parámetro de F se pasa a G exactamente una vez.
"""

from nucleo.obtener_tokens import Token
from nucleo.optimizacion.arbol import (
    Simple, If,
    recorrer, funciones_con_padre, ids_declarados,
    partir_argumentos, nombre_llamada_completa, TIPOS_LITERAL,
)
from nucleo.optimizacion.impresion import unir
from nucleo.optimizacion.resultado import Cambio

TECNICA = "Mirilla"
MAX_PASADAS = 100


def aplicar_mirilla(programa, cambios):
    # Se repite hasta que no haya intermediarias: así se resuelven
    # cadenas como A -> B -> C.
    for _ in range(MAX_PASADAS):
        funciones = list(funciones_con_padre(programa))
        por_nombre = {f.nombre: f for _, f in funciones}

        candidata = None
        for padre, f in funciones:
            res = _detectar_intermediaria(f, por_nombre)
            if res is not None:
                candidata = (padre, f) + res
                break
        if candidata is None:
            return

        padre, f, destino, plantilla = candidata
        padre.remove(f)
        cambios.append(Cambio(
            f.renglon, TECNICA,
            f"Se eliminó la función {f.nombre}: solo llamaba a {destino}"
        ))
        _redirigir_programa(programa, f.nombre, destino, plantilla, cambios)


def _detectar_intermediaria(f, por_nombre):
    """Devuelve (nombre_destino, plantilla_de_argumentos) o None."""
    cuerpo = f.cuerpo
    nombres_params = [nombre for _, nombre in f.parametros()]
    llamada = None

    if len(cuerpo) == 1 and _es_simple(cuerpo[0], "return"):
        llamada = cuerpo[0].expresion()

    elif (len(cuerpo) == 3 and _es_simple(cuerpo[0], "decl")
          and _es_simple(cuerpo[1], "asig") and _es_simple(cuerpo[2], "return")):
        decl, asig, ret = cuerpo
        expr_ret = ret.expresion()
        if (ids_declarados(decl) == [asig.destino]
                and asig.destino not in nombres_params
                and len(expr_ret) == 1 and expr_ret[0].tipo == "id"
                and expr_ret[0].lexema == asig.destino):
            llamada = asig.expresion()

    if not llamada:
        return None

    destino = nombre_llamada_completa(llamada)
    if destino is None or destino == f.nombre or destino not in por_nombre:
        return None
    g = por_nombre[destino]
    if g.tipo != f.tipo:
        return None

    args, _ = partir_argumentos(llamada, 1)
    if len(args) != len(g.parametros()):
        return None

    plantilla = []
    usados = []
    for arg in args:
        if len(arg) != 1:
            return None
        t = arg[0]
        if t.tipo == "id" and t.lexema in nombres_params:
            idx = nombres_params.index(t.lexema)
            if idx in usados:
                return None
            usados.append(idx)
            plantilla.append(("param", idx))
        elif t.tipo in TIPOS_LITERAL:
            plantilla.append(("literal", t))
        else:
            return None

    if sorted(usados) != list(range(len(nombres_params))):
        return None

    return destino, plantilla


def _es_simple(s, clase):
    return isinstance(s, Simple) and s.clase == clase


def _redirigir_programa(programa, origen, destino, plantilla, cambios):
    for s in recorrer(programa):
        if isinstance(s, Simple):
            s.tokens = _redirigir(s.tokens, origen, destino, plantilla, cambios)
        elif isinstance(s, If):
            s.cond = _redirigir(s.cond, origen, destino, plantilla, cambios)


def _redirigir(tokens, origen, destino, plantilla, cambios):
    """Reemplaza cada origen(args) por destino(args reacomodados)."""
    salida = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if (t.tipo == "id" and t.lexema == origen
                and i + 1 < len(tokens) and tokens[i + 1].lexema == "("):
            args, j = partir_argumentos(tokens, i + 1)
            args = [_redirigir(a, origen, destino, plantilla, cambios) for a in args]
            r = t.renglon

            nueva = [Token("id", destino, r), Token("delim", "(", r)]
            for pos, (clase, valor) in enumerate(plantilla):
                if pos:
                    nueva.append(Token("delim", ",", r))
                if clase == "param":
                    nueva.extend(args[valor] if valor < len(args) else [])
                else:
                    nueva.append(Token(valor.tipo, valor.lexema, r))
            nueva.append(Token("delim", ")", r))

            antes = unir(tokens[i:j])
            cambios.append(Cambio(
                r, TECNICA, f"Llamada «{antes}» reemplazada por «{unir(nueva)}»"
            ))
            salida.extend(nueva)
            i = j
        else:
            salida.append(t)
            i += 1
    return salida
