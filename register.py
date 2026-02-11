from src.services import MoltbookAPI
from src.settings import settings

moltbook_api = MoltbookAPI()

response = moltbook_api.register(
    name=settings.AGENT_NAME, description=settings.AGENT_DESCRIPTION
)

print(response)
