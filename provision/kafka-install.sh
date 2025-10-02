#!/usr/bin/env bash
set -euo pipefail

# Установка Apache Kafka KRaft на Ubuntu сервер
# Версия: 3.7.1
# Автор: ETL Pipeline Setup

echo "==================================="
echo "🚀 Установка Apache Kafka KRaft 3.7.1"
echo "==================================="

# Конфигурация
KAFKA_VERSION="3.7.1"
KAFKA_USER="dataops"
KAFKA_HOME="/opt/kafka"
KAFKA_CONFIG_FILE="$KAFKA_HOME/kafka/config/kraft/server.properties"
EXTERNAL_IP="89.169.152.54"
KAFKA_PORT="9092"
CONTROLLER_PORT="19092"

# Проверка прав root
if [[ $EUID -ne 0 ]]; then
   echo "❌ Этот скрипт должен запускаться с правами root: sudo bash kafka-install.sh"
   exit 1
fi

echo "📋 Установка зависимостей..."

# Обновление системы
export DEBIAN_FRONTEND=noninteractive
apt update
apt -y upgrade

# Установка Java и инструментов
apt -y install openjdk-17-jre-headless curl wget git ufw python3 python3-pip python3-venv

echo "👤 Создание пользователя $KAFKA_USER..."

# Создание пользователя dataops если не существует
if ! id "$KAFKA_USER" &>/dev/null; then
    adduser "$KAFKA_USER" --disabled-password --gecos ""
    usermod -aG sudo "$KAFKA_USER"
    echo "✅ Пользователь $KAFKA_USER создан"
else
    echo "✅ Пользователь $KAFKA_USER уже существует"
fi

echo "🔥 Настройка файрвола UFW..."

# Настройка UFW
ufw allow OpenSSH || true
ufw allow $KAFKA_PORT/tcp || true
ufw allow 8080/tcp || true  # Airflow
ufw allow 8000/tcp || true  # FastAPI
ufw --force enable || true

echo "📦 Скачивание Apache Kafka $KAFKA_VERSION..."

# Создание директории для Kafka
mkdir -p $KAFKA_HOME
chown $KAFKA_USER:$KAFKA_USER $KAFKA_HOME

# Переход в директорию и скачивание Kafka
cd $KAFKA_HOME
sudo -u $KAFKA_USER bash -c "
    KVER=$KAFKA_VERSION
    ARCHIVE_URL='https://archive.apache.org/dist/kafka/\$KVER/kafka_2.13-\$KVER.tgz'
    
    echo 'Скачивание из $ARCHIVE_URL...'
    wget -O kafka_2.13-\$KVER.tgz \"\$ARCHIVE_URL\"
    
    echo 'Извлечение архива...'
    tar xzf kafka_2.13-\$KVER.tgz
    
    echo 'Переименование и очистка...'
    mv kafka_2.13-\$KVER kafka
    rm -f kafka_2.13-\$KVER.tgz
    
    echo 'Создание директории логов...'
    mkdir -p logs
"

echo "⚙️  Настройка конфигурации Kafka..."

# Создание конфигурационного файла
cat > $KAFKA_CONFIG_FILE << EOF
# Apache Kafka KRaft конфигурация для ETL пайплайна
process.roles=broker,controller
node.id=1
controller.quorum.voters=1@localhost:$CONTROLLER_PORT
controller.listener.names=CONTROLLER
listeners=PLAINTEXT://0.0.0.0:$KAFKA_PORT,CONTROLLER://localhost:$CONTROLLER_PORT
inter.broker.listener.name=PLAINTEXT
advertised.listeners=PLAINTEXT://$EXTERNAL_IP:$KAFKA_PORT
listener.security.protocol.map=PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT

# Хранилище и производительность
log.dirs=$KAFKA_HOME/logs
num.partitions=3

# Производительность для одной ВМ
compression.type=snappy
log.cleanup.policy=delete
log.retention.hours=168
num.network.threads=8
num.io.threads=16
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600

# Контроллер и метаданные  
metadata.log.segment.bytes=1073741824
metadata.max.retention.bytes=1073741824
EOF

echo "🎯 Создание systemd сервиса..."

# Создание systemd сервиса
cat > /etc/systemd/system/kafka.service << EOF
[Unit]
Description=Apache Kafka (KRaft)
Documentation=https://kafka.apache.org/documentation/
After=network.target

[Service]
Type=simple
User=$KAFKA_USER
Environment=JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ExecStart=$KAFKA_HOME/kafka/bin/kafka-server-start.sh $KAFKA_CONFIG_FILE
Restart=always
RestartSec=5
SuccessExitStatus=143

# Ресурсы
LimitNOFILE=100000
TimeoutStopSec=90s

[Install]
WantedBy=multi-user.target
EOF

echo "🔄 Инициализация хранилища KRaft..."

# Генерация UUID кластера и форматирование хранилища
sudo -u $KAFKA_USER bash -c "
    cd $KAFKA_HOME
    echo 'Генерация UUID кластера...'
    $KAFKA_HOME/kafka/bin/kafka-storage.sh random-uuid | tee cluster.id
    
    echo 'Форматирование хранилища...'
    $KAFKA_HOME/kafka/bin/kafka-storage.sh format -t \"\$(cat cluster.id)\" -c $KAFKA_CONFIG_FILE
    
    echo 'Выставление прав доступа...'
    chown -R $KAFKA_USER:$KAFKA_USER $KAFKA_HOME
