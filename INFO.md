# 🚀 Best Trikotazh Data - Основная информация

## 📝 Что это?

**ETL система для обработки данных магазина трикотажа** с интеграцией Wildberries, Ozon и 1C через Apache Kafka.

### Функции:
- ✅ **Сбор данных** из маркетплейсов (WB, Ozon) и CRM (1C) 
- ✅ **Потоковая передача** через Apache Kafka KRaft
- ✅ **Аналитика** в ClickHouse + трансформация dbt
- ✅ **Автоматизация** через Apache Airflow (01:00 ежедневно)
- ✅ **Мониторинг** Prometheus + Grafana
- ✅ **Веб-UI** FastAPI для управления

## 🛠️ Быстрый старт

### На сервере Ubuntu:
```bash
git clone https://github.com/aiarsenov/best-trikotazh-data.git
cd best-trikotazh-data
sudo bash provision/kafka-install.sh
```

### На локальной машине:
```bash
git clone https://github.com/aiarsenov/best-trikotazh-data.git
cd best-trikotazh-data
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Запуск Kafka в Docker
docker run -d -p 9092:9092 --name kafka-local confluentinc/cp-kafka:7.4.0
sleep 30

# Создание топиков
docker exec kafka-local kafka-topics --bootstrap-server localhost:9092 \
  --create --topic wb-keywords --partitions 3 --replication-factor 1
# ... (остальные топики см. в docs/)
```

## 📊 Архитектура

```
External APIs → Python Producers → Kafka Topics → Python Consumers → ClickHouse → dbt → Data Marts
                                              ↓
                                        Airflow (01:00)
                                              ↓
                                        Monitoring (Prometheus/Grafana)
                                              ↓
                                        Web UI (FastAPI)
```

## 🔗 Доступ

- **Продакшен Kafka**: `89.169.152.54:9092` 
- **Топики**: wb-keywords, wb-campaigns, ozon-products, onec-entities, etl-logs
- **Пользователь сервера**: `dataops`
- **Директория**: `/opt/kafka`

## 📚 Документация

- **[Подробная установка](docs/KAFKA_SETUP.md)** - Полное руководство по установке
- **[Локальная разработка](docs/LOCAL_SETUP_GUIDE.md)** - Настройка на своей машине  
- **[Wiki-документация](docs/WIKI_DOCUMENTATION.md)** - Полная техническая документация
- **[Быстрый справочник](docs/WIKI_QUICK_REFERENCE.md)** - Основные команды

## 📋 Статус проекта

### ✅ Завершено:
- [x] Базовая настройка Ubuntu + пользователь dataops  
- [x] Apache Kafka KRaft 3.7.1 с внешним доступом
- [x] 5 топиков готовых к работе
- [x] Документация и автоматические скрипты

### 🔄 В разработке:
- [ ] Python окружение с зависимостями (kafka-python, clickhouse-connector)
- [ ] Apache Airflow для оркестрации
- [ ] Prometheus + Grafana для мониторинга  
- [ ] FastAPI ETL веб-интерфейс
- [ ] Producers для интеграции с API WB/Ozon/1C

## ⚡ Управление

### Основные команды:
```bash
# Kafka сервис
systemctl start|stop|restart|status kafka

# Список топиков  
/opt/kafka/kafka/bin/kafka-topics.sh --bootstrap-server 89.169.152.54:9092 --list

# Отправка тестового сообщения
echo "test message" | /opt/kafka/kafka/bin/kafka-console-producer.sh --bootstrap-server 89.169.152.54:9092 --topic wb-keywords

# Логи сервиса
journalctl -u kafka -f
```

### Python клиент:
```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=['89.169.152.54:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

producer.send('wb-keywords', value={
    'keyword': 'футболка мужская',
    'position': 1,
    'source': 'wb_api'
})
```

## 🔧 Разработка

### Подключение к проекту:
1. Форкните репозиторий на GitHub
2. Клонируйте локально: `git clone YOUR_FORK_URL`
3. Создайте feature ветку: `git checkout -b feature/new-integration`
4. После изменений: commit → push → Pull Request

### Следующие компоненты для разработки:
- **Python producers** для каждого источника данных
- **Consumers** с batch-загрузкой в ClickHouse
- **Airflow DAGs** с расписанием и retry-логикой
- **Monitoring metrics** для отслеживания performance
- **Web UI** для просмотра логов и метрик

## ⚠️ Важно

- **Продакшен система** работает на сервере `89.169.152.54`
- **Безопасность**: PLAINTEXT соединения (для внутренней сети)
- **Резервирование**: Текущая установка без репликации (single node)
- **Мониторинг**: Необходимо настроить алерты на отказоустойчивость

## 📞 Поддержка

- **GitHub Issues**: https://github.com/aiarsenov/best-trikotazh-data/issues
- **Документация**: `docs/` в репозитории  
- **Wiki**: Полная техническая документация в `docs/WIKI_DOCUMENTATION.md`

---

**🎯 Цель**: Создать надёжный ETL пайплайн для обработки данных онлайн-магазина трикотажа с интеграцией всех источников знаний.**
