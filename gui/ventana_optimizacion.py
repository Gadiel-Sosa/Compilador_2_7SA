import tkinter as tk
from tkinter import ttk, scrolledtext


class VentanaOptimizacion(tk.Toplevel):
    """Muestra el código original, el optimizado y la lista de cambios."""

    def __init__(self, master, codigo_original, resultado):
        super().__init__(master)
        self.title("Código Optimizado")
        self.geometry("1150x720")
        self.minsize(800, 500)
        self.configure(bg="#f0f0f0")

        main_frame = tk.Frame(self, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(
            main_frame, text="Optimización",
            font=("Arial", 14, "bold"), bg="#f0f0f0", fg="#2c3e50"
        ).pack(anchor="w")
        tk.Label(
            main_frame,
            text="Técnicas: mirilla (funciones) e instrucciones que se repiten sin modificación",
            font=("Arial", 10), bg="#f0f0f0", fg="#555"
        ).pack(anchor="w", pady=(0, 8))

        # ---------- Códigos lado a lado ----------
        frame_codigos = tk.Frame(main_frame, bg="#f0f0f0")
        frame_codigos.pack(fill="both", expand=True)

        self._panel_codigo(frame_codigos, " Código Original ", codigo_original) \
            .pack(side="left", fill="both", expand=True, padx=(0, 5))
        self._panel_codigo(frame_codigos, " Código Optimizado ", resultado.codigo) \
            .pack(side="right", fill="both", expand=True, padx=(5, 0))

        # ---------- Tabla de cambios ----------
        frame_cambios = tk.LabelFrame(
            main_frame, text=" Optimizaciones aplicadas (renglón del código original) ",
            font=("Arial", 11, "bold"), bg="#f0f0f0", fg="#2c3e50"
        )
        frame_cambios.pack(fill="both", pady=(10, 0))

        tabla = ttk.Treeview(
            frame_cambios, columns=("Renglón", "Técnica", "Descripción"),
            show="headings", height=8
        )
        tabla.heading("Renglón", text="Renglón")
        tabla.heading("Técnica", text="Técnica")
        tabla.heading("Descripción", text="Descripción")
        tabla.column("Renglón", width=80, anchor="center", stretch=False)
        tabla.column("Técnica", width=160, anchor="center", stretch=False)
        tabla.column("Descripción", width=800, anchor="w")

        scroll = ttk.Scrollbar(frame_cambios, orient="vertical", command=tabla.yview)
        tabla.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        tabla.pack(fill="both", expand=True, padx=5, pady=5)

        if resultado.cambios:
            for c in resultado.cambios:
                tabla.insert("", "end", values=(c.renglon, c.tecnica, c.descripcion))
        else:
            tabla.insert("", "end", values=("-", "-", "No se encontraron optimizaciones aplicables"))

    def _panel_codigo(self, padre, titulo, codigo):
        frame = tk.LabelFrame(
            padre, text=titulo,
            font=("Arial", 11, "bold"), bg="#f0f0f0", fg="#2c3e50"
        )
        txt = scrolledtext.ScrolledText(
            frame, wrap="none", font=("Consolas", 11),
            bg="#1e1e1e", fg="#ffffff", insertbackground="white",
            selectbackground="#264f78", height=16, bd=0, relief="flat"
        )
        txt.pack(fill="both", expand=True, padx=5, pady=5)
        txt.tag_configure("num", foreground="#858585")

        lineas = codigo.split("\n")
        ancho = len(str(len(lineas)))
        for i, linea in enumerate(lineas, start=1):
            txt.insert("end", f"{i:>{ancho}}  ", "num")
            txt.insert("end", linea + ("\n" if i < len(lineas) else ""))
        txt.configure(state="disabled")
        return frame
