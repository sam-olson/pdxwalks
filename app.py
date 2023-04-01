import tkinter as tk

from pdxwalks.gui import App

if __name__ == "__main__":
    root = tk.Tk()
    root.title("pdxwalks")
    app = App(master=root)
    app.mainloop()
