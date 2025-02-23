# Часть 1: Инициализация и работа с конфигурацией #
# Импортируем необходимые библиотеки
import requests
import time
import datetime
import os
import math
from colorama import init, Fore, Back, Style
from requests.exceptions import ConnectionError
from json import JSONDecodeError
from configparser import ConfigParser

# Инициализация Colorama для улучшенного отображения текста в терминале
init(autoreset=True)


# Параметры, которые можно задать вручную
# Задайте значения вручную или оставьте None, чтобы использовать ручной ввод типа и размера лота при минимальной стоимости
trafficType = None # Тип лота: 1 - "data", 2 - "voice", 3 - "sms"
volume = None # Размер лота
cost = None # Стоимость лота

# Запуск нескольких копий мониторинга через monitoring_RC4_mod_multi_16.4.5.py
import argparse

# Добавляем парсинг аргументов командной строки
parser = argparse.ArgumentParser(description="Мониторинг лотов")
parser.add_argument("--volume", type=int)
parser.add_argument("--trafficType", type=int)
args = parser.parse_args()

# Если аргументы переданы, используем их вместо ручного ввода
if args.volume is not None:
    volume = args.volume
if args.trafficType is not None:
    trafficType = args.trafficType
# Конец запуска нескольких копий

# Замена эмодзи
custom_emojis = {
    "devil": "👿",
    "cool": "😎",
    "cat": "🐱",
    "zipped": "🤐",
    "scream": "😱",
    "rich": "🤑",
    "tongue": "😛",
    "bomb": "💣"
}

# Проверяем наличие файла конфигурации, если нет, создаём новый с параметрами по умолчанию
if not os.path.exists('config.ini'): # Создаём пустой файл
    open('config.ini', 'w').close()
    print(Fore.YELLOW + 'Файл config.ini не найден, будет создан новый с параметрами по умолчанию.')
    with open("config.ini", "w") as file:
        file.write("""[Settings]
# interval - интервал записи логов (в минутах)
interval = 60
# delay - задержка обновления данных (в секундах)
delay = 6
# delete - удалять прошлый лог перед запуском? (y/n)
delete = n
# depth - глубина проверки проданных лотов
depth = 50
# ask_my_lot - запрашивать номер лота для отслеживания при запуске (y/n)
ask_my_lot = y

[Display]
# max_lines - число отображаемых строк для лотов и лога
max_lines = 15
# emojis - отображать эмодзи в списке лотов (True/False)
emojis = True
# rocket - отображать затраты продавца на ракеты (True/False)
rocket = True
# history - отображать лог проданных лотов (True/False)
history = True
# info_lots - отображать лоты в информационных сообщениях под основным списком (True/False)
info_lots = True

[User]
# my_names - имена для отсеживания: Рустам, Эльза и т.д. (работает только в сочетании с my_emojis)
my_names = 
# my_emojis - эмодзи для отслеживания: [], [cat scream devil], [bomb bomb cool] и т.д.
my_emojis = 
# СПИСОК ЭМОДЗИ: devil, cool, cat, zipped, scream, rich, tongue, bomb
""")

# Загружаем настройки из конфигурационного файла
config = ConfigParser()
config.read('config.ini')

# Инициализация переменных
headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'}
sellers_array = [] # Список продавцов
new_elements = [] # Новые элементы (лот)
timestamps = [] # Временные метки для лотов
selection_array = [] # Массив для выбора
raise_count = {} # Счётчик повышений для каждого продавца
cached_data = None # Кэшированные данные с сервера
r_r = 1 # Счётчик перезагрузки данных
# Остальные переменные для подсчёта различных параметров (например, для добавленных и проданных лотов)
a, a_b, a_p, s, s_b, s_p, r = 0, 0, 0, 0, 0, 0, 0
a_int, a_b_int, a_p_int, r_int, s_int, s_b_int, s_p_int = 0, 0, 0, 0, 0, 0, 0
yes = {'yes','y', ''} # Множество вариантов "да"
no = {'no','n'} # Множество вариантов "нет"

# Функция для создания папки с годом и месяцем в названии
def create_monthly_folder():
    current_year = datetime.datetime.now().year
    current_month = datetime.datetime.now().month
    folder_path = f"sales/{current_year}-{current_month:02d}"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path
    

# Часть 2: Ввод данных от пользователя #
# Если значения не заданы вручную, запрашиваем их у пользователя
if trafficType is None:
    while True:
        try:
            trafficType_input = int(input("Выберите тип лота (1-Гб, 2-минуты, 3-SMS): "))
            if trafficType_input not in [1, 2, 3]:
                raise ValueError
            trafficType = trafficType_input
            break
        except ValueError:
            print(Fore.YELLOW + 'Введите правильное значение (1, 2 или 3).')
# Преобразуем введенное значение в строку для дальнейшего использования
traffic_types = {1: "data", 2: "voice", 3: "sms"}
trafficType = traffic_types[trafficType]

