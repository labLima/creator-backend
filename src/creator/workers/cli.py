from __future__ import annotations

import argparse
import logging
import threading
import time

from redis import Redis
from rq import Queue, Worker

from creator.config import get_settings
from creator.workers.image_generation import recover_stale_processing_jobs


def main() -> None:
    parser = argparse.ArgumentParser(prog="creator-worker")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("image-generation")
    subparsers.add_parser("agent-workflow")
    subparsers.add_parser("pipeline-outbox")
    subparsers.add_parser("all", help="Run the shared RQ worker and the outbox publisher loop.")
    args = parser.parse_args()

    logging.basicConfig(level=get_settings().log_level)
    if args.command == "image-generation":
        run_image_generation_worker()
    elif args.command == "agent-workflow":
        run_agent_workflow_worker()
    elif args.command == "pipeline-outbox":
        run_pipeline_outbox_worker()
    elif args.command == "all":
        run_all_workers()


def _queue_and_connection() -> tuple[Queue, Redis]:
    settings = get_settings()
    connection = Redis.from_url(settings.redis_url)
    return Queue(settings.generation_queue_name, connection=connection), connection


def run_image_generation_worker() -> None:
    recover_stale_processing_jobs()
    queue, connection = _queue_and_connection()
    Worker([queue], connection=connection).work(with_scheduler=True)


def run_agent_workflow_worker() -> None:
    queue, connection = _queue_and_connection()
    Worker([queue], connection=connection).work(with_scheduler=True)


def run_pipeline_outbox_worker() -> None:
    from creator.workers.pipeline_events import publish_pipeline_outbox_once

    while True:
        try:
            publish_pipeline_outbox_once()
        except Exception:
            logging.getLogger(__name__).exception("pipeline_outbox_publish_failed")
        time.sleep(1)


def run_all_workers() -> None:
    recover_stale_processing_jobs()
    outbox_thread = threading.Thread(target=run_pipeline_outbox_worker, daemon=True)
    outbox_thread.start()
    queue, connection = _queue_and_connection()
    Worker([queue], connection=connection).work(with_scheduler=True)
