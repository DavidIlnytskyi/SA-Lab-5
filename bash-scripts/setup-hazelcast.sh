#!/bin/bash
docker run -d --rm -v "$(pwd)"/hazelcast-configs/hazelcast-one.xml:/opt/hazelcast/hazelcast-docker.xml \
    -e HAZELCAST_CONFIG=hazelcast-docker.xml \
    --network hazelcast-network \
    --ip 172.18.0.10 \
    --name hazelcast-node-one \
    -p 5701:5701 \
    hazelcast/hazelcast:latest


docker run -d --rm -v "$(pwd)"/hazelcast-configs/hazelcast-two.xml:/opt/hazelcast/hazelcast-docker.xml \
    -e HAZELCAST_CONFIG=hazelcast-docker.xml \
    --network hazelcast-network \
    --ip 172.18.0.11 \
    --name hazelcast-node-two \
    -p 5702:5701 \
    hazelcast/hazelcast:latest


docker run -d --rm -v "$(pwd)"/hazelcast-configs/hazelcast-three.xml:/opt/hazelcast/hazelcast-docker.xml \
    -e HAZELCAST_CONFIG=hazelcast-docker.xml \
    --network hazelcast-network \
    --ip 172.18.0.12 \
    --name hazelcast-node-three \
    -p 5703:5701 \
    hazelcast/hazelcast:latest