if volume is None:
    while True:
        try:
            if trafficType == 'data':
                volume = int(input('Введите количество Гб (от 1 до 120): '))
                if volume < 1 or volume > 120:
                    raise ValueError
            elif trafficType == 'voice':
                volume = int(input('Введите количество минут (от 50 до 3000): '))
                if volume < 50 or volume > 3000:
                    raise ValueError
            elif trafficType == 'sms':
                volume = int(input('Введите количество SMS (от 50 до 500): '))
                if volume < 50 or volume > 500:
                    raise ValueError
            break
        except ValueError:
            if trafficType == 'data':
                print(Fore.YELLOW + 'Введите правильное значение от 1 до 120.')
            elif trafficType == 'voice':
                print(Fore.YELLOW + 'Введите правильное значение от 50 до 3000.')
            elif trafficType == 'sms':
                print(Fore.YELLOW + 'Введите правильное значение от 50 до 500.')

start_time = time.time() # Время начала работы
start_time_str = datetime.datetime.fromtimestamp(start_time).strftime('%d.%m.%y, %H:%M')

# Загружаем значения значения из config.ini
interval = config.getint("Settings", "interval", fallback=60)
delay = config.getint("Settings", "delay", fallback=6)
delete = config.get("Settings", "delete", fallback="n")
interval *= 60 # Конвертируем интервал в секунды
depth = config.getint("Settings", "depth", fallback=50)
ask_my_lot = config.get("Settings", "ask_my_lot", fallback="y").lower() in yes

max_lines = config.getint("Display", "max_lines", fallback=15) # v11 по-умолчанию 25
display_emojis = config.getboolean("Display", "emojis", fallback=True)  # Флаг отображения эмодзи
display_count = config.getboolean("Display", "rocket", fallback=True)  # Флаг отображения количества повышений
display_history = config.getboolean("Display", "history", fallback=True)  # Флаг отображения истории продаж
info_lots = config.getboolean("Display", "info_lots", fallback=True)

my_names = config.get("User", "my_names", fallback="") # v13
my_emojis = config.get("User", "my_emojis", fallback="") # v13

# Если стоимость лота не задана вручную, получаем её через API
if cost is None:
    try:
        # Определяем диапазон стоимости в зависимости от типа трафика
        if trafficType == "data":
            min_cost = volume * 15
            max_cost = volume * 50
        elif trafficType == "voice":
            min_cost = math.ceil(volume * 0.8)  # Округляем вверх
            max_cost = volume * 2
        elif trafficType == "sms":
            min_cost = math.ceil(volume * 0.5)  # Округляем вверх
            max_cost = math.floor(volume * 5.5)  # Округляем вниз

        # Запрашиваем ввод стоимости у пользователя с указанием диапазона
        while True:
            try:
                cost_input = input(f"Введите стоимость лота (от {min_cost} до {max_cost} ₽) или нажмите Enter для минимальной: ")
                if cost_input.strip() == "":  # Если пользователь ничего не ввел, используем minCost
                    response = requests.get(f"https://t2.ru/api/exchange/lots/stats/volumes?trafficType={trafficType}", headers=headers, timeout=5)
                    data = response.json()

                    # Проверяем, существует ли лот с указанным volume
                    volume_exists = any(item['volume'] == volume for item in data['data'])
                    if not volume_exists:
                        print(Fore.RED + f"Выбранный лот не найден на сервере.")
                        input("Нажмите Enter для выхода...")
                        exit()  # Завершаем программу, если лот не найден

                    def get_cost(volume):
                        for item in data['data']:
                            if item['volume'] == volume:
                                return item.get("minCost")
                        return None
                    cost = get_cost(volume)
                    break
                else:
                    cost = float(cost_input)  # Преобразуем введенное значение в число
                    # Проверяем, что стоимость находится в допустимом диапазоне
                    if min_cost <= cost <= max_cost:
                        break
                    else:
                        print(Fore.YELLOW + f"Стоимость должна быть в диапазоне от {min_cost} до {max_cost} ₽.")
            except ValueError:
                print(Fore.YELLOW + "Введите корректное числовое значение.")
    except (JSONDecodeError, ConnectionError, requests.exceptions.ReadTimeout):
        print(Fore.RED + 'Нет связи с сервером')
        input("Нажмите Enter для выхода...")
        exit()


# Часть 3: Подготовка и обработка данных с сервера #
# Запрос на получение списка лотов по параметрам
try:
    response = requests.get(f"https://t2.ru/api/exchange/lots?trafficType={trafficType}&volume={volume}&cost={cost}&limit=5000", headers=headers, timeout=5) 
    data = response.json()
except (JSONDecodeError, ConnectionError, requests.exceptions.ReadTimeout):
    print(Fore.YELLOW + 'Нет связи с сервером')

# Обработка данных с лотами и добавление их в список
for item in reversed(data["data"]):
    seller = item.get("seller", {})
    name = seller.get("name")
    emojis = seller.get("emojis")
    id = item.get("id")
    my = item.get("my")
    seller_list = ["Анонимный продавец", emojis, str(id), str(my)] if name is None else [name, emojis, str(id), str(my)]
    sellers_array.insert(0, seller_list)
    timestamps.insert(0, time.time())
    
