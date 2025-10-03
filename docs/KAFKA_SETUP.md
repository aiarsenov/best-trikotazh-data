# Настройка Apache Kafka KRaft

## Обзор

Настройка Apache Kafka в режиме KRaft (без ZooKeeper) на сервере Ubuntu для ETL пайплайна.

## Архитектура

- **Kafka 3.7.1** в режиме KRaft (единственный узел)
- **Внешний доступ**: `89.169.152.54:9092`
- **Внутренний контроль**: `localhost:19092`
- **Топики**: 5 топиков для разных источников данных

## Топики

| Топик | Разделы | Описание |
|-------|---------|----------|
| `wb-keywords` | 3 | Wildberries ключевые слова |
| `wb-campaigns` | 3 | Wildberries кампании |
| `ozon-products` | 3 | Ozon продукты |
| `onec-entities` | 3 | 1C сущности |
| `etl-logs` | 1 | Логи ETL-процесса |

## Быстрая установка

```bash
# Запустите автоматический скрипт установки
sudo bash provision/kafka-install.sh
```

## Ручная установка

### 1. Подготовка системы

```bash
# Обновление системы
sudo apt update && sudo apt -y upgrade

# Установка зависимостей
sudo apt -y install openjdk-17-jre-headless curl wget git ufw

# Создание пользователя dataops
sudo adduser dataops --disabled-password --gecos ""
sudo usermod -aG sudo dataops

# Настройка UFW
sudo ufw allow OpenSSH
sudo ufw allow 9092/tcp    # Kafka Broker
sudo ufw allow 8080/tcp   # Airflow Web
sudo ufw allow 8000/tcp   # FastAPI UI
sudo ufw enable
```

### 2. Установка Kafka

```bash
# Создание директорий
sudo mkdir -p /opt/kafka
sudo chown dataops:dataops /opt/kafka

# Скачивание и извлечение Kafka
cd /opt/kafka
KVER=3.7.1
wget https://archive.apache.org/dist/kafka/${KVER}/kafka_2.13-${KVER}.tgz
tar xzf kafka_2.13-${KVER}.tgz
mv kafka_2.13-${KVER} kafka
rm kafka_2.13-${KVER}.tgz
mkdir -p logs
```

### 3. Конфигурация

```bash
# Конфигурация сервера
cat > /opt/kafka/kafka/config/kraft/server.properties << 'EOF'
process.roles=broker,controller
node.id=1
controller.quorum.voters=1@localhost:19092
controller.listener.names=CONTROLLER
listeners=PLAINTEXT://0.0.0.0:9092,CONTROLLER://localhost:19092
inter.broker.listener.name=PLAINTEXT
advertised.listeners=PLAINTEXT://89.169.152.54:9092
listener.security.protocol.map=PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT
log.dirs=/opt/kafka/logs
num.partitions=3
EOF
```

### 4. Systemd сервис

```bash
# Создание systemd сервиса
cat > /etc/systemd/system/kafka.service << 'EOF'
[Unit]
Description=Apache Kafka (KRaft)
After=network.target

[Service]
User=dataops
ExecStart=/opt/kafka/kafka/bin/kafka-server-start.sh /opt/kafka/kafka/config/kraft/server.properties
Restart=always
RestartSec=5
LimitNOFILE=100000

[Install]
WantedBy=multi-user.target
EOF

# Активация сервиса
sudo systemctl daemon-reload
sudo systemctl enable kafka
```

### 5. Инициализация и запуск

```bash
# Генерация и форматирование кластера
/opt/kafka/kafka/bin/kafka-storage.sh random-uuid | tee /opt/kafka/cluster.id
/opt/kafka/kafka/bin/kafka-storage.sh format \
  -t "$(cat /opt/kafka/cluster.id)" \
  -c /opt/kafka/kafka/config/kraft/server.properties

# Фиксация прав и запуск
sudo chown -R dataops:dataops /opt/kafka
sudo systemctl start kafka
sudo systemctl status kafka
```

### 6. Создание топиков

