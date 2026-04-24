"""Stage-1 parser tests. No network, no Redis."""
from __future__ import annotations

from app.mmkg.parsers import (
    HTMLParser,
    MarkdownParser,
    PlainTextParser,
    parse_document,
)
from app.mmkg.schemas import Modality


def test_markdown_parser_extracts_sections_and_modalities():
    doc = """# Title

Intro paragraph with a $$E = m c^2$$ equation.

## Section One

Some table follows:

| col | val |
|-----|-----|
| a   | 1   |
| b   | 2   |

![diagram](fig1.png)

### Deeper

```python
print("hi")
```

- item one
- item two
"""
    blocks = MarkdownParser().parse(doc_id="d1", path=None, content=doc)
    modalities = [b.modality for b in blocks]

    assert Modality.HEADING in modalities
    assert Modality.TEXT in modalities
    assert Modality.TABLE in modalities
    assert Modality.IMAGE in modalities
    assert Modality.CODE in modalities
    assert Modality.LIST in modalities

    # Hierarchy: the code block lives under Title/Section One/Deeper.
    code_block = next(b for b in blocks if b.modality == Modality.CODE)
    assert code_block.section_path == ["Title", "Section One", "Deeper"]


def test_plain_text_parser_splits_on_blank_lines():
    blocks = PlainTextParser().parse(doc_id="t1", path=None, content="one\n\ntwo\n\n")
    assert len(blocks) == 2
    assert all(b.modality == Modality.TEXT for b in blocks)


def test_html_parser_emits_blocks_with_hierarchy():
    html = """
    <html><body>
      <h1>Top</h1>
      <p>hello</p>
      <h2>Sub</h2>
      <table><tr><td>x</td></tr></table>
      <img src="a.png" alt="an image"/>
    </body></html>
    """
    blocks = HTMLParser().parse(doc_id="h1", path=None, content=html)
    kinds = {b.modality for b in blocks}
    assert Modality.HEADING in kinds
    assert Modality.TABLE in kinds
    assert Modality.IMAGE in kinds


def test_parse_document_dispatches_by_content():
    blocks = parse_document(content="# Hi\n\nWorld", doc_id="dispatch")
    assert blocks[0].modality == Modality.HEADING
    assert blocks[1].modality == Modality.TEXT
