import os
import sys, json
import threading
import concurrent.futures
from web3 import Web3, HTTPProvider
from colorama import *

with open('config.json', 'r') as file:
    config = json.load(file)

THREADS = config['MAX_THREADS'] 
RPC_URL = "https://carrot.megaeth.com/rpc"
WALLET_FILE = "wallets.txt"
PROXY_FILE = "proxies.txt"
MAX_RETRIES = 5

try:
    with open(WALLET_FILE, "r") as f:
        wallets = [line.strip() for line in f if line.strip()]
except FileNotFoundError:
    print("❌ wallets.txt file not found.")
    sys.exit(1)

if not wallets:
    print("❌ wallets.txt file does not contain valid wallet addresses.")
    sys.exit(1)

try:
    with open(PROXY_FILE, "r") as pf:
        proxies = [line.strip() for line in pf if line.strip()]
except FileNotFoundError:
    print("❌ proxies.txt file not found.")
    sys.exit(1)

if not proxies:
    print("❌ proxies.txt file does not contain valid proxies.")
    sys.exit(1)

proxy_index = 0
proxy_lock = threading.Lock()

def get_next_proxy():
    global proxy_index
    with proxy_lock:
        proxy = proxies[proxy_index % len(proxies)]
        proxy_index += 1
    return proxy

def get_balance_with_retry(wallet, attempts=MAX_RETRIES):
    last_error = None
    for _ in range(attempts):
        current_proxy = get_next_proxy()
        provider = HTTPProvider(
            RPC_URL,
            request_kwargs={
                "timeout": 10,
                "proxies": {
                    "http": current_proxy,
                    "https": current_proxy
                }
            }
        )
        w3 = Web3(provider)
        try:
            checksum_wallet = w3.to_checksum_address(wallet)
            balance_wei = w3.eth.get_balance(checksum_wallet)
            balance_eth = float(w3.from_wei(balance_wei, "ether"))
            return balance_eth
        except Exception as e:
            last_error = e
    raise last_error

def check_wallet(idx, wallet):
    try:
        balance_eth = get_balance_with_retry(wallet, MAX_RETRIES)
        return (idx, wallet, balance_eth, None)
    except Exception as e:
        return (idx, wallet, None, str(e))

def welcome():
        print(
            f"""
        {Fore.YELLOW + Style.BRIGHT}Tool được phát triển bởi nhóm telegram: https://t.me/airdrophuntersieutoc {Style.RESET_ALL}
            """
        )
def main():
    welcome()
    print("🔹 Checking ETH balance...\n")
    total_balance = 0.0
    has_balance = []
    no_balance = []
    futures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as executor:
        for idx, wallet in enumerate(wallets, start=1):
            print(f"{idx}. Starting to process wallet: {wallet}")
            future = executor.submit(check_wallet, idx, wallet)
            futures.append(future)
        for future in concurrent.futures.as_completed(futures):
            idx, wallet, balance, error = future.result()
            if error:
                print(f"{idx}. ❌ Error checking {wallet}: {error}")
            else:
                total_balance += balance
                if balance > 0:
                    has_balance.append(wallet)
                else:
                    no_balance.append(wallet)
                print(f"{idx}. 🟢 Wallet: {wallet} | Balance: {balance:.6f} ETH")
    print(f"\n🔹 Total ETH balance of wallets: {total_balance:.6f} ETH")
    with open("has_balance.txt", "w") as f:
        for wallet in has_balance:
            f.write(wallet + "\n")
    with open("no_balance.txt", "w") as f:
        for wallet in no_balance:
            f.write(wallet + "\n")

if __name__ == "__main__":
    main()