# Функция для форматирования эмодзи
def format_emojis(emojis):
    # Заменяем оригинальные эмодзи на кастомные, а отсутствующие — на \u3000
    custom_emojis_list = [custom_emojis.get(emoji, "\u3000") for emoji in emojis]
    while len(custom_emojis_list) < 3:  # Если эмодзи меньше 3, добавляем широкие пробелы в начало
        custom_emojis_list.insert(0, "\u3000")  # Широкий пробел Unicode
    return " ".join(custom_emojis_list[:3])  # Возвращаем строку с 3 эмодзи

if ask_my_lot:
    # Вывод списка лотов с порядковыми номерами, именами и эмодзи (без ботов)
    print("Список лотов:")
    seller_count = 0  # Счётчик для отслеживания количества выведенных продавцов
    displayed_lots = []  # Список для хранения индексов выведенных лотов

    for index, item in enumerate(data["data"][:depth]):  # Проходим по всем лотам, а не только по max_lines
        seller = item.get("seller", {})
        name = seller.get("name")
        emojis = seller.get("emojis", [])
        my = item.get("my")  # Флаг, указывающий, бот это или продавец
    
        # Если это бот, пропускаем его
        if my:
            continue
    
        # Если имя продавца отсутствует, заменяем его на "Анонимный продавец"
        name = "Анонимный продавец" if name is None else name
    
        # Форматируем эмодзи
        formatted_emojis = format_emojis(emojis)
    
        # Выводим лот с фиксированной шириной порядкового номера (3 символа) и имени (24 символа)
        print(f"{index + 1:<3} {Fore.GREEN}{name:<19} [{formatted_emojis}]")
    
        # Сохраняем индекс выведенного лота
        displayed_lots.append(index)
    
        # Увеличиваем счётчик продавцов
        seller_count += 1
    
        # Если вывели 10 продавцов, прерываем цикл
        if seller_count >= 10:
            break
    
    # Добавляем ввод порядкового номера лота для выделения
    try:
        user_input = input("Введите номер лота для отслеживания или нажмите Enter для пропуска: ")  # Получаем ввод пользователя
        if user_input.strip() == "":  # Если ввод пустой (нажат Enter)
            highlight_id = None  # Не выделяем лот
        else:
            lot_number = int(user_input)  # Получаем номер лота, введенный пользователем
            # Проверяем, что номер в допустимом диапазоне выведенных лотов
            if lot_number < 1 or lot_number > len(data["data"]):
                raise ValueError
            # Проверяем, что лот с таким номером был выведен на экран (исключаем ботов)
            if (lot_number - 1) not in displayed_lots:
                raise ValueError
            # Получаем ID лота по его индексу
            selected_lot = data["data"][lot_number - 1]
            highlight_id = selected_lot.get("id")  # Используем ID для выделения
    except ValueError:
        print(Fore.YELLOW + "Введён неверный номер лота.")
        input("Нажмите Enter, чтобы продолжить...")  # Пауза, чтобы пользователь увидел сообщение
        highlight_id = None  # Сброс выделения, если номер неверный
else:
    highlight_id = None  # Если запрос номера лота отключен, highlight_id остается None


# Часть 4: Обработка лотов и продаж #
# Функция для проверки изменений стоимости лота
def check(id):
    global cached_data
    if not cached_data:
        try:
            # Загружаем последние данные с сервера, если они не были ранее загружены
            response = requests.get(f"https://t2.ru/api/exchange/lots?trafficType={trafficType}&volume={volume}&&limit=500", headers=headers, timeout=5) ####### limit=500 по-умолчанию #######
            cached_data = response.json()
        except (JSONDecodeError, ConnectionError, requests.exceptions.ReadTimeout):
            print(Fore.YELLOW + 'Нет связи с сервером')
            time.sleep(10)

    try:
        # Ищем лот по id и проверяем изменения его стоимости
        for item in cached_data["data"]:
            id_check = item.get("id")
            cost_change = item.get("cost").get("amount")
            if id_check == id:
                return True, cost_change
    except Exception as e:
        print(Fore.YELLOW + f'Нет данных для обработки. Ошибка: {e}')
    return False, None


# Часть 5: Обработка и сохранение информации о лотах в файлы #
# Определение файла для сохранения данных о лотах в зависимости от типа трафика и объема
trafficTypeFile = "gb" if trafficType == "data" else "min" if trafficType == "voice" else "sms" # v08
# Проверка наличия файла и его создание, если файл не существует
folder_path = create_monthly_folder()
file_path = f"{folder_path}/sales_{trafficTypeFile}_{volume}_{str(cost).replace('.0', '')}.txt"
if not os.path.exists(file_path):
    open(file_path, 'w').close()

# Ожидаем подтверждения от пользователя, нужно ли очистить историю продаж
while True: # v08
    if delete in yes: # v08
        # Очистка истории продаж
        open(file_path, 'w').close()
        break # v08
    elif delete in no: # v08
        break # v08


# Часть 6: Сбор и запись статистики о лотах #
trafficTypeVisual = " Гб" if trafficType == "data" else " мин" if trafficType == "voice" else " SMS"

if a == 0: # v10 коэффициент
    k = round((s_p/(a+1+r))*100, 1) # v10 коэффициент
else: # v10 коэффициент
    k = round((s_p/(a+r))*100, 1) # v10 коэффициент

