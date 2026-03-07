import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import boto3, tempfile
import uvicorn
from fastapi import FastAPI, Depends, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse
import firebase_admin
from firebase_admin import credentials, firestore
from app.models.users import WaitlistEmail
from app.api.api import api_router
from app.core.auth import has_access
from app.core.config import rate_limit_dependency, redis_client

from app.services.odds_tracker.odds_scheduler import scheduler, start_tracking_job
from app.services.odds_tracker.odds_tracker import get_match_meta, get_all_tracked_ids

from app.services.flashscore_scraper.flashscore_scraper import FlashScoreScraper
from app.settings import settings
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)

io_executor = ThreadPoolExecutor(max_workers=50)


@asynccontextmanager
async def lifespan(app_: FastAPI):
    # 1. Start Scheduler
    scheduler.start()

    # 2. Setup shared resources
    # Using one scraper instance is more memory-efficient
    scraper = FlashScoreScraper(persist_outputs=False)

    # Get the raw redis client (bypass Dependency Injection for lifespan)
    # Ensure your get_redis_client() helper is available here

    # 3. Recover Jobs with Staggering
    tracked_ids = await get_all_tracked_ids(redis_client)

    if tracked_ids:
        logger.info("Resuming %d tracking jobs...", len(tracked_ids))
        for i, match_id in enumerate(tracked_ids):
            meta = await get_match_meta(redis_client, match_id)
            if meta and meta.get("status") == "tracking":
                # Stagger the first run by 'i' seconds so they don't all hit at once
                start_delay = i * 1.5
                start_tracking_job(
                    match_id,
                    scraper,
                    redis_client,
                    initial_delay=start_delay
                )

    yield

    # 4. Shutdown
    scheduler.shutdown(wait=False)
    io_executor.shutdown(wait=False)

load_dotenv()


def setup_firebase_credentials():
    print("DEBUG: Starting firebase credentials setup")

    # If already set (local dev via .env), do nothing
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        print("DEBUG: GOOGLE_APPLICATION_CREDENTIALS already set, skipping")
        return

    print("DEBUG: Fetching from Secrets Manager...")
    try:
        client = boto3.client('secretsmanager', region_name='eu-west-3')
        secret = client.get_secret_value(SecretId='firebase-credentials')
        print("DEBUG: Secret fetched successfully")
        creds = json.loads(secret['SecretString'])
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(creds, tmp)
        tmp.close()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name
        print(f"DEBUG: Credentials written to {tmp.name}")
    except Exception as e:
        print(f"DEBUG: ERROR fetching secret: {str(e)}")
        raise

setup_firebase_credentials()

credential_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMITING_FREQUENCY],
    enabled=settings.RATE_LIMITING_ENABLE,
)

app = FastAPI(title="Transfermarkt API",
              docs_url="/api/docs",  # Set the Swagger UI docs URL
              redoc_url="/api/redoc", openapi_url="/api/openapi.json",lifespan=lifespan)

app.state.limiter = limiter  # type: ignore
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api")

if not firebase_admin._apps:
    if not credential_path:
        raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS is not set. Cannot initialize Firebase Admin SDK.")
    cred = credentials.Certificate(credential_path)
    default_app = firebase_admin.initialize_app(cred)

# Initialize Firestore
db = firestore.client()


@app.get("/", include_in_schema=False)
def docs_redirect():
    return RedirectResponse(url="/api/docs")


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=9000, reload=True)
