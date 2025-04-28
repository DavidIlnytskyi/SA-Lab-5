#!/bin/bash

if ! docker network create --subnet=172.18.0.0/16 hazelcast-network 2>&1 | grep -q 'already exists'; then
  echo "Hazelcast network created."
else
  echo "Hazelcast network already exists."
fi

bash ./bash-scripts/setup-hazelcast.sh

cd ./bash-scripts

docker compose up -d

echo "Waiting for Kafka to be ready..."
while ! docker exec kafka-1 bash -c "</dev/tcp/localhost/19092" &> /dev/null; do
  echo "Kafka 1 is not ready yet. Waiting 2 seconds..."
  sleep 2
done

while ! docker exec kafka-2 bash -c "</dev/tcp/localhost/19093" &> /dev/null; do
  echo "Kafka 2  is not ready yet. Waiting 2 seconds..."
  sleep 2
done

while ! docker exec kafka-3 bash -c "</dev/tcp/localhost/19094" &> /dev/null; do
  echo "Kafka 3 is not ready yet. Waiting 2 seconds..."
  sleep 2
done

echo "Kafka is ready!"

if ! docker exec -it kafka-1 kafka-topics --create --topic messages \
  --bootstrap-server kafka-1:19092 \
  --replication-factor 3 \
  --partitions 3 2>&1 | grep -q 'exist'; then
  echo "Messages topic created."
else
  echo "Messages topic already exists."
fi

cd ..

if ! rm logs/* 2>&1 | grep -q 'No such file'; then
  echo "Logs dir is cleaned."
else
  echo "Logs dir is empty."
fi


python3 python-scripts/setup.py
