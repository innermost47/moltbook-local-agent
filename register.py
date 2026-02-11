from src.services import MoltbookAPI
from src.settings import settings

moltbook_api = MoltbookAPI()

response = moltbook_api.register()

print(response)
