import os
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
from requests.exceptions import HTTPError

import json

import asyncio

from clients import KalshiHttpClient, KalshiWebSocketClient, Environment
from buy_prompt import Propmt

# Load environment variables
load_dotenv()
env = Environment.DEMO # toggle environment here
KEYID = os.getenv('DEMO_KEYID') if env == Environment.DEMO else os.getenv('PROD_KEYID')
KEYFILE = os.getenv('DEMO_KEYFILE') if env == Environment.DEMO else os.getenv('PROD_KEYFILE')

try:
    with open(KEYFILE, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None  # Provide the password if your key is encrypted
        )
except FileNotFoundError:
    raise FileNotFoundError(f"Private key file not found at {KEYFILE}")
except Exception as e:
    raise Exception(f"Error loading private key: {str(e)}")

# Initialize the HTTP client
client = KalshiHttpClient(
    key_id=KEYID,
    private_key=private_key,
    environment=env
)

# Get account balance
balance = client.get_balance()
print("Balance:", balance)

# get market data and funnel all market tickers into list



markets = client.get_events('/?limit=200&status=open')
events = markets['events']
tickers = []
for event in events:
    tickers.append(event['event_ticker'])

# get event data for each ticker in the list

event_market_data = []
for ticker in tickers:  # for each of the tickers
    try:
        market = client.get_market(ticker)  # grab market data
        print(market) # print market data
        event_market_data.append(market) # add it to list of each tickers market data
    except HTTPError as e:   # throws error if market data does't exist for ticker
        if e.response is not None and e.response.status_code == 404:
            print()
            print("******************************************")
            print(f"{ticker} not found – skipping")
            print("******************************************")
            print()
            continue             # ignore and keep looping
        else:
            raise                # re-throw anything that isn’t 404


prompt = Propmt()  

prompting_results = []   # 
for market in event_market_data:

    # runs prompt using this market's data
    result = json.loads(prompt.post_prompt(market))
    dict(result)

    # cleans data so we only get gemini output
    str_result = str(result['candidates'][0]['content']['parts'][0]['text'])  
    


    start = str_result.find('{')
    end   = str_result.rfind('}') + 1
    result_dict  = json.loads(str_result[start:end])
    result_dict = dict(result_dict)

    print(result_dict['title'])
    print(result_dict['rationale'])
    
    # adds to list of prompting results
    prompting_results.append(result_dict)
    print()


# Initialize the WebSocket client
ws_client = KalshiWebSocketClient(
    key_id=KEYID,
    private_key=private_key,
    environment=env
)

# Connect via WebSocket
#asyncio.run(ws_client.connect())