# ─────────────────────────────────────────────────────────────────────────────
# MERGE — при необходимости можно склеить все данные из папок в единые датасеты(например для загрузки в Datalens)
# ─────────────────────────────────────────────────────────────────────────────

from config import (
    API_KEY,
    SERVERS,
    PLAYERS_COUNT,
    MATCHES_PER_PLAYER,
    OUTPUT_DIR_BASE,
    PROJECT_DIR
)
import time
from datetime import datetime
import os
import requests
import pandas as pd
from pathlib import Path
from typing import Any, Dict, Union, List
import logging


def merge_csv(files):
    dfs = [pd.read_csv(f) for f in files]
    return pd.concat(dfs, ignore_index=True)

def main() -> None:
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    log_filename = now.strftime("mergelog_%H_%M_%d_%m_%Y.log")
    logging.basicConfig(level=logging.INFO, filename=log_dir / log_filename,format="%(asctime)s %(levelname)s %(message)s")
    
    logging.info(Path(PROJECT_DIR))
    FULL_PATH = os.getcwd()
    logging.info(Path(FULL_PATH))

    out_dir = Path("out")
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        matches_files = list(Path(FULL_PATH).glob(f"{OUTPUT_DIR_BASE}_*/matches.csv"))
        matches = merge_csv(matches_files)
        matches.to_csv("out/all_matches.csv", index=False)
        logging.info("\nТаблицы матчей соединены успешно")
    except ValueError:
        logging.info("ValueError in matches?")
    try:
        players_files = list(Path(FULL_PATH).glob(f"{OUTPUT_DIR_BASE}_*/players.csv"))
        players = merge_csv(players_files)
        players.to_csv("out/all_players.csv", index=False)
        logging.info("\nТаблицы игроков соединены успешно")
    except KeyError:
        logging.info("ValueError in players?")

    try:
        participants_files = list(Path(FULL_PATH).glob(f"{OUTPUT_DIR_BASE}_*/participants.csv"))
        participants = merge_csv(participants_files)
        participants.to_csv("out/all_participants.csv", index=False)
        logging.info("\nТаблицы участников матчей соединены успешно")
    except KeyError:
        logging.info("ValueError in participants?")

if __name__ == "__main__":  # эта конструкция говорит что делать когда файл запускают
    main()


