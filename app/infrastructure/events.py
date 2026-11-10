"""Publicação de eventos no Azure Service Bus."""

from __future__ import annotations

import json
import logging

log = logging.getLogger("pmining.events")


class ServiceBusPublisher:
    def __init__(self, connection_string: str):
        from azure.servicebus import ServiceBusClient

        self._client = ServiceBusClient.from_connection_string(connection_string)

    def publish(self, queue: str, body: dict) -> None:
        from azure.servicebus import ServiceBusMessage

        with self._client.get_queue_sender(queue_name=queue) as sender:
            sender.send_messages(ServiceBusMessage(json.dumps(body), content_type="application/json"))
        log.info("evento publicado em %s: %s", queue, body)


class LogOnlyPublisher:
    """Usado em desenvolvimento local, sem Service Bus configurado."""

    def __init__(self):
        self.sent: list[tuple[str, dict]] = []

    def publish(self, queue: str, body: dict) -> None:
        self.sent.append((queue, body))
        log.warning("SERVICEBUS_CONNECTION ausente; evento não enviado (%s): %s", queue, body)
