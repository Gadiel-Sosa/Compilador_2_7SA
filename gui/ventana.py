import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
from nucleo.obtener_tokens import Tokenizador
from nucleo.analizador import Analizador
from nucleo.optimizacion import optimizar
import os
 
 
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
 
        # ---------- Botón EJECUTAR ----------
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
 
        self._n_optimizaciones = 0

        # ---------- Atajos de teclado ----------
        self.root.bind("<F5>", self.ejecutar)
        self.root.bind("<Control-Return>", self.ejecutar)
        # (en el editor también, para que Ctrl+Enter no inserte un salto de línea)

        # ---------- Barra de estado ----------
        self.lbl_estado = tk.Label(
            main_frame, text="Escribe código y presiona EJECUTAR (F5).",
            font=("Arial", 10), bg="#e4e4e4", fg="#555",
            anchor="w", padx=10, pady=4
        )
        self.lbl_estado.pack(side="bottom", fill="x", pady=(8, 0))
 
        style.configure("TNotebook", background="#f0f0f0", borderwidth=0)
        style.configure("TNotebook.Tab", font=("Arial", 10, "bold"),
                        padding=(14, 5), background="#dcdcdc", foreground="#2c3e50")
        style.map("TNotebook.Tab",
                  background=[("selected", "#2c3e50")],
                  foreground=[("selected", "white")])

        # ---------- División vertical: códigos arriba, tablas abajo ----------
        panel_vertical = ttk.PanedWindow(main_frame, orient="vertical")
        panel_vertical.pack(fill="both", expand=True)

        # ---------- División horizontal: fuente | optimizado ----------
        panel_codigos = ttk.PanedWindow(panel_vertical, orient="horizontal")
        panel_vertical.add(panel_codigos, weight=3)

        # ---------- Editor ----------
        frame_editor = tk.LabelFrame(
            panel_codigos, text=" Código Fuente ",
            font=("Arial", 11, "bold"), bg="#f0f0f0", fg="#2c3e50"
        )
        panel_codigos.add(frame_editor, weight=1)
 
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
        self.txt_codigo.bind("<Control-Return>", self.ejecutar)
 
        # ---------- Código optimizado (solo lectura) ----------
        frame_opt = tk.LabelFrame(
            panel_codigos, text=" Código Optimizado ",
            font=("Arial", 11, "bold"), bg="#f0f0f0", fg="#2c3e50"
        )
        panel_codigos.add(frame_opt, weight=1)

        self.txt_optimizado = scrolledtext.ScrolledText(
            frame_opt, wrap="none",
            font=("Consolas", 12),
            bg="#1e1e1e", fg="#ffffff",
            insertbackground="white",
            selectbackground="#264f78",
            height=14, bd=0, relief="flat"
        )
        self.txt_optimizado.pack(fill="both", expand=True, padx=5, pady=5)
        self.txt_optimizado.tag_configure("num", foreground="#858585")
        self.txt_optimizado.tag_configure("aviso", foreground="#858585",
                                          font=("Consolas", 11, "italic"))
        self._mostrar_aviso_optimizado("Ejecuta el código para ver su versión optimizada.")

        # ---------- Pestañas de resultados ----------
        self.notebook = ttk.Notebook(panel_vertical)
        panel_vertical.add(self.notebook, weight=2)

        # Tabla de Símbolos
        frame_simbolos = tk.Frame(self.notebook, bg="#f0f0f0")
        self.notebook.add(frame_simbolos, text="Tabla de Símbolos")

        self.tabla_simbolos = ttk.Treeview(
            frame_simbolos, columns=("Lexema", "Tipo"),
            show="headings", height=8
        )
        self.tabla_simbolos.heading("Lexema", text="Lexema")
        self.tabla_simbolos.heading("Tipo", text="Tipo")
        self.tabla_simbolos.column("Lexema", width=150, anchor="center")
        self.tabla_simbolos.column("Tipo", width=120, anchor="center")
        scroll_sim = ttk.Scrollbar(frame_simbolos, orient="vertical", command=self.tabla_simbolos.yview)
        self.tabla_simbolos.configure(yscrollcommand=scroll_sim.set)
        scroll_sim.pack(side="right", fill="y", pady=5)
        self.tabla_simbolos.pack(fill="both", expand=True, padx=5, pady=5)

        # Tabla de Errores
        frame_errores = tk.Frame(self.notebook, bg="#f0f0f0")
        self.notebook.add(frame_errores, text="Tabla de Errores")

        self.tabla_errores = ttk.Treeview(
            frame_errores,
            columns=("Token", "Lexema", "Renglón", "Descripción"),
            show="headings", height=8
        )
        self.tabla_errores.heading("Token", text="Token")
        self.tabla_errores.heading("Lexema", text="Lexema")
        self.tabla_errores.heading("Renglón", text="Renglón")
        self.tabla_errores.heading("Descripción", text="Descripción")
        self.tabla_errores.column("Token", width=80, anchor="center")
        self.tabla_errores.column("Lexema", width=120, anchor="center")
        self.tabla_errores.column("Renglón", width=70, anchor="center")
        self.tabla_errores.column("Descripción", width=500, minwidth=300, anchor="w")
        scroll_err = ttk.Scrollbar(frame_errores, orient="vertical", command=self.tabla_errores.yview)
        self.tabla_errores.configure(yscrollcommand=scroll_err.set)
        scroll_err.pack(side="right", fill="y", pady=5)
        self.tabla_errores.pack(fill="both", expand=True, padx=5, pady=5)

        # Optimizaciones aplicadas
        frame_cambios = tk.Frame(self.notebook, bg="#f0f0f0")
        self.notebook.add(frame_cambios, text="Optimizaciones")

        self.tabla_cambios = ttk.Treeview(
            frame_cambios, columns=("Renglón", "Técnica", "Descripción"),
            show="headings", height=8
        )
        self.tabla_cambios.heading("Renglón", text="Renglón")
        self.tabla_cambios.heading("Técnica", text="Técnica")
        self.tabla_cambios.heading("Descripción", text="Descripción")
        self.tabla_cambios.column("Renglón", width=80, anchor="center", stretch=False)
        self.tabla_cambios.column("Técnica", width=160, anchor="center", stretch=False)
        self.tabla_cambios.column("Descripción", width=800, anchor="w")

        scroll_cam = ttk.Scrollbar(frame_cambios, orient="vertical", command=self.tabla_cambios.yview)
        self.tabla_cambios.configure(yscrollcommand=scroll_cam.set)
        scroll_cam.pack(side="right", fill="y", pady=5)
        self.tabla_cambios.pack(fill="both", expand=True, padx=5, pady=5)

        # Código objeto (ensamblador generado del triplo optimizado)
        frame_asm = tk.Frame(self.notebook, bg="#f0f0f0")
        self.notebook.add(frame_asm, text="Código Objeto")

        self.txt_asm = scrolledtext.ScrolledText(
            frame_asm, wrap="none",
            font=("Consolas", 12),
            bg="#1e1e1e", fg="#ffffff",
            selectbackground="#264f78",
            height=8, bd=0, relief="flat"
        )
        self.txt_asm.pack(fill="both", expand=True, padx=5, pady=5)
        self.txt_asm.tag_configure("etiqueta", foreground="#4ec9b0")
        self.txt_asm.tag_configure("mnemonico", foreground="#569cd6")
        self.txt_asm.tag_configure("aviso", foreground="#858585",
                                   font=("Consolas", 11, "italic"))
        self._mostrar_codigo_objeto("Ejecuta el código para ver su código objeto.", aviso=True)

        # Doble clic en un error -> ir a su renglón
        self.tabla_errores.bind("<Double-1>", self._ir_a_error)
        self.txt_codigo.tag_configure("linea_error", background="#5a1d1d")

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
        for tabla in (self.tabla_simbolos, self.tabla_errores, self.tabla_cambios):
            for item in tabla.get_children():
                tabla.delete(item)

    def _actualizar_pestanas(self):
        """Muestra la cantidad de filas en el título de cada pestaña."""
        n_sim = len(self.tabla_simbolos.get_children())
        n_err = len(self.tabla_errores.get_children())
        self.notebook.tab(0, text=f"Tabla de Símbolos ({n_sim})")
        self.notebook.tab(1, text=f"Tabla de Errores ({n_err})")
        self.notebook.tab(2, text="Optimizaciones")
        self.notebook.tab(3, text="Código Objeto")

    def _escribir_optimizado(self, codigo):
        """Escribe el código optimizado (con números de línea) en su panel."""
        txt = self.txt_optimizado
        txt.configure(state="normal")
        txt.delete("1.0", tk.END)
        lineas = codigo.split("\n")
        ancho = len(str(len(lineas)))
        for i, linea in enumerate(lineas, start=1):
            txt.insert("end", f"{i:>{ancho}}  ", "num")
            txt.insert("end", linea + ("\n" if i < len(lineas) else ""))
        txt.configure(state="disabled")

    def _mostrar_codigo_objeto(self, texto, aviso=False):
        """Escribe el ensamblador en su pestaña (etiquetas y mnemónicos en color)."""
        txt = self.txt_asm
        txt.configure(state="normal")
        txt.delete("1.0", tk.END)
        if aviso:
            txt.insert("end", texto, "aviso")
        else:
            for linea in texto.split("\n"):
                if linea and not linea.startswith(" "):
                    txt.insert("end", linea + "\n", "etiqueta")
                    continue
                cuerpo = linea.lstrip()
                mnem, _, resto = cuerpo.partition(" ")
                txt.insert("end", linea[:len(linea) - len(cuerpo)])
                txt.insert("end", mnem, "mnemonico")
                txt.insert("end", (" " + resto if resto else "") + "\n")
        txt.configure(state="disabled")

    def _mostrar_aviso_optimizado(self, texto):
        """Muestra un mensaje en gris en el panel del código optimizado."""
        txt = self.txt_optimizado
        txt.configure(state="normal")
        txt.delete("1.0", tk.END)
        txt.insert("end", texto, "aviso")
        txt.configure(state="disabled")
 
    # ---------------------------------------------------------
 
    def ejecutar(self, event=None):
        codigo = self.txt_codigo.get("1.0", tk.END).strip()
        self.limpiar_tablas()
        self._actualizar_pestanas()
        self.txt_codigo.tag_remove("linea_error", "1.0", tk.END)
        self._mostrar_codigo_objeto("Ejecuta el código para ver su código objeto.", aviso=True)

        if not codigo:
            self._mostrar_aviso_optimizado("Ejecuta el código para ver su versión optimizada.")
            self._estado("Escribe código y presiona EJECUTAR (F5).", "neutro")
            return "break"

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
                "", "end", values=(token, lexema, renglon, descripcion)
            )
        self._actualizar_pestanas()

        # 5. Optimizar (el triplo se genera del código optimizado)
        analizador_triplo, aviso = self._optimizar(tokenizador, analizador, resultado)

        # 6. Resumen en la barra de estado
        if aviso:
            self._estado(*aviso)
        else:
            self._estado(
                f"✔ Sin errores · {self._n_optimizaciones} optimización(es) aplicada(s).",
                "ok"
            )

        # 7. Generar el triplo y exportarlo a CSV
        self._exportar_triplo(analizador_triplo)
        return "break"

    # ---------------------------------------------------------
    def _optimizar(self, tokenizador, analizador, resultado):
        """
        Optimiza el código y muestra el resultado en la ventana principal.
        Devuelve (analizador, aviso): el analizador del que se generará el
        triplo (el del código optimizado, o el original si no se pudo
        optimizar) y un aviso opcional (texto, tipo) para la barra de estado.
        """
        self._n_optimizaciones = 0
        errores_lex = tokenizador.errores
        if errores_lex or resultado.errores:
            n_err = len(resultado.errores) or len(errores_lex)
            self._mostrar_aviso_optimizado(
                "No se optimizó: el código tiene errores.\n"
                "Revisa la pestaña «Tabla de Errores»."
            )
            self.notebook.select(1)
            return analizador, (
                f"✖ Se detectaron {n_err} error(es) en el código, por lo que no fue "
                "posible optimizarlo. Doble clic en un error para ir a su renglón.",
                "error"
            )

        try:
            res_opt = optimizar(analizador.tokens)
        except Exception as e:
            self._mostrar_aviso_optimizado("Ocurrió un error al optimizar el código.")
            messagebox.showerror("Error al optimizar", str(e))
            return analizador, (
                "⚠ No se pudo optimizar; el triplo se generó con el código original.",
                "aviso"
            )

        # Mostrar el resultado en la ventana principal
        self._escribir_optimizado(res_opt.codigo)
        if res_opt.cambios:
            for c in res_opt.cambios:
                self.tabla_cambios.insert("", "end", values=(c.renglon, c.tecnica, c.descripcion))
        else:
            self.tabla_cambios.insert("", "end", values=("-", "-", "No se encontraron optimizaciones aplicables"))
        self._n_optimizaciones = len(res_opt.cambios)
        self.notebook.tab(2, text=f"Optimizaciones ({len(res_opt.cambios)})")
        self.notebook.select(2)

        # Re-analizar el código optimizado para generar su triplo
        tokenizador_opt = Tokenizador(res_opt.codigo)
        analizador_opt = Analizador(tokenizador_opt.tokenizar())
        resultado_opt = analizador_opt.analizar()
        if tokenizador_opt.errores or resultado_opt.errores:
            return analizador, (
                "⚠ El código optimizado presenta errores; "
                "el triplo se generó con el código original.",
                "aviso"
            )
        return analizador_opt, None

    # ---------------------------------------------------------
    def _exportar_triplo(self, analizador_triplo):
        """
        Genera el triplo (sin mostrarlo en la interfaz), lo traduce a código
        objeto (se muestra en su pestaña) y guarda ambos: triplo.csv y el
        .asm con el mismo nombre en la misma carpeta.
        """
        from nucleo.triplos import generar_triplos
        from nucleo.exportar import exportar_csv
        from nucleo.codigo_objeto import generar_codigo_objeto

        try:
            filas, catalogo = generar_triplos(analizador_triplo)
        except Exception as e:
            messagebox.showerror("Error al generar triplos", str(e))
            return

        try:
            lineas_asm = generar_codigo_objeto(filas)
        except Exception as e:
            lineas_asm = None
            self._mostrar_codigo_objeto("Ocurrió un error al generar el código objeto.", aviso=True)
            messagebox.showerror("Error al generar código objeto", str(e))
        else:
            self._mostrar_codigo_objeto("\n".join(lineas_asm))
            self.notebook.tab(3, text=f"Código Objeto ({sum(1 for l in lineas_asm if l.startswith(' ') and not l.lstrip().startswith(';'))})")

        # Preguntar dónde guardar
        guardar_dentro = messagebox.askyesno(
            "Guardar CSV",
            "¿Guardar triplo.csv dentro del proyecto (carpeta csv/)?\n\n"
            "Sí  → <proyecto>/csv/triplo.csv\n"
            "No → elegir otra ubicación"
        )

        if guardar_dentro:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            carpeta_csv = os.path.join(base_dir, "csv")
            os.makedirs(carpeta_csv, exist_ok=True)
            ruta_csv = os.path.join(carpeta_csv, "triplo.csv")
        else:
            ruta_csv = filedialog.asksaveasfilename(
                title="Guardar triplo como",
                defaultextension=".csv",
                initialfile="triplo.csv",
                filetypes=[
                    ("CSV", "*.csv"),
                    ("Todos los archivos", "*.*")
                ]
            )
            if not ruta_csv:
                return  # el usuario canceló

        ruta_asm = os.path.splitext(ruta_csv)[0] + ".asm"
        try:
            exportar_csv(filas, catalogo, ruta_csv)
            if lineas_asm is not None:
                with open(ruta_asm, "w", encoding="utf-8") as f:
                    f.write("\n".join(lineas_asm) + "\n")
        except Exception as e:
            messagebox.showerror("Error al exportar", str(e))
            return

        generados = ruta_csv + (f"\n{ruta_asm}" if lineas_asm is not None else "")
        messagebox.showinfo(
            "Exportación exitosa",
            f"Archivos generados:\n\n{generados}"
        )

    # ---------------------------------------------------------
    def _estado(self, texto, tipo="neutro"):
        """Actualiza la barra de estado inferior."""
        colores = {"ok": "#2d8a4e", "error": "#c0392b", "aviso": "#b9770e", "neutro": "#555"}
        self.lbl_estado.configure(text=texto, fg=colores.get(tipo, "#555"))

    def _ir_a_error(self, event=None):
        """Doble clic en un error: lleva el cursor a su renglón y lo resalta."""
        sel = self.tabla_errores.selection()
        if not sel:
            return
        try:
            renglon = int(self.tabla_errores.item(sel[0], "values")[2])
        except (ValueError, IndexError, TypeError):
            return
        self.txt_codigo.tag_remove("linea_error", "1.0", tk.END)
        self.txt_codigo.tag_add("linea_error", f"{renglon}.0", f"{renglon}.0 lineend+1c")
        self.txt_codigo.mark_set("insert", f"{renglon}.0")
        self.txt_codigo.see(f"{renglon}.0")
        self.txt_codigo.focus_set()
        self._programar_actualizacion()

