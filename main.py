import tkinter as tk
from gui.ventana import CompiladorGUI

if __name__ == "__main__":
  root = tk.Tk()
  app = CompiladorGUI(root)
  root.mainloop()