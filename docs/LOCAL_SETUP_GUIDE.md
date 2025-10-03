# Best Trikotazh Data - Локальная установка

## 📋 Описание проекта

**Best Trikotazh Data** - это ETL пайплайн для обработки данных о трикотаже из различных маркетплейсов и внутренних систем.

### Что делает система:
- **Сбор данных** с Wildberries, Ozon, 1C через API
- **Потоковая передача** через Apache Kafka
- **Аналитика** в ClickHouse с трансформацией dbt
- **Оркестрация** через Apache Airflow (запуск в 01:00)
- **Мониторинг** Prometheus + Grafana
- **Веб-интерфейс** FastAPI для управления

### Технологический стек:
- **Kafka KRaft 3.7.1** - брокер сообщений
- **Python 3.9+** - producers/consumers
- **ClickHouse** - аналитическая БД
- **Airflow** - планировщик задач
- **dbt** - трансформация данных
- **FastAPI** - веб-интерфейс
- **Prometheus/Grafana** - мониторинг

---

## 🚀 Быстрая локальная установка

### Вариант 1: Автоматическая установка на сервере

Если у вас есть Ubuntu сервер:
```bash
# Клонируйте репозиторий
git clone https://github.com/aiarsenov/best-trikotazh-data.git
cd best-trikotazh-data

# Запустите автоматический установщик
sudo bash provision/kafka-install.sh

# Система автоматически установит:
# - Apache Kafka KRaft 3.7.1
# - 5 топиков для разных источников данных
# - systemd сервис для автозапуска
# - Настройки firewall
```

### Вариант 2: Локальная разработка на macOS/Linux

#### Шаг 1: Подготовка окружения
```bash
# Клонируйте проект
git clone https://github.com/aiarsenov/best-trikotazh-data.git
cd best-trikotazh-data

# Создайте Python окружение
python3 -m venv venv
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
```

#### Шаг 2: Установка Docker для Kafka
```bash
# Если у вас Docker Desktop
docker run -d \
  --name kafka \
  -p 9092:9092 \
  -p 19092:19092 \
  -e KAFKA_NODE_ID=1 \
  -e KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT \
  -e KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:29092,PLAINTEXT_HOST://0.0.0.0:9092 \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092 \
  -e KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1 \
  -e KAFKA_TRANSACTION_STATE_LOG_MIN_ISR=1 \
  -e KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR=1 \
  confluentinc/cp-kafka:7.4.0

# Ждём запуска
sleep 30

# Создаём топики
docker exec kafka kafka-topics --bootstrap-server localhost:9092 \
  --create --topic wb-keywords --partitions 3 --replication-factor 1

docker exec kafka kafka-topics --bootstrap-server localhost:9092 \
  --create --topic wb-campaigns --partitions 3 --replication-factor 1

docker exec kafka kafka-topics --bootstrap-server localhost:9092 \
  --create --topic ozon-products --partitions 3 --replication-factor 1

docker exec kafka kafka-topics --bootstrap-server localhost:9092 \
  --create --topic onec-entities --partitions 3 --replication-factor 1

docker exec kafka kafka-topics --bootstrap-server localhost:9092 \
  --create --topic etl-logs --partitions 1 --replication-factor 1
```

#### Шаг 3: Проверка установки
```bash
# Проверяем, что есть топики
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# Тестируем отправку сообщения
echo "test message" | docker exec -i kafka kafka-console-producer --bootstrap-server localhost:9092 --topic wb-keywords

# Читаем сообщение
docker exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic wb-keywords --from-begin --timeout-ms 5000
```

#### Шаг 4: Python клиент
```bash
# Установка клиента Kafka
pip install kafka-python pandas requests clickhouse-connector
# Для подключения к Managed ClickHouse через нативный протокол используйте clickhouse-driver (порт 9440):
pip install clickhouse-driver

# Создайте тестовый файл test_kafka.py
cat > test_kafka.py << 'EOF'
from kafka import KafkaProducer, KafkaConsumer
import json
import time

# Настройка подключения
KAFKA_SERVER = 'localhost:9092'

# Producer
producer = KafkaProducer(
    bootstrap_servers=[KAFKA_SERVER],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Отправка тестового сообщения
producer.send('wb-keywords', value={
    'keyword': 'футболка мужская',
    'position': 1,
    'timestamp': '2025-01-01T00:00:00Z',
    'source': 'test'
})

producer.flush()
print("✅ Сообщение отправлено!")

# Consumer
consumer = KafkaConsumer(
    'wb-keywords',
    bootstrap_servers=[KAFKA_SERVER],
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='earliest'
)

# Чтение сообщений
print("📖 Чтение сообщений...")
for message in consumer:
    print(f"Получено: {message.value}")
    break

consumer.close()
producer.close()
print("✅ Тест завершён!")
EOF

# Запустите тест
python test_kafka.py
```

---

## 🏗️ Локальная разработка (docker-compose)

Создайте файл `docker-compose.yml`:

