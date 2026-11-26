"""
Traduce el triplo (código intermedio optimizado) a código ensamblador.

Reglas (Unidad IV. Generación de código objeto):
  - Operadores:  =  MOV   +  ADD   -  SUB   *  MUL   /  DIV   %  DIV
  - Temporales -> registros AX, BX (16 bits) o AH, AL, BH, BL (8 bits).
    No se combinan registros de distinto tamaño en una misma instrucción.
  - Multiplicación: multiplicando en AL, multiplicador en BL, MUL BL.
    El resultado queda en AX.
  - División: dividendo en AX, divisor en BL, DIV BL.
    El cociente queda en AL.
  - Módulo: igual que la división; el residuo queda en AH.
  - Cuando un valor de 8 bits (AL o AH) debe pasar a ocupar todo AX
    se escribe  MOV AX, AL  o  MOV AX, AH  (en lugar de MOV AH, 0).

Además (no viene en la presentación):
  - Comparaciones: CMP + salto condicional (JL, JG, JLE, JGE, JE, JNE).
  - Filas TRUE / FALSE / JMP del triplo -> saltos a etiquetas L<fila>.
  - Si hacen falta más de dos temporales a la vez se usan CX y DX.
"""

import re

_RE_TEMPORAL = re.compile(r"^T\d+$")

ARITMETICOS = {"+": "ADD", "-": "SUB"}
MULDIV = ("*", "/", "%")
RELACIONALES = {"<": "JL", ">": "JG", "<=": "JLE", ">=": "JGE", "==": "JE", "!=": "JNE"}

FAMILIAS = ("A", "B", "C", "D")


def _es_temporal(x):
    return isinstance(x, str) and bool(_RE_TEMPORAL.match(x))


def _familia(reg):
    return reg[0]


def _es_8bits(reg):
    return reg[1] in ("L", "H")


