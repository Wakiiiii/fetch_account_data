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

# Add GUI elements
api_key_label = tk.Label(window, text='API Key:')
api_key_label.grid(row=0, column=0, padx=5, pady=5)
api_key_line = tk.Entry(window)
api_key_line.grid(row=0, column=1, padx=0, pady=0)

secret_key_label = tk.Label(window, text='Secret Key:')
secret_key_label.grid(row=1, column=0, padx=5, pady=5)
secret_key_line = tk.Entry(window)
secret_key_line.grid(row=1, column=1, padx=0, pady=0)

json_file_label = tk.Label(window, text='JSON file:')
json_file_label.grid(row=2, column=0, padx=5, pady=5)

# Start the event loop
window.mainloop()