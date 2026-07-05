import logging

import boto3
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv(override=True)

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_default_region: str
    bedrock_llm_model: str

    model_config = {"env_file": ".env", "extra": "ignore"}

    def create_boto3_session(self) -> boto3.Session:
        return boto3.Session(
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_default_region,
        )


settings = Settings()

_masked_key = f"...{settings.aws_access_key_id[-4:]}" if settings.aws_access_key_id else "N/A"
logger.info(
    "Settings carregadas — região: %s | access key: %s | modelo: %s",
    settings.aws_default_region,
    _masked_key,
    settings.bedrock_llm_model,
)
