import json
import tempfile
import unittest
from pathlib import Path

from scripts import novel_project


SITE = '''<!doctype html>
<html><body>
      <ol class="chapter-list">
        <li>
          <button class="chapter-button" data-go="0" aria-current="true">
            <span class="chapter-number">第一章</span>
            <span class="chapter-name">开始</span>
          </button>
        </li>
        <li>
          <button class="chapter-button" data-go="1" aria-current="false">
            <span class="chapter-number">第二章</span>
            <span class="chapter-name">继续</span>
          </button>
        </li>
      </ol>
        当前共两章<br>
      <article class="reading-card" id="readingCard">
        <section class="chapter active" data-title="第一章　开始">
          <div class="prose">
            <p>第一章正文足够长。</p>
          </div>
        </section>

        <section class="chapter" data-title="第二章　继续">
          <div class="prose">
            <p>第二章正文同样足够长。</p>
          </div>
        </section>
      </article>
</body></html>
'''


class NovelProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.site = self.root / "dist" / "index.html"
        self.work = self.root / "work" / "manuscript"
        self.site.parent.mkdir(parents=True)
        self.site.write_text(SITE, encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_extract_and_build_preserve_site(self):
        before = self.site.read_text(encoding="utf-8")
        novel_project.extract_project(self.site, self.work, force=False)
        novel_project.build_project(self.site, self.work, min_chars=1)
        self.assertEqual(before, self.site.read_text(encoding="utf-8"))

    def test_new_chapter_updates_toc_footer_and_sections(self):
        novel_project.extract_project(self.site, self.work, force=False)
        novel_project.new_chapter(self.work, "第三章　回家")
        chapter = self.work / "chapters" / "003.html"
        chapter.write_text(chapter.read_text(encoding="utf-8").replace("【待写】", "第三章正文已经完成。"), encoding="utf-8")
        novel_project.finalize_chapter(self.work, 3, min_chars=1)
        novel_project.build_project(self.site, self.work, min_chars=1)
        text = self.site.read_text(encoding="utf-8")
        self.assertIn('data-go="2"', text)
        self.assertIn("当前共三章<br>", text)
        self.assertIn('data-title="第三章　回家"', text)
        self.assertEqual(text.count('class="chapter active"'), 1)

    def test_validate_rejects_title_mismatch(self):
        novel_project.extract_project(self.site, self.work, force=False)
        chapter = self.work / "chapters" / "002.html"
        chapter.write_text(chapter.read_text(encoding="utf-8").replace("第二章　继续", "第二章　错误标题"), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "标题不一致"):
            novel_project.validate_project(self.site, self.work, min_chars=1, check_git=False)

    def test_finalize_refreshes_hash_and_status(self):
        novel_project.extract_project(self.site, self.work, force=False)
        manifest_path = self.work / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        old_hash = manifest["chapters"][1]["sha256"]
        chapter = self.work / "chapters" / "002.html"
        chapter.write_text(chapter.read_text(encoding="utf-8").replace("同样", "依然"), encoding="utf-8")
        novel_project.finalize_chapter(self.work, 2, min_chars=1)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertNotEqual(old_hash, manifest["chapters"][1]["sha256"])
        self.assertEqual("ready", manifest["chapters"][1]["status"])


if __name__ == "__main__":
    unittest.main()

