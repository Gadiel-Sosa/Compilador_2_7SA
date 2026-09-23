import tkinter as tk
from tkinter import ttk, scrolledtext
from nucleo.obtener_tokens import Tokenizador
from nucleo.analizador import Analizador


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

        # ---------- Barra superior ----------
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

        self.btn_run.bind("<Enter>", lambda e: self.btn_run.configure(bg="#3aa862"))
        self.btn_run.bind("<Leave>", lambda e: self.btn_run.configure(bg="#2d8a4e"))

        # ---------- Editor ----------
        frame_editor = tk.LabelFrame(
            main_frame, text=" Código Fuente ",
            font=("Arial", 11, "bold"), bg="#f0f0f0", fg="#2c3e50"
        )
        frame_editor.pack(fill="x", pady=(0, 10))

        contenedor_editor = tk.Frame(frame_editor, bg="#1e1e1e")
        contenedor_editor.pack(fill="both", expand=True, padx=5, pady=5)

        self.lineas_canvas = tk.Canvas(
            contenedor_editor, width=45, bg="#252526",
            highlightthickness=0, bd=0
        )
        self.lineas_canvas.pack(side="left", fill="y")

        self.txt_codigo = scrolledtext.ScrolledText(
            contenedor_editor, wrap="none",
            font=("Consolas", 12),
            bg="#1e1e1e", fg="#ffffff",
            insertbackground="white",
            selectbackground="#264f78",
            height=14, bd=0, relief="flat"
        )
        self.txt_codigo.pack(side="left", fill="both", expand=True)

        # ---------- Eventos para actualizar números de línea ----------
        self.txt_codigo.bind("<KeyRelease>", self._programar_actualizacion)
        self.txt_codigo.bind("<MouseWheel>", self._programar_actualizacion)
        self.txt_codigo.bind("<Button-1>", self._programar_actualizacion)
        self.txt_codigo.bind("<ButtonRelease-1>", self._programar_actualizacion)
        self.txt_codigo.bind("<<Modified>>", self.on_modified)
        self.txt_codigo.bind("<FocusIn>", self._programar_actualizacion)
        self.txt_codigo.bind("<FocusOut>", self._programar_actualizacion)
        self.txt_codigo.bind("<Configure>", self._programar_actualizacion)

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
        self.tabla_errores.column("Lexema", width=120, anchor="center")
        self.tabla_errores.column("Renglón", width=70, anchor="center")
        self.tabla_errores.column("Descripción", width=500, minwidth=300, anchor="w")
        self.tabla_errores.pack(fill="both", expand=True, padx=5, pady=5)

        scroll_err = ttk.Scrollbar(frame_errores, orient="vertical", command=self.tabla_errores.yview)
        self.tabla_errores.configure(yscrollcommand=scroll_err.set)
        scroll_err.pack(side="right", fill="y")

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

    def _programar_actualizacion(self, event=None):
        """Programa la actualización de números tras el siguiente ciclo de eventos."""
        self.root.after_idle(self.actualizar_numeros)

    def on_modified(self, event):
        self.txt_codigo.edit_modified(False)
        self._programar_actualizacion()

    # ---------------------------------------------------------
    def limpiar_tablas(self):
        for item in self.tabla_simbolos.get_children():
            self.tabla_simbolos.delete(item)
        for item in self.tabla_errores.get_children():
            self.tabla_errores.delete(item)

    # ---------------------------------------------------------
    def ejecutar(self):
        codigo = self.txt_codigo.get("1.0", tk.END).strip()
        self.limpiar_tablas()

        if not codigo:
            return

        # 1. Tokenizar
        tokenizador = Tokenizador(codigo)
        tokens = tokenizador.tokenizar()

        # 2. Analizar
        analizador = Analizador(tokens)
        resultado = analizador.analizar()

        # 3. Volcar símbolos a la tabla
        for lexema, tipo in resultado.simbolos:
            self.tabla_simbolos.insert("", "end", values=(lexema, tipo))

        # 4. Volcar errores a la tabla
        for token, lexema, renglon, descripcion in resultado.errores:
            self.tabla_errores.insert(
                "", "end",
                values=(token, lexema, renglon, descripcion)
            )