```yaml
version: '3.8'

services:
  kafka:
    image: confluentinc/cp-kafka:7.4.0
    container_name: kafka-local
    ports:
      - "9092:9092"
      - "19092:19092"
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_CONTROLLER_QUORUM_VOTERS: '1@kafka:19092'
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:29092,PLAINTEXT_HOST://0.0.0.0:9092
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_CONTROLLER_LISTENER_NAMES: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0
    volumes:
      - kafka-data:/var/lib/kafka/data

  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    container_name: kafka-ui
    ports:
      - "8080:8080"
    environment:
      KAFKA_CLUSTERS_0_NAME: local
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:29092
      KAFKA_CLUSTERS_0_ZOOKEEPER: ""
    depends_on:
      - kafka

  # Для полноценной разработки добавьте:
  # clickhouse:
  #   image: clickhouse/clickhouse-server:latest
  #   ports:
  #     - "8123:8123"
  #     - "9000:9000"

volumes:
  kafka-data:
```

### Запуск с docker-compose:
```bash
# Создайте docker-compose.yml и запустите
docker-compose up -d

# Создайте топики
docker exec kafka-local kafka-topics --bootstrap-server localhost:9092 \
  --create --topic wb-keywords --partitions 3 --replication-factor 1

docker exec kafka-local kafka-topics --bootstrap-server localhost:9092 \
  --create --topic wb-campaigns --partitions 3 --replication-factor 1

docker exec kafka-local kafka-topics --bootstrap-server localhost:9092 \
  --create --topic ozon-products --partitions 3 --replication-factor 1

docker exec kafka-local kafka-topics --bootstrap-server localhost:9092 \
  --create --topic onec-entities --partitions 3 --replication-factor 1

docker exec kafka-local kafka-topics --bootstrap-server localhost:9092 \
  --create --topic etl-logs --partitions 1 --replication-factor 1

# Откройте Kafka UI: http://localhost:8080
```

---

## 🛠️ Управление локальной установкой

### Docker команды:
```bash
# Просмотр топиков
docker exec kafka-local kafka-topics --bootstrap-server localhost:9092 --list

# Отправка сообщения
echo '{"keyword": "джинсы", "category": "одежда"}' | docker exec -i kafka-local kafka-console-producer --bootstrap-server localhost:9092 --topic wb-keywords

# Чтение сообщений
docker exec kafka-local kafka-console-consumer --bootstrap-server localhost:9092 --topic wb-keywords --from-beginning --timeout-ms 10000

# Остановка контейнеров
docker-compose down

# Пересоздание с нуля
docker-compose down -v
docker-compose up -d
```

### Python интеграция:
```python
# Подключение к локальному Kafka
from kafka import KafkaProducer
import json

# Для Docker/Kafka UI
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Отправка данных о продуктах
product_data = {
    'product_id': '12345',
    'name': 'Футболка с логотипом',
    'price': 599,
    'category': 'трикотаж',
    'source': 'wb',
    'timestamp': '2025-01-02T10:30:00Z'
}

producer.send('wb-keywords', value=product_data)
producer.flush()
```

---

## 🔧 Разработка Producers и Consumers

### Создание Producer:
```python
# wb_producer.py
import json
import requests
from kafka import KafkaProducer
import time

class WBProducer:
    def __init__(self, kafka_server='localhost:9092'):
        self.producer = KafkaProducer(
            bootstrap_servers=[kafka_server],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
    
    def fetch_keywords(self, api_token):
        # Здесь интеграция с Wildberries API
        headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            'https://suppliers-api.wildberries.ru/api/v1/keywords',
            headers=headers
        )
        
        for keyword_data in response.json()['data']:
            self.producer.send('wb-keywords', value=keyword_data)
        
        self.producer.flush()
        print(f"✅ Отправлено {len(response.json()['data'])} ключевых слов")

# Использование
if __name__ == "__main__":
    producer = WBProducer()
    # Замените на ваш токен API
    producer.fetch_keywords('your_wb_api_token')
```

### Создание Consumer:
```python
# etl_consumer.py
from kafka import KafkaConsumer
import json
import logging

class ETLConsumer:
    def __init__(self, kafka_server='localhost:9092'):
        self.consumer = KafkaConsumer(
            'wb-keywords',
            'wb-campaigns',
            'ozon-products',
            bootstrap_servers=[kafka_server],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id='etl-processors',
            auto_offset_reset='earliest'
        )
    
    def process_messages(self):
        for message in self.consumer:
            topic = message.topic
            data = message.value
            
            print(f"📊 Получено из {topic}: {data}")
            
            # Здесь будет логика обработки и сохранения в ClickHouse
            if topic == 'wb-keywords':
                self.process_keyword_data(data)
            elif topic == 'wb-campaigns':
                self.process_campaign_data(data)
    
    def process_keyword_data(self, data):
        # Обработка данных ключевых слов
        print(f"🔍 Обрабатываю ключевое слово: {data}")
    
    def process_campaign_data(self, data):
        # Обработка данных кампаний
        print(f"📈 Обрабатываю кампанию: {data}")

# Использование
if __name__ == "__main__":
    consumer = ETLConsumer()
    consumer.process_messages()
```