```bash
# Ожидание запуска (30-60 секунд)
sleep 30

# Создание топиков
/opt/kafka/kafka/bin/kafka-topics.sh --bootstrap-server 89.169.152.54:9092 --create --topic wb-keywords --replication-factor 1 --partitions 3
/opt/kafka/kafka/bin/kafka-topics.sh --bootstrap-server 89.169.152.54:9092 --create --topic wb-campaigns --replication-factor 1 --partitions 3
/opt/kafka/kafka/bin/kafka-topics.sh --bootstrap-server 89.169.152.54:9092 --create --topic ozon-products --replication-factor 1 --partitions 3
/opt/kafka/kafka/bin/kafka-topics.sh --bootstrap-server 89.169.152.54:9092 --create --topic onec-entities --replication-factor 1 --partitions 3
/opt/kafka/kafka/bin/kafka-topics.sh --bootstrap-server 89.169.152.54:9092 --create --topic etl-logs --replication-factor 1 --partitions 1

# Проверка топиков
/opt/kafka/kafka/bin/kafka-topics.sh --bootstrap-server 89.169.152.54:9092 --list
```

## Проверка работоспособности

```bash
# Отправка тестового сообщения
echo "test message $(date)" | /opt/kafka/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server 89.169.152.54:9092 --topic wb-keywords

# Проверка статуса сервиса
sudo systemctl status kafka

# Проверка портов
ss -tlnp | grep :909

# Quick consumer test (assign from beginning)
/opt/kafka/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server 89.169.152.54:9092 \
  --topic wb-keywords \
  --from-beginning \
  --timeout-ms 5000
```

## Подключение клиентов

### Python

```python
from kafka import KafkaProducer, KafkaConsumer

# Producer
producer = KafkaProducer(
    bootstrap_servers=['89.169.152.54:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Consumer
consumer = KafkaConsumer(
    'wb-keywords',
    bootstrap_servers=['89.169.152.54:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)
```

### Внешние подключения

- **Bootstrap servers**: `89.169.152.54:9092`
- **Security**: PLAINTEXT (без шифрования)
- **Compression**: snappy (по умолчанию)

## Мониторинг

```bash
# Логи сервиса
journalctl -u kafka -f

# Статус топиков
/opt/kafka/kafka/bin/kafka-topics.sh --bootstrap-server 89.169.152.54:9092 --describe --topic wb-keywords

# Метрики консоли (если нужно)
/opt/kafka/kafka/bin/kafka-console-consumer.sh --bootstrap-server 89.169.152.54:9092 --topic wb-keywords --from-beginning --max-messages 10
```

## Устранение неполадок

### Сервис не запускается

```bash
# Проверить логи
journalctl -u kafka -n 50

# Проверить права
ls -la /opt/kafka/

# Проверить конфигурацию
cat /opt/kafka/kafka/config/kraft/server.properties
```

### Клиенты не подключаются

```bash
# Проверить UFW
sudo ufw status | grep 9092

# Проверить порты
ss -tlnp | grep :909

# Проверить доступность
telnet 89.169.152.54 9092
```

### Переинициализация хранилища

```bash
sudo systemctl stop kafka
sudo rm -rf /opt/kafka/logs/*
/opt/kafka/kafka/bin/kafka-storage.sh random-uuid | tee /opt/kafka/cluster.id
/opt/kafka/kafka/bin/kafka-storage.sh format \
  -t "$(cat /opt/kafka/cluster.id)" \
  -c /opt/kafka/kafka/config/kraft/server.properties
sudo chown -R dataops:dataops /opt/kafka
sudo systemctl start kafka
```

## ClickHouse подключение (важно)
- Нативный TLS порт: `9440` (рекомендуется с `clickhouse-driver`)
- HTTP TLS порт: `8443` (для `clickhouse-connect`/curl)
Установите корневой сертификат Yandex Cloud и используйте `verify=true`.

## Следующие шаги

После успешной установки Kafka можно переходить к настройке:

1. Python окружения с kafka-python
2. Apache Airflow для оркестрации
3. Prometheus/Grafana для мониторинга
4. FastAPI ETL UI

См. соответствующие документы в `docs/`.
