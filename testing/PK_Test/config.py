import os
import logging
from dotenv import load_dotenv
from msrest.authentication import CognitiveServicesCredentials
from azure.cognitiveservices.vision.computervision import ComputerVisionClient

load_dotenv()

# 1) Configure root logger to DEBUG (prints your messages)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],  # you can also add FileHandler here
)

# 2) Silence overly-chatty libraries by raising their levels
for noisy in ("httpx", "httpcore", "openai", "matplotlib"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

# 3) If you have other libs you want quiet, add them here:
# logging.getLogger("PIL").setLevel(logging.WARNING)
# logging.getLogger("urllib3").setLevel(logging.WARNING)


client_ocr = ComputerVisionClient(
    os.getenv("MSREST_ENDPOINT"), CognitiveServicesCredentials(os.getenv("MSREST_KEY"))
)
logger = logging.getLogger(__name__)
ONEDRIVE_PATH_MAC = os.getenv("ONEDRIVE_PATH_MAC")
ONEDRIVE_PATH_WIN = os.getenv("ONEDRIVE_PATH_WIN")
ONEDRIVE_PATH = ONEDRIVE_PATH_MAC
POPPLER_PATH = os.getenv("POPPLER_PATH")