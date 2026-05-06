from backend.smtp.outbound import send_direct
from backend.tasks.celery_app import celery_app
from backend.tasks.task_db import run_async


@celery_app.task(bind=True, max_retries=3, queue="email")
def deliver_email(self, payload: dict) -> str:
    backoffs = [60, 300, 900]
    try:
        run_async(
            send_direct(
                from_addr=payload["from_addr"],
                to_list=payload["to_list"],
                subject=payload["subject"],
                body_text=payload["body_text"],
                body_html=payload.get("body_html"),
            )
        )
        return "sent"
    except Exception as exc:
        if self.request.retries < len(backoffs):
            raise self.retry(exc=exc, countdown=backoffs[self.request.retries])
        raise
