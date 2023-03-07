import hashlib
import hmac
import requests
import time
import json
import os
import threading
from urllib.parse import urlencode
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog


api_key = None
secret_key = None
alias = None
old_trades = None
done_button = None
fetch_thread = None


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
    retry_count = 0
    max_retries = 60
    while retry_count < max_retries:
        try:
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
            print(response)
            print(response.json())
            return response
        except (
            requests.exceptions.ConnectTimeout, requests.exceptions.RetryError
            ) as e:
            print(f"Encountered error: {e}. Retrying in {1} seconds...")
            time.sleep(1)
            retry_count += 1
    # If all retries failed, raise the last error encountered
    raise e


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
        if api_key != api_key_line.get() or secret_key != secret_key_line.get():
            api_key = api_key_line.get()
            secret_key = secret_key_line.get()
            verify_keys()


def import_json():
    global json
    # Get filename of JSON file
    filename = filedialog.askopenfilename(
        filetypes=[("JSON files", "*.json")]
    )
    if filename:
        json_file_name = filename
        # Open file & read content as a JSON object
        with open(filename) as file:
            json = json.load(file)
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


def create_json_file(content):
    # Get user desktop path
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    # Create new json file on desktop
    file_name = "{}.json".format(str(time.time()).replace(".", ""))
    file_path = os.path.join(desktop_path, file_name)
    # Dump content
    with open(file_path, "w") as file:
        json.dump(content, file)


def add_done_button():
    global done_button
    # Create done button (exit)
    done_button = tk.Button(window, text="Done", command=window.destroy)
    done_button.grid(row=5, column=1, columnspan=2, padx=5, pady=5)
    done_button.config(state="normal")



def add_progress_bar():
    # Destroy done button if exists
    global done_button
    if done_button is not None:
        done_button.destroy()
        done_button = None
    # Create progress bar 
    progress_bar = ttk.Progressbar(window, orient="horizontal", mode="determinate", maximum=100)
    progress_bar.grid(row=4, column=1, padx=5, pady=5)
    progress_bar["value"] = 0  # Set the initial value of the progress bar to 0%
    return progress_bar


def update_progress_bar(progress_bar, percent_fetched):
    progress_bar.configure(value=int(percent_fetched))


def on_closing():
    window.destroy()
    os._exit(0)


def remove_duplicates(list):
    new_list = []
    for i in list:
        if i not in new_list:
            new_list.append(i)
    return new_list


def cut_after(list, time_max):
    new_list = []
    for i in list:
        if i["time"] <= time_max:
            new_list.append(i)
        else:
            break
    return new_list


def fetch_symbols(time_max):
    # Fetch all symbols from binance futures
    symbols = []
    total_time = 0
    response = send_signed_request("GET", "/fapi/v1/exchangeInfo")
    response = response.json()
    for i in response["symbols"]:
        symbol = i["symbol"]
        listing_time = i["onboardDate"]
        time_since = time_max - listing_time
        total_time += time_since
        symbols.append(
            {"symbol": symbol, "listing_time": listing_time,
             "time_since": time_since, "time_share": None}
        )
    for j in symbols:
        time_share = (j["time_since"] / total_time) * 100
        j["time_share"] = time_share
    return symbols


def fetch_trades(symbols, time_max, progress_bar):
    new_trades = []
    percent_fetched = 0
    for i in symbols:
        symbol = i["symbol"]
        startTime = i["listing_time"]
        endTime = startTime + (7 * 24 * 60 * 60 * 1000)
        fromId = None
        while fromId is None:
            if endTime > time_max:
                endTime = time_max
                fromId = False
            response = send_signed_request("GET", "/fapi/v1/userTrades",
                                           {"symbol": symbol, "startTime": startTime, "endTime": endTime, "limit": 1, "recWindow": 60000})
            if response.status_code == 200:
                response = response.json()
                if len(response) > 0:
                    fromId = response[0]["id"]
                else:
                    startTime = endTime
                    endTime = startTime + (7 * 24 * 60 * 60 * 1000)
        while fromId is not False:
            response = send_signed_request("GET", "/fapi/v1/userTrades",
                                           {"symbol": symbol, "fromId": fromId, "limit": 1000, "recWindow": 60000})
            if response.status_code == 200:
                response = response.json()
                new_trades += response
                if len(response) < 1000:
                    fromId = False
                else:
                    fromId = response[-1]["id"]
        percent_fetched += i["time_share"]
        update_progress_bar(progress_bar, percent_fetched)
    new_trades = sorted(new_trades, key=lambda x: int(x["time"]))
    new_trades = remove_duplicates(new_trades)
    new_trades = cut_after(new_trades, time_max)
    return new_trades


def fetch_orders(trades, time_max):
    already_seen = []
    new_orders = []
    for i in trades:
        symbol = i["symbol"]
        orderId = i["orderId"]
        if symbol not in already_seen:
            already_seen.append(symbol)
            while orderId is not False:
                response = send_signed_request("GET", "/fapi/v1/allOrders",
                                {"symbol": symbol, "orderId": orderId, "limit": 1000, "recWindow": 60000})
                if response.status_code == 200:
                    response = response.json()
                    new_orders += response
                    if len(response) < 1000:
                        orderId = False
                    else:
                        orderId = response[-1]["orderId"]
    new_orders = sorted(new_orders, key=lambda x: int(x["time"]))
    new_orders = remove_duplicates(new_orders)
    new_orders = cut_after(new_orders, time_max)
    return new_orders


def fetch_data_button():
    global fetch_thread
    if fetch_thread is None or not fetch_thread.is_alive():
        fetch_thread = threading.Thread(target=lambda: fetch_data())
        fetch_thread.start()



def fetch_data():
    disable_widgets()
    start_time = get_timestamp()
    symbols = fetch_symbols(start_time)
    progress_bar = add_progress_bar()
    new_trades = fetch_trades(symbols, start_time, progress_bar)
    new_orders = fetch_orders(new_trades, start_time)
    create_json_file({"orders": new_orders, "trades": new_trades})
    progress_bar.destroy()
    enable_widgets()
    add_done_button()


# Create window & set title
window = tk.Tk()
window.title("Fetch Account Data")

# Get screen dimensions & calculate center coordinates
screen_width = window.winfo_screenwidth()
screen_height = window.winfo_screenheight()
center_x = int(screen_width / 2 - 150)
center_y = int(screen_height / 2 - 110)

# Set size & window position
window.geometry(f'300x220+{center_x}+{center_y}')
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
                         fg="red", command=fetch_data_button)
fetch_button.grid(row=3, column=1, padx=5, pady=5)

message_label = tk.Label(window, text="")
message_label.grid(row=4, column=1, columnspan=2, padx=5, pady=5)

# Disable the import & fetch buttons initially
import_button.config(state="disabled")
fetch_button.config(state="disabled")

# Bind function to KeyRelease event of Entry widgets
api_key_line.bind("<KeyRelease>", check_fields)
secret_key_line.bind("<KeyRelease>", check_fields)
# Kill when red cross clicked
window.protocol("WM_DELETE_WINDOW", on_closing)

# Start event loop
window.mainloop()