# Запись заголовка начала сбора данных в файл
folder_path = create_monthly_folder()
file_path = f"{folder_path}/sales_{trafficTypeFile}_{volume}_{str(cost).replace('.0', '')}.txt"
with open(file_path, "a", encoding="utf-8") as f:
    f.write('==========================================================\n')
    f.write('Старт мониторинга: ' + datetime.datetime.now().strftime("%d.%m.%y, %H:%M") + f". Лот: {volume}{trafficTypeVisual} - " + f"{str(cost).replace('.0', '')} ₽.\n")
    f.write('==========================================================\n')


# Часть 7: Основной цикл обработки лотов и записи результатов #
while True:

    if a == 0: # v10 коэффициент
        k = round((s_p/(a+1+r))*100, 1) # v10 коэффициент
    else: # v10 коэффициент
        k = round((s_p/(a+r))*100, 1) # v10 коэффициент

    current_time = time.time()
    elapsed_time = current_time - start_time

    # Если прошёл заданный интервал времени, то записываем статистику в файл
    if elapsed_time > interval:
        # Вычисляем k_int на основе разницы значений за интервал
        s_p_diff = s_p - s_p_int  # Продажи продавцами за интервал
        a_diff = a - a_int  # Добавлено за интервал
        r_diff = r - r_int  # Ракеты за интервал

        if a_diff == 0: # Если добавлено 0, используем формулу с +1
            k_int = round((s_p_diff / (a_diff + 1 + r_diff)) * 100, 1)
        else: # Иначе используем стандартную формулу
            k_int = round((s_p_diff / (a_diff + r_diff)) * 100, 1)

        folder_path = create_monthly_folder()
        file_path = f"{folder_path}/sales_{trafficTypeFile}_{volume}_{str(cost).replace('.0', '')}.txt"
        with open(file_path, "a", encoding="utf-8") as f:
            f.write('----------------------------------------------------------\n' + datetime.datetime.now().strftime("%d.%m.%y, %H:%M") + f'. Статистика за {round(interval / 60)} мин.:\n')#v09
            f.write(f'Создано: {str(a - a_int):<4} Ботами: {str(a_b - a_b_int):<4} Продавцами: {str(a_p - a_p_int):<4} Ракет: {str(r - r_int)}\n')
            f.write(f'Продано: {str(s - s_int):<4} Ботами: {str(s_b - s_b_int):<4} Продавцами: {str(s_p - s_p_int):<4} Коэф.: {str(k_int)}\n')
            f.write('----------------------------------------------------------\n\n')
            start_time += interval # Обновление времени начала для следующего интервала
        a_int, a_b_int, a_p_int, r_int = a, a_b, a_p, r # Обновляем статистику
        s_int, s_b_int, s_p_int = s, s_b, s_p

    # Очистка экрана
    os.system('cls' if os.name == 'nt' else 'clear')

    # Инициализация счетчиков ботов и продавцов
    bot_count = 0
    seller_count = 0

    # Обработка ботов и продавцов в первых 100 лотах
    for index, item in enumerate(data["data"][:100]):  # Обрабатываем только первые 100 лотов
        seller = item.get("seller", {})
        my = item.get("my")  # Флаг, указывающий, бот это или продавец

        if my:  # Если это бот
            bot_count += 1
        else:  # Если это продавец
            seller_count += 1

    # Вывод на экран текущих данных
    print(Fore.WHITE + f"Старт мониторинга: {Fore.YELLOW}{start_time_str}")  # Выводим время начала работы
    print(Fore.WHITE + f"Лот: {Fore.YELLOW}{volume}{trafficTypeVisual}. " + f"{Fore.WHITE}Стоимость: {Fore.YELLOW}{str(cost).replace('.0', '')} ₽.")
    # Форматирование строк
    a_str = Fore.WHITE + 'Создано: ' + Back.WHITE + Fore.BLACK + f"{a:>4}" + Style.RESET_ALL + Fore.WHITE + ' (' + Fore.RED + str(a_b) + Fore.WHITE + ' + ' + Fore.GREEN + str(a_p) + Fore.WHITE + ')  '
    s_str = Fore.WHITE + 'Продано: ' + Back.GREEN + Fore.BLACK + f"{s:>4}" + Style.RESET_ALL + Fore.WHITE + ' (' + Fore.RED + str(s_b) + Fore.WHITE + ' + ' + Fore.GREEN + str(s_p) + Fore.WHITE + ')  '
    
    # Убираем цветовые коды для вычисления длины
    def clean_length(s):
        # Удаляем все ANSI-коды (цвета) из строки
        import re
        return len(re.sub(r'\x1b\[[0-9;]*m', '', s))
    
    # Вычисляем длину строк до "Ракет:" и "Коэф.:"
    a_length = clean_length(a_str)
    s_length = clean_length(s_str)
    
    # Определяем максимальную длину для выравнивания
    max_length = max(a_length, s_length)
    
    # Добавляем пробелы для выравнивания
    r_str = ' ' * (max_length - a_length) + 'Ракет: ' + Back.CYAN + Fore.BLACK + f"{r:>4}"
    k_str = ' ' * (max_length - s_length) + 'Коэф.: ' + Back.MAGENTA + f"{k:>4}"
    
    # Вывод
    print(a_str + r_str)
    print(s_str + k_str)
