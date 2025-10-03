#!/usr/bin/env python3
"""
Тестирование dbt моделей и проверка результатов трансформации
"""

import json
import subprocess
import os
from clickhouse_driver import Client

def get_clickhouse_client():
    """Получение ClickHouse клиента"""
    config = {
        "host": "rc1a-ioasjmp8oohqnaeo.mdb.yandexcloud.net",
        "port": 9440,
        "user": "databaseuser",
        "password": os.getenv("CLICKHOUSE_PASSWORD"),
        "database": "best-tricotaz-analytics",
        "secure": True,
        "verify": True
    }
    
    try:
        return Client(**config)
    except Exception as e:
        print(f"❌ Ошибка подключения к ClickHouse: {e}")
        return None

def check_raw_data():
    """Проверка данных в raw таблицах"""
    ch = get_clickhouse_client()
    if not ch:
        return
    
    print("🔍 ПРОВЕРКА RAW ДАННЫХ")
    print("=" * 50)
    
    tables = ["wb_keywords_raw", "wb_campaigns_raw", "ozon_products_raw", "onec_entities_raw"]
    
    for table in tables:
        try:
            result = ch.execute(f"SELECT count() FROM {table}")
            count = result[0][0]
            print(f"📊 {table}: {count} записей")
            
            if count > 0:
                # Примеры данных (максимум 2)
                samples = ch.execute(f"SELECT payload FROM {table} LIMIT 2")
                for i, (payload,) in enumerate(samples, 1):
                    try:
                        data = json.loads(payload)
                        if 'keyword' in data:
                            print(f"  📝 Пример {i}: {data.get('keyword', 'N/A')}")
                        elif 'name' in data:
                            print(f"  📝 Пример {i}: {data.get('name', 'N/A')}")
                        elif 'entity' in data:
                            print(f"  📝 Пример {i}: {data.get('entity', 'N/A')}")
                        else:
                            print(f"  📝 Пример {i}: {json.dumps(data)[:50]}...")
                    except Exception as e:
                        print(f"  ❌ Пример {i}: ошибка чтения JSON: {e}")
                        print(f"      Payload: {payload[:100]}...")
        
        except Exception as e:
            print(f"❌ {table}: таблица не существует или ошибка - {e}")
    
    print()

def run_dbt_fresh():
    """Запуск dbt с полным обновлением"""
    print("🔄 ЗАПУСК DBT МОДЕЛЕЙ")
    print("=" * 50)
    
    try:
        # Переходим в директорию dbt проекта
        os.chdir("/home/vasiliy_arsenov/etl/dbt/best_tricotaz")
        
        # Полное обновление staging моделей
        print("📝 Запуск staging моделей...")
        result = subprocess.run(
            ["dbt", "run", "--select", "staging", "--full-refresh"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            print("✅ dbt staging модели выполнены успешно")
            print("📄 Результат:")
            print(result.stdout)
        else:
            print("❌ Ошибка выполнения dbt:")
            print(result.stderr)
            
    except subprocess.TimeoutExpired:
        print("⏰ Таймаут выполнения dbt (120 сек)")
    except Exception as e:
        print(f"❌ Ошибка запуска dbt: {e}")

def check_staging_data():
    """Проверка данных в staging таблицах"""
    ch = get_clickhouse_client()
    if not ch:
        return
    
    print("\n🔍 ПРОВЕРКА STAGING ДАННЫХ")
    print("=" * 50)
    
    staging_tables = ["stg_wb_keywords"]
    
    for table in staging_tables:
        try:
            # Общее количество
            result = ch.execute(f"SELECT count() FROM {table}")
            count = result[0][0]
            print(f"📊 {table}: {count} записей")
            
            if count > 0:
                # Структурированные данные
                result = ch.execute(f"""
                    SELECT 
                        date,
                        campaignid,
                        keyword,
                        impressions,
                        clicks,
                        cost,
                        _ingested_at
                    FROM {table}
                    ORDER BY date DESC
                    LIMIT 5
                """)
                
                print(f"📋 Последние записи:")
                for row in result:
                    date, campaign_id, keyword, impressions, clicks, cost, ingested_at = row
                    print(f"  📅 {date} | 🆔 {campaign_id} | 🔑 {keyword}")
                    print(f"       👆 {impressions} показов | 👆 {clicks} кликов | 💰 {cost} руб.")
                    print(f"       ⏰ Загружено: {ingested_at}")
                    print("-" * 60)
            
        except Exception as e:
            print(f"❌ {table}: ошибка - {e}")

def test_json_parsing():
    """Тестирование парсинга JSON в ClickHouse"""
    ch = get_clickhouse_client()
    if not ch:
        return
    
    print("\n🧪 ТЕСТИРОВАНИЕ ПАРСИНГА JSON")
    print("=" * 50)
    
    try:
        # Тест на raw данных
        result = ch.execute("""
            SELECT 
                payload,
                JSON_VALUE(payload, '$.date') as parsed_date,
                JSON_VALUE(payload, '$.keyword') as parsed_keyword,
                JSON_VALUE(payload, '$.impressions') as parsed_impressions,
                isValidJSON(payload) as is_valid_json
            FROM wb_keywords_raw 
            LIMIT 3
        """)
        
        print("📋 Тест парсинга JSON:")
        for payload, parsed_date, parsed_keyword, parsed_impressions, is_valid in result:
            print(f"  📄 Payload: {payload[:50]}...")
            print(f"  📅 Parsed date: {parsed_date}")
            print(f"  🔑 Parsed keyword: {parsed_keyword}")
            print(f"  👆 Parsed impressions: {parsed_impressions}")
            print(f"  ✅ Valid JSON: {bool(is_valid)}")
            print("-" * 40)
    
    except Exception as e:
        print(f"❌ Ошибка тестирования JSON: {e}")

def full_pipeline_test():
    """Полный тест пайплайна: raw → staging → проверка"""
    print("🚀 ПОЛНЫЙ ТЕСТ ПАЙПЛАЙНА")
    print("=" * 60)
    
    # 1. Проверка raw данных
    check_raw_data()
    
    # 2. Запуск dbt трансформации
    run_dbt_fresh()
    
    # 3. Проверка staging данных
    check_staging_data()
    
    # 4. Тест парсинга JSON
    test_json_parsing()
    
    print("\n🎉 ТЕСТ ПАЙПЛАЙНА ЗАВЕРШЕН!")
    print("Проверьте результаты выше для диагностики проблем.")

if __name__ == "__main__":
    import sys
    
    command = sys.argv[1] if len(sys.argv) > 1 else "full"
    
    if command == "raw":
        check_raw_data()
    elif command == "dbt":
        run_dbt_fresh()
    elif command == "staging":
        check_staging_data()
    elif command == "json":
        test_json_parsing()
    elif command == "full":
        full_pipeline_test()
    else:
        print("""
🧪 Тестирование dbt и ClickHouse пайплайна

Команды:
  python examples/dbt_testing.py full      # Полный тест пайплайна
  python examples/dbt_testing.py raw       # Проверка raw таблиц
  python examples/dbt_testing.py dbt       # Запуск dbt моделей
  python examples/dbt_testing.py staging   # Проверка staging таблиц
  python examples/dbt_testing.py json      # Тест парсинга JSON

Требования:
  - Установленный dbt-clickhouse
  - Настроенный dbt проект в ~/etl/dbt/best_tricotaz/
  - Доступ к ClickHouse на порту 9440
  - Переменная CLICKHOUSE_PASSWORD в окружении
        """)
