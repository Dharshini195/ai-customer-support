from pathlib import Path

from sqlalchemy import func
from sqlalchemy.dialects.sqlite import insert

from app.database.models import KnowledgeBase
from app.database.session import SessionLocal


def parse(path: Path) -> list[tuple[str, str, str]]:
    """Split a section file into (section, title, content) rows, one per ## heading."""
    entries = []
    for block in path.read_text(encoding="utf-8").split("\n## ")[1:]:
        title, _, content = block.partition("\n")
        entries.append((path.stem, title.strip(), content.strip()))
    return entries


def main() -> None:
    with SessionLocal.begin() as session:
        for path in sorted(Path("knowledge_base").glob("*.md")):
            rows = parse(path)
            for section, title, content in rows:
                stmt = (
                    insert(KnowledgeBase)
                    .values(section=section, title=title, content=content)
                    .on_conflict_do_update(
                        index_elements=[
                            KnowledgeBase.section,
                            KnowledgeBase.title,
                        ],
                        set_={
                            "content": content,
                            "updated_at": func.current_timestamp(),
                        },
                    )
                )
                session.execute(stmt)
            print(f"{path.stem}: {len(rows)} entries")


if __name__ == "__main__":
    main()
