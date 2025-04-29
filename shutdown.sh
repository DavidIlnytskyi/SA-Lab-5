echo "Shutdown hazelcast"
bash ./bash-scripts/stop-hazelcast.sh
cd ./bash-scripts/

echo "Shutdown Kafka"
docker compose down

cd .. 

if ! rm logs/* 2>&1 | grep -q 'No such file'; then
  echo "Logs dir is cleaned."
else
  echo "Logs dir is empty."
fi


docker network rm hazelcast-network

kill $(lsof -ti :5001,5002,5003,5004,5005,5006,5007,5008)