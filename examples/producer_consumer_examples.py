#!/usr/bin/env python3
"""
Базовые примеры Producer/Consumer для Kafka
"""

import json
import time
import os
from confluent_kafka import Producer, Consumer

# Конфигурация Kafka
KAFKA_CONFIG = {
    "bootstrap.servers": "89.169.152.54:9092",
    "client.id": "etl-examples"
}

def send_test_data():
    """Производитель: отправка тестовых данных в Kafka"""
    producer = Producer(KAFKA_CONFIG)
    
    # Тестовые данные WB keywords
    test_data = [
        {
            "date": "2024-01-01", 
            "campaign_id": 12345, 
            "keyword": "трикотаж мужской",
            "impressions": 1000, 
            "clicks": 50, 
            "cost": 250.75
        },
        {
            "date": "2024-01-02",
            "campaign_id": 12346, 
            "keyword": "футболка хлопок",
            "impressions": 1500, 
            "clicks": 75, 
            "cost": 350.25
        },
        {
            "date": "2024-01-03",
            "campaign_id": 12347, 
            "keyword": "рубашка деловая",
            "impressions": 800, 
            "clicks": 40, 
            "cost": 200.00
        }
    ]
    
    try:
        for data in test_data:
            message = json.dumps(data)
            producer.produce(
                "wb_keywords",
                message.encode('utf-8'),
                callback=lambda err, msg: print(f"Delivered: {msg.topic()} at {msg.partition()}:{msg.offset()}") if not err else print(f"Failed: {err}")
            )
            print(f"📤 Отправлено: {data['keyword']}")
        
        producer.flush()
        print(f"✅ Всего отправлено: {len(test_data)} сообщений")
        
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")

def consume_to_console():
    """Консьюмер: чтение данных из Kafka и вывод в консоль"""
    consumer_config = {
        "bootstrap.servers": KAFKA_CONFIG["bootstrap.servers"],
        "group.id": f"console-consumer-{int(time.time())}",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True
    }
    
    consumer = Consumer(consumer_config)
    consumer.subscribe(["wb_keywords"])
    
    try:
        print("👂 Ожидание сообщений (Ctrl+C для выхода)...")
        
        while True:
            msg = consumer.poll(timeout=1.0)
            
            if msg is None:
                continue
            
            if msg.error():
                print(f"❌ Ошибка: {msg.error()}")
                continue
            
            # Десериализация сообщения
            data = json.loads(msg.value().decode('utf-8'))
            
            print(f"📨 Получено:")
            print(f"   Дата: {data.get('date')}")
            print(f"   Кампания: {data.get('campaign_id')}")
            print(f"   Ключевое слово: {data.get('keyword')}")
            print(f"   Показы: {data.get('impressions')}")
            print(f"   Клики: {data.get('clicks')}")
            print(f"   Стоимость: {data.get('cost')}")
            print("-" * 40)
            
    except KeyboardInterrupt:
        print("\n🛑 Остановка консьюмера...")
    finally:
        consumer.close()

