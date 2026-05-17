"""Prism concepts：跨 topic 概念标签管理。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from prism.scripts.topic import list_topics, read_topic

PRISM_ROOT = Path(__file__).resolve().parent.parent
CONCEPTS_FILE = PRISM_ROOT / "concepts.yaml"


def _load_concepts() -> dict[str, Any]:
    if not CONCEPTS_FILE.exists():
        return {"concepts": []}
    with open(CONCEPTS_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or {"concepts": []}


def _save_concepts(data: dict[str, Any]) -> None:
    CONCEPTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONCEPTS_FILE, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)


def list_concepts() -> list[dict[str, Any]]:
    """列出所有概念。"""
    data = _load_concepts()
    return data.get("concepts", [])


def add_concept(
    name: str,
    aliases: list[str] | None = None,
    description: str = "",
    related_concepts: list[str] | None = None,
) -> None:
    """添加新概念。"""
    data = _load_concepts()
    existing = {c["name"] for c in data.get("concepts", [])}
    if name in existing:
        raise ValueError(f"概念已存在: {name}")
    new_concept = {
        "name": name,
        "aliases": aliases or [],
        "description": description,
        "related_concepts": related_concepts or [],
    }
    data["concepts"].append(new_concept)
    _save_concepts(data)


def find_topics_by_concept(concept: str) -> list[dict[str, Any]]:
    """查找所有标注了某概念的 topic。"""
    topics = list_topics()
    result = []
    for t in topics:
        t_concepts = t.get("concepts", [])
        if concept in t_concepts:
            result.append(t)
        # 也检查别名
        for c in list_concepts():
            if c["name"] == concept and concept in t_concepts:
                result.append(t)
            elif concept in c.get("aliases", []) and c["name"] in t_concepts:
                result.append(t)
    return result


def find_concepts_in_topic(slug: str, variant: str) -> list[str]:
    """查找某 topic 标注的所有概念。"""
    try:
        t = read_topic(slug, variant)
        return t.get("concepts", [])
    except Exception:
        return []


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Prism concepts 管理")
    subparsers = parser.add_subparsers(dest="cmd")

    # list
    list_parser = subparsers.add_parser("list", help="列出所有概念")

    # add
    add_parser = subparsers.add_parser("add", help="添加新概念")
    add_parser.add_argument("name", help="概念名称")
    add_parser.add_argument("--alias", "-a", action="append", dest="aliases", default=[], help="别名")
    add_parser.add_argument("--desc", "-d", default="", help="描述")
    add_parser.add_argument("--related", "-r", action="append", dest="related", default=[], help="相关概念")

    # find-topics
    find_topics_parser = subparsers.add_parser("find-topics", help="查找标注了某概念的 topic")
    find_topics_parser.add_argument("concept", help="概念名称")

    # find-concepts
    find_concepts_parser = subparsers.add_parser("find-concepts", help="查找某 topic 标注的概念")
    find_concepts_parser.add_argument("slug", help="topic slug")
    find_concepts_parser.add_argument("variant", help="variant")

    args = parser.parse_args()

    if args.cmd == "list":
        concepts = list_concepts()
        print(f"共 {len(concepts)} 个概念:")
        for c in concepts:
            print(f"  - {c['name']}")
            if c.get("aliases"):
                print(f"    别名: {', '.join(c['aliases'])}")
            if c.get("description"):
                print(f"    {c['description']}")
    elif args.cmd == "add":
        add_concept(args.name, args.aliases, args.desc, args.related)
        print(f"已添加概念: {args.name}")
    elif args.cmd == "find-topics":
        topics = find_topics_by_concept(args.concept)
        print(f"标注了 '{args.concept}' 的 topic:")
        for t in topics:
            print(f"  - {t['slug']} ({t['variant']})")
    elif args.cmd == "find-concepts":
        concepts = find_concepts_in_topic(args.slug, args.variant)
        print(f"{args.slug}/{args.variant} 标注的概念:")
        for c in concepts:
            print(f"  - {c}")
