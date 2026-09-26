FROM confluentinc/cp-kafka-connect:7.7.1

RUN confluent-hub install --no-prompt mongodb/kafka-connect-mongodb:latest
RUN confluent-hub install --no-prompt debezium/debezium-connector-mongodb:latest
RUN confluent-hub install --no-prompt confluentinc/kafka-connect-elasticsearch:latest
RUN confluent-hub install --no-prompt confluentinc/kafka-connect-s3:latest