#    print(f'{Fore.WHITE}Первые 100 лотов: {Fore.RED}{bot_count}{Fore.WHITE} / {Fore.GREEN}{seller_count}')

    # Рассчитываем длину разделителя
    separator_length = 24  # Базовая длина разделителя
    if display_emojis:
        separator_length += 12  # Добавляем длину поля для эмодзи
    if display_count:
        separator_length += 3  # Добавляем длину поля для количества повышений
    separator = "-" * separator_length
    print(separator)  # Вывод разделителя


# Часть 8: Обработка данных о лотах (добавление новых лотов, проверка изменений и продаж) #
    # Инициализация переменной для подсчета количества лотов, которые обрабатываются
    counter = 0

    # Открываем файл с историей продаж для чтения последних 100 строк
    folder_path = create_monthly_folder()
    file_path = f"{folder_path}/sales_{trafficTypeFile}_{volume}_{str(cost).replace('.0', '')}.txt"
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()[-100:] # Чтение последних 100 строк из файла

    # Извлекаем имена продавцов из строк файла, если строка содержит статус "✅" (продавец), "❌" (бот) или "🙂" (мой)
    names = [line.strip().split("Лот: ")[0] for line in lines if '✅' in line or '❌' in line or '🙂' in line]
    names_reversed = list(reversed(names)) # Разворачиваем список

    # Получаем и обрабатываем данные с сервера
    try:
        for index, item in enumerate(data["data"][:max_lines]):  # Обрабатываем только первые max_lines лотов
            seller = item.get("seller", {}) # Извлекаем информацию о продавце
            name = seller.get("name") # Имя продавца
            emojis = seller.get("emojis") # Эмодзи продавца
            trafficType = item.get("trafficType") # Тип трафика (например, "data", "voice", "sms")
            id = item.get("id")
            my = item.get("my") # Флаг, указывающий бот это или продавец (True - бот, False - продавец)

#            # Функция для дополнения эмодзи до 3
#            def format_emojis(emojis):
#                # Заменяем оригинальные эмодзи на кастомные, а отсутствующие — на \u3000
#                custom_emojis_list = [custom_emojis.get(emoji, "\u3000") for emoji in emojis]
#                while len(custom_emojis_list) < 3:  # Если эмодзи меньше 3, добавляем широкие пробелы в начало
#                    custom_emojis_list.insert(0, "\u3000")  # Широкий пробел Unicode
#                return " ".join(custom_emojis_list[:3]) # Возвращаем строку с 3 эмодзи

            original_emojis = emojis[:]  # Оригинальные эмодзи с сервера
            formatted_emojis = format_emojis(original_emojis)  # Форматируем эмодзи

            # Если имя продавца отсутствует, заменяем его на "Анонимный продавец"
            name = "Анонимный продавец" if name is None else name

            # Определяем цвет для имени и эмодзи в зависимости от того, кто добавил лот (продавец или бот)
            if my is False:  # Если лот не бот
                if str(id) == str(highlight_id):
                    name = Fore.MAGENTA + str(name)
                    emojis = Fore.MAGENTA + f"[{formatted_emojis}]"
                elif name in my_names and f"[{' '.join(original_emojis)}]" in my_emojis:  # Пурпурный для my_names + my_emojis
                    name = Fore.MAGENTA + str(name)
                    emojis = Fore.MAGENTA + f"[{formatted_emojis}]"
                else:  # Зелёный для продавца
                    name = Fore.GREEN + str(name)
                    emojis = Fore.GREEN + f"[{formatted_emojis}]"
            else:  # Красный для бота
                name = Fore.RED + str(name)
                emojis = Fore.RED + f"[{formatted_emojis}]"

            # Увеличиваем счётчик лотов
            counter += 1

            seller_id = item.get("id") # Извлекаем ID лота
            count = raise_count.get(seller_id) # Получаем количество повышений для данного лота
            if not count:
                count = 0 # Если для этого лота нет записей о повышениях, устанавливаем счётчик в 0

            # Печать информации о лоте         
            if counter <= len(names):
                # Если позиция лота < или = количеству имен в файле, выводим позицию, имя, эмодзи и количество повышений + список проданных лотов из файла
                format_string = "{:<3} {:<24}"  # Базовая форматная строка
                print_items = [counter, name]
                if display_emojis:
                    format_string += " {:<13}"
                    print_items.append(emojis)
                if display_count:
                    format_string += " {:<3}"
                    print_items.append(count*5)
                if display_history:
                    format_string += " {}"
                    print_items.append(Fore.WHITE + str(names_reversed[counter - 1]))
                print(format_string.format(*print_items))
            else:
                # Если позиция лота больше количества имён, просто выводим имя, эмодзи и количество повышений
                format_string = "{:<3} {:<24}"  # Базовая форматная строка
                print_items = [counter, name]
                if display_emojis:
                    format_string += " {:<13}"
                    print_items.append(emojis)
                if display_count:
                    format_string += " {:<3}"
                    print_items.append(count*5)
                print(format_string.format(*print_items))
                
        # Создаем список для хранения выделенных лотов
        highlighted_lots = []
        
        # Проверяем каждый лот в selection_array
        for index, item in enumerate(selection_array):
            name = item[0]
            emojis = item[1]
            id = item[2]
            my = item[3]
        
            # Проверяем, соответствует ли лот условиям для выделения
            if (str(id) == str(highlight_id)) or (name in my_names and f"[{' '.join(emojis)}]" in my_emojis):
                if max_lines <= index < depth:  # Проверяем позицию лота
                    # Форматируем имя и эмодзи для выделенного лота
                    formatted_emojis = format_emojis(emojis)
                    name = Fore.MAGENTA + str(name)
                    emojis = Fore.MAGENTA + f"[{formatted_emojis}]"
                    
                    # Добавляем лот в список выделенных лотов
                    highlighted_lots.append((index + 1, name, emojis, raise_count.get(id, 0) * 5))
        
        # Если есть выделенные лоты, выводим их в отдельной секции
        if highlighted_lots:
            print(separator)
            
            # Выводим информацию о каждом выделенном лоте
            for pos, name, emojis, count in highlighted_lots:
                format_string = "{:<3} {:<24}"  # Базовая форматная строка
                print_items = [pos, name]
                if display_emojis:
                    format_string += " {:<13}"
                    print_items.append(emojis)
                if display_count:
                    format_string += " {:<3}"
                    print_items.append(count)
                print(format_string.format(*print_items))

    except KeyError:
        # Обработка исключения, если отсутствуют какие-либо данные
        print(Fore.YELLOW + "Произошла ошибка при обработке данных.")
        pass
    print(separator)  # Вывод разделителя

    # Попытка получить актуальные данные о лотах с сервера
    try:
        response = requests.get(f"https://t2.ru/api/exchange/lots?trafficType={trafficType}&volume={volume}&cost={cost}&limit=300", headers=headers, timeout=5) ####### limit=300 по-умолчанию #######
        data = response.json() # Преобразуем полученные данные в формат JSON

    except (JSONDecodeError, ConnectionError, requests.exceptions.ReadTimeout):
        # Обработка ошибок, если не удалось получить или обработать данные
        print(Fore.YELLOW + 'Потеряно соединение с сервером')
        time.sleep(10) # Пауза перед следующим запросом
        continue


