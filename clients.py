import requests, base64, time, json, ssl, certifi         # ← added ssl, certifi
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from enum import Enum

from requests.exceptions import HTTPError
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature

import websockets


class Environment(Enum):
    DEMO = "demo"
    PROD = "prod"


class KalshiBaseClient:
    """Base client class for interacting with the Kalshi API."""
    def __init__(
        self,
        key_id: str,
        private_key: rsa.RSAPrivateKey,
        environment: Environment = Environment.PROD,
    ):
        self.key_id = key_id
        self.private_key = private_key
        self.environment = environment
        self.last_api_call = datetime.now()

        if self.environment == Environment.DEMO:
            self.HTTP_BASE_URL = "https://demo-api.kalshi.co"
            self.WS_BASE_URL   = "wss://demo-api.kalshi.co"
        elif self.environment == Environment.PROD:
            self.HTTP_BASE_URL = "https://api.kalshi.com"
            self.WS_BASE_URL   = "wss://api.kalshi.com"
        else:
            raise ValueError("Invalid environment")

    # ---------- auth helpers -------------------------------------------------
    def request_headers(self, method: str, path: str) -> Dict[str, Any]:
        ts = str(int(time.time() * 1000))
        msg = ts + method + path.split("?")[0]
        sig = self.sign_pss_text(msg)
        return {
            "Content-Type": "application/json",
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-SIGNATURE": sig,
            "KALSHI-ACCESS-TIMESTAMP": ts,
        }

    def sign_pss_text(self, text: str) -> str:
        try:
            signature = self.private_key.sign(
                text.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.DIGEST_LENGTH,
                ),
                hashes.SHA256(),
            )
            return base64.b64encode(signature).decode()
        except InvalidSignature as e:
            raise ValueError("RSA sign PSS failed") from e

    # ---------- rate-limit & helpers -----------------------------------------
    def rate_limit(self):
        THRESHOLD_MS = 100
        if datetime.now() - self.last_api_call < timedelta(milliseconds=THRESHOLD_MS):
            time.sleep(THRESHOLD_MS / 1000)
        self.last_api_call = datetime.now()

    def raise_if_bad_response(self, response: requests.Response):
        if response.status_code not in range(200, 299):
            response.raise_for_status()

    # ---------- HTTP verbs ----------------------------------------------------
    def post(self, path: str, body: dict) -> Any:
        self.rate_limit()
        r = requests.post(
            self.HTTP_BASE_URL + path,
            json=body,
            headers=self.request_headers("POST", path),
        )
        self.raise_if_bad_response(r)
        return r.json()

    def get(self, path: str, params: Dict[str, Any] = {}) -> Any:
        self.rate_limit()
        r = requests.get(
            self.HTTP_BASE_URL + path,
            headers=self.request_headers("GET", path),
            params=params,
        )
        self.raise_if_bad_response(r)
        return r.json()

    def delete(self, path: str, params: Dict[str, Any] = {}) -> Any:
        self.rate_limit()
        r = requests.delete(
            self.HTTP_BASE_URL + path,
            headers=self.request_headers("DELETE", path),
            params=params,
        )
        self.raise_if_bad_response(r)
        return r.json()


class KalshiHttpClient(KalshiBaseClient):
    """Wrapper for REST endpoints."""
    def __init__(self, key_id, private_key, environment=Environment.DEMO):
        super().__init__(key_id, private_key, environment)
        self.exchange_url  = "/trade-api/v2/exchange"
        self.markets_url   = "/trade-api/v2/markets"
        self.portfolio_url = "/trade-api/v2/portfolio"
        self.events_url = "/trade-api/v2/events"

    # convenience wrappers
    def get_balance(self):
        return self.get(self.portfolio_url + "/balance")

    def get_exchange_status(self):
        return self.get(self.exchange_url + "/status")

    def get_trades(self, **params):
        params = {k: v for k, v in params.items() if v is not None}
        return self.get(self.markets_url + "/trades", params=params)
    
    def get_events(self, vars: str):

        return self.get(self.events_url + vars)
    def get_market(self, ticker: str):
        return self.get(self.markets_url + "/" + ticker)


class KalshiWebSocketClient(KalshiBaseClient):
    """Wrapper for WebSocket feed."""
    def __init__(self, key_id, private_key, environment=Environment.DEMO):
        super().__init__(key_id, private_key, environment)
        self.url_suffix = "/trade-api/ws/v2"
        self.message_id = 1
        self.ws = None

    async def connect(self):
        host = self.WS_BASE_URL + self.url_suffix
        auth_headers = self.request_headers("GET", self.url_suffix)

        # use certifi bundle to satisfy TLS verification
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())

        async with websockets.connect(
            host,
            additional_headers=auth_headers,
            ssl=ssl_ctx,                    # ← pass verified context
        ) as websocket:
            self.ws = websocket
            await self.on_open()
            await self.handler()

    # ----- ws callbacks ------------------------------------------------------
    async def on_open(self):
        print("WebSocket opened.")
        await self.subscribe_to_tickers()

    async def subscribe_to_tickers(self):
        payload = {
            "id": self.message_id,
            "cmd": "subscribe",
            "params": {"channels": ["ticker"]},
        }
        await self.ws.send(json.dumps(payload))
        self.message_id += 1

    async def handler(self):
        try:
            async for msg in self.ws:
                await self.on_message(msg)
        except websockets.ConnectionClosed as e:
            await self.on_close(e.code, e.reason)
        except Exception as e:
            await self.on_error(e)

    async def on_message(self, message):
        print("WS message:", message)

    async def on_error(self, err):
        print("WebSocket error:", err)

    async def on_close(self, code, reason):
        print("WebSocket closed:", code, reason)
