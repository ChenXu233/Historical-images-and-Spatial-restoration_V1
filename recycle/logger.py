import logging

logging.basicConfig(
    level=logging.DEBUG,
    filename="debug.log",
    filemode="w",
    format="%(asctime)s - %(levelname)s - %(message)s",
)
