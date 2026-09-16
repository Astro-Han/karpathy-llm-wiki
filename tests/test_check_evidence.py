import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_evidence.py"

RAW_CONTENT = """# Ghostty Update

> Source: https://example.com/ghostty
> Collected: 2026-04-17
> Published: 2026-04-16

Ghostty reached 42K stars on GitHub in April 2026.
The maintainer said "the terminal should feel invisible to users" in the interview.
Daily active users reached 10,000 by March.
"""

ARTICLE_CONTENT = """# Ghostty

> Sources: Example, 2026-04-16
> Raw: [ghostty](../../raw/ai-research/2026-04-17-ghostty.md)

## Overview

Ghostty has 42K stars and reached 10,000 daily active users.
The maintainer said "the terminal should feel invisible to users".

## Growth

Forks grew to 3,020 last week.
Install with `--limit 9000` after downloading.

```
example 78K and 9,999
```

> **Status: Outdated** (2026-07-23)
> The forks situation changed after this was written.
"""

SENTENCE_FINAL_RAW = """# Numbers

> Source: https://example.com/numbers
> Collected: 2026-06-01
> Published: Unknown

Revenue hit 42K. Uptime was 99.9%. The round closed on 2026-06-15.
"""

SENTENCE_FINAL_ARTICLE = """# Sentence final

> Sources: Example, 2026-06-01
> Raw: [numbers](../../raw/t/numbers.md)

Revenue hit 42K and uptime was 99.9%. The round closed on 2026-06-15.
"""

STATUS_EXPLANATION_ARTICLE = """# Status article

> Sources: Example, 2026-04-16
> Raw: [ghostty](../../raw/ai-research/2026-04-17-ghostty.md)

Ghostty has 42K stars.

> **Status: Outdated** (2026-07-23)
> Superseded by the 2026-07-18 report, which restated the count as 55K.
"""

FENCE_VARIANTS_ARTICLE = """# Fences

> Sources: Example, 2026-04-16
> Raw: [ghostty](../../raw/ai-research/2026-04-17-ghostty.md)

~~~text
not a factual claim: 777K
~~~

````text
also not a claim: 888K
````
"""

BODY_ARCHIVED_ARTICLE = """# Ordinary article

> Sources: Example, 2026-01-01

Some paragraph first.

> Archived: 2025-01-01

The release reached 321K users.
"""

RAW_WITH_BODY_METADATA_LINE = """# Source

> Source: https://example.com/x
> Collected: 2026-06-01
> Published: Unknown

First paragraph.
> Updated: The release reached 999K users.
"""

BODY_METADATA_ARTICLE = """# Body metadata

> Sources: Example, 2026-06-01
> Raw: [src](../../raw/t/src.md)

The release reached 999K users.
"""

ESCAPE_ARTICLE = """# Escape

> Sources: Example, 2026-01-01
> Raw: [support](../../notes/support.md)

The release reached 654K users.
"""

DEDUP_ARTICLE = """# Dedup

> Sources: Example, 2026-04-16
> Raw: [ghostty](../../raw/ai-research/2026-04-17-ghostty.md)

Missing value 88,123 appears here and again as 88,123 elsewhere.
"""

BOUNDARY_RAW = """# Numbers

> Source: https://example.com/numbers
> Collected: 2026-06-01
> Published: Unknown

Ghostty reached 142K stars. Uptime was 95.5%. Forks: 13,020.
"""

BOUNDARY_ARTICLE = """# Boundary

> Sources: Example, 2026-06-01
> Raw: [numbers](../../raw/t/numbers.md)

Ghostty has 42K stars and uptime of 5.5%. Forks grew to 3,020.
"""

PLAIN_RAW = """# Plain

> Source: https://example.com/plain
> Collected: 2026-06-01
> Published: Unknown

No numeric facts here at all.
"""

PLAIN_ARTICLE = """# Plain numbers

> Sources: Example, 2026-06-01
> Raw: [plain](../../raw/t/plain.md)

There were 42 users; the ratio was 3.14; founded in 2026.
"""