def consume_to_clickhouse():
    """Консьюмер: чтение из Kafka и запись в ClickHouse"""
    from clickhouse_driver import Client
    
    # ClickHouse клиент
    ch_config = {
        "host": "rc1a-ioasjmp8oohqnaeo.mdb.yandexcloud.net",
        "port": 9440,
        "user": "databaseuser",
        "password": os.getenv("CLICKHOUSE_PASSWORD"),  # Из .env файла
        "database": "best-tricotaz-analytics",
        "secure": True,
        "verify": True
    }
    
    try:
        ch = Client(**ch_config)
        print("🔗 Подключение к ClickHouse: OK")
    except Exception as e:
        print(f"❌ Ошибка подключения к ClickHouse: {e}")
        return
    
    # Kafka консьюмер
    consumer_config = {
        "bootstrap.servers": KAFKA_CONFIG["bootstrap.servers"],
        "group.id": f"clickhouse-consumer-{int(time.time())}",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False  # Ручное управление offset
    }
    
    consumer = Consumer(consumer_config)
    consumer.subscribe(["wb_keywords"])
    
    try:
        print("👂 Ожидание сообщений для ClickHouse...")
        count = 0
        deadline = time.time() + 30  # Таймаут 30 секунд
        
        while time.time() < deadline:
            msg = consumer.poll(timeout=1.0)
            
            if msg is None:
                continue
            
            if msg.error():
                print(f"❌ Ошибка Kafka: {msg.error()}")
                continue
            
            # Получение JSON данных
            json_data = msg.value().decode('utf-8')
            data = json.loads(json_data)
            
            # Проверка валидности JSON
            if not json_data or json_data.strip() == '':
                print("⚠️ Пропуск пустого сообщения")
                continue
            
            try:
                # Вставка в ClickHouse (raw таблица)
                ch.execute(
                    "INSERT INTO wb_keywords_raw (payload) VALUES",
                    [[json_data]]
                )
                count += 1
                print(f"💾 Вставлено в ClickHouse: {data.get('keyword', 'unknown')}")
                
                # Commit offset для Kafka
                consumer.commit(msg)
                
            except Exception as e:
                print(f"❌ Ошибка вставки в ClickHouse: {e}")
        
        print(f"✅ Всего обработано: {count} сообщений")
        
    except KeyboardInterrupt:
        print("\n🛑 Остановка консьюмера...")
    finally:
        consumer.close()

def check_clickhouse_raw_data():
    """Проверка данных в ClickHouse raw таблице"""
    from clickhouse_driver import Client
    
    ch_config = {
        "host": "rc1a-ioasjmp8oohqnaeo.mdb.yandexcloud.net",
        "port": 9440,
        "user": "databaseuser",
        "password": os.getenv("CLICKHOUSE_PASSWORD"),
        "database": "best-tricotaz-analytics",
        "secure": True,
        "verify": True
    }
    
    try:
        ch = Client(**ch_config)
        
        # Количество записей
        count_result = ch.execute("SELECT count() FROM wb_keywords_raw")
        count = count_result[0][0]
        print(f"📊 Всего записей в raw таблице: {count}")
        
        if count > 0:
            # Последние записи
            recent_data = ch.execute("""
                SELECT 
                    toString(payload) as json_data,
                    length(payload) as data_length
                FROM wb_keywords_raw 
                ORDER BY tuple() 
                LIMIT 5
            """)
            
            print(f"\n📋 Последние {len(recent_data)} записей:")
            for i, (json_data, data_length) in enumerate(recent_data, 1):
                try:
                    data = json.loads(json_data)
                    keyword = data.get('keyword', 'N/A')
                    date = data.get('date', 'N/A')
                    print(f"  {i}. {date} | {keyword} | размер: {data_length}")
                except:
                    print(f"  {i}. Невалидный JSON | размер: {data_length}")
        
    except Exception as e:
        print(f"❌ Ошибка проверки ClickHouse: {e}")

if __name__ == "__main__":
    import sys
    
    command = sys.argv[1] if len(sys.argv) > 1 else "help"
    
    if command == "send":
        send_test_data()
    elif command == "console":
        consume_to_console()
    elif command == "clickhouse":
        consume_to_clickhouse()
    elif command == "check":
        check_clickhouse_raw_data()
    else:
        print("""
🔧 Примеры использования Kafka Producer/Consumer

Команды:
  python examples/producer_consumer_examples.py send      # Отправить тестовые данные
  python examples/producer_consumer_examples.py console   # Чтение в консоль
  python examples/producer_consumer_examples.py clickhouse # Чтение в ClickHouse
  python examples/producer_consumer_examples.py check     # Проверить данные в ClickHouse

Требования:
  - Настроенные переменные окружения (.env файл)
  - Установленные модули: confluent_kafka, clickhouse_driver
  - Работающий Kafka на 89.169.152.54:9092
  - Доступ к ClickHouse на Yandex Cloud
        """)
