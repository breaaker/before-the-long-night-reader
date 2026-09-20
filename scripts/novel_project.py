#!/usr/bin/env python3
"""Manage private chapter sources and rebuild the public novel reader."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SITE = ROOT / "dist" / "index.html"
DEFAULT_WORK = ROOT / "work" / "manuscript"
SECTION_RE = re.compile(
    r'(?P<section>^[ \t]*<section class="chapter(?: active)?" data-title="(?P<title>[^"]+)">.*?^[ \t]*</section>)',
    re.MULTILINE | re.DOTALL,
)
TITLE_RE = re.compile(r"^(第[^章]+章)[　 ]+(.+)$")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(text)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def prose_chars(section: str) -> int:
    plain = re.sub(r"<[^>]+>", "", section)
    return len(re.sub(r"\s+", "", plain))


def extract_sections(site_text: str) -> list[dict[str, str]]:
    sections = []
    for match in SECTION_RE.finditer(site_text):
        sections.append({"title": match.group("title"), "section": match.group("section")})
    if not sections:
        raise ValueError("网页中没有找到正文章节")
    return sections


def load_manifest(work_dir: Path) -> dict:
    path = work_dir / "manifest.json"
    if not path.exists():
        raise ValueError(f"缺少章节清单：{path}")
    data = json.loads(read_text(path))
    if data.get("version") != 1 or not isinstance(data.get("chapters"), list):
        raise ValueError("章节清单格式无效")
    return data


def save_manifest(work_dir: Path, manifest: dict) -> None:
    atomic_write(work_dir / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def normalize_active(section: str, active: bool) -> str:
    replacement = 'class="chapter active"' if active else 'class="chapter"'
    return re.sub(r'class="chapter(?: active)?"', replacement, section, count=1)


def parse_title(title: str) -> tuple[str, str]:
    match = TITLE_RE.match(title)
    if not match:
        raise ValueError(f"章节标题格式错误：{title}")
    return match.group(1), match.group(2)


def chinese_total_label(title: str) -> str:
    number, _ = parse_title(title)
    return number.removeprefix("第").removesuffix("章")


def render_toc(chapters: list[dict]) -> str:
    lines = []
    for index, chapter in enumerate(chapters):
        number, name = parse_title(chapter["title"])
        current = "true" if index == 0 else "false"
        lines.extend(
            [
                "        <li>",
                f'          <button class="chapter-button" data-go="{index}" aria-current="{current}">',
                f'            <span class="chapter-number">{number}</span>',
                f'            <span class="chapter-name">{name}</span>',
                "          </button>",
                "        </li>",
            ]
        )
    return "\n".join(lines)


def validate_fragment(section: str, expected_title: str, min_chars: int) -> tuple[int, str]:
    match = SECTION_RE.fullmatch(section)
    if not match:
        raise ValueError(f"章节片段结构无效：{expected_title}")
    actual_title = match.group("title")
    if actual_title != expected_title:
        raise ValueError(f"标题不一致：清单为《{expected_title}》，正文为《{actual_title}》")
    if section.count("<section") != 1 or section.count("</section>") != 1:
        raise ValueError(f"章节 section 标签失衡：{expected_title}")
    if section.count("<div") != section.count("</div>"):
        raise ValueError(f"章节 div 标签失衡：{expected_title}")
    if "<script" in section or "<style" in section:
        raise ValueError(f"章节正文不允许包含脚本或样式：{expected_title}")
    count = prose_chars(section)
    if count < min_chars:
        raise ValueError(f"章节正文过短：{expected_title}，当前 {count} 字，至少 {min_chars} 字")
    return count, sha256(section)


def extract_project(site_path: Path, work_dir: Path, force: bool) -> dict:
    manifest_path = work_dir / "manifest.json"
    chapters_dir = work_dir / "chapters"
    if (manifest_path.exists() or chapters_dir.exists()) and not force:
        raise ValueError("本地稿源已存在；如确认重建，请使用 --force")
    sections = extract_sections(read_text(site_path))
    chapters_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for index, item in enumerate(sections, start=1):
        filename = f"{index:03d}.html"
        section = normalize_active(item["section"].rstrip("\n"), active=index == 1)
        atomic_write(chapters_dir / filename, section + "\n")
        entries.append(
            {
                "index": index,
                "title": item["title"],
                "file": f"chapters/{filename}",
                "status": "published",
                "chars": prose_chars(section),
                "sha256": sha256(section),
            }
        )
    manifest = {"version": 1, "chapters": entries}
    save_manifest(work_dir, manifest)
    return manifest


def new_chapter(work_dir: Path, title: str) -> Path:
    parse_title(title)
    manifest = load_manifest(work_dir)
    next_index = len(manifest["chapters"]) + 1
    filename = f"{next_index:03d}.html"
    path = work_dir / "chapters" / filename
    if path.exists():
        raise ValueError(f"章节文件已存在：{path}")
    section = (
        f'        <section class="chapter" data-title="{title}">\n'
        "          <div class=\"prose\">\n"
        "            <p>【待写】</p>\n"
        "          </div>\n"
        "        </section>\n"
    )
    atomic_write(path, section)
    manifest["chapters"].append(
        {
            "index": next_index,
            "title": title,
            "file": f"chapters/{filename}",
            "status": "draft",
            "chars": prose_chars(section),
            "sha256": sha256(section.rstrip("\n")),
        }
    )
    save_manifest(work_dir, manifest)
    return path


def finalize_chapter(work_dir: Path, index: int, min_chars: int) -> dict:
    manifest = load_manifest(work_dir)
    if index < 1 or index > len(manifest["chapters"]):
        raise ValueError(f"章节编号超出范围：{index}")
    entry = manifest["chapters"][index - 1]
    section = read_text(work_dir / entry["file"]).rstrip("\n")
    count, digest = validate_fragment(section, entry["title"], min_chars)
    entry.update({"status": "ready", "chars": count, "sha256": digest})
    save_manifest(work_dir, manifest)
    return entry


def mark_published(work_dir: Path, index: int) -> dict:
    manifest = load_manifest(work_dir)
    if index < 1 or index > len(manifest["chapters"]):
        raise ValueError(f"章节编号超出范围：{index}")
    entry = manifest["chapters"][index - 1]
    if entry["status"] != "ready":
        raise ValueError("只有 ready 状态的章节可以标记为 published")
    entry["status"] = "published"
    save_manifest(work_dir, manifest)
    return entry


def load_and_validate_sources(work_dir: Path, min_chars: int) -> tuple[dict, list[str]]:
    manifest = load_manifest(work_dir)
    chapters = manifest["chapters"]
    if not chapters:
        raise ValueError("章节清单为空")
    seen_titles = set()
    sections = []
    for expected_index, entry in enumerate(chapters, start=1):
        if entry.get("index") != expected_index:
            raise ValueError(f"章节编号不连续：期望 {expected_index}")
        if entry["title"] in seen_titles:
            raise ValueError(f"章节标题重复：{entry['title']}")
        seen_titles.add(entry["title"])
        path = work_dir / entry["file"]
        if not path.exists():
            raise ValueError(f"章节文件缺失：{path}")
        section = read_text(path).rstrip("\n")
        count, digest = validate_fragment(section, entry["title"], min_chars)
        if entry.get("status") == "draft":
            raise ValueError(f"章节仍为 draft：{entry['title']}，请先运行 finalize")
        if entry.get("chars") != count or entry.get("sha256") != digest:
            raise ValueError(f"章节清单已过期：{entry['title']}，请运行 finalize")
        sections.append(normalize_active(section, active=expected_index == 1))
    return manifest, sections


def rebuild_site_text(site_text: str, manifest: dict, sections: list[str]) -> str:
    matches = list(SECTION_RE.finditer(site_text))
    if not matches:
        raise ValueError("发布网页中没有找到章节区")
    chapter_block = "\n\n".join(sections)
    site_text = site_text[: matches[0].start()] + chapter_block + site_text[matches[-1].end() :]

    toc_match = re.search(r'(?P<open>^[ \t]*<ol class="chapter-list">\n).*?(?P<close>^[ \t]*</ol>)', site_text, re.MULTILINE | re.DOTALL)
    if not toc_match:
        raise ValueError("发布网页中没有找到章节目录")
    toc = render_toc(manifest["chapters"])
    site_text = site_text[: toc_match.end("open")] + toc + "\n" + site_text[toc_match.start("close") :]

    total_match = re.search(r"当前共[^<\n]+章<br>", site_text)
    if not total_match:
        raise ValueError("发布网页中没有找到总章数")
    # A no-op rebuild must be byte-for-byte stable. Existing sites may use a
    # colloquial numeral such as “两章”, so only rewrite the label when the
    # chapter count actually changes.
    if len(manifest["chapters"]) != len(matches):
        total = chinese_total_label(manifest["chapters"][-1]["title"])
        site_text = site_text[: total_match.start()] + f"当前共{total}章<br>" + site_text[total_match.end() :]
    return site_text


def build_project(site_path: Path, work_dir: Path, min_chars: int) -> None:
    manifest, sections = load_and_validate_sources(work_dir, min_chars)
    original = read_text(site_path)
    rebuilt = rebuild_site_text(original, manifest, sections)
    validate_site_text(rebuilt, manifest)
    atomic_write(site_path, rebuilt)


def validate_site_text(site_text: str, manifest: dict) -> None:
    sections = extract_sections(site_text)
    expected_titles = [entry["title"] for entry in manifest["chapters"]]
    actual_titles = [item["title"] for item in sections]
    if actual_titles != expected_titles:
        raise ValueError("发布网页章节顺序或标题与清单不一致")
    if site_text.count('class="chapter active"') != 1:
        raise ValueError("发布网页必须且只能有一个 active 章节")
    buttons = re.findall(r'class="chapter-button" data-go="(\d+)"', site_text)
    if buttons != [str(i) for i in range(len(expected_titles))]:
        raise ValueError("发布网页目录索引不连续")
    if site_text.count("<section") != site_text.count("</section>"):
        raise ValueError("发布网页 section 标签失衡")
    if site_text.count("<div") != site_text.count("</div>"):
        raise ValueError("发布网页 div 标签失衡")


def ensure_private_work_is_untracked(root: Path) -> None:
    if not (root / ".git").exists():
        return
    result = subprocess.run(
        ["git", "ls-files", "work"], cwd=root, text=True, capture_output=True, check=True
    )
    tracked = [line for line in result.stdout.splitlines() if line.strip()]
    if tracked:
        raise ValueError("私密 work/ 文件被 Git 跟踪：" + ", ".join(tracked))


def validate_project(site_path: Path, work_dir: Path, min_chars: int, check_git: bool = True) -> dict:
    manifest, _ = load_and_validate_sources(work_dir, min_chars)
    validate_site_text(read_text(site_path), manifest)
    if check_git:
        ensure_private_work_is_untracked(ROOT)
    return manifest


def print_status(site_path: Path, work_dir: Path) -> None:
    manifest = load_manifest(work_dir)
    chapters = manifest["chapters"]
    published = [entry for entry in chapters if entry["status"] == "published"]
    ready = [entry for entry in chapters if entry["status"] == "ready"]
    drafts = [entry for entry in chapters if entry["status"] == "draft"]
    print(f"章节总数: {len(chapters)}")
    print(f"已发布: {len(published)}")
    print(f"待发布: {len(ready)}")
    print(f"草稿: {len(drafts)}")
    print(f"当前末章: {chapters[-1]['title']}")
    print(f"下一章编号: {len(chapters) + 1:03d}")
    print(f"公开网页: {site_path}")
    print(f"私密稿源: {work_dir}")


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=DEFAULT_SITE)
    parser.add_argument("--work", type=Path, default=DEFAULT_WORK)
    parser.add_argument("--min-chars", type=int, default=3000)
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract = subparsers.add_parser("extract", help="从当前网页初始化私密章节稿源")
    extract.add_argument("--force", action="store_true")

    new = subparsers.add_parser("new", help="创建下一章草稿")
    new.add_argument("--title", required=True)

    finalize = subparsers.add_parser("finalize", help="校验并冻结一章的字数与哈希")
    finalize.add_argument("index", type=int)

    published = subparsers.add_parser("mark-published", help="在上线验证后标记章节已发布")
    published.add_argument("index", type=int)

    subparsers.add_parser("build", help="由私密稿源重建公开网页")
    subparsers.add_parser("validate", help="校验稿源、目录和公开网页")
    subparsers.add_parser("status", help="显示本地创作状态")
    return parser


def main() -> int:
    args = make_parser().parse_args()
    try:
        if args.command == "extract":
            manifest = extract_project(args.site, args.work, args.force)
            print(f"已提取 {len(manifest['chapters'])} 章到 {args.work}")
        elif args.command == "new":
            print(new_chapter(args.work, args.title))
        elif args.command == "finalize":
            entry = finalize_chapter(args.work, args.index, args.min_chars)
            print(f"已冻结：{entry['title']}（{entry['chars']} 字）")
        elif args.command == "mark-published":
            entry = mark_published(args.work, args.index)
            print(f"已标记发布：{entry['title']}")
        elif args.command == "build":
            build_project(args.site, args.work, args.min_chars)
            print(f"已重建：{args.site}")
        elif args.command == "validate":
            manifest = validate_project(args.site, args.work, args.min_chars)
            print(f"校验通过：{len(manifest['chapters'])} 章")
        elif args.command == "status":
            print_status(args.site, args.work)
    except (ValueError, OSError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
