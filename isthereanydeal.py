import requests
import json
from datetime import datetime
from dotenv import load_dotenv
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # папка где лежит скрипт
ENV_PATH = os.path.join(".env")
load_dotenv(ENV_PATH)

# --- КОНФИГУРАЦИЯ ---
API_KEY = os.getenv("API_KEY")  # Замените на свой ключ!
COUNTRY = "RU"          # Код страны (ISO 3166-1 alpha-2)
SHOPS = "61,16,35"      # ID магазинов: 61=Steam, 62=Epic, 35=GOG
LIMIT = 10              # Количество сделок (1-200)
# --- КОНЕЦ КОНФИГУРАЦИИ ---

BASE_URL = "https://api.isthereanydeal.com"
HEADERS = {"User-Agent": "FreeGamesScript/1.0"}

def get_deals_list(limit=10, offset=0):
    """
    Получает список текущих сделок через эндпоинт /v01/deals/
    с правильными параметрами из документации
    """
    endpoint = f"{BASE_URL}/deals/v2"
    
    params = {
        "key": API_KEY,
        "country": COUNTRY,
        "offset": offset,
        "limit": limit,
        "sort": "price",           # Сортировка по низкой цене
        "nondeals": "false",       # Не включать неакционные цены
        "mature": "false",         # Не включать контент для взрослых
        "shops": SHOPS,            # ID магазинов через запятую
    }
    
    print("📡 Запрос к API с параметрами:")
    print(f"   URL: {endpoint}")
    print(f"   Страна: {COUNTRY}")
    print(f"   Магазины: {SHOPS}")
    print(f"   Лимит: {limit}")
    print(f"   Сортировка: по цене (от низкой к высокой)")
    
    try:
        response = requests.get(endpoint, headers=HEADERS, params=params)
        print(f"📊 Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            print("❌ Ошибка 401: Неверный API ключ")
            print("   Получите ключ на https://isthereanydeal.com/app/")
        elif response.status_code == 403:
            print("❌ Ошибка 403: Доступ запрещен")
        else:
            print(f"❌ Ошибка {response.status_code}: {response.text[:200]}")
        
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка соединения: {e}")
        return None

def analyze_deals(data):
    """
    Анализирует полученные сделки и фильтрует бесплатные игры
    """
    if not data or "list" not in data:
        print("❌ Некорректный формат ответа - отсутствует 'list'")
        return []
    
    deals = data["list"]
    print(f"\n📊 Получено сделок: {len(deals)}")
    
    free_games = []
    
    for i, deal in enumerate(deals, 1):
        # Извлекаем основные данные об игре
        title = deal.get("title", "Без названия")
        game_id = deal.get("id", "")
        slug = deal.get("slug", "")
        
        # Извлекаем данные о сделке
        deal_info = deal.get("deal", {})
        
        # Получаем информацию о магазине
        shop_info = deal_info.get("shop", {})
        shop_name = shop_info.get("name", "Неизвестно")
        shop_id = shop_info.get("id", 0)
        
        # Получаем информацию о цене
        price_info = deal_info.get("price", {})
        price_amount = price_info.get("amount", 1)  # По умолчанию 1, чтобы не попало в бесплатные
        
        regular_info = deal_info.get("regular", {})
        regular_amount = regular_info.get("amount", 0)
        
        # Получаем скидку
        cut = deal_info.get("cut", 0)
        
        # Получаем дату истечения
        expiry = deal_info.get("expiry")
        
        # Получаем ссылку на сделку
        deal_url = deal_info.get("url", "")
        
        print(f"\n{i}. {title}")
        print(f"   Магазин: {shop_name} (ID: {shop_id})")
        print(f"   Цена: ${price_amount}")
        print(f"   Обычная цена: ${regular_amount}")
        print(f"   Скидка: {cut}%")
        print(f"   Истекает: {expiry if expiry else 'Нет даты'}")
        
        # Критерии для фильтрации бесплатных раздач:
        # 1. Текущая цена = 0
        # 2. Обычная цена > 0 (чтобы исключить free-to-play)
        # 3. Скидка = 100% (опционально, но хороший индикатор)
        
        if price_amount == 0 and regular_amount > 0:
            if cut == 100:
                print(f"   🎁 БЕСПЛАТНАЯ РАЗДАЧА (скидка 100%)")
                tag = "бесплатная раздача"
            else:
                print(f"   ⚠️  Бесплатно, но скидка {cut}%")
                tag = "бесплатная акция"
            
            # Формируем структурированные данные о бесплатной игре
            free_game_data = {
                "title": title,
                "id": game_id,
                "slug": slug,
                "shop": {
                    "id": shop_id,
                    "name": shop_name
                },
                "price": {
                    "current": price_amount,
                    "regular": regular_amount,
                    "currency": price_info.get("currency", "USD"),
                    "cut": cut
                },
                "expiry": expiry,
                "url": deal_url,
                "timestamp": deal_info.get("timestamp"),
                "assets": deal.get("assets", {}),
                "type": deal.get("type", "unknown"),
                "free_reason": tag
            }
            
            free_games.append(free_game_data)
    
    return free_games

def save_results(all_data, free_data, timestamp):
    """Сохраняет результаты в JSON файлы"""
    
    # Сохраняем полный ответ
    if all_data:
        filename = f"deals_full_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Полные данные сохранены в: {filename}")
    
    # Сохраняем бесплатные игры
    if free_data:
        filename = f"free_games_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(free_data, f, ensure_ascii=False, indent=2)
        print(f"💾 Бесплатные игры сохранены в: {filename}")

def main():
    print("=" * 50)
    print("ПОИСК БЕСПЛАТНЫХ ИГР - IsThereAnyDeal API")
    print("=" * 50)
    
    # Проверка API ключа
    if API_KEY == "ВАШ_КЛЮЧ_API_ЗДЕСЬ":
        print("\n❌ ОШИБКА: Вы не заменили API_KEY!")
        print("1. Зарегистрируйтесь на https://isthereanydeal.com")
        print("2. Перейдите в https://isthereanydeal.com/app/")
        print("3. Создайте приложение и получите API ключ")
        print("4. Вставьте ключ в переменную API_KEY")
        return
    
    # 1. Получаем сделки
    response_data = get_deals_list(limit=LIMIT, offset=0)
    
    if not response_data:
        print("\n❌ Не удалось получить данные от API")
        return
    
    # 2. Анализируем данные
    free_games = analyze_deals(response_data)
    
    print(f"\n{'='*50}")
    print(f"ИТОГО: найдено {len(free_games)} бесплатных игр.")
    
    # 3. Сохраняем результаты
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    save_results(response_data, free_games, timestamp)
    
    # 4. Выводим список найденных бесплатных игр
    if free_games:
        print("\n🎮 Найденные бесплатные игры:")
        for i, game in enumerate(free_games, 1):
            reason = game.get("free_reason", "бесплатно")
            print(f"{i}. {game.get('title')} в {game.get('shop', {}).get('name', '?')} ({reason})")

if __name__ == "__main__":
    main()