# Часть 9: Обработка новых лотов и их запись #
    # Получаем и обрабатываем новые лоты
    new_elements = []
    selection_array = []
    for item in reversed(data["data"]):
        seller = item.get("seller", {})
        name = seller.get("name")
        emojis = seller.get("emojis")
        id = item.get("id")
        my = item.get("my")
        # Если имя продавца None, то помечаем как "Анонимный продавец"
        seller_list = ["Анонимный продавец", emojis, str(id), str(my)] if name is None else [name, emojis, str(id), str(my)]

        # Добавляем нового продавца в массив selection_array
        selection_array.insert(0, seller_list)

        # Проверяем, есть ли уже такой лот в списке sellers_array (если нет — добавляем)
        if seller_list[-2] not in [element[-2] for element in sellers_array]:
            new_elements.insert(0, seller_list) # Добавляем новый элемент в массив
            a += 1 # Увеличиваем счетчик добавленных лотов
            sellers_array.insert(0, seller_list) # Добавляем лот в общий список
            timestamps.insert(0, time.time()) # Добавляем временную метку для нового лота

            # Увеличиваем счётчик для ботов или продавцов в зависимости от значения my
            value = seller_list[-1]
            if value == 'True':
                a_b += 1 # Лот добавлен ботом
            elif value == 'False':
                a_p += 1 # Лот добавлен продавцом
        else:
            # Если лот уже есть, проверяем, нужно ли обновить его информацию
            for i, element in enumerate(sellers_array):
                if element[-2] == seller_list[-2] and element[0] != seller_list[0]:
                    sellers_array[i] = seller_list # Обновляем информацию о лоте
                    break


# Часть 10: Вывод новых лотов и их статус #
    # Функция для определения правильных окончаний в заголовках информационных сообщений
    def get_lot_ending(count, header_type=None):
        if count % 10 == 1 and count % 100 != 11:
            if header_type == "sold":
                return "Продан", "лот"
            elif header_type == "expired":
                return "Сгорел", "лот"
            elif header_type == "changed":
                return "Стоимость", "-го лота изменена"
            elif header_type == "raise":
                return "Поднят в топ", "лот"
            else:
                return "Создан", "лот"
        elif count % 10 in [2, 3, 4] and not (count % 100 in [12, 13, 14]):
            if header_type == "sold":
                return "Продано", "лота"
            elif header_type == "expired":
                return "Сгорело", "лота"
            elif header_type == "changed":
                return "Стоимость", "-х лотов изменена"
            elif header_type == "raise":
                return "Поднято в топ", "лота"
            else:
                return "Создано", "лота"
        else:
            if header_type == "sold":
                return "Продано", "лотов"
            elif header_type == "expired":
                return "Сгорело", "лотов"
            elif header_type == "changed":
                return "Стоимость", "-ти лотов изменена"
            elif header_type == "raise":
                return "Поднято в топ", "лотов"
            else:
                return "Создано", "лотов"
    # Если добавлены новые элементы, выводим их на экран
    if len(new_elements) > 0:
        # Определяем количество добавленных лотов
        count_added = len(new_elements)
        added_ending, lot_ending = get_lot_ending(count_added)  # Получаем правильные окончания
        # Формируем заголовок
        print(f"{Back.WHITE}{Fore.BLACK}{added_ending} {count_added} {lot_ending}{Style.RESET_ALL} (➕)")
        if info_lots:
            for element in new_elements:

