"""Every "§ N Abs. M" (and "Nr. K") the website cites must exist in the HinSchG. The docs
once cited § 17 Abs. 3 and § 16 Abs. 7, which do not exist, and § 26 for data protection,
which is about external reporting offices. A new citation of a section missing below fails
here until someone has checked it against https://www.gesetze-im-internet.de/hinschg/ and
added its shape. The README and the interface: the same guard in openwhistle/OpenWhistle."""

import html
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]

# Section -> number of Absätze; per Absatz, the number of Nr. where cited.
SHAPE: dict[int, tuple[int, dict[int, int]]] = {
    2: (3, {1: 11}),
    3: (10, {8: 7}),
    7: (3, {}),
    8: (2, {}),
    9: (4, {}),
    11: (5, {}),
    12: (4, {}),
    13: (2, {}),
    14: (2, {}),
    16: (3, {}),
    17: (2, {1: 6}),
    19: (4, {}),
    26: (3, {}),
    32: (2, {}),
    40: (6, {2: 3}),
    42: (2, {}),
}

_OTHER_LAW = re.compile(
    r"\s*(?:[A-Za-z.\s\d]{0,8})?"
    r"\b(?:StGB|DSGVO|BetrVG|OWiG|BDSG|UWG|BGB|GG|AktG|GmbHG|KWG|BPersVG|MStV|TDDDG|LkSG)\b"
)
_CITE = re.compile(r"§\s?(\d+)\s?(?:Abs\.|Absatz|al\.)\s?(\d+)(?:\s?(?:Nr\.|Satz)\s?(\d+))?")


def _files() -> list[Path]:
    docs = [
        p
        for p in (ROOT / "docs").rglob("*")
        if p.suffix in {".html", ".md"} and "/docs/_" not in p.as_posix()
    ]
    return docs


def _wrong(name: str, text: str) -> list[str]:
    # Unescaped: most citations are written "§&nbsp;17&nbsp;Abs.&nbsp;1", which \s never matched,
    # so about a third of them went unchecked.
    text = html.unescape(text)
    wrong = []
    for m in _CITE.finditer(text):
        section, absatz = int(m.group(1)), int(m.group(2))
        if _OTHER_LAW.match(text[m.end() : m.end() + 16]):
            continue  # § 87 BetrVG, § 201 StGB, § 30 OWiG ...
        shape = SHAPE.get(section)
        if shape is None:
            wrong.append(f"{name}: {m.group(0)} (section not checked yet)")
        elif absatz > shape[0]:
            wrong.append(f"{name}: {m.group(0)} (§ {section} has {shape[0]})")
        elif m.group(3) and "Nr" in m.group(0):
            limit = shape[1].get(absatz)
            if limit is None or int(m.group(3)) > limit:
                wrong.append(f"{name}: {m.group(0)} (no such Nr.)")
    return wrong


def test_every_cited_absatz_exists() -> None:
    wrong = [
        line
        for path in _files()
        for line in _wrong(str(path.relative_to(ROOT)), path.read_text(encoding="utf-8"))
    ]
    assert not wrong, wrong


def test_a_citation_written_with_entities_is_checked() -> None:
    assert _wrong("p", "§&nbsp;40&nbsp;Abs.&nbsp;9 und §&nbsp;99&nbsp;Abs.&nbsp;7") == [
        "p: §\xa040\xa0Abs.\xa09 (§ 40 has 6)",
        "p: §\xa099\xa0Abs.\xa07 (section not checked yet)",
    ]


def test_a_citation_of_another_law_is_not_read_as_the_hinschg() -> None:
    """The roadmap cited "§12 Abs. 4 LkSG", which does not exist: it passed as HinSchG § 12, and
    the correct "§ 10 Abs. 2 LkSG" was refused as an unchecked HinSchG section."""
    assert _wrong("p", "§ 10 Abs. 2 LkSG und § 12 Abs. 5") == ["p: § 12 Abs. 5 (§ 12 has 4)"]
