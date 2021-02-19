# html-to-xml
Converts HTML to Python's ElementTree, from which XML can be generated.

A lightweight HTML to XML converter. Handles empty tags, but not optional tags; checkout BeautifulSoup if you want a more feature complete library.

`Node` elements are lightly wrapped `Element` objects from the builtin `ElementTree` library, and the root element is accessible through `tree.root`. ([Documentation for `ElementTree`](https://docs.python.org/3/library/xml.etree.elementtree.html).)

```py
html_text = """
<!DOCTYPE html>
<html>
    <head>
        <title>title text</title>
        <meta charset="utf-8">
    </head>
    <body>
        <section class="red" id="blue" active>
            <h1 class="green">heading</h1>
            <div>
                text <span>child</span> tail <strong>bold</strong> more &gt;tail <br /> <hr>
            </div>
            <!-- comment -->
            <?test?>
        </section>
    </body>
</html>
"""

tree = HTMLTree.fromstring(html_text.strip())

xml_text = tree.to_string()

print(ET.fromstring(xml_text))
```
