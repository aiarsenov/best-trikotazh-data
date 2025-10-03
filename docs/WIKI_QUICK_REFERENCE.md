# Wiki Quick Reference: Best Trikotazh Data

## 🚀 One-Click Installation
```bash
git clone https://github.com/aiarsenov/best-trikotazh-data.git
cd best-trikotazh-data
sudo bash provision/kafka-install.sh
```

## 🔧 Service Management

### Kafka Commands
```bash
# Service control
sudo systemctl start|stop|restart|status kafka
sudo journalctl -u kafka -f

# Airflow
sudo systemctl start|stop|restart airflow-scheduler airflow-webserver
sudo systemctl status --no-pager -l airflow-webserver

# Topic management
/opt/kafka/kafka/bin/kafka-topics.sh --bootstrap-server 89.169.152.54:9092 --list
/opt/kafka/kafka/bin/kafka-topics.sh --bootstrap-server 89.169.152.54:9092 --describe --topic TOPIC_NAME

# Test messaging
echo "test message" | /opt/kafka/kafka/bin/kafka-console-producer.sh --bootstrap-server 89.169.152.54:9092 --topic wb-keywords
/opt/kafka/kafka/bin/kafka-console-consumer.sh --bootstrap-server 89.169.152.54:9092 --topic wb-keywords --from-beginning
```

## 📊 Project Status

### ✅ Completed
- [x] Ubuntu 20.04 setup with user `dataops`
- [x] Apache Kafka KRaft 3.7.1 on `89.169.152.54:9092`
- [x] 5 Topics: wb-keywords, wb-campaigns, ozon-products, onec-entities, etl-logs
- [x] UFW firewall configured (ports 9092, 8080, 8000)
- [x] Documentation and automation scripts

### 🔄 In Progress
- [ ] Python environment with dependencies
- [ ] Apache Airflow orchestration
- [ ] Prometheus + Grafana monitoring
- [ ] FastAPI ETL Web UI

## 🔗 Connection Info

### Kafka Access
- **External**: `89.169.152.54:9092`
- **Security**: PLAINTEXT (internal network)
- **Java Version**: OpenJDK 17
- **User**: dataops
- **Home**: /opt/kafka

### ClickHouse Access
- **TLS (native)**: host `rc1a-ioasjmp8oohqnaeo.mdb.yandexcloud.net`, port `9440` (clickhouse-client/clickhouse-driver)
- **HTTPS**: port `8443` (curl/clickhouse-connect)
- Используйте `verify=true` и корневой сертификат Yandex Cloud.

### Topics Overview
| Topic | Partitions | Purpose |
|-------|------------|---------|
| wb-keywords | 3 | Wildberries keyword data |
| wb-campaigns | 3 | WB campaign metrics |
| ozon-products | 3 | Ozon product catalog |
| onec-entities | 3 | 1C CRM/ERP data |
| etl-logs | 1 | Processing logs |

## 🧪 End-to-End Test Pipeline

### ✅ Verified Working Flow:
```bash
# 1. Send test data to Kafka
Python3 - <<'PY'
from confluent_kafka import Producer
import json
p = Producer({"bootstrap.servers": "89.169.152.54:9092"})
p.produce("wb_keywords", json.dumps({
    "date": "2024-01-01", "campaign_id": 12345, 
    "keyword": "test", "impressions": 100, "clicks": 15, "cost": 50.5
}).encode('utf-8'))
p.flush()
print("✅ Data sent to Kafka")
PY

# 2. Consumer to ClickHouse
python3 - <<'PY'
from confluent_kafka import Consumer
from clickhouse_driver import Client
ch = Client(host="rc1a-ioasjmp8oohqnaeo.mdb.yandexcloud.net", port=9440, 
           user="databaseuser", password="YOUR_PASSWORD", secure=True)
c = Consumer({"bootstrap.servers": "89.169.152.54:9092", "group.id": "test"})
c.subscribe(["wb_keywords"])
msg = c.poll(5.0)
if msg: ch.execute("INSERT INTO wb_keywords_raw (payload) VALUES", 
                   [[msg.value().decode('utf-8')]])
print("✅ Data in ClickHouse")
PY

# 3. dbt transformation
cd ~/etl/dbt/best_tricotaz && dbt run --select staging
```

### ✅ Verified Results:
- **Raw records**: 9 в ClickHouse
- **Staging records**: 8 (dbt фильтрация работает)
- **Structured fields**: date, campaign_id, keyword, impressions, clicks, cost

## 🛠️ Troubleshooting

### Quick Fixes
```bash
# Service not starting
sudo journalctl -u kafka -n 50
sudo systemctl restart kafka

# Connection issues
sudo ufw status | grep 9092
ss -tlnp | grep :909
```

### ⚠️ CRITICAL: Known Working Solutions

**ClickHouse String vs JSON**: Use `String` columns, NOT `JSON`:
```sql
-- ✅ WORKS
CREATE TABLE wb_keywords_raw (payload String)

-- ❌ FAILS with clickhouse-driver
CREATE TABLE wb_keywords_raw (payload JSON)
```

**INSERT Syntax**: 
```python
# ✅ CORRECT
ch.execute("INSERT INTO table (payload) VALUES", [[json_string]])

# ❌ WRONG
ch.execute("INSERT INTO table FORMAT JSONEachRow %s", [json_string])
```

# Reset storage (USE WITH CAUTION)
sudo systemctl stop kafka
sudo rm -rf /opt/kafka/logs/*
/opt/kafka/kafka/bin/kafka-storage.sh random-uuid | tee /opt/kafka/cluster.id
/opt/kafka/kafka/bin/kafka-storage.sh format -t "$(cat /opt/kafka/cluster.id)" -c /opt/kafka/kafka/config/kraft/server.properties
sudo systemctl start kafka
```

### Health Checks
```bash
# Service status
sudo systemctl is-active kafka

# Port accessibility
nc -zv 89.169.152.54 9092

# Topic connectivity
/opt/kafka/kafka/bin/kafka-topics.sh --bootstrap-server 89.169.152.54:9092 --list
```

## 📚 Documentation Links

- **[Full Setup Guide](./KAFKA_SETUP.md)** - Detailed installation instructions
- **[Complete Wiki](./WIKI_DOCUMENTATION.md)** - Comprehensive documentation
- **[Main README](../README.md)** - Project overview and architecture
- **[GitHub Repository](https://github.com/aiarsenov/best-trikotazh-data)** - Source code and issues

## 🔧 Python Integration

```python
# Producer example
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=['89.169.152.54:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

producer.send('wb-keywords', value={'keyword': 'футболка', 'timestamp': '2025-01-01'})
producer.flush()
```

## 📈 Monitoring Commands

```bash
# System metrics
top -p $(pgrep java)
df -h /opt/kafka/
free -h

# Kafka metrics
/opt/kafka/kafka/bin/kafka-consumer-groups.sh --bootstrap-server 89.169.152.54:9092 --list

# Log analysis
sudo journalctl -u kafka | grep ERROR
sudo journalctl -u kafka | grep WARN
```

## 🚀 Next Steps

1. **Install Python clients**: `pip install kafka-python clickhouse-connector`
2. **Set up Apache Airflow**: Daily scheduling at 01:00 UTC
3. **Configure monitoring**: Prometheus metrics collection
4. **Develop web UI**: FastAPI interface for /logs and /metrics
5. **Data producers**: Connect to WB, Ozon, 1C APIs

---

**Last Updated**: $(date +"%Y-%m-%d %H:%M:%S")
**Environment**: Production ETL Pipeline
**Version**: v1.0-Kafka-Setup