ARCHIVE_ARTICLE = """# Old answer

> Sources: [Ghostty](ghostty.md)
> Archived: 2026-07-01

At the time, Ghostty had 999K stars and the maintainer said "totally made up quote here".
"""

NO_RAW_ARTICLE = """# No raw

> Sources: Example, 2026-06-01

This ordinary article forgot its Raw field and claims 999K users.
"""

BROKEN_RAW_ARTICLE = """# Broken

> Sources: Example, 2026-06-01
> Raw: [gone](../../raw/t/nonexistent.md)

Claims 999K users with no evidence anywhere.
"""


def make_wiki(root: Path, log: str = ""):
    (root / "raw" / "ai-research").mkdir(parents=True)
    (root / "raw" / "ai-research" / "2026-04-17-ghostty.md").write_text(RAW_CONTENT)
    (root / "raw" / "misc").mkdir(parents=True)
    (root / "raw" / "misc" / "notes.md").write_text(SECOND_RAW)
    (root / "wiki" / "ai-research").mkdir(parents=True)
    (root / "wiki" / "ai-research" / "ghostty.md").write_text(ARTICLE_CONTENT)
    (root / "wiki" / "index.md").write_text("# Knowledge Base Index\n")
    (root / "wiki" / "log.md").write_text(log or "# Wiki Log\n")


