
from sqlalchemy import select, update, func
from sqlalchemy.dialects.sqlite import insert

from app.database.session import SessionLocal
from app.database.models import Event, KnowledgeBase, Ticket, Message


def start_event(gmail_message_id: str) -> dict | None:
    """
    Claim a message.
    Returns None when it is already handled or in progress.
    Allows retry when the previous attempt failed.
    """
    with SessionLocal.begin() as session:
        stmt = (
            insert(Event)
            .values(gmail_message_id=gmail_message_id)
            .on_conflict_do_update(
                index_elements=[Event.gmail_message_id],
                set_={
                    "attempts": Event.attempts + 1,
                    "status": "processing",
                    "error": None,
                },
                where=Event.status == "failed",
            )
            .returning(Event.id, Event.attempts)
        )

        row = session.execute(stmt).mappings().first()

        return dict(row) if row else None


def finish_event(event_id: int, status: str, result: dict) -> None:
    with SessionLocal.begin() as session:
        session.execute(
            update(Event)
            .where(Event.id == event_id)
            .values(
                status=status,
                result=result,
                processed_at=func.current_timestamp(),
            )
        )


def fail_event(event_id: int, error: str) -> None:
    with SessionLocal.begin() as session:
        session.execute(
            update(Event)
            .where(Event.id == event_id)
            .values(
                status="failed",
                error=error,
            )
        )


def upsert_ticket(
    gmail_thread_id: str,
    customer_email: str,
    subject: str,
) -> int:

    with SessionLocal.begin() as session:
        stmt = (
            insert(Ticket)
            .values(
                gmail_thread_id=gmail_thread_id,
                customer_email=customer_email,
                subject=subject,
            )
            .on_conflict_do_update(
                index_elements=[Ticket.gmail_thread_id],
                set_={"updated_at": func.current_timestamp()},
            )
            .returning(Ticket.id)
        )

        return session.execute(stmt).scalar_one()


def update_ticket(
    ticket_id: int,
    status: str,
    category: str | None = None,
    proposed_action: str | None = None,
) -> None:

    with SessionLocal.begin() as session:
        session.execute(
            update(Ticket)
            .where(Ticket.id == ticket_id)
            .values(
                status=status,
                category=func.coalesce(category, Ticket.category),
                proposed_action=proposed_action,
                updated_at=func.current_timestamp(),
            )
        )


def save_message(
    ticket_id: int,
    gmail_message_id: str,
    direction: str,
    from_address: str,
    body: str,
) -> None:

    with SessionLocal.begin() as session:
        stmt = (
            insert(Message)
            .values(
                ticket_id=ticket_id,
                gmail_message_id=gmail_message_id,
                direction=direction,
                from_address=from_address,
                body=body,
            )
            .on_conflict_do_nothing(
                index_elements=[Message.gmail_message_id]
            )
        )

        session.execute(stmt)


def list_sections() -> list[str]:
    with SessionLocal() as session:
        rows = session.execute(
            select(KnowledgeBase.section)
            .distinct()
            .order_by(KnowledgeBase.section)
        ).scalars().all()
        return list(rows)


def get_section(section: str) -> list[dict]:
    with SessionLocal() as session:
        rows = session.execute(
            select(KnowledgeBase.title, KnowledgeBase.content)
            .where(KnowledgeBase.section == section)
            .order_by(KnowledgeBase.id)
        ).mappings().all()
        return [dict(row) for row in rows]
