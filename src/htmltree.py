import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from enum import Enum
import logging
import io


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__file__)

# Useful articles
# https://developer.mozilla.org/en-US/docs/Web/API/Node/nodeType
# https://docs.python.org/3/library/xml.etree.elementtree.html
# https://docs.python.org/3/library/html.parser.html
# https://stackoverflow.com/questions/34407468/what-is-the-default-namespace-for-html-html5

# TODO
# [ ] handle optional tags
# [ ] handle redundant text nodes (whitespace)

# inline level elements
INLINE = {
	"a", "abbr", "acronym", "b", "bdo", "big", "br", "button", "cite", "code",
	"dfn", "em", "i", "img", "input", "kbd", "label", "map", "object", "q",
	"samp", "script", "select", "small", "span", "strong", "sub", "sup",
	"textarea", "time", "tt", "var", "math"
}

# block level elements with inline printing
ENDINLINE = {
	"pre", "mi", "mn", "mo", "ms", "mglyph", "mspace", "mtext", "h1", "h2",
	"h3", "h4", "h5", "h6", "title"
}

# block level elements
BLOCK = {"address", "article", "aside", "blockquote", "details", "dialog",
    "dd", "div", "dl", "dt", "fieldset", "figcaption", "figure", "footer",
    "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hgroup", "hr", "li",
    "main", "nav", "ol", "p", "pre", "section", "table", "ul",
}

# block level elements that optionally have closing tags
OPTIONAL = {
	"body", "colgroup", "dd", "dt", "head", "html", "li", "option", "p",
	"tbody", "td", "tfoot", "th", "thead", "tr"
}

# block level elements that disallow closing tags
EMPTY = {
	"area", "base", "basefont", "br", "col", "frame", "hr", "img", "input",
	"link", "meta", "param", "mprescripts", "none", "mspace", "isindex",
}

# Math Markup Language elements
MML = {
	"math", "maction", "maligngroup", "malignmark", "menclose", "merror",
	"mfenced", "mfrac", "mglyph", "mi", "mlabeledtr", "mlongdiv",
	"mmultiscripts", "mn", "mo", "mover", "mpadded", "mphantom", "mroot",
	"mrow", "ms", "mscarries", "mscarry", "msgroup", "mstack", #?
	"mlongdiv","msline", "mspace", "msqrt", "msrow", "mstack", "mstyle",
	"msub", "msub", "msup", "msubsup", "mtable", "mtd", "mtext", "mtr",
	"munder", "munderover", "semantics", "annotation", "annotation-xml",
	"mprescripts", "none"
}

# Extensible Markup Language elements
# MML-elements that require xml-style <el /> instead of <el>
XML = {
	"mspace", "mprescripts", "none"
}


class ElementNode(ET.Element):
    def __init__(self, tag, attrs={}):
        super().__init__(tag, attrib=attrs)

class TextNode(ET.Element):
    def __init__(self, text):
        super().__init__(TextNode)
        self.text = text

class CommentNode(ET.Element):
    def __init__(self, text):
        super().__init__(CommentNode)
        self.text = text

class ProcessingInstructionNode(ET.Element):
    def __init__(self, text):
        super().__init__(ProcessingInstructionNode)
        self.text = text

class DeclarationNode(ET.Element):
    NotImplemented


# https://developer.mozilla.org/en-US/docs/Web/API/Node/nodeType#constants
class NodeType(Enum):
    ELEMENT_NODE = (1, ElementNode)
    TEXT_NODE = (3, TextNode)
    PROCESSING_INSTRUCTION_NODE = (7, ProcessingInstructionNode)
    COMMENT_NODE = (8, CommentNode)
    DOCUMENT_TYPE_NODE = (10, DeclarationNode)


CHILDLESS = EMPTY | {CommentNode, TextNode, ProcessingInstructionNode}


# https://docs.python.org/3/library/html.parser.html#examples
class HTMLTree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)

        self.declaration = None
        self._root = ET.Element("ROOT")
        self._stack = [self._root]

    @classmethod
    def fromstring(cls, string):
        tree = cls()

        tree.feed(string)

        return tree

    def to_string(self, indent=None, namespaces=None):
        stream = io.StringIO()

        if indent is not None:
            raise NotImplementedError

        if tree.declaration:
            stream.write(f"<!{self.declaration}>\n")

        _serialize_html(stream.write, self.root, indent, namespaces)

        return stream.getvalue()

    @property
    def root(self):
        # Returns first ElementNode in root
        return next(filter(lambda x: isinstance(x, ElementNode), self._root))

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
        self._push(ElementNode(tag, dict(attrs)))

    def handle_endtag(self, tag):
        self._log("HANDLE ENDTAG", tag)
        if tag not in EMPTY:
            assert tag == self._pop().tag

    def handle_charref(self, name):
        # unused
        self._log("HANDLE CHARREF", name)

    def handle_entityref(self, name):
        # unused
        self._log("HANDLE ENTITY REFERENCE", name)

    def handle_data(self, data):
        # text
        self._log("HANDLE DATA", data)
        self._push(TextNode(data))

    def handle_comment(self, data):
        self._log("HANDLE COMMENT", data)
        self._push(CommentNode(data))

    def handle_decl(self, decl):
        self._log("HANDLE DECLARATION", decl)
        self.declaration = decl

    def handle_pi(self, data):
        self._push(ProcessingInstructionNode(data))
        self._log("HANDLE PROCESSING INSTRUCTION", data)

    def unknown_decl(self, data):
        # unused?
        self._log("UNKNOWN DECL", data)


# based off: https://github.com/python/cpython/blob/3.9/Lib/xml/etree/ElementTree.py#L929
def _serialize_html(write, elem, indent, namespaces=None, level=0):
    tag = elem.tag
    text = elem.text

    # TODO: Replace with match statement in 3.10
    if tag is CommentNode:
        write(f"<!--{text}-->")
    elif tag is TextNode:
        # if not text.isspace(): write(text)
        write(text)
    elif tag is ProcessingInstructionNode:
        write(f"<?{text}>")
    else:
        write("<" + tag)

        items = list(elem.items())
        if items or namespaces:
            if namespaces:
                for attr, value in sorted(namespaces.items(),key=lambda x:x[1]):
                    write(' xmlns:{attr}="{value}"')
            for attr, value in items:
                if value is not None:
                    write(f' {attr}="{value}"')
                else:
                    write(f' {attr}=""')

        ltag = tag.lower()


        if ltag not in EMPTY:
            write(">")
        else:
            write("/>")

        if text:
            if ltag == "script" or ltag == "style":
                write(text)
            else:
                write(text)
        for e in elem:
            _serialize_html(write, e, indent, None, level+1)

        if ltag not in EMPTY:
            write(f"</{tag}>")
