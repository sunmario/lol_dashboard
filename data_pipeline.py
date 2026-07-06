from config import (
    API_KEY,
    SERVERS,
    PLAYERS_COUNT,
    MATCHES_PER_PLAYER,
    OUTPUT_DIR_BASE
)
import time
from datetime import datetime
import os
import requests
import pandas as pd
from pathlib import Path
from typing import Any, Dict, Union, List
import logging

print("Ваш конфигурационный файл имеет следующие параметры:")
print("Используемый ключ Riot API:", API_KEY)
print("Игроков:", PLAYERS_COUNT)
print("Матчей на игрока:", MATCHES_PER_PLAYER)




# ─────────────────────────────────────────────────────────────────────────────
# EXTRACT — функции получения данных из API
# ─────────────────────────────────────────────────────────────────────────────

def riot_get(url: str) -> Any:

    """
    Отправляет GET-запрос к Riot API с обработкой rate limit.

    При ответе 429 (Too Many Requests) ждёт время из заголовка
    Retry-After и повторяет запрос. Между запросами — пауза 0.06 с.

    Args:
        url: полный URL эндпоинта Riot API.

    Returns:
        Ответ API в виде Python-объекта (dict или list).

    Raises:
        requests.exceptions.HTTPError: при HTTP-ошибках кроме 429.
    """

    headers = {"X-Riot-Token": API_KEY}
    response = requests.get(url, headers=headers)

    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", 5))
        logging.info(f"  [rate limit] ждём {retry_after} сек...")
        time.sleep(retry_after)
        return riot_get(url)  # повторяем запрос

    response.raise_for_status()
    time.sleep(0.06)  # небольшая пауза чтобы не превысить лимит
    return response.json()




def get_challenger_players(region:str,queue: str = "RANKED_SOLO_5x5") -> List[Dict[str, Any]]:

    """
    Получает список игроков из лиги Challenger.

    Args:
        region: код региона (euw1, na1, ...).
        queue:  тип очереди. По умолчанию — RANKED_SOLO_5x5.

    Returns:
        Список словарей с данными игроков (summonerId, leaguePoints, ...).
    """

    url = (
        f"https://{region}.api.riotgames.com"
        f"/lol/league/v4/challengerleagues/by-queue/{queue}"
    )
    data = riot_get(url)
    return data["entries"]


def get_match_ids(routing_region: str,puuid: str,count: int = 20) -> List[str]:

    """
    Получает список Match ID для игрока по его PUUID.

    Args:
        puuid:          PUUID игрока.
        count:          количество матчей (макс. 100).
        routing_region: маршрутизирующий регион (europe, americas, asia).

    Returns:
        Список строк с идентификаторами матчей.
    """

    url = (
        f"https://{routing_region}.api.riotgames.com"
        f"/lol/match/v5/matches/by-puuid/{puuid}/ids"
        f"?start=0&count={count}"
    )
    return riot_get(url)


def get_match(routing_region:str,match_id: str) -> Dict[str, Any]:

    """
    Получает полные данные о матче по его ID.

    Args:
        match_id:       идентификатор матча (например, 'EUW1_5987369961').
        routing_region: маршрутизирующий регион.

    Returns:
        Словарь с полными данными матча (metadata, info, participants, teams).
    """

    url = (
        f"https://{routing_region}.api.riotgames.com"
        f"/lol/match/v5/matches/{match_id}"
    )
    return riot_get(url)


def collect_players(region:str,players_count: int = 10) -> List[Dict[str, Any]]:

    """
    Собирает топ-N игроков из Challenger, отсортированных по LP.

    Args:
        players_count: количество игроков для возврата.

    Returns:
        Список словарей с данными топ-игроков.
    """

    players = get_challenger_players(region)
    players_sorted = sorted(
        players,
        key=lambda p: p["leaguePoints"],
        reverse=True
    )
    return players_sorted[:players_count]