"

echo "🚀 Запуск Kafka сервиса..."

# Активация и запуск сервиса
systemctl daemon-reload
systemctl enable kafka
systemctl start kafka

echo "⏳ Ожидание запуска Kafka (30 секунд)..."
sleep 30

echo "🔍 Проверка статуса сервиса..."
systemctl is-active --quiet kafka && echo "✅ Kafka сервис запущен" || echo "❌ Ошибка запуска Kafka"

echo "📊 Создание топиков..."

# Массив топиков для создания
declare -a TOPICS=(
    "wb-keywords:3"
    "wb-campaigns:3" 
    "ozon-products:3"
    "onec-entities:3"
    "etl-logs:1"
)

# Создание топиков
for topic_config in "${TOPICS[@]}"; do
    TOPIC_NAME=$(echo $topic_config | cut -d: -f1)
    PARTITIONS=$(echo $topic_config | cut -d: -f2)
    
    echo "Создание топика: $TOPIC_NAME ($PARTITIONS разделов)"
    sudo -u $KAFKA_USER bash -c "
        $KAFKA_HOME/kafka/bin/kafka-topics.sh \
            --bootstrap-server $EXTERNAL_IP:$KAFKA_PORT \
            --create \
            --topic $TOPIC_NAME \
            --replication-factor 1 \
            --partitions $PARTITIONS || echo 'Топик $TOPIC_NAME уже существует'
    "
done

echo "✅ Проверка созданных топиков..."
sudo -u $KAFKA_USER bash -c "$KAFKA_HOME/kafka/bin/kafka-topics.sh --bootstrap-server $EXTERNAL_IP:$KAFKA_PORT --list"

echo ""
echo "==================================="
echo "🎉 Установка Kafka завершена!"
echo "==================================="
echo ""
echo "📋 Информация о инсталляции:"
echo "   • Версия: Apache Kafka $KAFKA_VERSION (KRaft)"
echo "   • Пользователь: $KAFKA_USER"
echo "   • Директория: $KAFKA_HOME"
echo "   • Контроллер: localhost:$CONTROLLER_PORT"
echo "   • Брокер (внешний): $EXTERNAL_IP:$KAFKA_PORT"
echo "   • UFW: порт $KAFKA_PORT открыт"
echo ""
echo "📋 Управление сервисом:"
echo "   • Статус:    systemctl status kafka"
echo "   • Остановка: systemctl stop kafka"
echo "   • Запуск:    systemctl start kafka"
echo "   • Перезапуск: systemctl restart kafka"
echo "   • Логи:      journalctl -u kafka -f"
echo ""
echo "📋 Тестирование:"
echo "   • Список топиков:"
echo "     $KAFKA_HOME/kafka/bin/kafka-topics.sh --bootstrap-server $EXTERNAL_IP:$KAFKA_PORT --list"
echo ""
echo "   • Отправка сообщения:"
echo "     echo 'test message' | $KAFKA_HOME/kafka/bin/kafka-console-producer.sh --bootstrap-server $EXTERNAL_IP:$KAFKA_PORT --topic wb-keywords"
echo ""
echo "   • Чтение сообщений:"
echo "     $KAFKA_HOME/kafka/bin/kafka-console-consumer.sh --bootstrap-server $EXTERNAL_IP:$KAFKA_PORT --topic wb-keywords --from-beginning"
echo ""
echo "🔧 Подключение клиентов:"
echo "   • Python kafka-python:"
echo "     bootstrap_servers=['$EXTERNAL_IP:$KAFKA_PORT']"
echo ""
echo "✅ Kafka готов к использованию в ETL пайплайне!"
echo ""

# Проверка успешности всей установки
FINAL_STATUS=0

if systemctl is-active --quiet kafka; then
    echo "✅ Сервис Kafka: РАБОТАЕТ"
else
    echo "❌ Сервис Kafka: НЕ РАБОТАЕТ"
    FINAL_STATUS=1
fi

if ss -tlnp | grep -q ":$KAFKA_PORT "; then
    echo "✅ Порт $KAFKA_PORT: ОТКРЫТ"
else
    echo "❌ Порт $KAFKA_PORT: НЕ ОТКРЫТ"
    FINAL_STATUS=1
fi

if sudo -u $KAFKA_USER bash -c "$KAFKA_HOME/kafka/bin/kafka-topics.sh --bootstrap-server $EXTERNAL_IP:$KAFKA_PORT --list" > /dev/null 2>&1; then
    echo "✅ Подключение к Kafka: УСПЕШНО"
else
    echo "❌ Подключению к Kafka: ОШИБКА"
    FINAL_STATUS=1
fi

if [[ $FINAL_STATUS -eq 0 ]]; then
    echo ""
    echo "🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! Kafka готов к работе."
else
    echo ""
    echo "⚠️  Обнаружены проблемы. Проверьте логи: journalctl -u kafka -n 50"
fi

exit $FINAL_STATUS
