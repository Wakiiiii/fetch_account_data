import tkinter as tk
import hashlib
import hmac
import requests
import time
from urllib.parse import urlencode


API_KEY = None
SECRET_KEY = None


def hashing(query_string):
    return hmac.new(
        SECRET_KEY.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def get_timestamp():
    return int(time.time() * 1000)


def dispatch_request(http_method):
    session = requests.Session()
    session.headers.update(
        {"Content-Type": "application/json;charset=utf-8", "X-MBX-APIKEY": API_KEY}
    )

    return {
        "GET": session.get,
        "DELETE": session.delete,
        "PUT": session.put,
        "POST": session.post,
    }.get(http_method, "GET")


def send_signed_request(http_method, url_path, payload=None):
    # sends signed request to binance
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
    response = send_signed_request("GET", "/fapi/v2/balance")
    if response.status_code == 200:
        print("valid keys")
    else:
        print("invalid keys")


def check_fields(event):
    global API_KEY, SECRET_KEY
    # Check if both API key and Secret key have values
    if api_key_line.get() and secret_key_line.get():
        API_KEY = api_key_line.get()
        SECRET_KEY = secret_key_line.get()
        verify_keys()


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

# Bind the function to the KeyRelease event of the Entry widgets
api_key_line.bind("<KeyRelease>", check_fields)
secret_key_line.bind("<KeyRelease>", check_fields)

# Start the event loop
window.mainloop()