from kafka import KafkaProducer, KafkaConsumer
import os

KAFKA_BROKER = os.getenv('KAFKA_BROKER', '127.0.0.1:9092')


def produce_message(topic, message):
    producer = KafkaProducer(bootstrap_servers=KAFKA_BROKER)
    producer.send(topic, message.encode())
    producer.close()


def consume_messages(topic):
    consumer = KafkaConsumer(topic, bootstrap_servers=KAFKA_BROKER)
    for message in consumer:
        print(f'Received message: {message.value.decode()}')
