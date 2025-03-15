import requests
import json
import time
import os
import math
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from colorama import init, Fore, Back, Style

# Инициализация colorama
init()

# Константы
USE_BRIGHT_COLORS = False
BASE_URL_VOLUMES = "https://t2.ru/api/exchange/lots/stats/volumes"
BASE_URL_LOTS = "https://t2.ru/api/exchange/lots"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
TRAFFIC_TYPES = {"1": "data", "2": "voice", "3": "sms"}
UNIT_TYPES = {"data": "Гб", "voice": "мин", "sms": "SMS"}
VOLUME_LIMITS = {
    "data": (1, 120),
    "voice": (50, 3000),
    "sms": (50, 500)
}
UPDATE_INTERVAL = 6
DEPTH = 30
MAIN_LOTS_LIMIT = 15
LOT_LIMIT = 200
MAX_NAME_LENGTH = len("Анонимный продавец")  # 17 символов
EMOJI_MAP = {
    "devil": "👿", "cool": "😎", "cat": "🐱", "zipped": "🤐",
    "scream": "😱", "rich": "🤑", "tongue": "😛", "bomb": "💣"
}
TEXT_EMOJI_MAP = {
    "devil": "devil ", "cool": "cool  ", "cat": "cat   ",
    "zipped": "zipped", "scream": "scream", "rich": "rich  ",
    "tongue": "tongue", "bomb": "bomb  "
}
DEFAULT_EMOJI = "\u3000"
TEXT_DEFAULT_EMOJI = "--    "
SEPARATOR = "-" * 36
TEXT_SEPARATOR = "-" * 48
TRACKED_LOTS_FILE = "tracked_lots.json"
TRACKED_LOTS_LIMIT = 10
REQUEST_TIMEOUT = 5
RETRY_INTERVAL = 10

def get_color(color):
    """Возвращает яркий или стандартный цвет в зависимости от USE_BRIGHT_COLORS."""
    if not USE_BRIGHT_COLORS:
        return color

    color_map = {
        Fore.RED: Fore.LIGHTRED_EX,
        Fore.GREEN: Fore.LIGHTGREEN_EX,
        Fore.YELLOW: Fore.LIGHTYELLOW_EX,
        Fore.MAGENTA: Fore.LIGHTMAGENTA_EX,
        Fore.CYAN: Fore.LIGHTCYAN_EX,
        Fore.BLACK: Fore.LIGHTWHITE_EX,
        Fore.WHITE: Fore.LIGHTWHITE_EX,
    }
    return color_map.get(color, color)

def clear_screen():
    """Очищает экран консоли."""
    os.system('cls' if os.name == 'nt' else 'clear')

def format_cost(cost: float) -> str:
    """Форматирует стоимость, убирая '.0' если есть."""
    return str(int(cost)) if cost.is_integer() else str(cost)

def format_duration(start_time: float) -> str:
    """Форматирует время работы в формате 00ч 05м 03с."""
    duration = time.time() - start_time
    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)
    seconds = int(duration % 60)
    return f"{hours:02d}ч {minutes:02d}м {seconds:02d}с"

