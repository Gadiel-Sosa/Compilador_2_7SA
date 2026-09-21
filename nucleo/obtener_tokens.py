import re


class Token:
    """Representa un token del código fuente."""

    def __init__(self, tipo, lexema, renglon):
        self.tipo = tipo          # "id", "full", "royal", "chain", "op", "delim", "reservada"
        self.lexema = lexema      # el texto tal cual
        self.renglon = renglon    # número de línea (1-based)

    def __repr__(self):
        return f"Token({self.tipo!r}, {self.lexema!r}, renglon {self.renglon})"


class ErrorLexico:
    """Representa un error detectado durante el análisis léxico."""

    def __init__(self, token, lexema, renglon, descripcion):
        self.token = token            # etiqueta corta del tipo de error, ej. "ID_INV"
        self.lexema = lexema          # el texto que causó el error
        self.renglon = renglon        # número de línea (1-based)
        self.descripcion = descripcion  # explicación legible del error

    def __repr__(self):
        return f"ErrorLexico({self.token!r}, {self.lexema!r}, renglon {self.renglon}, {self.descripcion!r})"


class Tokenizador:
    """Convierte el código fuente en una lista de tokens."""

    # Palabras reservadas del lenguaje
    RESERVADAS = {
        "full", "royal", "chain", "void", "return", "if", "else",
        "return"
        
        }

    # Operadores
    OPERADORES = {"=", "+", "-", "*", "/", "<", ">", "!"}
    
    OPERADORES_2 = {"<=", ">=", "==", "!=", "&&", "||"}

    # Delimitadores (incluye paréntesis, llaves y corchetes)
    DELIMITADORES = {";", ",", "(", ")", "{", "}", "[", "]"}

    # Regex
    RE_VARIABLE = re.compile(r"Q[a-z0-9]+Z")
    RE_REAL = re.compile(r"\d+\.\d+")
    RE_ENTERO = re.compile(r"\d+")

    def __init__(self, codigo):
        self.codigo = codigo
        self.tokens = []
        self.errores = []

    def tokenizar(self):
        """Recorre el código y genera la lista de tokens."""
        codigo_limpio = self._quitar_comentarios(self.codigo)
        for num_linea, linea in enumerate(codigo_limpio.split("\n"), start=1): 
            self._procesar_linea(linea, num_linea)
        return self.tokens

    def _quitar_comentarios(self, codigo):
        """Elimina comentarios de línea (//) y de bloque (/* */)."""
        codigo = re.sub(r"/\*.*?\*/", "", codigo, flags=re.DOTALL)
        codigo = re.sub(r"//.*", "", codigo)
        return codigo

    def _procesar_linea(self, linea, num_linea):
        """Extrae todos los tokens de una sola línea."""
        pos = 0
        while pos < len(linea):
            char = linea[pos]

            if char.isspace():
                pos += 1
                continue

            if linea[pos:pos+2] == "//":
                break

            if char == '"':
                fin = linea.find('"', pos + 1)
                if fin == -1:
                    fin = len(linea) - 1
                lexema = linea[pos:fin+1]
                self.tokens.append(Token("chain", lexema, num_linea))
                pos = fin + 1
                continue

            match = self.RE_VARIABLE.match(linea, pos)
            if match:
                lexema = match.group()
                self.tokens.append(Token("id", lexema, num_linea))
                pos = match.end()
                continue

            match = self.RE_REAL.match(linea, pos)
            if match:
                lexema = match.group()
                self.tokens.append(Token("royal", lexema, num_linea))
                pos = match.end()
                continue

            match = self.RE_ENTERO.match(linea, pos)
            if match:
                lexema = match.group()
                self.tokens.append(Token("full", lexema, num_linea))
                pos = match.end()
                continue

            if char.isalpha():
                j = pos
                while j < len(linea) and linea[j].isalpha():
                    j += 1
                palabra = linea[pos:j]
                if palabra in self.RESERVADAS:
                    self.tokens.append(Token("reservada", palabra, num_linea))
                else:
                    # No es palabra reservada ni cumple el patrón de variable
                    # (Q...Z) -> se reporta como identificador inválido.
                    self.errores.append(ErrorLexico(
                        "ID_INV",
                        palabra,
                        num_linea,
                        "Identificador no válido: no sigue el patrón Q...Z ni es palabra reservada"
                    ))
                pos = j
                continue

            # ----- Operadores de DOS caracteres (se intentan PRIMERO) -----
            if pos + 2 <= len(linea):
                dos_chars = linea[pos:pos+2]
                if dos_chars in self.OPERADORES_2:
                    self.tokens.append(Token("op", dos_chars, num_linea))
                    pos += 2
                    continue

            # ----- Operadores de UN carácter -----
            if char in self.OPERADORES:
                self.tokens.append(Token("op", char, num_linea))
                pos += 1
                continue

            if char in self.DELIMITADORES:
                self.tokens.append(Token("delim", char, num_linea))
                pos += 1
                continue

            pos += 1