# ᝰ.ᐟ MegaETH

Tool được phát triển bởi nhóm tele Airdrop Hunter Siêu Tốc (https://t.me/airdrophuntersieutoc)

## 🚨 Attention Before Running MegaETH Cli Version

I am not `responsible` for the possibility of an account being `banned`!

## 📎 MegaETH Node cli version Script features

- Auto faucet
- Support proxy or not
- Mutiple threads, multiple accounts

## ✎ᝰ. RUNNING

- Clone Repository

```bash
git clone https://github.com/Hunga9k50doker/megaETH.git
cd megaETH
```

- Install Dependency

```bash
pip install -r requirements.txt
```

- Setup config in config.json: get TWO_CAPTCHA_API_KEY from https://2captcha.com/?from=24402314

```bash
nano config.json
```

- Setup input value

* proxy: http://user:pass@ip:port

```bash
nano proxies.txt
```

- wallets: how to get wallets => join my channel: https://t.me/airdrophuntersieutoc

```bash
nano wallets.txt
```

- Run the script check balance

```bash
python main.py or python3 main.py
```

- Run the script faucet

```bash
python faucet.py or python3 faucet.py
```
