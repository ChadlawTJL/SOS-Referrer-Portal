#API Key generation - To be then saved in .env
import secrets
print(secrets.token_urlsafe(32))