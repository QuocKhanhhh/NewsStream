import logging

from src.models.news import News
from src.exporters.base_exporter import BaseExporter
from src.clients.kafka_client import KafkaClient

logger = logging.getLogger(__name__)


class ExportError(RuntimeError):
    def __init__(self, failed_records: list[News]):
        self.failed_records = failed_records
        super().__init__(f"Failed to export {len(failed_records)} news record(s)")


class KafkaExporter(BaseExporter):
    def __init__(self, kafka_client: KafkaClient, topic: str, dlq_topic: str | None = None):
        self.kafka_client = kafka_client
        self.topic = topic
        self.dlq_topic = dlq_topic

    def export(self, records: list[News]) -> int:
        """
        Exports a list of News records to a Kafka topic.

        Args:
            records (list[News]): The list of News records to be exported.

        Returns:
            int: The number of successfully exported records.
        """
        success_count = 0
        failed_records = []
        for record in records:
            try:
                self.export_one(record)
                success_count += 1
            except Exception as e:
                failed_records.append(record)
                logger.exception("Failed to export record %s", record._id)
                self._publish_dlq(record, e)
        if failed_records:
            raise ExportError(failed_records)
        return success_count

    def _publish_dlq(self, record: News, error: Exception) -> None:
        if not self.dlq_topic:
            return
        try:
            self.kafka_client.publish(
                topic=self.dlq_topic,
                key=record._id,
                message={
                    "error": str(error),
                    "record": record.to_dict(),
                },
            )
        except Exception:
            logger.exception("Failed to publish record %s to DLQ", record._id)
    
    def export_one(self, record: News):
        message = record.to_dict()
        self.kafka_client.publish(
            topic=self.topic,
            key=record._id,
            message=message
        )
