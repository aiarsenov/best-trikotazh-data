# Best Trikotazh Data 🚀

**ETL пайплайн для обработки данных о трикотаже** с потоковой передачей через Apache Kafka и аналитическими возможностями.

## 🏗️ Архитектура

Схема работы ETL-пайплайна для развертывания на одном сервере Ubuntu:

### Основные компоненты:
- **Источники**: Wildberries API, Ozon API, 1C API
- **Apache Kafka KRaft**: Потоковая передача данных
- **Yandex ClickHouse**: Аналитическая БД (TLS:8443)
- **Apache Airflow**: Оркестрация (запуск в 01:00)
- **dbt**: Трансформация данных (staging → marts)
- **FastAPI ETL UI**: Веб-интерфейс для логов/метрик
- **Prometheus + Grafana**: Мониторинг

## 🛠️ Быстрый старт

### Предварительные требования
- Ubuntu 20.04+ сервер
- 8GB RAM, 32GB SSD (рекомендуется)
- Внешний IP для доступа

### 1. Клонирование и локальная настройка
```bash
git clone https://github.com/aiarsenov/best-trikotazh-data.git
cd best-trikotazh-data

# Настройка Python окружения
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Настройка сервера

#### Автоматическая установка Kafka
```bash
# Копируйте скрипт на сервер и запустите
sudo bash provision/kafka-install.sh
```

#### Или пошагово согласно документации
См. подробные инструкции: [📚 Kafka Setup Guide](./docs/KAFKA_SETUP.md)

## 📚 Документация

- [🔧 Kafka Setup](./docs/KAFKA_SETUP.md) - Установка и настройка Apache Kafka KRaft
- [🐍 Python Environment](./docs/PYTHON_SETUP.md) - Python окружение с зависимостями *(в разработке)*
- [🔄 Airflow Setup](./docs/AIRFLOW_SETUP.md) - Настройка Apache Airflow *(в разработке)*
- [📊 Monitoring](./docs/MONITORING_SETUP.md) - Prometheus + Grafana *(в разработке)*
- [🌐 FastAPI UI](./docs/FASTAPI_SETUP.md) - Веб-интерфейс ETL *(в разработке)*

## 🗂️ Структура проекта

```
best-trikotazh-data/
├── 📁 docs/                           # Документация
│   └── KAFKA_SETUP.md                 # Инструкции по Kafka
├── 📁 provision/                      # Скрипты автоматизации
│   └── kafka-install.sh              # Установка Kafka
├── 📄 requirements.txt               # Python зависимости
├── 📄 hello_world.py                 # Тестовый файл
├── 📄 .gitignore                     # Игнорируемые Git файлы
└── 📄 README.md                      # Этот файл
```

## 🚀 Текущий статус

### ✅ Завершено:
- [x] **Базовая настройка Ubuntu**: пользователь `dataops`, UFW, зависимости
- [x] **Apache Kafka KRaft 3.7.1**: установлен и работает на `89.169.152.54:9092`
- [x] **Топики**: 5 топиков созданы (wb-keywords, wb-campaigns, ozon-products, onec-entities, etl-logs)
- [x] **Документация**: инструкции по установке и настройке

### 🔜 В разработке:
- [ ] **Python окружение**: kafka-python, clickhouse-connector, pandas
- [ ] **Apache Airflow**: оркестрация по расписанию 01:00
- [ ] **Prometheus + Grafana**: мониторинг метрик
- [ ] **FastAPI ETL UI**: веб-интерфейс `/logs`, `/metrics`
- [ ] **Python Producers/Consumers**: интеграция с API источников

## 🔗 Подключение к Kafka

После установки Kafka доступен по адресу `89.169.152.54:9092`:

### Python клиент:
```python
from kafka import KafkaProducer, KafkaConsumer

# Producer для отправки данных
producer = KafkaProducer(
    bootstrap_servers=['89.169.152.54:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Consumer для чтения данных
consumer = KafkaConsumer(
    'wb-keywords',
    bootstrap_servers=['89.169.152.54:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)
```

### Консольные клиенты:
```bash
# Отправка сообщения
echo "test message" | /opt/kafka/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server 89.169.152.54:9092 --topic wb-keywords

# Чтение сообщений
/opt/kafka/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server 89.169.152.54:9092 --topic wb-keywords --from-beginning
```

## ⚙️ Управление сервисами

### Kafka сервис:
```bash
# Статус
systemctl status kafka

# Логи
journalctl -u kafka -f

# Управление
sudo systemctl start|stop|restart kafka
```

### Проверка системы:
```bash
# Проверка портов
ss -tlnp | grep :909

# Список топиков
/opt/kafka/kafka/bin/kafka-topics.sh --bootstrap-server 89.169.152.54:9092 --list

# Детали топика
/opt/kafka/kafka/bin/kafka-topics.sh --bootstrap-server 89.169.152.54:9092 --describe --topic wb-keywords
```

## 🤝 Разработка

### Добавление новых топиков:
```bash
/opt/kafka/kafka/bin/kafka-topics.sh --bootstrap-server 89.169.152.54:9092 \
  --create --topic YOUR_TOPIC --replication-factor 1 --partitions 3
```

### Локальное тестирование:
```bash
python hello_world.py
```

### Деактивация окружения:
```bash
deactivate
```

## 📋 Roadmap

1. **Phase 1**: Python клиенты для источников данных
2. **Phase 2**: Оркестрация через Airflow  
3. **Phase 3**: Мониторинг и алерты
4. **Phase 4**: Веб-интерфейс управления
5. **Phase 5**: Масштабирование и оптимизация

## 📄 Лицензия

MIT License - см. файл LICENSE для деталей.

## 🔍 Мониторинг и поддержка

- **Статус сервисов**: `systemctl status` для каждого сервиса
- **Логи**: `journalctl -u SERVICE_NAME -f`
- **Проблемы**: см. раздел Troubleshooting в документации компонентов

## 👥 Вклад в проект

1. Форкните репозиторий
2. Создайте feature ветку (`git checkout -b feature/amazing-feature`)
3. Закоммитьте изменения (`git commit -m 'Add amazing feature'`)
4. Запушьте в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

---

**Удачной разработки! 🚀**