# Kalshi Trading Bot

An Python bot that scans the **Kalshi** prediction-market exchange and recommends trades based on large-language-model (Gemini 2.5 Flash) signals.

---

##   Features

| Area              | What it does                                                                                                                             |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **Data ingest**   | Pulls live market books, ticker metadata and P\&L via the Kalshi REST API                                                                |
| **Signal engine** | Uses an Gemini LLM prompt (see `buy_prompt.py`) to turn a market snapshot into a **“Buy YES / Buy NO”** decision with a confidence score |
| **Execution**     | Submits **limit** orders sized by confidence, manages open orders, and respects budget / risk caps                                       |
| **Logging**       | Streams trades, errors and account state to stdout and (optionally) a local SQLite DB                                                    |
| **Pluggable**     | Strategy, sizing rule and prompt text live in isolated modules → swap them freely                                                        |

---

##   Quick Start

```bash
git clone https://github.com/zluqman206/trading_bot.git
cd trading_bot
pip install -r requirements.txt    
# create your own .env file, API URL/KEYS, etc 
python main.py                                   
```

