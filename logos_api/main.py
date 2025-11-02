from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import re
from typing import Dict, Any, List

app = FastAPI()

API_KEY = "LOGOS_SECRET_MVP2_KEY"
API_KEY_NAME = "X-API-Key"

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

class VerificationRequest(BaseModel):
    prompt: str

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    else:
        raise HTTPException(status_code=403, detail="Could not validate credentials")

def parse_prompt(prompt: str) -> Dict[str, Any]:
    inputs = {}
    pattern = re.compile(r"(\w+)\s*=\s*(\d+(\.\d+)?)")
    matches = pattern.findall(prompt)
    for key, value, _ in matches:
        try:
            inputs[key] = float(value) if '.' in value else int(value)
        except ValueError:
            inputs[key] = value
    return inputs

@app.post("/api/verify")
async def verify_prompt(request: VerificationRequest, api_key: str = Depends(get_api_key)):
    # --- НАЧАЛО ДИАГНОСТИЧЕСКОГО БЛОКА ---
    print("\n--- [LOGOS-API DIAGNOSTICS] ---")
    print(f"1. ПОЛУЧЕН СЫРОЙ PROMPT: '{request.prompt}'")

    inputs = parse_prompt(request.prompt)
    print(f"2. РЕЗУЛЬТАТ РАБОТЫ parse_prompt: {inputs}")

    # Проверяем наличие ключа 'balance'
    has_balance_key = 'balance' in inputs
    print(f"3. ПРОВЕРКА 'balance' in inputs: {has_balance_key}")

    if has_balance_key:
        balance_value = inputs['balance']
        print(f"4. ЗНАЧЕНИЕ inputs['balance']: {balance_value}")
        print(f"5. ТИП ДАННЫХ type(inputs['balance']): {type(balance_value)}")
        
        # Проверяем условие сравнения
        is_less_or_equal = balance_value <= 1500
        print(f"6. ПРОВЕРКА УСЛОВИЯ (balance_value <= 1500): {is_less_or_equal}")
    else:
        print("4. КЛЮЧ 'balance' НЕ НАЙДЕН В inputs. ДАЛЬНЕЙШИЕ ПРОВЕРКИ ПРОПУЩЕНЫ.")
    
    print("--- [END OF DIAGNOSTICS] ---\n")
    # --- КОНЕЦ ДИАГНОСТИЧЕСКОГО БЛОКА ---

    triggered_rules: List[str] = []

    if 'amount' in inputs and inputs['amount'] < 10000:
        triggered_rules.append("amount < 10000")

    if 'risk_score' in inputs and inputs['risk_score'] <= 0.85:
        triggered_rules.append("risk_score <= 0.85")

    if 'age' in inputs and inputs['age'] > 18:
        triggered_rules.append("age > 18")

    if 'score' in inputs and inputs['score'] > 90:
        triggered_rules.append("score > 90")

    if 'balance' in inputs and inputs['balance'] <= 1500:
        triggered_rules.append("balance <= 1500")

    decision = "approved" if triggered_rules else "denied"

    return {"result": decision, "triggered_rules": triggered_rules}

@app.get("/")
async def root():
    return {"message": "Logos API is running"}
