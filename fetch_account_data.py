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

BINANCE_API_URL = "https://fapi.binance.com"

api_key = None
secret_key = None
alias = None
imported_json = {"alias": alias, "trades": [], "orders": []}
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
        {"Content-Type": "application/json;charset=utf-8", "X-MBX-APIKEY": api_key}
    )
    return {
        "GET": session.get,
        "DELETE": session.delete,
        "PUT": session.put,
        "POST": session.post,
    }.get(http_method, "GET")


def send_signed_request(http_method, url_path, payload=None):
    retry_count = 0
    while retry_count < 60:
        try:
            if payload is None:
                payload = {}
            query_string = urlencode(payload)
            query_string = query_string.replace("%27", "%22")
            if query_string:
                query_string = "{}&timestamp={}".format(
                    query_string, get_timestamp())
            else:
                query_string = "timestamp={}".format(get_timestamp())
            url = (
                BINANCE_API_URL + url_path + "?" + query_string
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
    # If all retries failed raise the last error encountered
    raise e


def verify_keys():
    global alias
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


def verify_import(imported_json, alias):
    try:
        if imported_json["trades"]:
            pass
        if imported_json["orders"]:
            pass
        if not (imported_json["alias"] == alias):
            message_label.config(text="JSON doesn't match keys", fg="red")
            return False
    except KeyError:
        message_label.config(text="JSON format is invalid", fg="red")
    message_label.config(text="")
    return True


def check_fields(event):
    global api_key, secret_key
    if api_key_line.get() and secret_key_line.get():
        if api_key != api_key_line.get() or secret_key != secret_key_line.get():
            api_key = api_key_line.get()
            secret_key = secret_key_line.get()
            verify_keys()


def import_json_button():
    global imported_json, alias
    filename = filedialog.askopenfilename(
        filetypes=[("JSON files", "*.json")]
    )
    if filename:
        with open(filename) as file:
            imported_json = json.load(file)
        if verify_import(imported_json, alias):
            import_button.config(text=filename.split("/")[-1])
        else:
            imported_json = {"alias": alias, "trades": [], "orders": []}


def onoff_widgets(state):
    api_key_line.config(state=state)
    secret_key_line.config(state=state)
    import_button.config(state=state)
    fetch_button.config(state=state)


def create_json_file(content):
    # Get user desktop path
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    # Create new json file on desktop
    file_name = "{}.json".format(str(time.time()).replace(".", ""))
    file_path = os.path.join(desktop_path, file_name)
    with open(file_path, "w") as file:
        json.dump(content, file)


def add_done_button():
    done_button = tk.Button(window, text="Done", command=on_closing)
    done_button.grid(row=4, column=1, columnspan=2, padx=5, pady=5)
    done_button.config(state="normal")


def add_progress_bar():
    global done_button
    if done_button is not None:
        done_button.destroy()
        done_button = None
    progress_bar = ttk.Progressbar(
        window, orient="horizontal", mode="determinate", maximum=100
        )
    progress_bar.grid(row=4, column=1, padx=5, pady=5)
    progress_bar["value"] = 0
    return progress_bar


def on_closing():
    window.destroy()
    os._exit(0)


def get_unique_data(data):
    unique_data = []
    for item in data:
        if item not in unique_data:
            unique_data.append(item)
    return unique_data


def cut_after(data, time_max):
    new_data = []
    for item in data:
        if item["time"] <= time_max:
            new_data.append(item)
        else:
            break
    return new_data


def fetch_symbols(time_max):
    symbols = []
    total_time = 0
    response = send_signed_request("GET", "/fapi/v1/exchangeInfo")
    response = response.json()
    for item in response["symbols"]:
        symbol = item["symbol"]
        listing_time = item["onboardDate"]
        time_since = time_max - listing_time
        total_time += time_since
        item = {
            "symbol": symbol, "listing_time": listing_time,"time_since": time_since,
            "time_share": None, "time_cum": total_time
            }
        symbols.append(item)
    for item in symbols:
        item["time_share"] = (item["time_since"] / total_time) * 100
        item["time_cum"] = (item["time_cum"] / total_time) * 100
    return symbols


def fetch_data_button():
    global fetch_thread
    if fetch_thread is None or not fetch_thread.is_alive():
        fetch_thread = threading.Thread(target=lambda: main_process())
        fetch_thread.start()


def edit(data, time_max):
    sorted_data = sorted(data, key=lambda x: int(x["time"]))
    cut_data = cut_after(get_unique_data(sorted_data), time_max)
    return cut_data


def from_json(imported_json, time_max):
    already_seen = []
    trades = imported_json["trades"]
    orders = imported_json["orders"]
    for trade_1 in imported_json["trades"]:
        symbol = trade_1["symbol"]
        symbol_trades = []
        if symbol not in already_seen:
            already_seen.append(symbol)
            for trade_2 in imported_json["trades"]:
                if trade_2["symbol"] == symbol:
                    symbol_trades.append(trade_2)
            fromId = symbol_trades[-1]["id"]
            orderId = symbol_trades[-1]["orderId"]
            trades += from_id(symbol, "id", fromId, "/fapi/v1/userTrades")
            orders += from_id(symbol, "orderId", orderId, "/fapi/v1/allOrders")
    account_data = {"trades": edit(trades, time_max), "orders": edit(orders, time_max)}
    return account_data, already_seen



def from_id(symbol, key_id, value_id, url):
    symbol_data = []
    while value_id is not False:
        params = {"symbol": symbol, key_id: value_id, "limit": 1000, "recWindow": 60000}
        response = send_signed_request("GET", url, params)
        if response.status_code == 200:
            response = response.json()
            symbol_data += response
            if len(response) < 1000:
                value_id = False
            else:
                value_id = response[-1][key_id]
    return symbol_data


def fetch_data(symbols, time_max, progress_bar, imported_json):
    account_data, already_seen = from_json(imported_json, time_max)
    for item in symbols:
        symbol = item["symbol"]
        if len(imported_json["orders"]) > 0:
            imported_json["trades"] = edit(imported_json["trades"], time_max)
            imported_json["orders"] = edit(imported_json["orders"], time_max)
            startTime = imported_json["orders"][-1]["time"]
        else:
            startTime = item["listing_time"]
        endTime = startTime + (7 * 24 * 60 * 60 * 1000)
        fromId = None
        if symbol not in already_seen:
            while fromId is None:
                if endTime > time_max:
                    endTime = time_max
                    fromId = False
                params = {
                    "symbol": symbol, "startTime": startTime,
                    "endTime": endTime, "limit": 1, "recWindow": 60000
                    }
                response = send_signed_request("GET", "/fapi/v1/userTrades", params)
                if response.status_code == 200:
                    response = response.json()
                    if len(response) > 0:
                        fromId = response[0]["id"]
                        orderId = response[0]["orderId"]
                        account_data["trades"] += from_id(symbol, "id", fromId, "/fapi/v1/userTrades")
                        account_data["orders"] += from_id(symbol, "orderId", orderId, "/fapi/v1/allOrders")
                    else:
                        startTime = endTime
                        endTime = startTime + (7 * 24 * 60 * 60 * 1000)
        progress_bar.configure(value=int(item["time_cum"]))
    final_account_data = {
        "alias": alias,
        "trades": edit(account_data["trades"], time_max),
        "orders": edit(account_data["orders"], time_max)
        }
    return final_account_data


def main_process():
    onoff_widgets("disabled")
    start_time = get_timestamp()
    symbols = fetch_symbols(start_time)
    progress_bar = add_progress_bar()
    account_data = fetch_data(symbols, start_time, progress_bar, imported_json)
    create_json_file(account_data)
    progress_bar.destroy()
    onoff_widgets("normal")
    add_done_button()


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
import_button = tk.Button(window, text="Import", command=import_json_button)
import_button.grid(row=2, column=1, padx=0, pady=0)

fetch_button = tk.Button(
    window, text="Fetch Data", fg="red", command=fetch_data_button
    )
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

window.mainloop()
