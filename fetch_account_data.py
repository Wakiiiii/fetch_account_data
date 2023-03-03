import tkinter as tk
import hashlib
import hmac
import requests
import time
import json
from urllib.parse import urlencode
from tkinter import filedialog


API_KEY = None
SECRET_KEY = None
ALIAS = None
JSON = None


def hashing(query_string):
    return hmac.new(
        SECRET_KEY.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def get_timestamp():
    return int(time.time() * 1000)


def dispatch_request(http_method):
    session = requests.Session()
    session.headers.update(
        {"Content-Type": "application/json;charset=utf-8",
          "X-MBX-APIKEY": API_KEY}
    )

    return {
        "GET": session.get,
        "DELETE": session.delete,
        "PUT": session.put,
        "POST": session.post,
    }.get(http_method, "GET")


def send_signed_request(http_method, url_path, payload=None):
    # send signed request to binance
    if payload is None:
        payload = {}
    query_string = urlencode(payload)
    # replace single quote to double quote
    query_string = query_string.replace("%27", "%22")
    if query_string:
        query_string = "{}&timestamp={}".format(query_string, get_timestamp())
    else:
        query_string = "timestamp={}".format(get_timestamp())
    url = (
        "https://fapi.binance.com" + url_path + "?" + query_string
        + "&signature=" + hashing(query_string)
    )
    params = {"url": url, "params": {}}
    response = dispatch_request(http_method)(**params)
    return response


def verify_keys():
    global ALIAS
    # Check if keys match binance futures account
    response = send_signed_request("GET", "/fapi/v2/balance")
    # Successful
    if response.status_code == 200:
        message_label.config(text="")
        response = response.json()
        ALIAS = response[0]["accountAlias"]
        import_button.config(state="normal")
        fetch_button.config(state="normal")
    # Unsuccessful
    elif response.status_code >= 500:
         message_label.config(text="Server side error", fg="red")
    else:
         message_label.config(text="Keys are not valid", fg="red")
         import_button.config(state="disabled")
         fetch_button.config(state="disabled")


def check_fields(event):
    global API_KEY, SECRET_KEY
    # Check if both API key & Secret key have values
    if api_key_line.get() and secret_key_line.get():
        API_KEY = api_key_line.get()
        SECRET_KEY = secret_key_line.get()
        verify_keys()


def import_json():
    global JSON
    # Get filename of JSON file
    filename = filedialog.askopenfilename(
        filetypes=[("JSON files", "*.json")]
        )
    if filename:
        json_file_name = filename
        # Open file & read content as a JSON object
        with open(filename) as file:
            JSON = json.load(file)
            # Modify button text to file name
            import_button.config(text=json_file_name.split("/")[-1])

def disable_widgets():
    # Disable the entry lines and the import button
    api_key_line.config(state="disabled")
    secret_key_line.config(state="disabled")
    import_button.config(state="disabled")
    fetch_button.config(state="disabled")

def fetch_data():
    disable_widgets()


# Create window & set title
window = tk.Tk()
window.title("Fetch Account Data")

# Get screen dimensions & calculate center coordinates
screen_width = window.winfo_screenwidth()
screen_height = window.winfo_screenheight()
center_x = int(screen_width / 2 - 150)
center_y = int(screen_height / 2 - 100)

# Set size & window position
window.geometry(f'300x200+{center_x}+{center_y}')
window.resizable(0, 0) # Resize OFF

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
import_button = tk.Button(window, text="Import", command=import_json)
import_button.grid(row=2, column=1, padx=0, pady=0)

fetch_button = tk.Button(window, text="Fetch Data", fg="red", command=fetch_data)
fetch_button.grid(row=3, column=1, padx=5, pady=5)

message_label = tk.Label(window, text="", fg="black")
message_label.grid(row=4, column=1, columnspan=2, padx=5, pady=5)

# Disable the import & fetch buttons initially
import_button.config(state="disabled")
fetch_button.config(state="disabled")

# Bind function to KeyRelease event of Entry widgets
api_key_line.bind("<KeyRelease>", check_fields)
secret_key_line.bind("<KeyRelease>", check_fields)

# Start event loop
window.mainloop()