def format_interval(minutes: int) -> str:
    """Форматирует интервал в формате 00ч 00м 00с."""
    hours = int(minutes // 60)
    remaining_minutes = int(minutes % 60)
    return f"{hours:02d}ч {remaining_minutes:02d}м 00с"

def load_tracked_lots(traffic_type: str, volume: int) -> List[str]:
    """Загружает ID отслеживаемых лотов для заданного traffic_type и volume."""
    if os.path.exists(TRACKED_LOTS_FILE):
        with open(TRACKED_LOTS_FILE, "r", encoding="utf-8") as f:
            tracked_lots = json.load(f)
            key = f"{traffic_type}_{volume}"
            return tracked_lots.get(key, [])
    return []

def save_tracked_lots(tracked_lots: Dict[str, List[str]]):
    """Сохраняет ID отслеживаемых лотов в файл с сортировкой по trafficType и volume."""
    items = []
    for key, value in tracked_lots.items():
        traffic_type, volume = key.split("_")
        volume = int(volume)
        items.append((traffic_type, volume, key, value))
    
    items.sort(key=lambda x: (x[0], x[1]))
    sorted_tracked_lots = {item[2]: item[3] for item in items}
    
    with open(TRACKED_LOTS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted_tracked_lots, f, ensure_ascii=False, indent=4)

def get_cost_limits(traffic_type: str, volume: int) -> Tuple[float, float]:
    """Возвращает минимальную и максимальную стоимость для заданного типа трафика и объёма."""
    if traffic_type == "data":
        min_cost = volume * 15
        max_cost = volume * 50
    elif traffic_type == "voice":
        min_cost = math.ceil(volume * 0.8)
        max_cost = volume * 2
    elif traffic_type == "sms":
        min_cost = math.ceil(volume * 0.5)
        max_cost = math.floor(volume * 5.5)
    else:
        raise ValueError(f"Неизвестный тип трафика: {traffic_type}")
    return min_cost, max_cost

def get_user_input(traffic_type: Optional[str] = None, volume: Optional[int] = None) -> Tuple[str, int, Optional[float]]:
    """Запрашивает у пользователя тип трафика, размер лота и стоимость с повторным вводом при ошибке."""
    if traffic_type is None:
        while True:
            print("Выберите тип трафика: 1 - Гб (data), 2 - минуты (voice), 3 - смс (sms):")
            traffic_input = input().strip()
            if traffic_input in TRAFFIC_TYPES:
                traffic_type = TRAFFIC_TYPES[traffic_input]
                break
            else:
                print(f"{get_color(Fore.YELLOW)}Неверный выбор. Введите 1, 2 или 3.{Style.RESET_ALL}")

    unit = UNIT_TYPES[traffic_type]
    if volume is None:
        min_volume, max_volume = VOLUME_LIMITS[traffic_type]
        while True:
            print(f"Введите размер лота ({unit}) от {min_volume} до {max_volume}:")
            try:
                volume = int(input().strip())
                if min_volume <= volume <= max_volume:
                    break
                else:
                    print(f"{get_color(Fore.YELLOW)}Ошибка: Размер лота должен быть от {min_volume} до {max_volume}.{Style.RESET_ALL}")
            except ValueError:
                print(f"{get_color(Fore.YELLOW)}Ошибка: Введите целое число.{Style.RESET_ALL}")

    while True:
        min_cost_limit, max_cost_limit = get_cost_limits(traffic_type, volume)
        print(f"Введите стоимость лота (руб.) от {min_cost_limit} до {max_cost_limit} (или нажмите Enter для минимальной цены с биржи):")
        cost_input = input().strip()

        if cost_input:
            try:
                cost = float(cost_input)
                if min_cost_limit <= cost <= max_cost_limit:
                    return traffic_type, volume, cost
                else:
                    print(f"{get_color(Fore.YELLOW)}Ошибка: Стоимость должна быть от {min_cost_limit} до {max_cost_limit}.{Style.RESET_ALL}")
            except ValueError:
                print(f"{get_color(Fore.YELLOW)}Ошибка: Введите число.{Style.RESET_ALL}")
        else:
            return traffic_type, volume, None

def select_tracked_lot(lots: List[Dict[str, str]], traffic_type: str, volume: int, cost: float, use_text_emojis: bool = False) -> Optional[str]:
    """Показывает первые TRACKED_LOTS_LIMIT продавцов (не ботов) и запрашивает выбор лота для отслеживания."""
    sellers = [lot for lot in lots if not lot["my"]][:TRACKED_LOTS_LIMIT]
    if not sellers:
        print("Нет доступных продавцов для отслеживания.")
        return None

    print(f"\nДоступные продавцы для отслеживания (первые {TRACKED_LOTS_LIMIT}, исключая ботов):")
    positions = []
    for i, lot in enumerate(lots, 1):
        if not lot["my"] and len(positions) < TRACKED_LOTS_LIMIT:
            positions.append(i)
            name = lot["name"].ljust(MAX_NAME_LENGTH)
            emojis = process_emojis(lot["emojis"], use_text_emojis)
            print(f"{get_color(Fore.GREEN)}{i:2} {name}  [{emojis}]{Style.RESET_ALL}")

    while True:
        print("\nВведите номер лота для отслеживания (или нажмите Enter для пропуска):")
        choice = input().strip()
        if choice == "":
            return None
        try:
            pos = int(choice)
            if pos in positions:
                lot_index = pos - 1
                while lots[lot_index]["my"]:
                    lot_index -= 1
                return lots[pos - 1]["id"]
            else:
                print(f"{get_color(Fore.YELLOW)}Ошибка: Введите номер из списка: {', '.join(map(str, positions))}.{Style.RESET_ALL}")
        except ValueError:
            print(f"{get_color(Fore.YELLOW)}Ошибка: Введите число или нажмите Enter.{Style.RESET_ALL}")

def get_min_cost(traffic_type: str, volume: int) -> float:
    """Получает минимальную цену для заданного типа трафика и объёма."""
    headers = {"User-Agent": USER_AGENT}
    url = f"{BASE_URL_VOLUMES}?trafficType={traffic_type}"
    
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        if data["meta"]["status"] != "OK":
            raise ValueError(f"Ошибка API: {data['meta']['message']}")
        
        for item in data["data"]:
            if item["volume"] == float(volume):
                return item["minCost"]
        raise ValueError(f"Размер лота {volume} не найден для типа {traffic_type}.")
    except requests.RequestException as e:
        raise RuntimeError(f"Ошибка при запросе к API volumes: {e}") from e
    except (KeyError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Ошибка парсинга ответа API volumes: {e}") from e

def fetch_lots(traffic_type: str, volume: int, min_cost: float) -> List[Dict[str, str]]:
    """Загружает до LOT_LIMIT лотов с заданной ценой, включая эмодзи."""
    headers = {"User-Agent": USER_AGENT}
    url = f"{BASE_URL_LOTS}?trafficType={traffic_type}&volume={volume}&cost={min_cost}&limit={LOT_LIMIT}"
    
    attempt = 0
    while True:
        try:
            attempt += 1
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            if data["meta"]["status"] != "OK":
                raise ValueError(f"Ошибка API: {data['meta']['message']}")
            
            lots = []
            for lot in data["data"]:
                seller_name = lot["seller"]["name"] or "Анонимный продавец"
                lots.append({
                    "id": lot["id"],
                    "name": seller_name,
                    "my": lot["my"],
                    "cost": lot["cost"]["amount"],
                    "emojis": lot["seller"]["emojis"]
                })
            return lots
        except requests.RequestException:
            print(f"{get_color(Fore.YELLOW)}Ошибка при запросе к API lots. Попытка соединения {attempt}.{Style.RESET_ALL}")
            time.sleep(RETRY_INTERVAL)
        except (KeyError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Ошибка парсинга ответа API lots: {e}") from e

def fetch_all_lots(traffic_type: str, volume: int) -> List[Dict[str, str]]:
    """Загружает до LOT_LIMIT лотов всех цен для проверки изменений стоимости."""
    headers = {"User-Agent": USER_AGENT}
    url = f"{BASE_URL_LOTS}?trafficType={traffic_type}&volume={volume}&limit={LOT_LIMIT}"
    
    attempt = 0
    while True:
        try:
            attempt += 1
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            if data["meta"]["status"] != "OK":
                raise ValueError(f"Ошибка API: {data['meta']['message']}")
            
            lots = []
            for lot in data["data"]:
                lots.append({
                    "id": lot["id"],
                    "name": lot["seller"]["name"] or "Анонимный продавец",
                    "my": lot["my"],
                    "cost": lot["cost"]["amount"],
                    "emojis": lot["seller"]["emojis"]
                })
            return lots
        except requests.RequestException:
            print(f"{get_color(Fore.YELLOW)}Ошибка при запросе к API all lots. Попытка соединения {attempt}.{Style.RESET_ALL}")
            time.sleep(RETRY_INTERVAL)
        except (KeyError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Ошибка парсинга ответа API all lots: {e}") from e

def log_sale(lot: Dict[str, str], position: int, traffic_type: str, volume: int, min_cost: float, is_tracked: bool = False):
    """Записывает информацию о проданном лоте в файл с динамическим именем."""
    timestamp = datetime.now()
    folder = f"sales/{timestamp.strftime('%Y_%m')}"
    os.makedirs(folder, exist_ok=True)
    cost_str = format_cost(min_cost)
    filename = f"{folder}/sales_{traffic_type}_{volume}_{cost_str}.txt"
    
    marker = "[Я]" if is_tracked else ("[П]" if not lot["my"] else "[Б]")
    log_entry = f"{timestamp.strftime('%d.%m.%y %H:%M')} {marker} {lot['name']} ({position + 1})\n"
    
    with open(filename, "a", encoding="utf-8") as f:
        f.write(log_entry)

def read_last_sales(traffic_type: str, volume: int, min_cost: float, limit: int = MAIN_LOTS_LIMIT) -> List[str]:
    """Читает последние проданные лоты из файла (используется только для отображения)."""
    cost_str = format_cost(min_cost)
    folder = f"sales/{datetime.now().strftime('%Y_%m')}"
    filename = f"{folder}/sales_{traffic_type}_{volume}_{cost_str}.txt"
    
    if not os.path.exists(filename):
        return []
    
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()
        return lines[-limit:][::-1]

def colorize_sale_line(sale_line: str) -> str:
    """Добавляет цветовое форматирование для строки продажи."""
    if "[П]" in sale_line:
        return sale_line.replace("[П]", f"{get_color(Fore.GREEN)}[П]{Style.RESET_ALL}")
    elif "[Б]" in sale_line:
        return sale_line.replace("[Б]", f"{get_color(Fore.RED)}[Б]{Style.RESET_ALL}")
    elif "[Я]" in sale_line:
        return sale_line.replace("[Я]", f"{get_color(Fore.MAGENTA)}[Я]{Style.RESET_ALL}")
    return sale_line

def process_emojis(emojis: List[str], use_text_emojis: bool = False) -> str:
    """Обрабатывает список эмодзи, заменяет их и дополняет до 3-х."""
    emoji_map = TEXT_EMOJI_MAP if use_text_emojis else EMOJI_MAP
    default_emoji = TEXT_DEFAULT_EMOJI if use_text_emojis else DEFAULT_EMOJI
    result = []
    for emoji in emojis:
        result.append(emoji_map.get(emoji, default_emoji))
    
    while len(result) < 3:
        result.insert(0, default_emoji)
    
    return " ".join(result[:3])

def track_changes(prev_lots: List[Dict], curr_lots: List[Dict], traffic_type: str, volume: int, min_cost: float, tracked_lot_ids: List[str]) -> Tuple[int, int, int, int, int, List[Dict], List[Dict], List[Dict], List[Dict], List[str]]:
    """Отслеживает изменения и возвращает статистику, списки событий и проданные отслеживаемые лоты с временными метками."""
    prev_ids = {lot["id"]: idx for idx, lot in enumerate(prev_lots)}
    curr_ids = {lot["id"]: idx for idx, lot in enumerate(curr_lots)}
    prev_track_ids = {lot["id"] for lot in prev_lots[:DEPTH]}
    
    created_ids = {lot["id"] for lot in curr_lots[:DEPTH] if lot["id"] not in prev_ids}
    created_lots = [dict(lot, position=curr_ids[lot["id"]], timestamp=datetime.now()) for lot in curr_lots if lot["id"] in created_ids]
    created_bots = sum(1 for lot in created_lots if lot["my"])
    created_sellers = len(created_lots) - created_bots
    
    sold_ids = prev_track_ids - set(curr_ids.keys())
    
    sold_lots = []
    changed_lots = []
    true_sold_ids = set()
    
    sold_bot_ids = {lot_id for lot_id in sold_ids if prev_lots[prev_ids[lot_id]]["my"]}
    sold_seller_ids = sold_ids - sold_bot_ids
    
    if sold_seller_ids:
        all_lots = fetch_all_lots(traffic_type, volume)
        all_lots_dict = {lot["id"]: lot for lot in all_lots}
        
        true_sold_ids = {lot_id for lot_id in sold_ids if lot_id not in all_lots_dict or all_lots_dict[lot_id]["cost"] == min_cost}
        sold_lots = [dict(prev_lots[prev_ids[lot_id]], position=prev_ids[lot_id], timestamp=datetime.now()) for lot_id in true_sold_ids]
        
        for lot_id in sold_ids - true_sold_ids:
            if lot_id in all_lots_dict and all_lots_dict[lot_id]["cost"] != min_cost:
                changed_lot = dict(all_lots_dict[lot_id], position=prev_ids[lot_id], new_cost=all_lots_dict[lot_id]["cost"])
                changed_lots.append(changed_lot)
    else:
        true_sold_ids = sold_bot_ids
        sold_lots = [dict(prev_lots[prev_ids[lot_id]], position=prev_ids[lot_id], timestamp=datetime.now()) for lot_id in sold_bot_ids]
    
    sold_bots = sum(1 for lot in sold_lots if lot["my"])
    sold_sellers = len(sold_lots) - sold_bots
    
    sold_tracked_lot_ids = [lot_id for lot_id in true_sold_ids if lot_id in tracked_lot_ids]
    for lot in sold_lots:
        is_tracked = lot["id"] in tracked_lot_ids
        log_sale(lot, lot["position"], traffic_type, volume, min_cost, is_tracked)
    
    rockets = 0
    rocket_lots = []
    sales_shift = len(sold_ids)
    for lot_id, curr_pos in curr_ids.items():
        if lot_id not in prev_ids:
            continue
        prev_pos = prev_ids[lot_id]
        lot = curr_lots[curr_pos]
        if lot["my"]:
            continue
        
        creations_above = sum(1 for cid in created_ids if curr_ids.get(cid, LOT_LIMIT) < curr_pos)
        expected_pos = prev_pos - sales_shift + creations_above
        
        if (prev_pos > DEPTH and curr_pos < DEPTH) or (prev_pos <= DEPTH and curr_pos < prev_pos):
            if curr_pos < expected_pos:
                rockets += 1
                rocket_lots.append(dict(lot, position=curr_pos, prev_position=prev_pos, timestamp=datetime.now()))
    
    return created_bots, created_sellers, sold_bots, sold_sellers, rockets, created_lots, sold_lots, rocket_lots, changed_lots, sold_tracked_lot_ids

def parse_args():
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(description="Отслеживание лотов на бирже.")
    parser.add_argument("-tt", "--trafficType", type=str, choices=["1", "2", "3"], help="Тип трафика: 1 - data, 2 - voice, 3 - sms")
    parser.add_argument("-v", "--volume", type=int, help="Размер лота")
    parser.add_argument("-c", "--cost", type=float, help="Стоимость лота")
    parser.add_argument("-u", "--updateInterval", type=int, default=UPDATE_INTERVAL, help=f"Интервал обновления в секундах (по умолчанию {UPDATE_INTERVAL})")
    parser.add_argument("-d", "--depth", type=int, default=DEPTH, help=f"Глубина отслеживания (по умолчанию {DEPTH})")
    parser.add_argument("-ll", "--mainLotsLimit", type=int, default=MAIN_LOTS_LIMIT, help=f"Количество лотов для основного отображения (по умолчанию {MAIN_LOTS_LIMIT})")
    parser.add_argument("-tl", "--trackLot", action="store_true", help="Запрашивать лот для отслеживания после ввода стоимости")
    parser.add_argument("-bc", "--brightColors", action="store_true", help="Использовать яркие цвета (по умолчанию False)")
    parser.add_argument("-hh", "--hideHistory", action="store_true", help="Скрыть столбец с историей продаж")
    parser.add_argument("-te", "--textEmojis", action="store_true", help="Использовать текстовые эмодзи вместо графических")
    parser.add_argument("-si", "--statInterval", type=int, help="Интервал для дополнительной статистики в минутах (по умолчанию не используется)")
    return parser.parse_args()

def main():
    """Основная логика скрипта."""
    try:
        global USE_BRIGHT_COLORS
        global SEPARATOR

        args = parse_args()
        use_text_emojis = args.textEmojis
        if use_text_emojis:
            SEPARATOR = TEXT_SEPARATOR
            DEFAULT_EMOJI = TEXT_DEFAULT_EMOJI

        if args.trafficType and args.volume and args.cost is not None:
            traffic_type = TRAFFIC_TYPES[args.trafficType]
            volume = args.volume
            custom_cost = args.cost
            update_interval = args.updateInterval
            depth = args.depth
            main_lots_limit = args.mainLotsLimit
            track_lot = args.trackLot
            use_bright_colors = args.brightColors
            hide_history = args.hideHistory
            stat_interval = args.statInterval
        else:
            if args.trafficType:
                traffic_type = TRAFFIC_TYPES[args.trafficType]
                volume, custom_cost = None, None
            else:
                traffic_type, volume, custom_cost = None, None, None
            if args.volume:
                volume = args.volume
            if args.cost is not None:
                custom_cost = args.cost
            traffic_type, volume, custom_cost = get_user_input(traffic_type, volume)
            update_interval = UPDATE_INTERVAL
            depth = DEPTH
            main_lots_limit = MAIN_LOTS_LIMIT
            track_lot = args.trackLot
            use_bright_colors = args.brightColors
            hide_history = args.hideHistory
            stat_interval = args.statInterval

        USE_BRIGHT_COLORS = use_bright_colors

        unit = UNIT_TYPES[traffic_type]
        
        if custom_cost is None:
            min_cost = get_min_cost(traffic_type, volume)
            print(f"Используем минимальную цену с биржи: {format_cost(min_cost)} руб.")
        else:
            min_cost = custom_cost
            print(f"Используем введённую стоимость: {format_cost(min_cost)} руб.")
        
        min_cost_str = format_cost(min_cost)

        tracked_lot_ids = load_tracked_lots(traffic_type, volume)
        tracked_lots = {}
        if os.path.exists(TRACKED_LOTS_FILE):
            with open(TRACKED_LOTS_FILE, "r", encoding="utf-8") as f:
                tracked_lots = json.load(f)

        if track_lot:
            initial_lots = fetch_lots(traffic_type, volume, min_cost)
            selected_lot_id = select_tracked_lot(initial_lots, traffic_type, volume, min_cost, use_text_emojis)
            if selected_lot_id and selected_lot_id not in tracked_lot_ids:
                tracked_lot_ids.append(selected_lot_id)
                lot_key = f"{traffic_type}_{volume}"
                tracked_lots[lot_key] = tracked_lot_ids
                save_tracked_lots(tracked_lots)

        print("Начинаем отслеживание...")
        start_time = time.time()
        time.sleep(2)
        
        total_created_bots, total_created_sellers = 0, 0
        total_sold_bots, total_sold_sellers = 0, 0
        total_rockets = 0
        prev_lots = []
        
        # Хранение событий
        created_events = []
        sold_events = []
        rocket_events = []
        
        last_sales = read_last_sales(traffic_type, volume, min_cost, main_lots_limit)
        
        while True:
            curr_lots = fetch_lots(traffic_type, volume, min_cost)
            
            if prev_lots:
                cb, cs, sb, ss, rockets, created_lots, sold_lots, rocket_lots, changed_lots, sold_tracked_lot_ids = track_changes(
                    prev_lots, curr_lots, traffic_type, volume, min_cost, tracked_lot_ids
                )
                total_created_bots += cb
                total_created_sellers += cs
                total_sold_bots += sb
                total_sold_sellers += ss
                total_rockets += rockets
                
                # Добавление событий в списки с временными метками
                created_events.extend(created_lots)
                sold_events.extend(sold_lots)
                rocket_events.extend(rocket_lots)
                
                if sold_tracked_lot_ids:
                    tracked_lot_ids = [lot_id for lot_id in tracked_lot_ids if lot_id not in sold_tracked_lot_ids]
                    lot_key = f"{traffic_type}_{volume}"
                    tracked_lots[lot_key] = tracked_lot_ids
                    if not tracked_lot_ids:
                        tracked_lots.pop(lot_key, None)
                    save_tracked_lots(tracked_lots)
                
                if sold_lots:
                    last_sales = read_last_sales(traffic_type, volume, min_cost, main_lots_limit)
            
            created_total = total_created_bots + total_created_sellers
            denominator = created_total + total_rockets
            if denominator == 0:
                denominator = 1
            coef = (total_sold_sellers / denominator) * 100
            
            total_created_str = str(created_total)
            total_sold_str = str(total_sold_bots + total_sold_sellers)
            bots_created_str = str(total_created_bots)
            bots_sold_str = str(total_sold_bots)
            sellers_created_str = str(total_created_sellers)
            sellers_sold_str = str(total_sold_sellers)
            rockets_str = str(total_rockets)
            coef_str = f"{coef:.1f}"
            
            align_total = max(len(total_created_str), len(total_sold_str))
            align_bots = max(len(bots_created_str), len(bots_sold_str))
            align_sellers = max(len(sellers_created_str), len(sellers_sold_str))
            
            bots_created_colored = f"{get_color(Fore.RED)}{bots_created_str.rjust(align_bots)}{Style.RESET_ALL}"
            bots_sold_colored = f"{get_color(Fore.RED)}{bots_sold_str.rjust(align_bots)}{Style.RESET_ALL}"
            sellers_created_colored = f"{get_color(Fore.GREEN)}{sellers_created_str.rjust(align_sellers)}{Style.RESET_ALL}"
            sellers_sold_colored = f"{get_color(Fore.GREEN)}{sellers_sold_str.rjust(align_sellers)}{Style.RESET_ALL}"
            
            clear_screen()
            print(f"Лот: {get_color(Fore.YELLOW)}{volume} {unit}{Style.RESET_ALL}. Стоимость: {get_color(Fore.YELLOW)}{min_cost_str} руб.{Style.RESET_ALL}")
            print(f"Статистика за: {get_color(Fore.YELLOW)}{format_duration(start_time)}{Style.RESET_ALL}")
            print(f"Создано: {Back.WHITE}{Fore.BLACK}{total_created_str.rjust(align_total)}{Style.RESET_ALL} ({bots_created_colored} + {sellers_created_colored})  Ракет: {Back.CYAN}{Fore.BLACK}{rockets_str}{Style.RESET_ALL}")
            print(f"Продано: {Back.GREEN}{Fore.BLACK}{total_sold_str.rjust(align_total)}{Style.RESET_ALL} ({bots_sold_colored} + {sellers_sold_colored})  Коэф.: {Back.MAGENTA}{get_color(Fore.WHITE)}{coef_str}{Style.RESET_ALL}")
            
            # Дополнительная статистика за указанный интервал
            if stat_interval is not None:
                current_duration = time.time() - start_time
                interval_seconds = stat_interval * 60
                if current_duration >= interval_seconds:
                    interval_ago = datetime.now() - timedelta(minutes=stat_interval)
                    created_interval = [event for event in created_events if event.get("timestamp", datetime.now()) >= interval_ago]
                    sold_interval = [event for event in sold_events if event.get("timestamp", datetime.now()) >= interval_ago]
                    rocket_interval = [event for event in rocket_events if event.get("timestamp", datetime.now()) >= interval_ago]
                    
                    created_bots_interval = sum(1 for event in created_interval if event["my"])
                    created_sellers_interval = len(created_interval) - created_bots_interval
                    sold_bots_interval = sum(1 for event in sold_interval if event["my"])
                    sold_sellers_interval = len(sold_interval) - sold_bots_interval
                    rockets_interval = len(rocket_interval)
                    
                    created_total_interval = created_bots_interval + created_sellers_interval
                    denominator_interval = created_total_interval + rockets_interval
                    if denominator_interval == 0:
                        denominator_interval = 1
                    coef_interval = (sold_sellers_interval / denominator_interval) * 100
                    
                    created_total_interval_str = str(created_total_interval)
                    total_sold_interval_str = str(sold_bots_interval + sold_sellers_interval)
                    bots_created_interval_str = str(created_bots_interval)
                    bots_sold_interval_str = str(sold_bots_interval)
                    sellers_created_interval_str = str(created_sellers_interval)
                    sellers_sold_interval_str = str(sold_sellers_interval)
                    rockets_interval_str = str(rockets_interval)
                    coef_interval_str = f"{coef_interval:.1f}"
                    
                    align_total_interval = max(len(created_total_interval_str), len(total_sold_interval_str))
                    align_bots_interval = max(len(bots_created_interval_str), len(bots_sold_interval_str))
                    align_sellers_interval = max(len(sellers_created_interval_str), len(sellers_sold_interval_str))
                    
                    bots_created_interval_colored = f"{get_color(Fore.RED)}{bots_created_interval_str.rjust(align_bots_interval)}{Style.RESET_ALL}"
                    bots_sold_interval_colored = f"{get_color(Fore.RED)}{bots_sold_interval_str.rjust(align_bots_interval)}{Style.RESET_ALL}"
                    sellers_created_interval_colored = f"{get_color(Fore.GREEN)}{sellers_created_interval_str.rjust(align_sellers_interval)}{Style.RESET_ALL}"
                    sellers_sold_interval_colored = f"{get_color(Fore.GREEN)}{sellers_sold_interval_str.rjust(align_sellers_interval)}{Style.RESET_ALL}"
                    
                    print(SEPARATOR)
                    print(f"Статистика за: {get_color(Fore.YELLOW)}{format_interval(stat_interval)}{Style.RESET_ALL}")
                    print(f"Создано: {Back.WHITE}{Fore.BLACK}{created_total_interval_str.rjust(align_total_interval)}{Style.RESET_ALL} ({bots_created_interval_colored} + {sellers_created_interval_colored})  Ракет: {Back.CYAN}{Fore.BLACK}{rockets_interval_str}{Style.RESET_ALL}")
                    print(f"Продано: {Back.GREEN}{Fore.BLACK}{total_sold_interval_str.rjust(align_total_interval)}{Style.RESET_ALL} ({bots_sold_interval_colored} + {sellers_sold_interval_colored})  Коэф.: {Back.MAGENTA}{get_color(Fore.WHITE)}{coef_interval_str}{Style.RESET_ALL}")
            
            print(SEPARATOR)
            
            display_limit = min(len(curr_lots), main_lots_limit)
            
            for i in range(display_limit):
                lot = curr_lots[i]
                position = str(i + 1).ljust(3)
                name = lot["name"].ljust(MAX_NAME_LENGTH)
                emojis = process_emojis(lot["emojis"], use_text_emojis)
                color = get_color(Fore.MAGENTA) if lot["id"] in tracked_lot_ids else (get_color(Fore.RED) if lot["my"] else get_color(Fore.GREEN))
                lot_line = f"{color}{position} {name}  [{emojis}]{Style.RESET_ALL}"
                
                sale_line = ""
                if not hide_history and i < len(last_sales):
                    sale_line = colorize_sale_line(last_sales[i].strip())
                
                print(f"{lot_line}  {sale_line}")
            
            print(SEPARATOR)
            
            tracked_lots_below_limit = [(i + 1, lot) for i, lot in enumerate(curr_lots[main_lots_limit:], main_lots_limit) if lot["id"] in tracked_lot_ids]
            if tracked_lots_below_limit:
                for position, lot in tracked_lots_below_limit:
                    name = lot["name"].ljust(MAX_NAME_LENGTH)
                    emojis = process_emojis(lot["emojis"], use_text_emojis)
                    line = f"{str(position).ljust(3)} {name}  [{emojis}]"
                    print(f"{get_color(Fore.MAGENTA)}{line}{Style.RESET_ALL}")
                print(SEPARATOR)
            
            if prev_lots:
                if created_lots:
                    print(f"{Back.WHITE}{Fore.BLACK} Создано лотов: {len(created_lots)} {Style.RESET_ALL} {'+' if use_text_emojis else '➕'}")
                    for lot in created_lots:
                        position = str(lot["position"] + 1).rjust(3)
                        name = lot["name"].ljust(MAX_NAME_LENGTH)
                        emojis = process_emojis(lot["emojis"], use_text_emojis)
                        line = f"{position} {name}  [{emojis}]"
                        color = get_color(Fore.RED) if lot["my"] else get_color(Fore.GREEN)
                        print(f"{color}{line}{Style.RESET_ALL}")
                    print()
                
                if sold_lots:
                    print(f"{Back.GREEN}{Fore.BLACK} Продано лотов: {len(sold_lots)} {Style.RESET_ALL} {'$' if use_text_emojis else '💲'}")
                    for lot in sold_lots:
                        position = str(lot["position"] + 1).rjust(3)
                        name = lot["name"].ljust(MAX_NAME_LENGTH)
                        emojis = process_emojis(lot["emojis"], use_text_emojis)
                        line = f"{position} {name}  [{emojis}]"
                        color = get_color(Fore.RED) if lot["my"] else get_color(Fore.GREEN)
                        print(f"{color}{line}{Style.RESET_ALL}")
                    print()
                
                if rocket_lots:
                    print(f"{Back.CYAN}{Fore.BLACK} Поднято в топ: {len(rocket_lots)} {Style.RESET_ALL} {'▲' if use_text_emojis else '🚀'}")
                    for lot in rocket_lots:
                        position = str(lot["position"] + 1).rjust(3)
                        name = lot["name"].ljust(MAX_NAME_LENGTH)
                        emojis = process_emojis(lot["emojis"], use_text_emojis)
                        prev_pos = str(lot["prev_position"] + 1).rjust(3)
                        line = f"{position} {name}  [{emojis}] {Fore.LIGHTBLACK_EX}{prev_pos}{Style.RESET_ALL} > {Fore.LIGHTWHITE_EX}{lot['position'] + 1}{Style.RESET_ALL}"
                        print(f"{get_color(Fore.GREEN)}{line}{Style.RESET_ALL}")
                    print()
                
                if changed_lots:
                    print(f"{Back.YELLOW}{Fore.BLACK}Изменено лотов: {len(changed_lots)} {Style.RESET_ALL} {'*' if use_text_emojis else '✏️'}")
                    for lot in changed_lots:
                        position = str(lot["position"] + 1).rjust(3)
                        name = lot["name"].ljust(MAX_NAME_LENGTH)
                        emojis = process_emojis(lot["emojis"], use_text_emojis)
                        old_cost = format_cost(min_cost)
                        new_cost = format_cost(lot["new_cost"])
                        line = f"{position} {name}  [{emojis}] {Fore.LIGHTBLACK_EX}{old_cost} руб.{Style.RESET_ALL} > {Fore.LIGHTWHITE_EX}{new_cost} руб.{Style.RESET_ALL}"
                        print(f"{get_color(Fore.GREEN)}{line}{Style.RESET_ALL}")
            
            prev_lots = curr_lots
            time.sleep(update_interval)
            
    except (ValueError, RuntimeError) as e:
        print(f"{get_color(Fore.RED)}Ошибка: {e}{Style.RESET_ALL}")
        print("Нажмите Enter для выхода...")
        input()
    except KeyboardInterrupt:
        print(f"\n{get_color(Fore.RED)}Остановлено пользователем.{Style.RESET_ALL}")
        print("Нажмите Enter для выхода...")
        input()

if __name__ == "__main__":
    main()