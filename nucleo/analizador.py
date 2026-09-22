"""
Orquestador del análisis semántico.

Ejecuta todas las fases en orden:
  1. Inferir tipos declarados
  2. Verificar duplicados
  3. Llenar tabla de símbolos
  4. Verificar variables/funciones indefinidas
  5. Verificar asignaciones
  6. Verificar llamadas a funciones
  7. Verificar returns
"""

from nucleo.inferencia import inferir_tipos_declarados
from nucleo.duplicados import verificar_duplicados
from nucleo.tabla_simbolos import llenar_tabla_simbolos
from nucleo.indefinidos import verificar_indefinidos
from nucleo.asignaciones import verificar_asignaciones
from nucleo.llamadas import verificar_llamadas
from nucleo.returns import verificar_returns


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

        # Tabla de símbolos: el "primer tipo" encontrado por nombre
        self.simbolos_globales = {}

        # Firmas de funciones: {nombre: [tipo_param1, tipo_param2, ...]}
        self.firmas_funciones = {}

    # =========================================================
    # API pública
    # =========================================================
    def analizar(self):
        inferir_tipos_declarados(self)
        verificar_duplicados(self)
        llenar_tabla_simbolos(self)
        verificar_indefinidos(self)
        verificar_asignaciones(self)
        verificar_llamadas(self)
        verificar_returns(self)

        # Ordenar errores por renglón
        self.resultado.errores.sort(key=lambda e: e[2])

        # Reasignar tokens secuencialmente
        errores_renumerados = []
        for idx, (_, lexema, renglon, descripcion) in enumerate(self.resultado.errores, start=1):
            errores_renumerados.append((f"ErrSem{idx}", lexema, renglon, descripcion))
        self.resultado.errores = errores_renumerados

        return self.resultado

    # =========================================================
    # Helper compartido por todas las fases
    # =========================================================
    def _insertar_error(self, tok, descripcion, errores_reportados):
        clave = (tok.lexema, tok.renglon)
        if clave in errores_reportados:
            return
        errores_reportados.add(clave)

        self.contador_errores += 1
        self.resultado.errores.append(
            (f"ErrSem{self.contador_errores}", tok.lexema, tok.renglon, descripcion)
        )