def run_checker(root: Path, *args: str, cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(root), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


class WikiTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()


class FidelityCheckTest(WikiTestCase):
    def setUp(self):
        super().setUp()
        make_wiki(self.root)

    def test_flags_value_absent_from_raw(self):
        result = run_checker(self.root)
        self.assertIn("3,020", result.stdout)

    def test_passes_values_and_quotes_present_in_raw(self):
        result = run_checker(self.root)
        self.assertNotIn("42K", result.stdout.replace("3,020", ""))
        self.assertNotIn("10,000", result.stdout)
        self.assertNotIn("invisible to users", result.stdout)

    def test_ignores_numbers_in_code(self):
        result = run_checker(self.root)
        self.assertNotIn("9000", result.stdout)
        self.assertNotIn("78K", result.stdout)
        self.assertNotIn("9,999", result.stdout)

    def test_ignores_status_block_marker_date(self):
        result = run_checker(self.root)
        self.assertNotIn("2026-07-23", result.stdout)


class BoundaryMatchingTest(WikiTestCase):
    def setUp(self):
        super().setUp()
        (self.root / "raw" / "t").mkdir(parents=True)
        (self.root / "raw" / "t" / "numbers.md").write_text(BOUNDARY_RAW)
        (self.root / "wiki" / "t").mkdir(parents=True)
        (self.root / "wiki" / "t" / "a.md").write_text(BOUNDARY_ARTICLE)
        (self.root / "wiki" / "index.md").write_text("# Knowledge Base Index\n")
        (self.root / "wiki" / "log.md").write_text("# Wiki Log\n")

    def test_substring_of_larger_number_does_not_pass(self):
        result = run_checker(self.root)
        self.assertIn("42K", result.stdout)
        self.assertIn("5.5%", result.stdout)
        self.assertIn("3,020", result.stdout)


class DateBoundaryTest(WikiTestCase):
    def test_missing_date_does_not_also_report_its_year(self):
        article = PLAIN_ARTICLE.replace(
            "There were 42 users; the ratio was 3.14; founded in 2026.",
            "Released on 2031-09-12.",
        )
        plain_wiki(self.root, "a.md", article, raw_name="plain.md")
        result = run_checker(self.root)
        self.assertIn("- 2031-09-12", result.stdout)
        self.assertNotIn("- 2031\n", result.stdout)

    def test_month_does_not_match_prefix_of_full_date(self):
        raw = PLAIN_RAW.replace(
            "No numeric facts here at all.",
            "Released on 2026-03-19.",
        )
        article = PLAIN_ARTICLE.replace(
            "There were 42 users; the ratio was 3.14; founded in 2026.",
            "Released in 2026-03.",
        )
        plain_wiki(self.root, "a.md", article, raw=raw, raw_name="plain.md")
        result = run_checker(self.root)
        self.assertIn("- 2026-03", result.stdout)


class NumberCoverageTest(WikiTestCase):
    def setUp(self):
        super().setUp()
        (self.root / "raw" / "t").mkdir(parents=True)
        (self.root / "raw" / "t" / "plain.md").write_text(PLAIN_RAW)
        (self.root / "wiki" / "t").mkdir(parents=True)
        (self.root / "wiki" / "t" / "a.md").write_text(PLAIN_ARTICLE)
        (self.root / "wiki" / "index.md").write_text("# Knowledge Base Index\n")
        (self.root / "wiki" / "log.md").write_text("# Wiki Log\n")

    def test_flags_decimals_and_long_numbers(self):
        result = run_checker(self.root)
        self.assertIn("3.14", result.stdout)
        self.assertIn("2026", result.stdout)

    def test_small_plain_integers_are_out_of_scope(self):
        result = run_checker(self.root)
        self.assertNotIn("42 users", result.stdout)
        for line in result.stdout.splitlines():
            self.assertFalse(line.strip() == "- 42", f"small int flagged: {line}")


class EvidenceErrorTest(WikiTestCase):
    def setUp(self):
        super().setUp()
        make_wiki(self.root)

    def test_archive_page_without_raw_is_legitimate(self):
        (self.root / "wiki" / "ai-research" / "old-answer.md").write_text(ARCHIVE_ARTICLE)
        result = run_checker(self.root)
        self.assertNotIn("999K", result.stdout)
        self.assertNotIn("old-answer", result.stdout)

    def test_ordinary_article_without_raw_is_an_evidence_error(self):
        (self.root / "wiki" / "ai-research" / "no-raw.md").write_text(NO_RAW_ARTICLE)
        result = run_checker(self.root)
        self.assertIn("no-raw", result.stdout)
        self.assertIn("no Raw field", result.stdout)

    def test_broken_raw_link_is_an_evidence_error(self):
        (self.root / "wiki" / "ai-research" / "broken.md").write_text(BROKEN_RAW_ARTICLE)
        result = run_checker(self.root)
        self.assertIn("broken", result.stdout)
        self.assertIn("unresolvable Raw link", result.stdout)


class CliTest(WikiTestCase):
    def setUp(self):
        super().setUp()
        make_wiki(self.root)

    def test_article_args_resolve_against_root_not_cwd(self):
        result = run_checker(self.root, "wiki/ai-research/ghostty.md", cwd="/")
        self.assertEqual(result.returncode, 0)
        self.assertIn("3,020", result.stdout)

    def test_missing_article_is_a_warning_not_a_traceback(self):
        result = run_checker(self.root, "wiki/nope.md")
        self.assertEqual(result.returncode, 0)
        self.assertIn("wiki/nope.md", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


SECOND_RAW = """# Unrelated Notes

> Source: https://example.com/notes
> Collected: 2026-05-01
> Published: Unknown

Nothing here is compiled anywhere.
"""


def plain_wiki(root: Path, article_name: str, article: str, raw: str = PLAIN_RAW, raw_name: str = "src.md"):
    (root / "raw" / "t").mkdir(parents=True)
    (root / "raw" / "t" / raw_name).write_text(raw)
    (root / "wiki" / "t").mkdir(parents=True)
    (root / "wiki" / "t" / article_name).write_text(article)
    (root / "wiki" / "index.md").write_text("# Knowledge Base Index\n")
    (root / "wiki" / "log.md").write_text("# Wiki Log\n")


class SentenceFinalTest(WikiTestCase):
    def test_sentence_final_values_pass(self):
        plain_wiki(self.root, "a.md", SENTENCE_FINAL_ARTICLE, raw=SENTENCE_FINAL_RAW)
        (self.root / "raw" / "t" / "src.md").unlink()
        (self.root / "raw" / "t" / "numbers.md").write_text(SENTENCE_FINAL_RAW)
        result = run_checker(self.root)
        self.assertIn("0 fidelity suspect(s)", result.stdout)


class StatusBlockTest(WikiTestCase):
    def test_status_block_explanation_is_not_checked(self):
        make_wiki(self.root)
        (self.root / "wiki" / "ai-research" / "statused.md").write_text(STATUS_EXPLANATION_ARTICLE)
        result = run_checker(self.root)
        self.assertNotIn("2026-07-18", result.stdout)
        self.assertNotIn("55K", result.stdout)


class FenceVariantsTest(WikiTestCase):
    def test_tilde_and_long_backtick_fences_are_stripped(self):
        make_wiki(self.root)
        (self.root / "wiki" / "ai-research" / "fences.md").write_text(FENCE_VARIANTS_ARTICLE)
        result = run_checker(self.root)
        self.assertNotIn("777K", result.stdout)
        self.assertNotIn("888K", result.stdout)


class HeaderScopeTest(WikiTestCase):
    def test_archived_marker_in_body_does_not_exempt(self):
        plain_wiki(self.root, "a.md", BODY_ARCHIVED_ARTICLE)
        result = run_checker(self.root)
        self.assertIn("no Raw field", result.stdout)

    def test_raw_body_metadata_line_remains_evidence(self):
        plain_wiki(self.root, "a.md", BODY_METADATA_ARTICLE, raw=RAW_WITH_BODY_METADATA_LINE)
        result = run_checker(self.root)
        self.assertNotIn("999K", result.stdout)


class RawEscapeTest(WikiTestCase):
    def test_raw_link_outside_raw_dir_is_an_evidence_error(self):
        (self.root / "raw").mkdir()
        (self.root / "notes").mkdir()
        (self.root / "notes" / "support.md").write_text("The release reached 654K users.\n")
        (self.root / "wiki" / "t").mkdir(parents=True)
        (self.root / "wiki" / "t" / "a.md").write_text(ESCAPE_ARTICLE)
        (self.root / "wiki" / "index.md").write_text("# Knowledge Base Index\n")
        (self.root / "wiki" / "log.md").write_text("# Wiki Log\n")
        result = run_checker(self.root)
        self.assertIn("escapes raw/", result.stdout)


class NoMaterialParsingTest(WikiTestCase):
    def test_heading_inside_fence_does_not_suppress(self):
        (self.root / "raw" / "t").mkdir(parents=True)
        (self.root / "raw" / "t" / "orphan.md").write_text("# Orphan\n")
        (self.root / "wiki").mkdir()
        (self.root / "wiki" / "index.md").write_text("# Knowledge Base Index\n")
        (self.root / "wiki" / "log.md").write_text(
            "# Wiki Log\n\n```markdown\n"
            "## [2026-01-01] ingest | no material: raw/t/orphan.md\n"
            "- Disposition: No material\n```\n"
        )
        result = run_checker(self.root)
        self.assertIn("raw/t/orphan.md", result.stdout)

    def test_prose_mention_in_lint_entry_does_not_suppress(self):
        (self.root / "raw" / "t").mkdir(parents=True)
        (self.root / "raw" / "t" / "orphan.md").write_text("# Orphan\n")
        (self.root / "wiki").mkdir()
        (self.root / "wiki" / "index.md").write_text("# Knowledge Base Index\n")
        (self.root / "wiki" / "log.md").write_text(
            "# Wiki Log\n\n"
            "## [2026-01-01] lint | 1 issues found, 0 auto-fixed\n"
            "- Note: investigate no material: raw/t/orphan.md\n"
        )
        result = run_checker(self.root)
        self.assertIn("raw/t/orphan.md", result.stdout)


class DedupTest(WikiTestCase):
    def test_candidate_reported_once_without_trailing_space(self):
        make_wiki(self.root)
        (self.root / "wiki" / "ai-research" / "dedup.md").write_text(DEDUP_ARTICLE)
        result = run_checker(self.root)
        self.assertEqual(result.stdout.count("- 88,123"), 1)


class ExplicitArgsTest(WikiTestCase):
    def test_index_and_log_are_skipped_even_when_passed_explicitly(self):
        make_wiki(self.root)
        result = run_checker(self.root, "wiki/log.md")
        self.assertNotIn("no Raw field", result.stdout)


class TokenizerClosedFormTest(WikiTestCase):
    def test_version_numbers_match_as_whole(self):
        raw = PLAIN_RAW.replace("No numeric facts here at all.", "After v2.1.80, everything changed.")
        article = PLAIN_ARTICLE.replace(
            "There were 42 users; the ratio was 3.14; founded in 2026.",
            "After v2.1.80, everything changed.",
        )
        plain_wiki(self.root, "a.md", article, raw=raw, raw_name="plain.md")
        result = run_checker(self.root)
        self.assertIn("0 fidelity suspect(s)", result.stdout)

    def test_version_number_absent_flagged_as_whole(self):
        article = PLAIN_ARTICLE.replace(
            "There were 42 users; the ratio was 3.14; founded in 2026.",
            "After v2.1.80, everything changed.",
        )
        plain_wiki(self.root, "a.md", article, raw_name="plain.md")
        result = run_checker(self.root)
        self.assertIn("- 2.1.80", result.stdout)
        self.assertNotIn("- 2.1\n", result.stdout)

    def test_prose_commas_do_not_create_candidates(self):
        article = PLAIN_ARTICLE.replace(
            "There were 42 users; the ratio was 3.14; founded in 2026.",
            "There were 42, then 17, and finally 9 items.",
        )
        plain_wiki(self.root, "a.md", article, raw_name="plain.md")
        result = run_checker(self.root)
        self.assertIn("0 fidelity suspect(s)", result.stdout)


class RawLinksHeaderScopeTest(WikiTestCase):
    def test_fence_template_raw_line_is_ignored(self):
        article = (
            "# A\n\n> Sources: Example, 2026-01-01\n> Raw: [src](../../raw/t/src.md)\n\n"
            "Value 42K.\n\n```markdown\n> Raw: [template](../../raw/topic/filename.md)\n```\n"
        )
        raw = PLAIN_RAW.replace("No numeric facts here at all.", "Value 42K confirmed.")
        plain_wiki(self.root, "a.md", article, raw=raw)
        result = run_checker(self.root)
        self.assertNotIn("unresolvable Raw link", result.stdout)

    def test_body_raw_line_does_not_count(self):
        article = (
            "# A\n\n> Sources: Example, 2026-01-01\n\n"
            "Claims 42% growth.\n\n> Raw: [src](../../raw/t/src.md)\n"
        )
        raw = PLAIN_RAW.replace("No numeric facts here at all.", "42% growth confirmed.")
        plain_wiki(self.root, "a.md", article, raw=raw)
        result = run_checker(self.root)
        self.assertIn("no Raw field", result.stdout)


class DocumentStructureTest(WikiTestCase):
    def test_fence_between_h1_and_body_raw_does_not_create_header(self):
        article = (
            "# A\n\n```text\nthis is body content\n```\n\n"
            "> Raw: [src](../../raw/t/src.md)\n\nValue 42K.\n"
        )
        raw = PLAIN_RAW.replace("No numeric facts here at all.", "Value 42K.")
        plain_wiki(self.root, "a.md", article, raw=raw)
        result = run_checker(self.root)
        self.assertIn("article has no Raw field", result.stdout)

    def test_archived_marker_in_fence_before_real_h1_does_not_exempt(self):
        article = (
            "```markdown\n# Fake\n> Archived: 2026-01-01\n```\n\n"
            "# Real article\n\n> Sources: Example, 2026-01-01\n\nValue 777K.\n"
        )
        plain_wiki(self.root, "a.md", article)
        result = run_checker(self.root)
        self.assertIn("article has no Raw field", result.stdout)

    def test_title_candidates_are_checked(self):
        article = (
            "# GPT 9.7 Migration Notes\n\n"
            "> Sources: Example, 2026-01-01\n"
            "> Raw: [src](../../raw/t/src.md)\n\nNo other claim.\n"
        )
        plain_wiki(self.root, "a.md", article)
        result = run_checker(self.root)
        self.assertIn("- 9.7", result.stdout)

    def test_fence_closer_with_trailing_text_does_not_close(self):
        article = (
            "# A\n\n> Sources: Example, 2026-01-01\n"
            "> Raw: [src](../../raw/t/src.md)\n\n"
            "```text\ninside 777K\n``` trailing text\nstill inside 888K\n```\n"
        )
        plain_wiki(self.root, "a.md", article)
        result = run_checker(self.root)
        self.assertNotIn("777K", result.stdout)
        self.assertNotIn("888K", result.stdout)

    def test_backtick_in_info_string_does_not_open_fence(self):
        article = (
            "# A\n\n> Sources: Example, 2026-01-01\n"
            "> Raw: [src](../../raw/t/src.md)\n\n"
            "```lang`bad\nUnsupported 666K claim.\n```\n"
        )
        plain_wiki(self.root, "a.md", article)
        result = run_checker(self.root)
        self.assertIn("- 666K", result.stdout)


class QuotePairingTest(WikiTestCase):
    def test_multiline_quote_is_checked_within_paragraph(self):
        article = PLAIN_ARTICLE.replace(
            "There were 42 users; the ratio was 3.14; founded in 2026.",
            'The maintainer said "the terminal should\nfeel invisible to users".\n',
        )
        plain_wiki(self.root, "a.md", article, raw_name="plain.md")
        result = run_checker(self.root)
        self.assertIn("the terminal should feel invisible to users", result.stdout)

    def test_short_quote_pairs_do_not_create_phantom_quote(self):
        raw = PLAIN_RAW.replace(
            "No numeric facts here at all.",
            "Accuracy is high on paper but reliability is low in practice.",
        )
        article = PLAIN_ARTICLE.replace(
            "There were 42 users; the ratio was 3.14; founded in 2026.",
            'Accuracy is "high" but reliability is "low".',
        )
        plain_wiki(self.root, "a.md", article, raw=raw, raw_name="plain.md")
        result = run_checker(self.root)
        self.assertNotIn("but reliability is", result.stdout)


class NestedIndexLogTest(WikiTestCase):
    def test_article_named_index_in_topic_dir_is_checked(self):
        article = BODY_METADATA_ARTICLE.replace("999K users", "888K users")
        plain_wiki(self.root, "index.md", article)
        result = run_checker(self.root)
        self.assertIn("888K", result.stdout)

    def test_article_named_log_in_topic_dir_is_checked(self):
        article = BODY_METADATA_ARTICLE.replace("999K users", "888K users")
        plain_wiki(self.root, "log.md", article)
        result = run_checker(self.root)
        self.assertIn("888K", result.stdout)


class BlockquoteQuoteTest(WikiTestCase):
    def test_short_blockquote_number_is_checked(self):
        article = PLAIN_ARTICLE.replace(
            "There were 42 users; the ratio was 3.14; founded in 2026.",
            "> 999K users\n",
        )
        plain_wiki(self.root, "a.md", article, raw_name="plain.md")
        result = run_checker(self.root)
        self.assertIn("- 999K", result.stdout)

    def test_blockquote_link_target_is_not_part_of_quote(self):
        raw = PLAIN_RAW.replace(
            "No numeric facts here at all.",
            "The terminal should feel invisible to users.",
        )
        article = PLAIN_ARTICLE.replace(
            "There were 42 users; the ratio was 3.14; founded in 2026.",
            "> The [terminal](https://example.com) should feel invisible to users.\n",
        )
        plain_wiki(self.root, "a.md", article, raw=raw, raw_name="plain.md")
        result = run_checker(self.root)
        self.assertIn("0 fidelity suspect(s)", result.stdout)

    def test_fabricated_blockquote_quote_is_flagged(self):
        article = PLAIN_ARTICLE.replace(
            "There were 42 users; the ratio was 3.14; founded in 2026.",
            "As the review put it:\n\n> This fabricated quotation is definitely absent.\n",
        )
        plain_wiki(self.root, "a.md", article, raw_name="plain.md")
        result = run_checker(self.root)
        self.assertIn("fabricated quotation", result.stdout)

    def test_verbatim_blockquote_quote_passes(self):
        article = ARTICLE_CONTENT.replace(
            "Forks grew to 3,020 last week.",
            "> the terminal should feel invisible to users\n",
        )
        make_wiki(self.root)
        (self.root / "wiki" / "ai-research" / "ghostty.md").write_text(article)
        result = run_checker(self.root)
        self.assertNotIn("invisible to users", result.stdout)


class FenceIndentTest(WikiTestCase):
    def test_four_space_indented_backticks_are_not_a_fence(self):
        article = (
            "# A\n\n> Sources: Example, 2026-01-01\n> Raw: [src](../../raw/t/src.md)\n\n"
            "    ```\n    some indented text\n\nUnsupported claim 777K here.\n"
        )
        plain_wiki(self.root, "a.md", article)
        result = run_checker(self.root)
        self.assertIn("777K", result.stdout)


class BacktickNoMaterialTest(WikiTestCase):
    def test_backticked_path_still_suppresses(self):
        log = (
            "# Wiki Log\n\n"
            "## [2026-05-01] ingest | no material: `raw/misc/notes.md`\n"
            "- Disposition: No material\n"
        )
        make_wiki(self.root, log=log)
        result = run_checker(self.root)
        self.assertNotIn("notes.md", result.stdout)


class SpacedSuffixTest(WikiTestCase):
    def test_word_after_number_is_not_a_suffix(self):
        raw = PLAIN_RAW.replace(
            "No numeric facts here at all.",
            "The product reached 10 Million users and used 42 Kilobytes.",
        )
        article = PLAIN_ARTICLE.replace(
            "There were 42 users; the ratio was 3.14; founded in 2026.",
            "The product reached 10 Million users and used 42 Kilobytes.",
        )
        plain_wiki(self.root, "a.md", article, raw=raw, raw_name="plain.md")
        result = run_checker(self.root)
        self.assertIn("0 fidelity suspect(s)", result.stdout)

    def test_same_spaced_suffix_in_article_and_raw_passes(self):
        raw = PLAIN_RAW.replace("No numeric facts here at all.", "Uptime hit 99.9 % last week.")
        article = PLAIN_ARTICLE.replace(
            "There were 42 users; the ratio was 3.14; founded in 2026.",
            "Uptime hit 99.9 % last week.",
        )
        plain_wiki(self.root, "a.md", article, raw=raw, raw_name="plain.md")
        result = run_checker(self.root)
        self.assertIn("0 fidelity suspect(s)", result.stdout)

    def test_suffix_does_not_match_prefix_of_word(self):
        raw = PLAIN_RAW.replace("No numeric facts here at all.", "The package weighs 42Kg.")
        article = PLAIN_ARTICLE.replace(
            "There were 42 users; the ratio was 3.14; founded in 2026.",
            "The package weighs 42K.",
        )
        plain_wiki(self.root, "a.md", article, raw=raw, raw_name="plain.md")
        result = run_checker(self.root)
        self.assertIn("- 42K", result.stdout)

    def test_spaced_suffix_does_not_match_different_raw_spelling(self):
        raw = PLAIN_RAW.replace("No numeric facts here at all.", "Uptime hit 99.9% last week.")
        article = PLAIN_ARTICLE.replace(
            "There were 42 users; the ratio was 3.14; founded in 2026.",
            "Uptime hit 99.9 % last week.",
        )
        plain_wiki(self.root, "a.md", article, raw=raw, raw_name="plain.md")
        result = run_checker(self.root)
        self.assertIn("- 99.9 %", result.stdout)


EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


class ExamplesSmokeTest(WikiTestCase):
    def test_examples_have_zero_suspects(self):
        raw_src = EXAMPLES_DIR / "2026-03-19-claude-code-statusline-landscape.md"
        article_src = EXAMPLES_DIR / "claude-code-statusline-landscape.md"
        (self.root / "raw" / "ai-coding-tools").mkdir(parents=True)
        (self.root / "raw" / "ai-coding-tools" / raw_src.name).write_text(
            raw_src.read_text(encoding="utf-8"), encoding="utf-8"
        )
        (self.root / "wiki" / "ai-coding-tools").mkdir(parents=True)
        (self.root / "wiki" / "ai-coding-tools" / article_src.name).write_text(
            article_src.read_text(encoding="utf-8"), encoding="utf-8"
        )
        (self.root / "wiki" / "index.md").write_text("# Knowledge Base Index\n")
        (self.root / "wiki" / "log.md").write_text("# Wiki Log\n")
        result = run_checker(self.root)
        self.assertIn("0 fidelity suspect(s)", result.stdout)
        self.assertIn("0 evidence error(s)", result.stdout)


class RawFenceEvidenceTest(WikiTestCase):
    def test_fenced_raw_quote_is_evidence(self):
        raw = PLAIN_RAW.replace(
            "No numeric facts here at all.",
            "Log excerpt:\n\n```\nSep 08 11:00:41 host systemd[1]: "
            "service: Deactivated successfully.\n```\n",
        )
        article = PLAIN_ARTICLE.replace(
            "There were 42 users; the ratio was 3.14; founded in 2026.",
            'The unit reported "Deactivated successfully".',
        )
        plain_wiki(self.root, "a.md", article, raw=raw, raw_name="plain.md")
        result = run_checker(self.root)
        self.assertIn("0 fidelity suspect(s)", result.stdout)

    def test_fenced_raw_number_is_evidence(self):
        raw = PLAIN_RAW.replace(
            "No numeric facts here at all.",
            "Measured:\n\n```\nuptime was 99.9% for the window\n```\n",
        )
        article = PLAIN_ARTICLE.replace(
            "There were 42 users; the ratio was 3.14; founded in 2026.",
            "Uptime was 99.9% for the window.",
        )
        plain_wiki(self.root, "a.md", article, raw=raw, raw_name="plain.md")
        result = run_checker(self.root)
        self.assertIn("0 fidelity suspect(s)", result.stdout)

    def test_fenced_raw_date_is_evidence(self):
        raw = PLAIN_RAW.replace(
            "No numeric facts here at all.",
            "Journal:\n\n```\nboot completed on 2031-09-12\n```\n",
        )
        article = PLAIN_ARTICLE.replace(
            "There were 42 users; the ratio was 3.14; founded in 2026.",
            "The boot completed on 2031-09-12.",
        )
        plain_wiki(self.root, "a.md", article, raw=raw, raw_name="plain.md")
        result = run_checker(self.root)
        self.assertIn("0 fidelity suspect(s)", result.stdout)


class SchemaFileSkipTest(WikiTestCase):
    def test_toplevel_agents_md_is_not_an_article(self):
        make_wiki(self.root)
        (self.root / "wiki" / "AGENTS.md").write_text(
            "# Wiki conventions\n\nSchema file, no Raw field.\n"
        )
        result = run_checker(self.root)
        self.assertNotIn("AGENTS.md", result.stdout)
        self.assertIn("0 evidence error(s)", result.stdout)


class RawInventoryTest(WikiTestCase):
    def test_reports_raw_file_never_compiled(self):
        make_wiki(self.root)
        result = run_checker(self.root)
        self.assertIn("raw/misc/notes.md", result.stdout)

    def test_no_material_disposition_suppresses_report(self):
        log = (
            "# Wiki Log\n\n"
            "## [2026-05-01] ingest | no material: raw/misc/notes.md\n"
            "- Disposition: No material\n"
        )
        make_wiki(self.root, log=log)
        result = run_checker(self.root)
        self.assertNotIn("notes.md", result.stdout)

    def test_no_material_does_not_suppress_same_name_elsewhere(self):
        (self.root / "raw" / "other").mkdir(parents=True)
        (self.root / "raw" / "other" / "notes.md").write_text(SECOND_RAW)
        log = (
            "# Wiki Log\n\n"
            "## [2026-05-01] ingest | no material: raw/misc/notes.md\n"
            "- Disposition: No material\n"
        )
        make_wiki(self.root, log=log)
        result = run_checker(self.root)
        self.assertNotIn("raw/misc/notes.md", result.stdout)
        self.assertIn("raw/other/notes.md", result.stdout)


if __name__ == "__main__":
    unittest.main()
