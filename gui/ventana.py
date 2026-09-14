import tkinter as tk
from tkinter import ttk, scrolledtext
from nucleo.obtener_tokens import Tokenizador


class CompiladorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Compilador")
        self.root.geometry("1200x750")
        self.root.configure(bg="#f0f0f0")
        self.root.minsize(900, 600)

        # ---------- Estilos ----------
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background="white",
                        foreground="#333",
                        rowheight=24,
                        fieldbackground="white",
                        font=("Arial", 10))
        style.configure("Treeview.Heading",
                        background="#2c3e50",
                        foreground="white",
                        font=("Arial", 10, "bold"),
                        relief="flat")
        style.map("Treeview.Heading", background=[("active", "#34495e")])

        # ---------- Frame principal ----------
        main_frame = tk.Frame(root, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # ---------- Barra superior con título + botón ----------
        barra_superior = tk.Frame(main_frame, bg="#f0f0f0")
        barra_superior.pack(fill="x", pady=(0, 8))

        titulo = tk.Label(
            barra_superior, text="Compilador",
            font=("Arial", 14, "bold"), bg="#f0f0f0", fg="#2c3e50"
        )
        titulo.pack(side="left")

        self.btn_run = tk.Button(
            barra_superior, text="EJECUTAR",
            font=("Arial", 11, "bold"),
            bg="#2d8a4e", fg="white",
            activebackground="#236b3d", activeforeground="white",
            padx=25, pady=6, bd=0, relief="flat",
            cursor="hand2", command=self.ejecutar
        )
        self.btn_run.pack(side="right")

        # Efecto hover
        self.btn_run.bind("<Enter>", lambda e: self.btn_run.configure(bg="#3aa862"))
        self.btn_run.bind("<Leave>", lambda e: self.btn_run.configure(bg="#2d8a4e"))

        # ---------- Editor con números de línea ----------
        frame_editor = tk.LabelFrame(
            main_frame, text=" Código Fuente ",
            font=("Arial", 11, "bold"), bg="#f0f0f0", fg="#2c3e50"
        )
        frame_editor.pack(fill="x", pady=(0, 10))

        contenedor_editor = tk.Frame(frame_editor, bg="#1e1e1e")
        contenedor_editor.pack(fill="both", expand=True, padx=5, pady=5)

        # Canvas con los números de línea (a la izquierda)
        self.lineas_canvas = tk.Canvas(
            contenedor_editor, width=45, bg="#252526",
            highlightthickness=0, bd=0
        )
        self.lineas_canvas.pack(side="left", fill="y")

        # Editor de texto
        self.txt_codigo = scrolledtext.ScrolledText(
            contenedor_editor, wrap="none",
            font=("Consolas", 12),
            bg="#1e1e1e", fg="#ffffff",
            insertbackground="white",
            selectbackground="#264f78",
            height=14, bd=0, relief="flat"
        )
        self.txt_codigo.pack(side="left", fill="both", expand=True)

        # Eventos para actualizar números de línea
        self.txt_codigo.bind("<KeyRelease>", self.actualizar_numeros)
        self.txt_codigo.bind("<MouseWheel>", self.actualizar_numeros)
        self.txt_codigo.bind("<Button-1>", self.actualizar_numeros)
        self.txt_codigo.bind("<<Modified>>", self.on_modified)

        # ---------- Tablas ----------
        frame_tablas = tk.Frame(main_frame, bg="#f0f0f0")
        frame_tablas.pack(fill="both", expand=True)

        # Tabla de Símbolos
        frame_simbolos = tk.LabelFrame(
            frame_tablas, text=" Tabla de Símbolos ",
            font=("Arial", 11, "bold"), bg="#f0f0f0", fg="#2c3e50"
        )
        frame_simbolos.pack(side="left", fill="both", expand=True, padx=(0, 5))

        self.tabla_simbolos = ttk.Treeview(
            frame_simbolos, columns=("Lexema", "Tipo"),
            show="headings", height=12
        )
        self.tabla_simbolos.heading("Lexema", text="Lexema")
        self.tabla_simbolos.heading("Tipo", text="Tipo")
        self.tabla_simbolos.column("Lexema", width=150, anchor="center")
        self.tabla_simbolos.column("Tipo", width=120, anchor="center")
        self.tabla_simbolos.pack(fill="both", expand=True, padx=5, pady=5)

        scroll_sim = ttk.Scrollbar(frame_simbolos, orient="vertical", command=self.tabla_simbolos.yview)
        self.tabla_simbolos.configure(yscrollcommand=scroll_sim.set)
        scroll_sim.pack(side="right", fill="y")

        # Tabla de Errores
        frame_errores = tk.LabelFrame(
            frame_tablas, text=" Tabla de Errores ",
            font=("Arial", 11, "bold"), bg="#f0f0f0", fg="#2c3e50"
        )
        frame_errores.pack(side="right", fill="both", expand=True, padx=(5, 0))

        self.tabla_errores = ttk.Treeview(
            frame_errores,
            columns=("Token", "Lexema", "Renglón", "Descripción"),
            show="headings", height=12
        )
        self.tabla_errores.heading("Token", text="Token")
        self.tabla_errores.heading("Lexema", text="Lexema")
        self.tabla_errores.heading("Renglón", text="Renglón")
        self.tabla_errores.heading("Descripción", text="Descripción")
        self.tabla_errores.column("Token", width=80, anchor="center")
        self.tabla_errores.column("Lexema", width=100, anchor="center")
        self.tabla_errores.column("Renglón", width=70, anchor="center")
        self.tabla_errores.column("Descripción", width=250, anchor="w")
        self.tabla_errores.pack(fill="both", expand=True, padx=5, pady=5)

        scroll_err = ttk.Scrollbar(frame_errores, orient="vertical", command=self.tabla_errores.yview)
        self.tabla_errores.configure(yscrollcommand=scroll_err.set)
        scroll_err.pack(side="right", fill="y")

        # Inicializar números de línea
        self.actualizar_numeros()

    # ---------------------------------------------------------
    def actualizar_numeros(self, event=None):
        """Redibuja los números de línea del editor."""
        self.lineas_canvas.delete("all")

        i = self.txt_codigo.index("@0,0")
        while True:
            dline = self.txt_codigo.dlineinfo(i)
            if dline is None:
                break
            y = dline[1]
            linenum = str(i).split(".")[0]
            self.lineas_canvas.create_text(
                38, y, anchor="ne", text=linenum,
                fill="#858585", font=("Consolas", 12)
            )
            i = self.txt_codigo.index(f"{i}+1line")

    def on_modified(self, event):
        """Detecta cambios para actualizar números."""
        self.txt_codigo.edit_modified(False)
        self.actualizar_numeros()

    # ---------------------------------------------------------
    def limpiar_tablas(self):
        """Limpia las tablas antes de cada ejecución."""
        for item in self.tabla_simbolos.get_children():
            self.tabla_simbolos.delete(item)
        for item in self.tabla_errores.get_children():
            self.tabla_errores.delete(item)

    # ---------------------------------------------------------
    def _inferir_tipos_declarados(self, tokens):
        """
        Recorre los tokens buscando dos patrones:

          1) Declaración de variables:  TIPO id (',' id)*  ';'
             ej.  full QunoZ, QdosZ ;

          2) Declaración de función:    TIPO id '(' ... ')' ...
             ej.  full QfuncionZ() { ... }
             Se registra el nombre de la función con el tipo declarado
             (su "tipo de retorno") y solo se saltan los paréntesis de
             parámetros; el cuerpo { ... } se sigue recorriendo con el
             mismo bucle, así que las declaraciones internas (variables
             locales) se detectan igual.

        Regresa un diccionario {lexema: tipo} que cubre tanto variables
        como funciones.
        """
        tipos = {}
        n = len(tokens)
        i = 0
        while i < n:
            tok = tokens[i]
            if tok.tipo == "reservada" and tok.lexema in ("full", "royal", "chain"):
                tipo_decl = tok.lexema
                j = i + 1

                if j < n and tokens[j].tipo == "id":
                    nombre = tokens[j].lexema
                    k = j + 1

                    if k < n and tokens[k].tipo == "delim" and tokens[k].lexema == "(":
                        # Es una función: registramos el nombre y saltamos
                        # solo la lista de parámetros "( ... )"
                        tipos[nombre] = tipo_decl
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
                        # Es declaración normal de variables hasta el ';'
                        ids_declarados = [nombre]
                        m = k
                        while m < n and not (tokens[m].tipo == "delim" and tokens[m].lexema == ";"):
                            if tokens[m].tipo == "id":
                                ids_declarados.append(tokens[m].lexema)
                            m += 1
                        for var in ids_declarados:
                            tipos[var] = tipo_decl
                        i = m
            i += 1
        return tipos

    def llenar_tabla_simbolos(self, tokens):
        """Vuelca los tokens a la tabla de símbolos de la GUI.

        - Las palabras clave de tipo (full/royal/chain) aparecen como
          su propia fila: lexema = tipo (ej. "full" | "full").
        - A cada variable (id) se le asigna el tipo con el que fue
          declarada. Si nunca se declaró, la columna Tipo queda vacía
          (pero la variable igual aparece en la tabla).
        - A las constantes (literales full/royal/chain) se les asigna
          su propio tipo de token.
        - Operadores (=, +, -, *, /) y delimitadores ( ) { } [ ] , ;
          también aparecen en la tabla, pero con Tipo vacío: la columna
          Tipo solo puede valer full, royal o chain.
        - Otras palabras reservadas (void, return, if) no van en la tabla.
        - Ningún lexema se repite en la tabla.
        """
        tipos_declarados = self._inferir_tipos_declarados(tokens)
        lexemas_insertados = set()

        for tok in tokens:
            # Palabras clave de tipo: van como su propia fila (full|full, etc.)
            if tok.tipo == "reservada":
                if tok.lexema in ("full", "royal", "chain"):
                    if tok.lexema not in lexemas_insertados:
                        self.tabla_simbolos.insert("", "end", values=(tok.lexema, tok.lexema))
                        lexemas_insertados.add(tok.lexema)
                continue

            # Operadores y delimitadores: van en la tabla, pero la columna
            # Tipo se deja vacía (Tipo solo aplica a full/royal/chain)
            if tok.tipo in ("op", "delim"):
                if tok.lexema in lexemas_insertados:
                    continue
                self.tabla_simbolos.insert("", "end", values=(tok.lexema, ""))
                lexemas_insertados.add(tok.lexema)
                continue

            # La tabla de símbolos también lleva identificadores y constantes
            if tok.tipo not in ("id", "full", "royal", "chain"):
                continue

            if tok.lexema in lexemas_insertados:
                continue

            if tok.tipo == "id":
                tipo_tabla = tipos_declarados.get(tok.lexema, "")
            else:
                tipo_tabla = tok.tipo

            self.tabla_simbolos.insert(
                "", "end",
                values=(tok.lexema, tipo_tabla)
            )
            lexemas_insertados.add(tok.lexema)

    def ejecutar(self):
        """Aquí irá la lógica del análisis semántico."""
        codigo = self.txt_codigo.get("1.0", tk.END).strip()
        self.limpiar_tablas()

        if not codigo:
            return

        # 1. Tokenizar
        tokenizador = Tokenizador(codigo)
        tokens = tokenizador.tokenizar()

        # 2. Llenar la tabla de símbolos
        self.llenar_tabla_simbolos(tokens)