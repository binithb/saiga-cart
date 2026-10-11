"""Dependency-free regressions for the static GitHub Pages guide."""

from html.parser import HTMLParser
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "docs" / "presentation"
PAGES = [
    ("index.html", "Start"),
    ("01-problem.html", "Drift"),
    ("02-context-tax.html", "Context Tax"),
    ("03-bottleneck.html", "The Shift"),
    ("05-modes.html", "Modes"),
    ("06-four-artifacts.html", "Four Artifacts"),
    ("07-colocation.html", "Co-location"),
    ("08-roles.html", "Roles & Flow"),
    ("10-payoff.html", "Adopt"),
]
ALIASES = {
    "04-agile-inversion.html": "03-bottleneck.html",
    "09-lifecycle.html": "08-roles.html",
}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
             "link", "meta", "param", "source", "track", "wbr"}


class Node:
    def __init__(self, tag, attrs=(), parent=None):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.parts = []

    @property
    def text(self):
        return " ".join("".join(self.parts).split())

    def has_class(self, name):
        return name in self.attrs.get("class", "").split()

    def inside(self, ancestor):
        node = self.parent
        while node:
            if node is ancestor:
                return True
            node = node.parent
        return False


class Document(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.nodes = []
        self.stack = []
        self.feed(path.read_text(encoding="utf-8"))
        self.close()

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.stack[-1] if self.stack else None)
        self.nodes.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1].tag == tag:
            self.stack.pop()
        else:
            raise AssertionError(f"Unbalanced closing tag: {tag}")

    def handle_data(self, data):
        for node in self.stack:
            node.parts.append(data)

    def by_class(self, name):
        return [node for node in self.nodes if node.has_class(name)]

    def by_tag(self, name):
        return [node for node in self.nodes if node.tag == name]

    def links_in(self, node):
        return [link for link in self.by_tag("a") if link.inside(node)]


class PresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = {path.name: Document(path) for path in DECK.glob("*.html")}

    def test_exact_nine_page_static_and_script_order(self):
        script = (DECK / "assets" / "nav.js").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r'\{ file: "([^"]+)", label: "([^"]+)" \}', script), PAGES)
        self.assertEqual(
            {name for name, doc in self.docs.items() if doc.by_class("guide")},
            {name for name, _ in PAGES},
        )
        for filename, doc in self.docs.items():
            if filename in ALIASES:
                continue
            with self.subTest(page=filename):
                nav, = doc.by_class("topnav")
                links = doc.links_in(nav)
                self.assertEqual([link.attrs["href"] for link in links], [name for name, _ in PAGES])
                self.assertEqual([link.text for link in links],
                                 [f"{i:02} {label}" for i, (_, label) in enumerate(PAGES, 1)])
                current = [link.attrs["href"] for link in links
                           if link.attrs.get("aria-current") == "page"]
                self.assertEqual(current, [] if filename == "ai-agile-manifesto.html" else [filename])

    def test_static_counts_prev_next_and_headings(self):
        for i, (filename, label) in enumerate(PAGES):
            with self.subTest(page=filename):
                doc = self.docs[filename]
                self.assertEqual(doc.by_class("kicker")[0].text, f"{label} · {i + 1} / 9")
                self.assertIn(f"Page {i + 1} of 9", doc.by_class("site-footer")[0].text)
                self.assertTrue(doc.by_tag("title")[0].text.startswith(label + " · "))
                self.assertEqual(len(doc.by_tag("h1")), 1)
                previous = doc.by_class("prev")
                self.assertEqual(len(previous), int(i > 0))
                destinations = [(doc.by_class("next")[0], (i + 1) % len(PAGES))]
                if i:
                    destinations.append((previous[0], i - 1))
                for link, index in destinations:
                    target = PAGES[index][0]
                    self.assertEqual(link.attrs["href"], target)
                    self.assertIn(f"Page {index + 1}", link.text)
                    self.assertIn(self.docs[target].by_tag("h1")[0].text, link.text)

    def test_manifesto_discovery_is_static_and_outside_topbar(self):
        for filename, _ in PAGES:
            with self.subTest(page=filename):
                doc = self.docs[filename]
                resource, = doc.by_class("guide-resource")
                self.assertEqual(resource.parent.tag, "main")
                self.assertLess(doc.nodes.index(resource), doc.nodes.index(doc.by_class("page-head")[0]))
                self.assertEqual(doc.links_in(resource)[0].attrs["href"], "ai-agile-manifesto.html")
                self.assertFalse(any(link.attrs["href"] == "ai-agile-manifesto.html"
                                     for link in doc.links_in(doc.by_class("topbar")[0])))
        manifesto = self.docs["ai-agile-manifesto.html"]
        self.assertEqual(manifesto.links_in(manifesto.by_class("guide-resource")[0])[0].attrs["href"],
                         "index.html")
        self.assertNotIn("Page ", manifesto.by_class("site-footer")[0].text)
        self.assertEqual(len(manifesto.by_class("manifesto-values")), 1)
        principles = manifesto.by_class("manifesto-principles")[0]
        self.assertEqual(len([node for node in manifesto.by_tag("li") if node.inside(principles)]), 12)

    def test_merged_urls_have_small_non_js_landing_pages(self):
        for alias, target in ALIASES.items():
            with self.subTest(alias=alias):
                doc = self.docs[alias]
                canonical, = [node for node in doc.by_tag("link")
                              if node.attrs.get("rel") == "canonical"]
                self.assertEqual(canonical.attrs["href"], target)
                self.assertTrue(any(link.attrs.get("href") == target for link in doc.by_tag("a")))
                self.assertFalse(doc.by_class("topnav"))
                self.assertFalse(doc.by_class("card"))
                self.assertFalse(doc.by_tag("script"))
        for filename, doc in self.docs.items():
            if filename not in ALIASES:
                self.assertFalse(any(link.attrs.get("href") in ALIASES for link in doc.by_tag("a")))

    def test_local_links_assets_and_skip_targets(self):
        for filename, doc in self.docs.items():
            with self.subTest(page=filename):
                self.assertFalse(doc.stack, "Unclosed HTML elements")
                ids = [node.attrs["id"] for node in doc.nodes if "id" in node.attrs]
                self.assertEqual(len(ids), len(set(ids)), "Duplicate IDs")
                self.assertEqual(doc.by_class("skip-link")[0].attrs["href"], "#content")
                self.assertIn("content", ids)
                for node in doc.nodes:
                    for attr in ("href", "src"):
                        if attr not in node.attrs:
                            continue
                        url = urlsplit(node.attrs[attr])
                        if url.scheme or url.netloc:
                            self.assertNotIn(node.tag, ("script", "link", "img"), "External asset dependency")
                            continue
                        target = (DECK / unquote(url.path)).resolve() if url.path else DECK / filename
                        self.assertTrue(target.is_relative_to(DECK), "Link escapes deployed Pages directory")
                        self.assertTrue(target.is_file(), f"Missing target: {node.attrs[attr]}")
                        if url.fragment:
                            linked = self.docs[target.name]
                            self.assertIn(unquote(url.fragment),
                                          [n.attrs.get("id") for n in linked.nodes])
                for node in doc.nodes:
                    for label_id in node.attrs.get("aria-labelledby", "").split():
                        self.assertIn(label_id, ids)

    def test_preserved_editorial_contract(self):
        flow = self.docs["08-roles.html"]
        self.assertEqual([card.text.split(" · ")[1] for card in flow.by_class("card-number")],
                         ["Aim", "Map", "Draft", "Prove", "Audit", "Merge"])
        text = flow.by_tag("main")[0].text
        for requirement in ("unblocked", "≤ Medium", "affected repos", "acceptance criteria",
                            "AGENTS.md", "docs/architecture.md", "sibling repositories", "ADRs",
                            "Passing checks are evidence, not human approval",
                            "approved PR summary", "marks the local story Done", "linked tracker"):
            self.assertIn(requirement, text)
        self.assertEqual(len(self.docs["01-problem.html"].by_class("card")), 3)
        self.assertFalse(self.docs["05-modes.html"].by_tag("table"))
        self.assertIn("Focused checks appropriate to the change",
                      self.docs["05-modes.html"].by_tag("main")[0].text)
        self.assertIn("not four literal files",
                      self.docs["06-four-artifacts.html"].by_tag("main")[0].text)
        adopt = self.docs["10-payoff.html"]
        self.assertEqual(len(adopt.by_class("card")), 4)
        self.assertIn("No measured ROI is established here", adopt.by_tag("main")[0].text)
        self.assertTrue(any("quickstart" in link.attrs.get("href", "")
                            for link in adopt.by_tag("a")))
        shift = self.docs["03-bottleneck.html"]
        self.assertEqual([node.text for node in shift.by_tag("h3")][:2],
                         ["Before Fast Generation", "With Fast Generation"])
        for card in shift.by_class("card"):
            for dimension in ("Delivery:", "Review:", "Context:"):
                self.assertIn(dimension, card.text)
        self.assertTrue(any("youtu.be/h0hdaHPKDdI" in link.attrs.get("href", "")
                            for link in shift.by_tag("a")))


if __name__ == "__main__":
    unittest.main()
