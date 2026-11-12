from __future__ import annotations

import time

from confluent_kafka.admin import AdminClient, NewTopic


def ensure_topic(bootstrap: str, topic: str, partitions: int = 3, attempts: int = 30) -> None:
    """Create the topic with a fixed partition count before anyone can auto-create it with one."""
    admin = AdminClient({"bootstrap.servers": bootstrap})
    for attempt in range(attempts):
        try:
            if topic in admin.list_topics(timeout=5).topics:
                return
            futures = admin.create_topics([NewTopic(topic, num_partitions=partitions, replication_factor=1)])
            for future in futures.values():
                try:
                    future.result()
                except Exception as exc:  # another process created it first
                    if "TOPIC_ALREADY_EXISTS" not in str(exc):
                        raise
            return
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(2)
