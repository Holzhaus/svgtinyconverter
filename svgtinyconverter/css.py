import xml.dom.minidom
import tinycss.css21
import bs4


def extract_styles(soup):
    for elem in soup.find_all("style"):
        yield elem.string.strip()
        elem.extract()


def parse_style_attribute(value):
    for decl in value.split(";"):
        name, sep, value = decl.partition(":")
        name, value = name.strip(), value.strip()
        if name and value:
            yield name, value


def convert_stylesheets(doc):
    soup = bs4.BeautifulSoup(doc.toxml(), "xml")

    parser = tinycss.css21.CSS21Parser()
    stylesheet = parser.parse_stylesheet("\n".join(extract_styles(soup)))

    # Inline all styles from the stylesheets and style-attributes as individual
    # attributes
    for rule in stylesheet.rules:
        selector = rule.selector.as_css()
        declarations = {d.name: d.value.as_css() for d in rule.declarations}

        for element in soup.select(selector):
            element_style = dict(
                parse_style_attribute(element.attrs.get("style", "")))
            element_style.update(declarations)
            element.attrs.update(element_style)
            if "style" in element.attrs:
                del element.attrs["style"]

    # Remove all other style/class attributes (that were not referenced from
    # style tags)
    for element in soup.find_all(
            lambda tag: any(attr in tag.attrs for attr in ("style", "class"))):
        if "style" in element.attrs:
            for name, value in parse_style_attribute(element.attrs["style"]):
                element.attrs[name] = value
            del element.attrs["style"]

        if "class" in element.attrs:
            del element.attrs["class"]

    return xml.dom.minidom.parseString(str(soup))