def collect_match_ids(region:str,routing_region:str,players_count: int = 10,matches_per_player: int = 5) -> List[str]:

    """
    Собирает Match ID для топ-N игроков.

    Для каждого игрока: получает PUUID → запрашивает список матчей.
    Ошибки на уровне отдельного игрока не останавливают сбор.

    Args:
        players_count:     количество топ-игроков.
        matches_per_player: количество матчей на игрока.

    Returns:
        Общий список Match ID для всех игроков.
    """

    players = collect_players(region,players_count)
    all_match_ids = []

    for i, player in enumerate(players, 1):
        # puuid уже есть в ответе Challenger API — отдельный запрос не нужен
        puuid = player["puuid"]
        logging.info(f"  [{i}/{len(players)}] получаем матчи для {puuid[:12]}...")

        try:
            match_ids = get_match_ids(routing_region,puuid, count=matches_per_player)
            all_match_ids.extend(match_ids)
        except Exception as e:
            logging.warning(f"  ⚠ Ошибка для {puuid[:12]}: {e}")
            continue

    return all_match_ids


def collect_matches(region:str,routing_region:str,players_count: int = 10,matches_per_player: int = 5) -> List[Dict[str, Any]]:

    """
    Собирает полные данные матчей для топ-N игроков.

    Шаги: collect_match_ids() → для каждого ID вызывает get_match().
    Ошибки на уровне отдельного матча не останавливают сбор.

    Args:
        players_count:     количество топ-игроков.
        matches_per_player: количество матчей на игрока.

    Returns:
        Список словарей с полными данными матчей от Riot API.
    """

    match_ids = collect_match_ids(region,routing_region,players_count, matches_per_player)
    matches = []

    for i, match_id in enumerate(match_ids, 1):
        logging.info(f"  [{i}/{len(match_ids)}] загружаем матч {match_id}...")

        try:
            match = get_match(routing_region,match_id)
            matches.append(match)
        except Exception as e:
            logging.warning(f"  ⚠ Ошибка для {match_id}: {e}")
            continue

    return matches


# ─────────────────────────────────────────────────────────────────────────────
# TRANSFORM — функции преобразования сырых данных в таблицы
# ─────────────────────────────────────────────────────────────────────────────

def transform_players(region,routing_region,matches: List[Dict[str, Any]]) -> pd.DataFrame:

    """
    Извлекает уникальных игроков из сырых данных матчей.

    Один puuid = одна строка. Дубликаты удаляются —
    один игрок мог участвовать в нескольких матчах выборки.

    Args:
        matches: список матчей из collect_matches().

    Returns:
        DataFrame со столбцом:
        - puuid (str): уникальный идентификатор игрока.
    """

    rows = []

    for match in matches:
        for participant in match["info"]["participants"]:
            rows.append({"region":region,"routing_region":routing_region,
                "puuid": participant["puuid"]})

    return (
        pd.DataFrame(rows)
        .drop_duplicates(subset="puuid")
        .reset_index(drop=True)
    )


def transform_matches(region,routing_region,matches: List[Dict[str, Any]]) -> pd.DataFrame:

    """
    Извлекает метаданные матчей из сырых данных API.

    Один match_id = одна строка. Дубликаты убираются — один матч
    мог попасть в выборку через разных игроков.

    Args:
        matches: список матчей из collect_matches().

    Returns:
        DataFrame со столбцами:
        - match_id (str):       уникальный ID матча.
        - game_mode (str):      режим игры (CLASSIC, ARAM, ...).
        - game_version (str):   версия патча.
        - game_duration (int):  длительность в секундах.
        - game_start_ts (int):  время начала (unix timestamp, мс).
    """

    rows = []

    for match in matches:
        info = match["info"]
        rows.append({
            "region":region,
            "routing_region":routing_region,
            "match_id":      match["metadata"]["matchId"],
            "game_mode":     info.get("gameMode"),
            "game_version":  info.get("gameVersion"),
            "game_duration": info.get("gameDuration"),
            "game_start_ts": info.get("gameStartTimestamp"),
        })

    return (
        pd.DataFrame(rows)
        .drop_duplicates(subset="match_id")
        .reset_index(drop=True)
    )