#                # Функция для замены оригинальных эмодзи на кастомные
#                def format_emojis(emojis):
#                    # Заменяем оригинальные эмодзи на кастомные, а отсутствующие — на \u3000
#                    custom_emojis_list = [custom_emojis.get(emoji, "\u3000") for emoji in emojis]
#                    while len(custom_emojis_list) < 3:  # Если эмодзи меньше 3, добавляем широкие пробелы в начало
#                        custom_emojis_list.insert(0, "\u3000")  # Широкий пробел Unicode
#                    return " ".join(custom_emojis_list[:3])  # Возвращаем строку с 3 эмодзи

                # Если лот добавлен ботом, выводим его красным, если продавцом — зеленым
                if element[-1] == 'True':
                    formatted_emojis = format_emojis(element[1])  # Форматируем эмодзи
                    print(f"  {'+'} {Fore.RED}{str(element[0]):<19} [{formatted_emojis}]")  # Используем замененные эмодзи
                else:
                    formatted_emojis = format_emojis(element[1])  # Форматируем эмодзи
                    print(f"  {'+'} {Fore.GREEN}{str(element[0]):<19} [{formatted_emojis}]")
            print()


# Часть 11: Запись в файл #
    # Открываем файл для записи информации о лотах
    folder_path = create_monthly_folder()
    file_path = f"{folder_path}/sales_{trafficTypeFile}_{volume}_{str(cost).replace('.0', '')}.txt"
    with open(file_path, "a", encoding="utf-8") as f:
        # Записываем данные о лотах
        expired_lots = []  # Список сгоревших лотов
        sold_lots = []  # Список проданных лотов
        price_changed_lots = []  # Список лотов с измененной стоимостью
        sold_ids = set()  # Множество для отслеживания проданных лотов

        for element in sellers_array[:depth]:  # Глубина проверки лотов
            id = element[-2]
            if id not in [element[-2] for element in selection_array]:
                # Если лот из selection_array не найден в sellers_array, это новый лот
                pos = sellers_array.index(element) - len(new_elements) + 1
                timestamp_index = [element[-2] for element in sellers_array].index(id)
                timestamp = timestamps[timestamp_index]
                count = raise_count.get(id)
                if not count:
                    count = 0  # Если не найдено количество повышений, ставим 0

                # Заменяем эмодзи
                emojis = element[1][:]  # Создаем копию списка эмодзи
                for j in range(len(emojis)):
                    emojis[j] = custom_emojis.get(emojis[j], "\u3000")  # Заменяем эмодзи, если он есть в словаре, иначе используем длинный пробел
                while len(emojis) < 3:
                    emojis.insert(0, "\u3000")

                # Если лот был БОТОМ и не был продан в течение последнего часа, выводим информацию о нем
                if (element[-1] == 'True' and 0 <= time.time() - timestamp <= 3600):  # Лот продан
                    if id not in sold_ids:  # Проверяем, был ли лот уже продан
                        sold_lots.append((pos, Fore.RED + str(element[0]), f" [{' '.join(emojis)}]"))
                        f.write('{} '.format(datetime.datetime.now().strftime("%d.%m.%y %H:%M")) + '❌ ' + str(element[0]) + ' (' + str(pos) + ')' + "\n")
                        sold_ids.add(id)  # Добавляем идентификатор в множество
                        s_b += 1  # Увеличиваем счётчики проданных лотов ботами
                        s += 1  # Увеличиваем общее количество проданных лотов
                elif (element[-1] == 'True' and time.time() - timestamp > 3600):
                    # Если лот был добавлен более часа назад, но не был продан, выводим, что он "сгорел"
                    expired_lots.append((pos, Fore.RED + str(element[0]), f" [{' '.join(emojis)}]"))  # v13
                elif element[-1] == 'False':  # Если лот был добавлен продавцом
                    # Проверяем изменения стоимости лота, если она была изменена
                    result, cost_change = check(id)
                    if not result:  # Лот продан
                        if id not in sold_ids:  # Проверяем, был ли лот уже продан
                            # Проверяем, выделен ли лот с помощью Magenta
                            if str(id) == str(highlight_id) or (element[0] in my_names and f"[{' '.join(element[1])}]" in my_emojis):
                                sold_lots.append((pos, Fore.MAGENTA + str(element[0]), f" [{' '.join(emojis)}]"))
                                f.write('{} '.format(datetime.datetime.now().strftime("%d.%m.%y %H:%M")) + '🙂 ' + str(element[0]) + ' (' + str(pos) + ')' + "\n")  # Запись в файл с 🙂
                            else:
                                sold_lots.append((pos, Fore.GREEN + str(element[0]), f" [{' '.join(emojis)}]"))
                                f.write('{} '.format(datetime.datetime.now().strftime("%d.%m.%y %H:%M")) + '✅ ' + str(element[0]) + ' (' + str(pos) + ')' + "\n")  # Запись в файл с ✅
                            sold_ids.add(id)  # Добавляем идентификатор в множество
                            s_p += 1  # Увеличиваем счётчики проданных лотов продавцами
                            s += 1  # Увеличиваем общее количество проданных лотов
                    else:  # Стоимость изменена
                        price_changed_lots.append((pos, Fore.GREEN + str(element[0]), f" [{' '.join(emojis)}]", Fore.WHITE + str(cost_change).replace('.0', ' ₽')))

                # Удаляем обработанный лот из sellers_array и удаляем его временную метку
                sellers_array.remove(element)
                timestamps.pop(timestamp_index)
                r_r += 1

    # Вывод информации о лотах
    if sold_lots:
        count_sold = len(sold_lots)  # Определяем количество проданных лотов
        added_ending, lot_ending = get_lot_ending(count_sold, "sold")  # Получаем правильное окончание
        print(f'{Back.GREEN}{Fore.BLACK}{added_ending} {count_sold} {lot_ending}{Style.RESET_ALL} (💲)')
        if info_lots:
            for pos, name, emojis in sold_lots:
                print(f'{pos:>3} {name:<24}{emojis}')
            print()

    if expired_lots:
        count_expired = len(expired_lots)  # Определяем количество сгоревших лотов
        added_ending, lot_ending = get_lot_ending(count_expired, "expired")  # Получаем правильное окончание
        print(f'{Back.RED}{added_ending} {count_expired} {lot_ending}{Style.RESET_ALL} (🔥)')
        if info_lots:
            for pos, name, emojis in expired_lots:
                print(f'{pos:>3} {name:<24}{emojis}')
            print()

    if price_changed_lots:
        count_changed = len(price_changed_lots)  # Определяем количество измененных лотов
        added_ending, lot_ending = get_lot_ending(count_changed, "changed")  # Получаем правильное окончание
        print(f'{Back.YELLOW}{Fore.BLACK}{added_ending} {count_changed}{lot_ending}{Style.RESET_ALL} (✏️)')
        if info_lots:
            for pos, name, emojis, cost_change in price_changed_lots:
                print(f'{pos:>3} {name:<24}{emojis}{Fore.WHITE} на {cost_change}')
            print()


