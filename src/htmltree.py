"""Lightweight HTML parser for Python.

For a more comprehensive implementation, check out BeautifulSoup or Selenium.
Assumes documents are well-formed (e.g. no tbody insertion).

This library uses the built-in xml.etree.ElementTree library to create HTML
document trees. A document has a <DOCUMENT> element as the root node.

A notable implementation quirk is that the text attribute on regular elements
is ignored and the tail attribute is never used. Instead a child text node is
used with the <str> type as its tag.

Below is a comparison between the two. The main issue with Element style, is
that the string "!" is attached to the child instead of the parent:

Source XML:
```
<span>hello <span>world</span>!</span>
```

Element style:
```
span{
    text: "hello "
    children: [
        span{
            text: "world"
            tail: "!"
        }
    ]
}
```

Node style:
```
span{
    children: [
        <str>{
            text: "hello "
        }
        span{
            children: [
                <str>{
                    text: "world"
                }
            ]
        }
        <str>{
            text: "!"
        }
    ]
}
```

For compatibility with other Python libraries using the `etree` module, the
`elify` function can be used to convert from node style to an element style
tree.

"""

import logging
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

logger = logging.getLogger(__name__)


# Empty tags

MML_EMPTY = {"mprescripts", "none", "mspace"}
EMPTY = ET.HTML_EMPTY | MML_EMPTY
CHILDLESS = EMPTY | {str, ET.Comment, ET.ProcessingInstruction}


# Text element

def Text(text):
    """Text element factory.

    *text* is a string containing the text string.

    """
    # ET's XML model is fundamentally bad at representing HTML documents
    # because it doesn't have text nodes. We solve this by using 'str' as
    # text node tags. We cannot use `Text`, because we need a singleton.
    Text = ET.Element(str)
    Text.text = text
    return Text


# Node helper functions

def children(node):
    """Returns only element nodes, not comment or text nodes"""
    for child in node:
        if isinstance(child.tag, str):
            yield child


def text_content(node):
    return "".join(node.itertext())


# HTML Parser

# Ugly implementation; ElementTree and HTMLParser shouldn't be joined
class HTMLTree(HTMLParser, ET.ElementTree):
    def __init__(self):
        super().__init__(convert_charrefs=True)

        self.declaration = None
        self._root = ET.Element("DOCUMENT")
        self._stack = [self._root]

    @classmethod
    def fromstring(cls, string):
        tree = cls()
        tree.feed(string)
        return tree

    @classmethod
    def parse(cls, filename, encoding="utf-8"):
        with open(filename, mode="rt", encoding=encoding) as f:
            return cls.fromstring(f.read())

    @property
    def root(self):
        return self._root

    @property
    def html(self):
        # Returns first ElementNode in root
        return next(filter(lambda x: isinstance(x, ET.Element), self._root))

    @staticmethod
    def _log(*text):
        logger.debug(" ".join(map(str, text)))

    def _push(self, el):
        self._stack[-1].append(el)
        if el.tag not in CHILDLESS:
            self._stack.append(el)

    def _pop(self):
        return self._stack.pop()

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_starttag(self, tag, attrs):
        self._log("HANDLE STARTTAG", tag, attrs)
        self._push(ET.Element(tag, dict(attrs)))

    def handle_endtag(self, tag):
        self._log("HANDLE ENDTAG", tag)
        if tag not in EMPTY and tag == self._stack[-1].tag:
            # assert tag == self._stack.pop().tag
            self._pop().tag

    def handle_charref(self, name):
        # unused
        self._log("HANDLE CHARREF", name)

    def handle_entityref(self, name):
        # unused
        self._log("HANDLE ENTITY REFERENCE", name)

    def handle_data(self, data):
        # text
        self._log("HANDLE DATA", data)
        self._push(Text(data))

    def handle_comment(self, data):
        self._log("HANDLE COMMENT", data)
        self._push(ET.Comment(data))

    def handle_decl(self, decl):
        self._log("HANDLE DECLARATION", decl)
        self.declaration = decl

    def handle_pi(self, data):
        self._log("HANDLE PROCESSING INSTRUCTION", data)
        target = data[:-1]  # Remove trailing '?'
        self._push(ET.ProcessingInstruction(target))

    def unknown_decl(self, data):
        # unused?
        self._log("UNKNOWN DECL", data)



# Tree formatters

def nodify(el):
    """
    Converts <element>text</element> into <element><str>text></str></element>
    """
    node = ET.Element(el.tag, el.attrib)

    if el.text is not None:
        node.append(Text(el.text))

    for cel in el:
        node.append(nodify(cel))
        if cel.tail is not None:
            node.append(Text(cel.tail))

    return node


def normalize(nol):
    """
    Attempts to convert a mixed-style tree (containing node style and element
    style elements) into node style.
    """
    node = ET.Element(nol.tag, nol.attrib)

    if nol.tag is str or nol.tag is ET.Comment or nol.tag is ET.ProcessingInstruction:
        node.text = nol.text
        return node

    if hasattr(nol, "text") and nol.text is not None:
        node.append(Text(nol.text))

    for cnol in nol:
        node.append(normalize(cnol))
        if hasattr(cnol, "tail") and cnol.tail is not None:
            node.append(Text(cnol.tail))

    return node


def elify(node):
    """
    Converts <element><str>text></str></element> into <element>text</element>
    """
    el = ET.Element(node.tag, node.attrib)

    start = 0
    if len(node) and node[0].tag is str:
        el.text = node[0].text
        start = 1
    elif node.tag is ET.Comment:
        el.text = node.text
        start = 1
    elif node.tag is ET.ProcessingInstruction:
        el.text = node.text
        start = 1

    for cnode in node[start:]:
        if cnode.tag is str:
            # assumes text nodes aren't consecutive
            el[-1].tail = cnode.text
        else:
            el.append(elify(cnode))

    return el


if __name__ == "__main__":
    doc = """<!-- Comment --><!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>htmllib</title>
</head>
<body>
    <h1>Hello world!</h1>
</body>
</html><!-- Comment -->
"""
    tree = HTMLTree.fromstring(doc)
    print(elify(tree.getroot())[0].text)
    print(ET.tostring(elify(tree.getroot()), encoding="utf-8").decode("utf-8"))
