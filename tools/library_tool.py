# tools/library_tool.py
import json, os
from typing import List, Dict, Tuple

LIB_PATH = "data/library.json"

def _ensure_file():
    os.makedirs(os.path.dirname(LIB_PATH), exist_ok=True)
    if not os.path.exists(LIB_PATH):
        with open(LIB_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)

def load_library() -> List[Dict]:
    _ensure_file()
    with open(LIB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def add_to_library(entry: Dict) -> Tuple[bool, str]:
    """
    저장 성공 여부와 메시지를 반환.
    중복 기준: (title.strip(), year)
    """
    _ensure_file()
    lib = load_library()
    key = (entry.get("title","").strip(), entry.get("year"))
    keys = {(e.get("title","").strip(), e.get("year")) for e in lib}
    if key in keys:
        return False, "이미 저장된 항목입니다."

    lib.append(entry)
    with open(LIB_PATH, "w", encoding="utf-8") as f:
        json.dump(lib, f, ensure_ascii=False, indent=2)
    return True, "저장 완료! (data/library.json)"

def clear_library() -> None:
    with open(LIB_PATH, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)