# Часть 12: Перемещение лотов и обработка «ракет» #
    # Перемещаем лоты в случае их изменения или повышения
    raise_lots = []  # Список для хранения информации о повышениях
    for element in selection_array[:15]: # Проверяем только первые 15 лотов

        # Заменяем эмодзи
        emojis = element[1][:]  # Создаем копию списка эмодзи
        for j in range(len(emojis)):
            emojis[j] = custom_emojis.get(emojis[j], "\u3000")  # Заменяем эмодзи, если он есть в словаре, иначе используем длинный пробел
        while len(emojis) < 3:
            emojis.insert(0, "\u3000")

        if element in sellers_array and sellers_array.index(element) - selection_array.index(element) > r_r:
            r += 1 # Увеличиваем счётчик ракет
            old_index = sellers_array.index(element)
            new_index = selection_array.index(element)
            sellers_array.remove(element) # Убираем лот из старой позиции
            sellers_array.insert(new_index, element) # Вставляем лот в новую позицию
            value_to_move = timestamps.pop(old_index)
            timestamps.insert(new_index, value_to_move) # Перемещаем временную метку

            # Если лот был добавлен продавцом, увеличиваем счётчик повышения
            if element[-1] == 'False':
                seller_id = element[2]
                if seller_id not in raise_count:
                    raise_count[seller_id] = 0
                raise_count[seller_id] += 1
                count = raise_count.get(seller_id)                
                raise_lots.append((Fore.GREEN + str(element[0]), f"[{' '.join(emojis)}]", old_index + 1, new_index + 1))  # Добавляем информацию о повышении

    # Вывод информации о повышениях
    if raise_lots:
        count_raise = len(raise_lots)  # Определяем количество измененных лотов
        added_ending, lot_ending = get_lot_ending(count_raise, "raise")  # Получаем правильное окончание
        print(f'{Back.CYAN}{Fore.BLACK}{added_ending} {count_raise} {lot_ending}{Style.RESET_ALL} (🚀)')
        if info_lots:
            for name, emojis, old_pos, new_pos in raise_lots:
                print(f'  {"\u25B2"} {name:<24} {emojis} {Fore.WHITE}{Style.DIM}{old_pos:>4} {Style.RESET_ALL}> {Style.BRIGHT}{new_pos}')  # Вывод информации о повышении


# Часть 13: Ограничение размера списка лотов и пауза #
    # Ограничиваем количество лотов в sellers_array, чтобы избежать переполнения
    sellers_array = sellers_array[:30000]
    timestamps = timestamps [:30000]
    cached_data = None # Очищаем кэшированные данные для следующего запроса
    r_r = 1 # Сброс счётчика ракет

    # Пауза перед следующим циклом
    time.sleep(delay)
