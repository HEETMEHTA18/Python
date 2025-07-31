import tkinter as tk

def on_click(button_text):
    current = display_var.get()
    if button_text == "=":
        try:
            result = str(eval(current))
            display_var.set(result)
        except:
            display_var.set("Error")
    elif button_text == "C":
        display_var.set("")
    else:
        display_var.set(current + button_text)

# GUI window setup
root = tk.Tk()
root.title("Calculate It!")
root.geometry("300x400")

# Display field
display_var = tk.StringVar()
display_entry = tk.Entry(root, textvariable=display_var, font=("Arial", 20), bd=10, relief="ridge", justify="right")
display_entry.pack(fill="both", ipadx=8, ipady=20, padx=10, pady=10)

# Button layout
buttons = [
    ["7", "8", "9", "/"],
    ["4", "5", "6", "*"],
    ["1", "2", "3", "-"],
    ["0", ".", "=", "+"],
    ["C"]
]

for row in buttons:
    frame = tk.Frame(root)
    frame.pack(expand=True, fill="both")
    for btn in row:
        tk.Button(frame, text=btn, font=("Arial", 18), height=2, width=5,
                  command=lambda b=btn: on_click(b)).pack(side="left", expand=True, fill="both")

root.mainloop()