class GeneradorCodigoObjeto:
    def __init__(self, filas):
        self.filas = sorted(filas, key=lambda f: f.numero)
        self.lineas = []
        self.ubicacion = {}      # temporal -> registro donde está su valor
        self.ultima_rel = None   # último operador relacional comparado
        self.ultimo_temp = None  # último temporal definido (para condiciones simples)

    # ==========================================================
    # API
    # ==========================================================
    def generar(self):
        destinos = self._destinos_de_salto()
        numeros = [f.numero for f in self.filas]
        etiquetas_por_fila = {}
        etiquetas_finales = []
        for d in sorted(destinos):
            # La etiqueta va en la fila destino (o la siguiente que exista)
            siguiente = next((n for n in numeros if n >= d), None)
            if siguiente is None:
                etiquetas_finales.append(d)
            else:
                etiquetas_por_fila.setdefault(siguiente, []).append(d)

        for idx, fila in enumerate(self.filas):
            for d in etiquetas_por_fila.get(fila.numero, []):
                self.lineas.append(f"L{d}:")
            self._traducir(idx, fila)

        for d in etiquetas_finales:
            self.lineas.append(f"L{d}:")
        return self.lineas

    # ==========================================================
    # Utilidades
    # ==========================================================
    def _emitir(self, instr):
        self.lineas.append(f"    {instr}")

    def _destinos_de_salto(self):
        destinos = set()
        for f in self.filas:
            if f.operador == "JMP" and str(f.fuente).isdigit():
                destinos.add(int(f.fuente))
            elif f.fuente in ("TRUE", "FALSE") and str(f.operador).isdigit():
                destinos.add(int(f.operador))
        return destinos

    def _sigue_vivo(self, idx, temp):
        """¿Se vuelve a usar `temp` antes de redefinirse?"""
        for f in self.filas[idx + 1:]:
            if f.fuente == temp:
                return True
            if f.objeto == temp:
                return f.operador != "="   # '=' lo redefine -> muere
        return False

    def _rol(self, idx, temp):
        """Papel del temporal en su primera multiplicación/división."""
        for f in self.filas[idx + 1:]:
            if f.objeto == temp and f.operador == "=":
                break
            if f.operador in MULDIV:
                if f.objeto == temp:
                    return "multiplicando" if f.operador == "*" else "dividendo"
                if f.fuente == temp:
                    return "operando"
        return "libre"

    def _familias_ocupadas(self, excepto=()):
        return {_familia(r) for t, r in self.ubicacion.items() if t not in excepto}

    def _familia_libre(self, preferencia=FAMILIAS, excepto=()):
        ocupadas = self._familias_ocupadas(excepto)
        for f in preferencia:
            if f not in ocupadas:
                return f
        return preferencia[0]

    def _liberar_familia(self, familia, excepto=()):
        """Si otro temporal vivo ocupa `familia`, lo mueve a un registro libre."""
        for t, r in list(self.ubicacion.items()):
            if t in excepto or _familia(r) != familia:
                continue
            ocupadas = self._familias_ocupadas() | {familia}
            nueva = next((f for f in ("C", "D", "B", "A") if f not in ocupadas), None)
            if nueva is None:
                continue
            destino = f"{nueva}L" if _es_8bits(r) else f"{nueva}X"
            self._emitir(f"MOV {destino}, {r}")
            self.ubicacion[t] = destino

    def _ubic(self, temp):
        """Registro de un temporal (si se perdió el rastro, se asume AX)."""
        return self.ubicacion.get(temp, "AX")

    def _a_16bits(self, temp):
        """Extiende un temporal de 8 bits a su registro de 16 bits (MOV AX, AL)."""
        r = self._ubic(temp)
        if not _es_8bits(r):
            return r
        fam = _familia(r)
        self._emitir(f"MOV {fam}X, {r}")   # MOV AX, AL  /  MOV AX, AH
        self.ubicacion[temp] = f"{fam}X"
        return f"{fam}X"

    def _en_bajo(self, reg):
        """Parte baja (8 bits) de un registro."""
        return f"{reg[0]}L" if reg.endswith("X") else reg

    def _liberar_si_muere(self, idx, *temps):
        for t in temps:
            if _es_temporal(t) and t in self.ubicacion and not self._sigue_vivo(idx, t):
                del self.ubicacion[t]

    # ==========================================================
    # Traducción fila por fila
    # ==========================================================
    def _traducir(self, idx, f):
        op, obj, fte = f.operador, f.objeto, f.fuente

        if op == "JMP":
            if str(fte).isdigit():
                self._emitir(f"JMP L{fte}")
            else:
                # p. ej. el JMP de retorno de una función que nunca se llama
                self.lineas.append(f"    ; fila {f.numero}: JMP sin destino")
        elif fte == "TRUE":
            self._salto_verdadero(op)
        elif fte == "FALSE":
            self._emitir(f"JMP L{op}")
        elif op == "=":
            self._asignacion(idx, obj, fte)
        elif op in ARITMETICOS:
            self._suma_resta(idx, ARITMETICOS[op], obj, fte)
        elif op == "*":
            self._multiplicacion(idx, obj, fte)
        elif op in ("/", "%"):
            self._division(idx, op, obj, fte)
        elif op in RELACIONALES:
            self._comparacion(idx, op, obj, fte)
        else:
            self.lineas.append(f"    ; fila {f.numero}: operador '{op}' sin traducción")

    # ---------- = ----------
    def _asignacion(self, idx, obj, fte):
        if _es_temporal(obj):
            origen = self._ubic(fte) if _es_temporal(fte) else fte
            if _es_temporal(fte) and fte == obj:
                return  # T = T: ya está en su registro
            self.ubicacion.pop(obj, None)

            rol = self._rol(idx, obj)
            excepto = (fte,) if _es_temporal(fte) else ()
            if rol == "multiplicando":
                self._liberar_familia("A", excepto=excepto)
                destino = "AL"
            elif rol == "dividendo":
                self._liberar_familia("A", excepto=excepto)
                destino = "AX"
            elif rol == "operando":
                self._liberar_familia("B", excepto=excepto)
                destino = "BL"
            else:
                destino = f"{self._familia_libre(excepto=excepto)}X"

            if _es_temporal(fte):
                if _es_8bits(destino) and not _es_8bits(origen):
                    origen = self._en_bajo(origen)
            if destino != origen:
                self._emitir(f"MOV {destino}, {origen}")
            self.ubicacion[obj] = destino
            self.ultimo_temp = obj
            self._liberar_si_muere(idx, fte)
            return

        # Variable = temporal  (o variable = valor)
        if _es_temporal(fte):
            self._emitir(f"MOV {obj}, {self._ubic(fte)}")
            self._liberar_si_muere(idx, fte)
        else:
            reg = f"{self._familia_libre()}X"
            self._emitir(f"MOV {reg}, {fte}")
            self._emitir(f"MOV {obj}, {reg}")

    # ---------- + - ----------
    def _suma_resta(self, idx, mnem, obj, fte):
        r = self._ubic(obj)
        if _es_temporal(fte):
            r2 = self._ubic(fte)
            if _es_8bits(r) != _es_8bits(r2):
                # No se combinan tamaños: se extiende el de 8 bits
                if _es_8bits(r):
                    r = self._a_16bits(obj)
                else:
                    r2 = self._a_16bits(fte)
            self._emitir(f"{mnem} {r}, {r2}")
            self._liberar_si_muere(idx, fte)
        else:
            self._emitir(f"{mnem} {r}, {fte}")
        self.ubicacion[obj] = r

    # ---------- * ----------
    def _cargar_bl(self, obj, fte):
        """Deja el multiplicador/divisor en BL."""
        if _es_temporal(fte):
            r = self._ubic(fte)
            if _familia(r) == "B":
                if r == "BH":
                    self._emitir("MOV BL, BH")
            else:
                self._liberar_familia("B", excepto=(fte,))
                self._emitir(f"MOV BL, {self._en_bajo(r) if r != 'AH' else 'AH'}")
            self.ubicacion[fte] = "BL"
        else:
            self._liberar_familia("B")
            self._emitir(f"MOV BL, {fte}")

    def _operando_en_familia_a(self, fte):
        return _es_temporal(fte) and _familia(self._ubic(fte)) == "A"

    def _multiplicacion(self, idx, obj, fte):
        # Orden del PDF: 1) multiplicando en AL, 2) multiplicador en BL, 3) MUL BL.
        # Solo si el multiplicador ocupa AX se pasa primero a BL para no perderlo.
        primero_bl = self._operando_en_familia_a(fte)
        if primero_bl:
            self._cargar_bl(obj, fte)
        r = self._ubic(obj)
        if _familia(r) == "A":
            if r == "AH":
                self._emitir("MOV AL, AH")
        else:
            self._liberar_familia("A", excepto=(obj,))
            self._emitir(f"MOV AL, {self._en_bajo(r)}")
            self.ubicacion[obj] = "AL"
        if not primero_bl:
            self._cargar_bl(obj, fte)
        self._emitir("MUL BL")
        self.ubicacion[obj] = "AX"
        self._liberar_si_muere(idx, fte)

    # ---------- / % ----------
    def _division(self, idx, op, obj, fte):
        # Orden del PDF: 1) dividendo en AX, 2) divisor en BL, 3) DIV BL.
        # Solo si el divisor ocupa AX se pasa primero a BL para no perderlo.
        primero_bl = self._operando_en_familia_a(fte)
        if primero_bl:
            self._cargar_bl(obj, fte)
        r = self._ubic(obj)
        if r != "AX":
            if _familia(r) != "A":
                self._liberar_familia("A", excepto=(obj,))
            # MOV AX, AL / MOV AX, AH / MOV AX, BX ...: el valor pasa a todo AX
            self._emitir(f"MOV AX, {r}")
        self.ubicacion[obj] = "AX"
        if not primero_bl:
            self._cargar_bl(obj, fte)
        self._emitir("DIV BL")
        # Cociente en AL, residuo en AH
        self.ubicacion[obj] = "AL" if op == "/" else "AH"
        self._liberar_si_muere(idx, fte)

    # ---------- < > <= >= == != ----------
    def _comparacion(self, idx, op, obj, fte):
        r = self._ubic(obj)
        if _es_temporal(fte):
            r2 = self._ubic(fte)
            if _es_8bits(r) != _es_8bits(r2):
                if _es_8bits(r):
                    r = self._a_16bits(obj)
                else:
                    r2 = self._a_16bits(fte)
            self._emitir(f"CMP {r}, {r2}")
            self._liberar_si_muere(idx, fte)
        else:
            self._emitir(f"CMP {r}, {fte}")
        self.ultima_rel = op
        self._liberar_si_muere(idx, obj)

    def _salto_verdadero(self, destino):
        if self.ultima_rel is None:
            # Condición sin operador relacional: verdadera si es distinta de 0
            reg = self._ubic(self.ultimo_temp) if self.ultimo_temp else "AX"
            self._emitir(f"CMP {reg}, 0")
            salto = "JNE"
        else:
            salto = RELACIONALES[self.ultima_rel]
        self._emitir(f"{salto} L{destino}")
        self.ultima_rel = None
        self.ubicacion.clear()


def generar_codigo_objeto(filas):
    """Devuelve la lista de líneas de ensamblador a partir de las filas del triplo."""
    return GeneradorCodigoObjeto(filas).generar()
