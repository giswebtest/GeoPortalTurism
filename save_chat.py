"""
Збереження чату Claude Code у Markdown-файл.
Використання:
    python save_chat.py              — зберігає поточну (найновішу) сесію
    python save_chat.py <session_id> — зберігає конкретну сесію
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime

CLAUDE_DIR = Path.home() / ".claude" / "projects" / "D--GeoPortalTurism-GeoPortalTurism"
OUTPUT_DIR = Path(__file__).parent / "chats"


def find_sessions():
    return sorted(CLAUDE_DIR.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)


def parse_jsonl(path):
    messages = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                msg = obj.get("message", obj)
                role = msg.get("role", "")
                content = msg.get("content", "")

                if isinstance(content, list):
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                text_parts.append(block.get("text", ""))
                        elif isinstance(block, str):
                            text_parts.append(block)
                    content = "\n".join(text_parts)

                if role and content:
                    messages.append({"role": role, "content": content.strip()})
            except (json.JSONDecodeError, AttributeError):
                continue
    return messages


def save_markdown(messages, session_id, output_path):
    lines = [
        f"# Чат Claude Code — GeoPortalTurism",
        f"**Сесія:** `{session_id}`",
        f"**Збережено:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Повідомлень:** {len(messages)}",
        "",
        "---",
        "",
    ]

    for msg in messages:
        role = msg["role"]
        content = msg["content"]

        if role == "user":
            lines.append(f"## 👤 Користувач\n")
            lines.append(f"{content}\n")
        elif role == "assistant":
            lines.append(f"## 🤖 Claude\n")
            lines.append(f"{content}\n")

        lines.append("---\n")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    sessions = find_sessions()
    if not sessions:
        print("❌ Сесії не знайдено")
        return

    if len(sys.argv) > 1:
        session_id = sys.argv[1]
        path = CLAUDE_DIR / f"{session_id}.jsonl"
        if not path.exists():
            print(f"❌ Сесія {session_id} не знайдена")
            return
    else:
        path = sessions[0]
        session_id = path.stem

    print(f"📂 Читаю: {path.name}")
    messages = parse_jsonl(path)
    print(f"📝 Повідомлень: {len(messages)}")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out = OUTPUT_DIR / f"chat_{timestamp}_{session_id[:8]}.md"
    save_markdown(messages, session_id, out)

    print(f"✅ Збережено: {out}")
    print(f"   Розмір: {out.stat().st_size // 1024} KB")

    # Показати список всіх сесій
    print("\n📋 Всі сесії:")
    for s in sessions:
        mtime = datetime.fromtimestamp(s.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        size = s.stat().st_size // 1024
        marker = " ← поточна" if s == sessions[0] else ""
        print(f"   {mtime}  {s.name}  ({size} KB){marker}")


if __name__ == "__main__":
    main()
