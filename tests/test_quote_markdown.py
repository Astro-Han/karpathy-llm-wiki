"""Markdown formatting must not hide real quotes or changed quoted text."""

from test_check_evidence import PLAIN_RAW, WikiTestCase, plain_wiki, run_checker


class MarkdownQuoteTest(WikiTestCase):
    def check_quote(self, source, quotation, expected_suspects=0):
        article = "# Article\n\n> Raw: [src](../../raw/t/src.md)\n\n" + quotation + "\n"
        raw = PLAIN_RAW.replace("No numeric facts here at all.", source)
        plain_wiki(self.root, "a.md", article, raw=raw)
        result = run_checker(self.root)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn(f"{expected_suspects} fidelity suspect(s)", result.stdout)
        self.assertIn("0 evidence error(s)", result.stdout)
        return result.stdout

    def test_verbatim_inline_code_in_blockquote(self):
        source = "`priority` means business importance, `bucket_confidence` means classification confidence."
        self.check_quote(source, "> " + source)

    def test_inline_code_text_is_preserved_in_double_quoted_span(self):
        source = "The `priority` field controls the processing order."
        self.check_quote(source, f'The guide says "{source}"')

    def test_changed_inline_code_is_still_reported(self):
        output = self.check_quote(
            "The `priority` field controls the processing order.",
            "> The `confidence` field controls the processing order.",
            expected_suspects=1,
        )
        self.assertIn("confidence", output)

    def test_changed_inline_code_in_double_quotes_is_still_reported(self):
        output = self.check_quote(
            "The `priority` field controls the processing order.",
            'The guide says "The `confidence` field controls the processing order."',
            expected_suspects=1,
        )
        self.assertIn("confidence", output)

    def test_multiline_raw_blockquote(self):
        self.check_quote(
            "> The terminal should\n> feel invisible to users.",
            "> The terminal should\n> feel invisible to users.",
        )

    def test_nested_raw_blockquote(self):
        self.check_quote(
            "> > The terminal should\n> > feel invisible to users.",
            "> The terminal should feel invisible to users.",
        )

    def test_link_labels_match_without_the_source_url(self):
        self.check_quote(
            "The [terminal](https://example.com) should feel invisible to users.",
            "> The terminal should feel invisible to users.",
        )

    def test_inline_code_does_not_create_new_quote_candidates(self):
        self.check_quote("No relevant evidence.", '`print("This is only a code example")`')

    def test_double_quotes_inside_inline_code_do_not_split_a_real_quote(self):
        source = 'The `config["priority"]` field controls the processing order.'
        self.check_quote(source, f'The guide says "{source}"')

    def test_link_syntax_inside_inline_code_remains_literal(self):
        source = 'Use `[label](target)` to reference another document.'
        self.check_quote(source, f'The guide says "{source}"')

    def test_link_destinations_do_not_create_quote_candidates(self):
        self.check_quote("No relevant evidence.", '[link](https://example.com/"not a quotation here")')

    def test_quoted_link_label_is_matched_as_visible_text(self):
        source = "The terminal should feel invisible to users."
        self.check_quote(source, f'The guide says ["{source}"](https://example.com).')

    def test_formatting_does_not_remove_word_boundaries(self):
        self.check_quote(
            "The icecream service is available to users.",
            "> The ice cream service is available to users.",
            expected_suspects=1,
        )

    def test_numeric_matching_keeps_its_existing_whitespace_normalization(self):
        self.check_quote("Uptime reached 99.9\n% last week.", "Uptime reached 99.9 % last week.")

    def test_inline_code_in_link_label_matches_plain_source(self):
        self.check_quote(
            "The priority field controls the processing order.",
            "> The [`priority` field](https://example.com) controls the processing order.",
        )

    def test_linked_code_in_raw_matches_a_different_destination(self):
        self.check_quote(
            "The [`priority` field](https://source.example) controls the processing order.",
            '> The [`priority` field](https://article.example) controls the processing order.',
        )

    def test_changed_linked_code_is_still_reported(self):
        output = self.check_quote(
            "The priority field controls the processing order.",
            "> The [`confidence` field](https://example.com) controls the processing order.",
            expected_suspects=1,
        )
        self.assertIn("confidence", output)

    def test_double_backtick_code_does_not_create_quote_candidates(self):
        self.check_quote("No relevant evidence.", 'Example: ``print("This is only a code example")``')

    def test_code_with_inner_backticks_does_not_create_quote_candidates(self):
        self.check_quote("No relevant evidence.", 'Example: ``print(`value`, "This is only a code example")``')

    def test_mismatched_backticks_do_not_hide_a_real_quote(self):
        self.check_quote(
            "No relevant evidence.",
            'Example: ``prefix ` "This is a real unsupported quote"',
            expected_suspects=1,
        )

    def test_balanced_parentheses_in_link_destination_are_masked(self):
        self.check_quote("No relevant evidence.", '[link](https://example.com/a(b)"not-a-quotation-here")')

    def test_quote_after_nested_link_destination_is_still_checked(self):
        self.check_quote(
            "No relevant evidence.",
            '[link](https://example.com/a(b)"not-a-quotation-here") "This is a real unsupported quote"',
            expected_suspects=1,
        )

    def test_nested_destination_and_code_label_normalize_together(self):
        self.check_quote(
            "The priority field controls the processing order.",
            '> The [``priority`` field](https://example.com/a(b(c))) controls the processing order.',
        )

    def test_escaped_parenthesis_does_not_end_link_destination(self):
        self.check_quote("No relevant evidence.", r'[link](https://example.com/a\)"not-a-quotation-here")')