---

## 📊 Мониторинг локальной разработки

### Web UI доступы:
- **Kafka UI**: http://localhost:8080 (если используете docker-compose)
- **ClickHouse**: http://localhost:8123 (если добавите в docker-compose)

### Проверка состояния:
```bash
# Проверка логов Kafka
docker logs kafka-local

# Статистика по топикам
docker exec kafka-local kafka-consumer-groups --bootstrap-server localhost:9092 --describe --all-groups

# Использование диска
docker system df
```

---

## 🧪 Тестирование пайплайна на сервере

### ✅ Проверенный кейс: end-to-end поток данных

**Тест-сценарий**: Отправка данных в Kafka → Обработка в ClickHouse → Трансформация через dbt

1. **Отправка тестовых данных в Kafka:**
```bash
python3 - <<'PY'
from confluent_kafka import Producer
import json

p = Producer({"bootstrap.servers": "89.169.152.54:9092"})
test_data = [
    {"date": "2024-01-01", "campaign_id": 12345, "keyword": "тест", "impressions": 100, "clicks": 15, "cost": 50.5},
    {"date": "2024-01-02", "campaign_id": 12346, "keyword": "тест2", "impressions": 200, "clicks": 25, "cost": 75.0}
]
for msg in test_data:
    p.produce("wb_keywords", json.dumps(msg).encode('utf-8'))
p.flush()
print("✅ Данные отправлены в Kafka")
PY
```

2. **Consumer для ClickHouse:**
```bash
python3 - <<'PY'
from confluent_kafka import Consumer
from clickhouse_driver import Client
import time

# Kafka consumer
c = Consumer({"bootstrap.servers": "89.169.152.54:9092", "group.id": f"test_{int(time.time())}"})
c.subscribe(["wb_keywords"])

# ClickHouse client (важно: порт 9440 для TLS!)
ch = Client(
    host="rc1a-ioasjmp8oohqnaeo.mdb.yandexcloud.net",
    port=9440,  # ✅ Нативный TLS порт
    user="databaseuser", 
    password="YOUR_PASSWORD",
    database="best-tricotaz-analytics", 
    secure=True
)

# Обработка сообщений (timeout 15 сек)
deadline = time.time() + 15
count = 0
while time.time() < deadline:
    msg = c.poll(1.0)
    if msg and not msg.error():
        json_data = msg.value().decode('utf-8')
        # ✅ Правильный синтаксис для String колонки
        ch.execute("INSERT INTO wb_keywords_raw (payload) VALUES", [[json_data]])
        count += 1
        print(f"💾 Обработано {count} сообщений")

c.close()
print(f"✅ Консьюмер завершен. Всего: {count} сообщений")
PY
```

### ✅ Результат теста:
- **Raw данных**: 9 записей в ClickHouse
- **Staging данных**: 8 записей (dbt отфильтровал 1 некорректную)
- **Структурированные поля**: date, campaign_id, keyword, impressions, clicks, cost

## 🚀 Следующие шаги разработки

После успешной локальной установки:

1. **Создайте Producers** для каждого источника данных:
   - Wildberries API integration
   - Ozon API integration  
   - 1C API integration

2. **Настройте Consumers** для загрузки в хранилище:
   - ClickHouse batch loader
   - Error handling и dead letter queues
   - Data validation

3. **Дебюггинг и тестирование**:
   - Unit tests для producers/consumers
   - Integration tests с Kafka
   - Performance testing

4. **Подготовка к продакшену**:
   - Environment-specific configurations
   - Monitoring и alerting
   - Documentation и runbooks

---

## ❓ Частые вопросы

**Q: Как изменить порты Kafka?**
A: Измените порты в docker-compose.yml и пересоздайте контейнеры

**Q: Где хранятся данные Kafka?**
A: В Docker volume `kafka-data` (для macOS: ~/Library/Containers/com.docker.docker/Data/vms/0/data/docker/volumes/)

**Q: Как подключить реальные API?**
A: Получите токены доступа к API маркетплейсов и измените URL/headers в producers

**Q: Могу ли я разрабатывать без Docker?**
A: Да, установите Kafka локально или используйте cloud Kafkas (Upstash, Confluent Cloud)

**Q: Где взять примеры данных?**
A: Используйте публичные API эндпоинты маркетплейсов или создайте mock-данные для разработки

---

**📝 Примечание**: Эта установка предназначена для разработки. Для продакшена используйте полноценную инфраструктуру с Kubernetes, мониторингом и высокой доступностью.

**🔗 Полезные ссылки:**
- [Апache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Kafka Python Client](https://kafka-python.readthedocs.io/)
- [Docker Kafka Setup](https://docs.confluent.io/platform/current/installation/docker/config-reference.html)
