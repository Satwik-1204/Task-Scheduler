import tkinter as tk
from tkinter import ttk
from tkcalendar import Calendar
from datetime import datetime

root = tk.Tk()
root.title("Calendar + Time Input")
root.configure(bg="gray15")
font = ("Times New Roman", 11)

# Calendar setup
cal = Calendar(root, selectmode="day", date_pattern="yyyy-mm-dd",
               background="gray25", foreground="white",
               headersbackground="gray30", normalbackground="gray30",
               weekendbackground="gray20", weekendforeground="white",
               othermonthbackground="gray15", othermonthforeground="gray50")
cal.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

# Time input frame
tk.Label(root, text="Hour:", font=font, bg="gray15", fg="white").grid(row=1, column=0, sticky="e", padx=10)
hour_spin = tk.Spinbox(root, from_=0, to=23, width=5, font=font, bg="gray25", fg="white", insertbackground="white")
hour_spin.grid(row=1, column=1, sticky="w")

tk.Label(root, text="Minute:", font=font, bg="gray15", fg="white").grid(row=2, column=0, sticky="e", padx=10)
minute_spin = tk.Spinbox(root, from_=0, to=59, width=5, font=font, bg="gray25", fg="white", insertbackground="white")
minute_spin.grid(row=2, column=1, sticky="w")

def get_datetime():
    date_str = cal.get_date()
    hour = int(hour_spin.get())
    minute = int(minute_spin.get())
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=hour, minute=minute)
    print("Selected:", dt)

ttk.Button(root, text="Submit", command=get_datetime).grid(row=3, column=0, columnspan=2, pady=10)

root.mainloop()
