import tkinter as tk

# Create the window and set its title
window = tk.Tk()
window.title("Fetch Account Data")

# Get the screen dimensions and calculate the center coordinates
screen_width = window.winfo_screenwidth()
screen_height = window.winfo_screenheight()
center_x = int(screen_width / 2 - 150)
center_y = int(screen_height / 2 - 100)

# Set size and position of the window
window.geometry(f'300x200+{center_x}+{center_y}')
window.resizable(0, 0)

# Start the event loop
window.mainloop()