def transform_participants(region,routing_region,matches: List[Dict[str, Any]]) -> pd.DataFrame:

    """
    Извлекает статистику участников из сырых данных матчей.

    Связующая таблица игрок ↔ матч (many-to-many).
    В одном матче всегда 10 участников → строк = матчей × 10.
    Поле win конвертируется из bool в int (0/1) для совместимости с SQLite.

    Args:
        matches: список матчей из collect_matches().

    Returns:
        DataFrame со столбцами:
        - match_id (str):                    ID матча.
        - puuid (str):                       ID игрока.
        - champion (str):                    имя чемпиона.
        - kills (int):                       убийства.
        - deaths (int):                      смерти.
        - assists (int):                     ассисты.
        - gold_earned (int):                 заработанное золото.
        - total_damage_to_champions (int):   урон по чемпионам.
        - vision_score (int):                очки обзора.
        - win (int):                         победа: 1 — да, 0 — нет.
    """

    rows = []

    for match in matches:
        match_id = match["metadata"]["matchId"]

        for p in match["info"]["participants"]:
            rows.append({
                "region":region,
                "routing_region":routing_region,
                "match_id":                  match_id,
                "puuid":                     p["puuid"],
                "champion":                  p["championName"],
                "kills":                     p["kills"],
                "deaths":                    p["deaths"],
                "assists":                   p["assists"],
                "gold_earned":               p["goldEarned"],
                "total_damage_to_champions": p["totalDamageDealtToChampions"],
                "vision_score":              p["visionScore"],
                "win":                       int(p["win"]),  # bool → 0/1
            })

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# LOAD — функции записи данных
# ─────────────────────────────────────────────────────────────────────────────


def load_to_csv(
    df_players: pd.DataFrame,
    df_matches: pd.DataFrame,
    df_participants: pd.DataFrame,
    output_dir: str 
) -> None:

    """
    Сохраняет три таблицы в CSV-файлы.

    Создаёт папку output_dir если она не существует.
    Каждая таблица — отдельный файл. Индекс pandas не сохраняется.

    Args:
        df_players:      DataFrame с уникальными игроками.
        df_matches:      DataFrame с метаданными матчей.
        df_participants: DataFrame со статистикой участников.
        output_dir:      папка для сохранения файлов.

    Returns:
        None.
    """

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    df_players.to_csv(out / "players.csv", index=False)
    df_matches.to_csv(out / "matches.csv", index=False)
    df_participants.to_csv(out / "participants.csv", index=False)

    logging.info(f"  players.csv      — {len(df_players)} строк,путь к файлу:{out}")
    logging.info(f"  matches.csv      — {len(df_matches)} строк,путь к файлу:{out}")
    logging.info(f"  participants.csv — {len(df_participants)} строк,путь к файлу:{out}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN — точка входа, запускает полный ETL-пайплайн (так называемая оркестрация)
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:

    """
    Запускает полный ETL-пайплайн:
        1. Extract   — собирает матчи из Riot API
        2. Transform — разбивает данные на три таблицы
        3. Load      — сохраняет в CSV и SQLite
    """
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    log_filename = now.strftime("log_%H_%M_%d_%m_%Y.log")
    
    logging.basicConfig(level=logging.INFO, filename=log_dir / log_filename,format="%(asctime)s %(levelname)s %(message)s")
    # EXTRACT
    logging.info("\n[1/3] EXTRACT — получаем данные из API")
    for server in SERVERS:

        ROUTING_REGION = server["name"]
        REGION = server["region"]
        OUTPUT_DIR = OUTPUT_DIR_BASE + f"_{ROUTING_REGION}_{REGION}"
        if OUTPUT_DIR in list()
        logging.info(f"Данные собираем для региона: {ROUTING_REGION}:{REGION}")

        matches = collect_matches(
            players_count=PLAYERS_COUNT,
            matches_per_player=MATCHES_PER_PLAYER,
            routing_region = ROUTING_REGION,
            region = REGION
        )

        logging.info(f"Загружено матчей: {len(matches)}")

        # TRANSFORM
        logging.info("\n[2/3] TRANSFORM — разбиваем на таблицы")

        df_players      = transform_players(REGION,ROUTING_REGION,matches)
        df_matches      = transform_matches(REGION,ROUTING_REGION,matches)
        df_participants = transform_participants(REGION,ROUTING_REGION,matches)

        logging.info(f"Игроков:    {len(df_players)}")
        logging.info(f"Матчей:     {len(df_matches)}")
        logging.info(f"Участников: {len(df_participants)}")

        # LOAD
        logging.info("\n[3/3] LOAD — сохраняем данные")

        logging.info(f"\n  → CSV в '{OUTPUT_DIR}/'")
        load_to_csv(df_players, df_matches, df_participants,OUTPUT_DIR)
        time.sleep(120)
    logging.info("\nETL завершён успешно.")



if __name__ == "__main__":  # эта конструкция говорит что делать когда файл запускают
    main()


