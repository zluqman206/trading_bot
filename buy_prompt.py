import os
from dotenv import load_dotenv
#from openai import OpenAI
from google import genai

from google.genai.types import Tool, GenerateContentConfig, GoogleSearch


import os
load_dotenv()

class Propmt:
    def __init__(self):
        pass

    
    def post_prompt(self, market_data_entry: str):
        client = genai.Client(api_key=os.getenv('GENAI_KEYID'))
        model_id='gemini-2.0-flash'

        google_search_tool = Tool(
            google_search = GoogleSearch()
        )
        
        
        output_form = """
                }
                    "market_ticker": "...",
                    "title": "...",
                    "recommendation": "Buy YES | Buy NO",
                    "order_type": "Limit | Market",
                    "confidence_score": 0-100,
                    "rationale": "≤60-word explanation",
                    "notable_changes": 
                        "yes_price_change_pct": ...,
                        "no_price_change_pct": ...,
                        "volume_change_24h": ...,
                        "open_interest_change_24h",
                        "bid_ask_spread_cents"
                {
            """
       

        response = client.models.generate_content(model = model_id, contents = 
            f"""

                ### SYSTEM
                You are a quantitative trading assistant.

                ### GOAL
                Analyse the Kalshi market snapshot and return **one clear trading call**:  
                either **Buy YES** or **Buy NO** (never “Hold”).

                ### INSTRUCTIONS
                1. **Parse** the JSON exactly as supplied—do not invent fields.  
                2. **Extract / derive** (when present)  
                • yes_price, no_price  
                • implied_prob   = yes_price / 1.00  
                • 24 h % change in yes_price and no_price  
                • 24 h volume & open-interest change  
                • bid_price, ask_price → bid-ask spread (¢)

                3. **Momentum** = sign of 24 h yes_price_change_pct.  
                4. **Decision Rule**  
                • If implied_prob ≥ 50 % **and** momentum ≥ 0 → **Buy YES**  
                • Otherwise → **Buy NO**

                5. **Order Type**  
                • **Limit** if spread > 3 ¢ **or** 24 h volume < 2 000  
                • else **Market**

                6. **Confidence Score** 0-100 (liquidity × distance from 50 % pivot).  
                7. **Rationale** ≤ 60 words citing the key numbers.  

                8. **Return exactly this JSON structure**
                

                    {output_form}

                HERES THE MARKET DATA
                {market_data_entry}

                Return the JSON object **only** (no markdown fences or tags).

                
            """
            
            
            )

        return response.model_dump_json()

