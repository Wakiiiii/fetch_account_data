import tkinter as tk
import hashlib
import hmac
import requests
import time
import json
import os
from urllib.parse import urlencode
from tkinter import filedialog


api_key = None
secret_key = None
alias = None
old_data = None


def hashing(query_string):
    return hmac.new(
        secret_key.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def get_timestamp():
    return int(time.time() * 1000)


def dispatch_request(http_method):
    session = requests.Session()
    session.headers.update(
        {"Content-Type": "application/json;charset=utf-8",
         "X-MBX-APIKEY": api_key}
    )

    return {
        "GET": session.get,
        "DELETE": session.delete,
        "PUT": session.put,
        "POST": session.post,
    }.get(http_method, "GET")


def send_signed_request(http_method, url_path, payload=None):
    # Send signed request to binance
    if payload is None:
        payload = {}
    query_string = urlencode(payload)
    # Replace single quote to double quote
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
    global alias
    # Check if keys match binance futures account
    response = send_signed_request("GET", "/fapi/v2/balance")
    # Successful
    if response.status_code == 200:
        message_label.config(text="")
        response = response.json()
        alias = response[0]["accountAlias"]
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
    global api_key, secret_key
    # Check if both API key & Secret key have values
    if api_key_line.get() and secret_key_line.get():
        api_key = api_key_line.get()
        secret_key = secret_key_line.get()
        verify_keys()


def import_json():
    global old_data
    # Get filename of JSON file
    filename = filedialog.askopenfilename(
        filetypes=[("JSON files", "*.json")]
    )
    if filename:
        json_file_name = filename
        # Open file & read content as a JSON object
        with open(filename) as file:
            old_data = json.load(file)
            # Change button text to file name
            import_button.config(text=json_file_name.split("/")[-1])


def disable_widgets():
    # Disable all widgets
    api_key_line.config(state="disabled")
    secret_key_line.config(state="disabled")
    import_button.config(state="disabled")
    fetch_button.config(state="disabled")


def enable_widgets():
    # Enable all widgets
    api_key_line.config(state="normal")
    secret_key_line.config(state="normal")
    import_button.config(state="normal")
    fetch_button.config(state="normal")


def create_json_file(content=None):
    # Get user desktop path
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    # Create new json file on desktop
    file_name = "{}.json".format(str(time.time()).replace(".", ""))
    file_path = os.path.join(desktop_path, file_name)
    # Dump content
    with open(file_path, "w") as file:
        json.dump(content, file)
    print("JSON file created: {}".format(file_path))


def done():
    # Create done button (exit)
    done_button = tk.Button(window, text="Done", command=window.destroy)
    done_button.grid(row=4, column=1, columnspan=2, padx=5, pady=5)
    done_button.config(state="normal")


def fetch_symbols():
    # Fetch all symbols from binance futures
    symbols = []
    response = send_signed_request("GET", "/fapi/v1/exchangeInfo")
    response = response.json()
    for i in response["symbols"]:
        symbols.append(
            {"symbol": i["symbol"], "last_time": i["onboardDate"]}
        )
    return symbols


def fetch_orders(symbols, time_max):
    new_orders = []
    for i in symbols:
        symbol = i["symbol"]
        startTime = i["last_time"]
        endTime = startTime + (7 * 24 * 60 * 60 * 1000)
        orderId = None
        while orderId is None:
            if endTime > time_max:
                endTime = time_max
                orderId = False
            response = send_signed_request("GET", "/fapi/v1/allOrders",
                                           {"symbol": symbol, "startTime": startTime,"endTime": endTime, "limit": 1})
            response = response.json()
            if len(response) > 0:
                orderId = response[0]["orderId"]
            startTime = endTime
            endTime = startTime + (7 * 24 * 60 * 60 * 1000)
        while orderId is not False:
            response = send_signed_request("GET", "/fapi/v1/allOrders",
                                           {"symbol": symbol, "orderId": orderId, "limit": 1000})
            response = response.json()
            new_orders += response
            if len(response) < 1000:
                orderId = False
            else:
                orderId = response[-1]["orderId"]
    return new_orders

def fetch_data():
    disable_widgets()
    symbols = fetch_symbols()
    start_time = get_timestamp()
    create_json_file()
    enable_widgets()
    done()


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
window.resizable(0, 0)  # Resize OFF

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

fetch_button = tk.Button(window, text="Fetch Data",
                         fg="red", command=fetch_data)
fetch_button.grid(row=3, column=1, padx=5, pady=5)

message_label = tk.Label(window, text="")
message_label.grid(row=4, column=1, columnspan=2, padx=5, pady=5)

# Disable the import & fetch buttons initially
import_button.config(state="disabled")
fetch_button.config(state="disabled")

# Bind function to KeyRelease event of Entry widgets
api_key_line.bind("<KeyRelease>", check_fields)
secret_key_line.bind("<KeyRelease>", check_fields)

# Start event loop
window.mainloop()