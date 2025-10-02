# Wiki Documentation: Best Trikotazh Data ETL Pipeline

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture & Components](#architecture--components)
3. [Environment Setup](#environment-setup)
4. [Apache Kafka Installation](#apache-kafka-installation)
5. [Configuration & Setup](#configuration--setup)
6. [Service Management](#service-management)
7. [Client Configuration](#client-configuration)
8. [Troubleshooting](#troubleshooting)
9. [Monitoring & Maintenance](#monitoring--maintenance)
10. [Best Practices](#best-practices)
11. [FAQ](#faq)

---

## Project Overview

### Purpose
ETL pipeline for processing tricot clothing data from multiple marketplaces and internal systems using Apache Kafka for streaming data processing.

### Business Goals
- Real-time data ingestion from Wildberries, Ozon marketplaces
- Integration with 1C internal systems
- Scalable data processing pipeline
- Analytics and reporting capabilities
- Operational monitoring and alerting

### Technical Stack
- **Streaming**: Apache Kafka KRaft 3.7.1
- **Database**: Yandex ClickHouse (external, TLS:8443)
- **Orchestration**: Apache Airflow
- **Transformation**: dbt
- **Monitoring**: Prometheus + Grafana
- **UI**: FastAPI Web Interface
- **Infrastructure**: Ubuntu 20.04+ on cloud VM

---

## Architecture & Components

### Data Flow Diagram
```
External APIs → Python Producers → Kafka Topics → Python Consumers → ClickHouse → dbt → Data Marts
                                                      ↓
                                            Airflow Orchestrator
                                                      ↓
                                            Monitoring (Prometheus/Grafana)
                                                      ↓
                                            Web UI (FastAPI)
```

### Component Details

#### Data Sources
- **Wildberries API**: Product catalogs, campaigns, keywords
- **Ozon API**: Product information, sales data
- **1C API**: Internal inventory, customers, orders

#### Core Infrastructure
- **Apache Kafka KRaft**: Message broker (no ZooKeeper dependency)
  - Cluster: Single-node, external access enabled
  - Topics: 5 topics for different data types
  - Security: PLAINTEXT (internal network)

#### Processing Layer
- **Python Producers**: Data extraction from APIs
  - Watermark tracking for incremental loads
  - Rate limiting and retry logic
  - Error handling and dead letter queues

- **Python Consumers**: Batch data loading to ClickHouse
  - Batch processing for efficiency
  - Error logging and monitoring

#### Storage & Analytics
- **Yandex ClickHouse**: Columnar analytics database
  - Connections: TLS secured (port 8443)
  - Tables: staging and marts layers
  - Partitioning: By date and source system

#### Orchestration & Monitoring
- **Apache Airflow**: Workflow scheduler
  - Schedule: Daily at 01:00 UTC
  - DAGs: Producer triggers, consumer monitoring
  - Retry policies: Configurable retry logic

- **Monitoring Stack**:
  - **Prometheus**: Metrics collection
  - **Grafana**: Visualization and dashboards
  - **FastAPI**: Operational web interface

---

## Environment Setup

### Prerequisites

#### Hardware Requirements
- **CPU**: 8+ cores recommended
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 32GB SSD minimum
- **Network**: Stable internet connection, external IP

#### Software Requirements
- **OS**: Ubuntu 20.04 LTS or later
- **Java**: OpenJDK 17+ (for Kafka)
- **Python**: 3.9+ (for producers/consumers)
- **System**: systemd, UFW firewall enabled

### Initial Server Configuration

#### Step 1: Base System Setup
```bash
# Update system
sudo apt update && sudo apt -y upgrade

# Install essential packages
sudo apt -y install build-essential curl wget git unzip ufw python3 python3-venv python3-pip openjdk-17-jre-headless

# Set timezone
sudo timedatectl set-timezone Europe/Moscow
sudo timedatectl set-ntp true
```

#### Step 2: Security Setup
```bash
# Create dedicated user
sudo adduser dataops --disabled-password --gecos ""
sudo usermod -aG sudo dataops

# Configure firewall
sudo ufw allow OpenSSH
sudo ufw allow 9092/tcp    # Kafka Broker
sudo ufw allow 8080/tcp    # Airflow Web
sudo ufw allow 8000/tcp    # FastAPI UI
sudo ufw enable

# Verify firewall status
sudo ufw status verbose
```

#### Step 3: Directory Structure
```bash
# Create application directories
sudo mkdir -p /opt/kafka
sudo mkdir -p /opt/airflow
sudo mkdir -p /opt/etl-apps
sudo mkdir -p /var/log/etl

# Set ownership
sudo chown -R dataops:dataops /opt/kafka /opt/airflow /opt/etl-apps /var/log/etl
```

---

## Apache Kafka Installation

### Overview
Apache Kafka 3.7.1 in KRaft mode (no ZooKeeper dependency) for single-node deployment with external access.

### Installation Methods

#### Method 1: Automated Installation (Recommended)
```bash
# Clone repository
git clone https://github.com/aiarsenov/best-trikotazh-data.git
cd best-trikotazh-data

# Run automated installer
sudo bash provision/kafka-install.sh
```

#### Method 2: Manual Installation

##### Step 1: Download Kafka
```bash
cd /opt/kafka
KVER=3.7.1
wget https://archive.apache.org/dist/kafka/${KVER}/kafka_2.13-${KVER}.tgz
tar xzf kafka_2.13-${KVER}.tgz
mv kafka_2.13-${KVER} kafka
rm kafka_2.13-${KVER}.tgz
mkdir -p logs
```

##### Step 2: Configuration
```bash
# Main server configuration
cat > /opt/kafka/kafka/config/kraft/server.properties << 'EOF'
# Cluster configuration
process.roles=broker,controller
node.id=1
controller.quorum.voters=1@localhost:19092
controller.listener.names=CONTROLLER

# Network configuration
listeners=PLAINTEXT://0.0.0.0:9092,CONTROLLER://localhost:19092
inter.broker.listener.name=PLAINTEXT
advertised.listeners=PLAINTEXT://89.169.152.54:9092
listener.security.protocol.map=PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT

# Storage and performance
log.dirs=/opt/kafka/logs
num.partitions=3
compression.type=snappy
log.cleanup.policy=delete
log.retention.hours=168

# Resource tuning for single VM
num.network.threads=8
num.io.threads=16
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600
EOF
```

##### Step 3: Systemd Service
```bash
cat > /etc/systemd/system/kafka.service << 'EOF'
[Unit]
Description=Apache Kafka (KRaft)
Documentation=https://kafka.apache.org/documentation/
After=network.target

[Service]
Type=simple
User=dataops
Environment=JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ExecStart=/opt/kafka/kafka/bin/kafka-server-start.sh /opt/kafka/kafka/config/kraft/server.properties
Restart=always
RestartSec=5
SuccessExitStatus=143
LimitNOFILE=100000
TimeoutStopSec=90s

[Install]
WantedBy=multi-user.target
EOF
```

##### Step 4: Initialize and Start
```bash
# Generate cluster UUID and format storage
/opt/kafka/kafka/bin/kafka-storage.sh random-uuid | tee /opt/kafka/cluster.id
/opt/kafka/kafka/bin/kafka-storage.sh format \
  -t "$(cat /opt/kafka/cluster.id)" \
  -c /opt/kafka/kafka/config/kraft/server.properties

# Set permissions and start service
sudo chown -R dataops:dataops /opt/kafka
sudo systemctl daemon-reload
sudo systemctl enable kafka
sudo systemctl start kafka

# Wait for startup
sleep 30
sudo systemctl status kafka
```

---

## Configuration & Setup

### Topic Creation

#### Core Topics
```bash
# Analytics data topics
/opt/kafka/kafka/bin/kafka-topics.sh --bootstrap-server 89.169.152.54:9092 --create --topic wb-keywords --replication-factor 1 --partitions 3
/opt/kafka/kafka/bin/kafka-topics.sh --bootstrap-server 89.169.152.54:9092 --create --topic wb-campaigns --replication-factor 1 --partitions 3
/opt/kafka/kafka/bin/kafka-topics.sh --bootstrap-server 89.169.152.54:9092 --create --topic ozon-products --replication-factor 1 --partitions 3
/opt/kafka/kafka/bin/kafka-topics.sh --bootstrap-server 89.169.152.54:9092 --create --topic onec-entities --replication-factor 1 --partitions 3

# Operational topics
/opt/kafka/kafka/bin/kafka-topics.sh --bootstrap-server 89.169.152.54:9092 --create --topic etl-logs --replication-factor 1 --partitions 1
```

#### Topic Description
| Topic Name | Partitions | Purpose | Data Source |
|------------|------------|---------|-------------|
| `wb-keywords` | 3 | Wildberries keyword analytics | WB API |
| `wb-campaigns` | 3 | WB campaign performance data | WB API |
| `ozon-products` | 3 | Ozon product catalog | Ozon API |
| `onec-entities` | 3 | Internal CRM/ERP data | 1C API |
| `etl-logs` | 1 | Processing logs and errors | ETL Apps |

### Network Configuration
- **External Access**: `89.169.152.54:9092`
- **Internal Controller**: `localhost:19092`
- **Security**: PLAINTEXT (for internal networks)
- **Firewall**: Port 9092 opened for external connections

### Environment Variables
```bash
# For external applications
export KAFKA_BROKER="89.169.152.54:9092"
export KAFKA_SECURITY_PROTOCOL="PLAINTEXT"
export KAFKA_TOPIC_PREFIX="etl"
```

---

## Service Management

### Basic Operations

#### Start/Stop/Restart Services
```bash
# Kafka service management
sudo systemctl start kafka
sudo systemctl stop kafka
sudo systemctl restart kafka
sudo systemctl status kafka

# Enable auto-start on boot
sudo systemctl enable kafka

# Check service health
sudo systemctl is-active kafka
```

#### Viewing Logs
```bash
# Real-time logs
sudo journalctl -u kafka -f

# Recent logs (last 100 lines)
sudo journalctl -u kafka -n 100

# Logs with timestamps
sudo journalctl -u kafka --no-pager -S "1 hour ago"
```

### Advanced Operations

#### Topic Management
```bash
# List all topics
/opt/kafka/kafka/bin/kafka-topics.sh --bootstrap-server 89.169.152.54:9092 --list

# Describe topic details
/opt/kafka/kafka/bin/kafka-topics.sh --bootstrap-server 89.169.152.54:9092 --describe --topic wb-keywords

# Add partitions to existing topic
/opt/kafka/kafka/bin/kafka-topics.sh --bootstrap-server 89.169.152.54:9092 --alter --topic wb-keywords --partitions 6

# Delete topic (use with caution)
/opt/kafka/kafka/bin/kafka-topics.sh --bootstrap-server 89.169.152.54:9092 --delete --topic unwanted-topic
```

#### Consumer Group Management
```bash
# List consumer groups
/opt/kafka/kafka/bin/kafka-consumer-groups.sh --bootstrap-server 89.169.152.54:9092 --list

# Describe consumer group
/opt/kafka/kafka/bin/kafka-consumer-groups.sh --bootstrap-server 89.169.152.54:9092 --describe --group etl-consumers
```

---

## Client Configuration

### Python Client Setup

#### Installation
```bash
# Install Kafka Python client
pip install kafka-python

# Additional dependencies
pip install clickhouse-connector pandas numpy requests
```

#### Producer Configuration
```python
from kafka import KafkaProducer
import json
import logging

# Configuration
KAFKA_CONFIG = {
    'bootstrap_servers': ['89.169.152.54:9092'],
    'value_serializer': lambda v: json.dumps(v).encode('utf-8'),
    'key_serializer': lambda k: k.encode('utf-8') if k else None,
    'retries': 3,
    'retry_backoff_ms': 1000,
    'compression_type': 'snappy',
    'acks': 'all',  # Wait for all replicas
    'enable_idempotence': True,
    'max_in_flight_requests_per_connection': 1,
}

# Initialize producer
producer = KafkaProducer(**KAFKA_CONFIG)

# Send message
producer.send('wb-keywords', 
              key='keyword_id_123', 
              value={'keyword': 'футболка', 'position': 1, 'timestamp': '2025-01-01T00:00Z'})

# Flush and close
producer.flush()
producer.close()
```

#### Consumer Configuration
```python
from kafka import KafkaConsumer
import json
import logging

# Configuration
KAFKA_CONFIG = {
    'bootstrap_servers': ['89.169.152.54:9092'],
    'group_id': 'etl-consumers',
    'value_deserializer': lambda m: json.loads(m.decode('utf-8')),
    'key_deserializer': lambda m: m.decode('utf-8') if m else None,
    'auto_offset_reset': 'earliest',
    'enable_auto_commit': False,
    'fetch_max_wait_ms': 5000,
    'max_partition_fetch_bytes': 1048576,
}

# Initialize consumer
consumer = KafkaConsumer('wb-keywords', **KAFKA_CONFIG)

# Consume messages
try:
    for message in consumer:
        print(f"Topic: {message.topic}")
        print(f"Partition: {message.partition}")
        print(f"Offset: {message.offset}")
        print(f"Key: {message.key}")
        print(f"Value: {message.value}")
        print("---")
        
        # Process message
        process_message(message.value)
        
        # Commit offset
        consumer.commit()
        
except KeyboardInterrupt:
    print("Stopping consumer...")
finally:
    consumer.close()
```

### External Client Examples

#### Java Client
```java
// Producer configuration
Properties props = new Properties();
props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, "89.169.152.54:9092");
props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
props.put(ProducerConfig.ACKS_CONFIG, "all");
props.put(ProducerConfig.RETRIES_CONFIG, 3);

Producer<String, String> producer = new KafkaProducer<>(props);
```

#### REST API (via Kafka REST Proxy)
```json
{
  "records": [
    {
      "key": "keyword_123",
      "value": "{\"keyword\":\"футболка\",\"category\":\"одежда\"}"
    }
  ]
}
```

---

## Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check detailed logs
sudo journalctl -u kafka -n 50

# Verify Java installation
java -version

# Check configuration syntax
/opt/kafka/kafka/bin/kafka-server-start.sh /opt/kafka/kafka/config/kraft/server.properties --help

# Verify ports are available
ss -tlnp | grep -E ":(9092|19092)"

# Check disk space
df -h /opt/kafka/
```

#### Connection Issues
```bash
# Test external connectivity
telnet 89.169.152.54 9092

# Check firewall status
sudo ufw status | grep 9092

# Verify advertised listeners
cat /opt/kafka/kafka/config/kraft/server.properties | grep advertised.listeners

# Test local connectivity
/opt/kafka/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
```

#### Performance Issues
```bash
# Monitor system resources
top -p $(pgrep java)

# Check Kafka logs for GC issues
sudo journalctl -u kafka | grep -i gc

# Monitor disk I/O
iostat -x 1

# Check network usage
iftop -i eth0
```

### Reset/Restore Procedures

#### Reset Kafka Storage
```bash
# Stop service
sudo systemctl stop kafka

# Backup existing data (optional)
sudo cp -r /opt/kafka/logs /opt/kafka/logs.backup.$(date +%Y%m%d)

# Clear storage
sudo rm -rf /opt/kafka/logs/*

# Regenerate cluster ID and reformat
/opt/kafka/kafka/bin/kafka-storage.sh random-uuid | tee /opt/kafka/cluster.id
/opt/kafka/kafka/bin/kafka-storage.sh format \
  -t "$(cat /opt/kafka/cluster.id)" \
  -c /opt/kafka/kafka/config/kraft/server.properties

# Restart service
sudo chown -R dataops:dataops /opt/kafka
sudo systemctl start kafka
```

#### Recovery from Corruption
```bash
# Stop all clients first
sudo systemctl stop kafka

# Run recovery tools
/opt/kafka/kafka/bin/kafka-streams-application-reset.sh \
  --bootstrap-servers 89.169.152.54:9092 \
  --application-id etl-streams-app \
  --input-topics wb-keywords,wb-campaigns \
  --to-earliest
```

---

## Monitoring & Maintenance

### Key Metrics

#### System Metrics
- CPU usage (should be < 80%)
- Memory usage (JVM heap < 7GB)
- Disk I/O (IOPS and throughput)
- Network throughput
- Disk space (keep > 20% free)

#### Kafka Metrics
- Broker status and uptime
- Topic partition lag
- Consumer group lag
- Message throughput (messages/second)
- Disk usage by topic
- Replica sync status

### Monitoring Tools Setup

#### Prometheus Configuration
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'kafka-server'
    static_configs:
      - targets: ['89.169.152.54:9092']
    metrics_path: /metrics
    
  - job_name: 'system-metrics'
    static_configs:
      - targets: ['localhost:9100']  # node_exporter
```

#### Grafana Dashboards
- **System Overview**: CPU, RAM, disk, network
- **Kafka Broker**: Topic metrics, partition lag
- **Consumer Lag**: Consumer group status
- **ETL Pipeline**: Processing rates, error rates

### Backup Strategy

#### Topic Data Backup
```bash
#!/bin/bash
# backup-topics.sh
BACKUP_DIR="/opt/kafka/backups/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

TOPICS=("wb-keywords" "wb-campaigns" "ozon-products" "onec-entities")

for topic in "${TOPICS[@]}"; do
    /opt/kafka/kafka/bin/kafka-console-consumer.sh \
        --bootstrap-server 89.169.152.54:9092 \
        --topic $topic \
        --from-beginning \
        --max-messages 10000 > "$BACKUP_DIR/${topic}.json"
done

# Compress backup
tar -czf "$BACKUP_DIR.tar.gz" "$BACKUP_DIR"
```

#### Configuration Backup
```bash
# Backup configurations
sudo cp /etc/systemd/system/kafka.service /opt/kafka/backups/
sudo cp /opt/kafka/kafka/config/kraft/server.properties /opt/kafka/backups/
sudo cp /opt/kafka/cluster.id /opt/kafka/backups/
```

### Maintenance Schedule

#### Daily Tasks
- Monitor service status
- Check disk space
- Review error logs
- Verify topic lag

#### Weekly Tasks
- Performance metrics review
- Log rotation cleanup
- Security updates check
- Backup verification

#### Monthly Tasks
- Configuration review
- Capacity planning
- Security audit
- Performance optimization

---

## Best Practices

### Security Best Practices
- Use TLS encryption for external connections
- Implement authentication (SASL/SCRAM)
- Regular security updates
- Firewall configuration review
- Access logging and monitoring

### Performance Optimization
- Monitor and tune JVM heap size
- Optimize batch sizes for producers/consumers
- Use compression (snappy/gzip)
- Proper partition count based on throughput needs
- Regular cleanup of old data

### Operational Excellence
- Implement comprehensive logging
- Set up alerting for critical metrics
- Regular backup testing
- Documentation updates
- Monitoring and observability

### Data Quality
- Schema validation for messages
- Dead letter queue handling
- Data lineage tracking
- Error handling and retry logic
- Data quality metrics

---

## FAQ

### Q: How do I add a new data source?
A: Create a new topic for the data source, develop a producer to ingest data from the source's API, and update the consumer groups to process the new topic.

### Q: Can I scale this to multiple Kafka brokers?
A: Yes, but you'll need to update the configuration to include additional nodes and reconfigure replication factors for topics.

### Q: What happens if ClickHouse is unavailable?
A: Consumers should implement retry logic and dead letter queues. Messages will be retained in Kafka according to retention policy.

### Q: How do I monitor pipeline health?
A: Use Prometheus metrics, Kafka JMX metrics, and Grafana dashboards. Key metrics include lag, throughput, and error rates.

### Q: Can I change topic partition counts?
A: You can increase partitions but not decrease them. Consider data distribution and consumer performance when changing partition counts.

### Q: What's the recommended message batch size?
A: Depends on message size and throughput requirements. Start with 1000-5000 messages per batch and tune based on performance.

### Q: How do I handle schema evolution?
A: Implement schema registry or use versioned message formats. Update consumers to handle multiple schema versions gracefully.

### Q: What's the backup retention policy?
A: Topics are configured with 168-hour (7-day) retention. Critical data should be backed up to ClickHouse or external storage.

---

## Appendix

### Configuration Files

#### Server Properties Template
```properties
# Refer to docs/KAFKA_SETUP.md for complete configuration
```

#### Systemd Service Template
```ini
# Refer to automation scripts in provision/ directory
```

### External Links
- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Yandex ClickHouse Documentation](https://clickhouse.com/docs)
- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [dbt Documentation](https://docs.getdbt.com/)

### Support Contacts
- **System Administrator**: Infrastructure and Kafka issues
- **Data Engineering**: Pipeline and integration issues
- **Development Team**: Application and client development

---

*This documentation is maintained as part of the Best Trikotazh Data project. Last updated: $(date)*
