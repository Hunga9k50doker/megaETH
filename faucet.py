import requests
from twocaptcha import TwoCaptcha
from colorama import init, Fore, Style
from datetime import datetime
import pytz, json
import threading
from datetime import datetime
from tzlocal import get_localzone
from concurrent.futures import ThreadPoolExecutor, as_completed

init(autoreset=True)

with open('config.json', 'r') as file:
    config = json.load(file)

# ================== CONFIG ==================
THREADS = config['MAX_THREADS'] # Config number of threads
TWO_CAPTCHA_API_KEY = config['TWO_CAPTCHA_API_KEY']  # Config your 2captcha api key


TURNSTILE_SITEKEY = "0x4AAAAAABA4JXCaw9E2Py-9"
TURNSTILE_PAGE_URL = "https://testnet.megaeth.com/"

MEGAETH_API_URL = "https://carrot.megaeth.com/claim"

WALLETS_FILE = "wallets.txt"
PROXIES_FILE = "proxies.txt"

SUCCESS_FILE = "success.txt"
FAIL_FILE = "fail.txt"

headers = {
    "Accept": "*/*",
    "Content-Type": "text/plain;charset=UTF-8",
    "Origin": "https://testnet.megaeth.com",
    "Referer": "https://testnet.megaeth.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
}

def now_local():
    local_tz = get_localzone()
    return datetime.now(local_tz).strftime("%H:%M:%S %d/%m/%Y")

def log_info(msg, idx=None):
    if idx is not None:
        print(f"{Fore.CYAN}[{now_local()}] [{idx}] {msg}{Style.RESET_ALL}")
    else:
        print(f"{Fore.CYAN}[{now_local()}] {msg}{Style.RESET_ALL}")

def log_success(msg, idx=None):
    if idx is not None:
        print(f"{Fore.GREEN}[{now_local()}] [{idx}] {msg}{Style.RESET_ALL}")
    else:
        print(f"{Fore.GREEN}[{now_local()}] {msg}{Style.RESET_ALL}")

def log_fail(msg, idx=None):
    if idx is not None:
        print(f"{Fore.RED}[{now_local()}] [{idx}] {msg}{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}[{now_local()}] {msg}{Style.RESET_ALL}")

def log_warning(msg, idx=None):
    if idx is not None:
        print(f"{Fore.YELLOW}[{now_local()}] [{idx}] {msg}{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}[{now_local()}] {msg}{Style.RESET_ALL}")

with open(PROXIES_FILE, "r") as f:
    proxies_list = [line.strip() for line in f if line.strip()]

proxy_index = 0
PROXY_LOCK = threading.Lock()

def get_next_proxy():
    global proxy_index
    with PROXY_LOCK:
        if not proxies_list:
            return None
        p = proxies_list[proxy_index % len(proxies_list)]
        proxy_index += 1
        return p

def get_current_ip(proxy, idx=None):
    try:
        r = requests.get("https://api.myip.com", proxies={"http": proxy, "https": proxy}, timeout=30)
        if r.status_code == 200:
            return r.json().get("ip", "Unknown IP")
        return "Unknown IP"
    except Exception as e:
        log_fail(f"Error getting IP: {e}", idx=idx)
        return "Error"

def solve_turnstile(idx=None):
    try:
        solver = TwoCaptcha(TWO_CAPTCHA_API_KEY)
        result = solver.turnstile(sitekey=TURNSTILE_SITEKEY, url=TURNSTILE_PAGE_URL)
        token = result.get("code")
        if token:
            log_success("Turnstile solved OK", idx=idx)
            return token
        else:
            log_fail(f"Turnstile solve got invalid response: {result}", idx=idx)
            return None
    except Exception as e:
        log_fail(f"Turnstile solve error: {e}", idx=idx)
        return None

def megaeth_claim(wallet, token, proxy, idx=None):
    try:
        resp = requests.post(
            MEGAETH_API_URL,
            json={"addr": wallet, "token": token},
            headers=headers,
            proxies={"http": proxy, "https": proxy},
            timeout=60
        )
        return resp.json() 
    except Exception as e:
        log_fail(f"Claim API error for {wallet}: {e}", idx=idx)
        return None

def process_wallet(wallet, index, stop_event):
    log_info(f"Claiming for address: {wallet}", idx=index)
    max_retries = 3
    attempts = 0
    success_flag = False

    while attempts < max_retries and not success_flag:
        if stop_event.is_set():
            log_info("Stop event detected. Exiting thread.", idx=index)
            return

        proxy = get_next_proxy()
        ip = get_current_ip(proxy, idx=index)
        log_info(f"Attempt {attempts+1}, Using proxy: {ip}", idx=index)

        turnstile_token = solve_turnstile(idx=index)
        if not turnstile_token:
            log_fail("Turnstile solve failed", idx=index)
            attempts += 1
            continue

        resp = megaeth_claim(wallet, turnstile_token, proxy, idx=index)
        if resp:
            log_info(f"Claim response: {resp}", idx=index)

            msg = resp.get("message", "").lower()
            if "less than" in msg and "hours have passed since the last claim" in msg:
                log_warning(f"Wallet {wallet} has claimed <X hours -> skipping", idx=index)
                return 

            success_val = resp.get("success", False)
            txhash_val = resp.get("txhash", "")
            if success_val is True and txhash_val:
                success_flag = True
            else:
                log_fail("Claim not successful, will retry...", idx=index)
        else:
            log_fail("Claim returned None, will retry...", idx=index)

        attempts += 1

    if success_flag:
        log_success(f"Claim SUCCESS for wallet {wallet}", idx=index)
        with open(SUCCESS_FILE, "a") as f:
            f.write(wallet + "\n")
    else:
        log_fail(f"Claim FAILED after {max_retries} attempts for {wallet}", idx=index)
        with open(FAIL_FILE, "a") as f:
            f.write(wallet + "\n")

def welcome():
        print(
            f"""
        {Fore.YELLOW + Style.BRIGHT}Tool được phát triển bởi nhóm telegram: https://t.me/airdrophuntersieutoc
            """
        )
def main(stop_event):
    welcome()
    log_info("Start reading wallets.txt and proceed to Megaeth faucet...", idx=0)
    log_info(f"Number of threads: {THREADS}", idx=0)

    with open(WALLETS_FILE, "r") as f:
        wallets = [line.strip() for line in f if line.strip()]

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = {
            executor.submit(process_wallet, w, i, stop_event): w
            for i, w in enumerate(wallets, start=1)
        }
        try:
            for future in as_completed(futures):
                future.result()
        except KeyboardInterrupt:
            log_info("KeyboardInterrupt detected in main loop. Setting stop event...", idx=0)
            stop_event.set()
            for future in futures:
                future.cancel()
            raise

if __name__ == "__main__":
    stop_event = threading.Event()
    try:
        main(stop_event)
    except KeyboardInterrupt:
        log_info("User has stopped the program. Exiting...", idx=0)
