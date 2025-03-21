import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(filename)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data_pipeline.log", mode="w"),
    ],
)

logger = logging.getLogger(__name__)
