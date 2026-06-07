import jwt
import os
from dotenv import load_dotenv

load_dotenv()

# Paste your token between the triple quotes:
TOKEN = """eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjQsImlhdCI6MTc4MDg0NDQ0NiwiZXhwIjoxNzgzNDM2NDQ2fQ.V2kHSc4cgybNWWVKje7KZT-2c9sORDwcv0vLWM17cJ4"""

secret = os.getenv('SECRET_KEY')
print(f"Using SECRET_KEY: {repr(secret)}")

try:
    decoded = jwt.decode(TOKEN.strip(), secret, algorithms=['HS256'])
    print(f"SUCCESS: {decoded}")
except jwt.ExpiredSignatureError:
    print("ERROR: Token expired")
except jwt.InvalidSignatureError:
    print("ERROR: Signature mismatch — SECRET_KEY differs from what signed the token")
except jwt.DecodeError as e:
    print(f"ERROR: Decode failed — {e}")
except Exception as e:
    print(f"ERROR: {type(e).__name__} — {e}")