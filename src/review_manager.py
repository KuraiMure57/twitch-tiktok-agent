import json
import sys
from datetime import datetime, timezone
from pathlib import Path


VALID_STATES = {
    "pending",
    "approved",
    "rejected",
    "revision_requested",
}


def create_review_state(
    metadata_path: str,
    output_path: str,
) -> None:
    metadata_file = Path(metadata_path)
    output_file = Path(output_path)

    if not metadata_file.exists():
        raise FileNotFoundError(
            f"No existe el archivo de metadata: {metadata_file}"
        )

    with metadata_file.open("r", encoding="utf-8") as file:
        metadata = json.load(file)

    state = {
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "revision_count": 0,
        "metadata": metadata,
        "corrections": [],
    }

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(
            state,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print("Estado de revisión creado correctamente.")
    print("Estado: pending")


def update_review_state(
    state_path: str,
    status: str,
    correction: str | None = None,
) -> None:
    state_file = Path(state_path)

    if not state_file.exists():
        raise FileNotFoundError(
            f"No existe el estado de revisión: {state_file}"
        )

    if status not in VALID_STATES:
        raise ValueError(
            f"Estado no válido: {status}. "
            f"Estados permitidos: {', '.join(sorted(VALID_STATES))}"
        )

    with state_file.open("r", encoding="utf-8") as file:
        state = json.load(file)

    state["status"] = status
    state["updated_at"] = datetime.now(timezone.utc).isoformat()

    if status == "revision_requested":
        state["revision_count"] = state.get(
            "revision_count",
            0,
        ) + 1

        if correction:
            state.setdefault("corrections", []).append(
                {
                    "timestamp": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "text": correction,
                }
            )

    with state_file.open("w", encoding="utf-8") as file:
        json.dump(
            state,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print("Estado de revisión actualizado correctamente.")
    print(f"Estado: {status}")

    if correction:
        print(f"Corrección: {correction}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Uso:\n"
            "  python src/review_manager.py create "
            "<metadata.json> <review_state.json>\n"
            "  python src/review_manager.py update "
            "<review_state.json> <status> [correction]"
        )
        sys.exit(1)

    action = sys.argv[1]

    if action == "create":
        if len(sys.argv) != 4:
            print(
                "Uso: python src/review_manager.py create "
                "<metadata.json> <review_state.json>"
            )
            sys.exit(1)

        create_review_state(
            sys.argv[2],
            sys.argv[3],
        )

    elif action == "update":
        if len(sys.argv) < 4 or len(sys.argv) > 5:
            print(
                "Uso: python src/review_manager.py update "
                "<review_state.json> <status> [correction]"
            )
            sys.exit(1)

        correction = sys.argv[4] if len(sys.argv) == 5 else None

        update_review_state(
            sys.argv[2],
            sys.argv[3],
            correction,
        )

    else:
        print(f"Acción desconocida: {action}")
        sys.exit(1)
