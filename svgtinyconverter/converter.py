import argparse
import importlib.resources
import itertools
import logging
import re
import xml.dom.minidom

import bs4
import tinycss.css21


class Rules:
    def __init__(self, fp):
        doc = xml.dom.minidom.parse(fp)
        elem = doc.getElementsByTagName("allowed")[0]
        self.allowed_elements = dict(self._parse_allowed(elem))

    def is_acceptable_tag(self, tag):
        if tag in self.allowed_elements:
            return True
        return False

    def is_acceptable_attribute(self, tag, attr):
        if attr in self.allowed_elements.get(tag, ()):
            return True
        return False

    def _parse_allowed(self, element):
        for node in element.childNodes:
            if node.nodeName != "element":
                continue

            if not node.hasAttribute("name"):
                continue

            yield (node.getAttribute("name"), set(self._parse_element(node)))

    def _parse_element(self, element):
        for node in element.childNodes:
            if node.nodeName != "attribute":
                continue

            if not node.hasAttribute("name"):
                continue

            yield node.getAttribute("name")


def validate(soup):
    logger = logging.getLogger(__name__)

    root = soup.contents[0]
    for attr in ('width', 'height'):
        if not root.has_attr(attr):
            logger.error("Attribute '%s' missing or root node", attr)

    attr = "viewBox"
    if not root.has_attr(attr):
        logger.warning("Attribute '%s' missing or empty in root node. This is required for S60 3rd Edition FP1 or older.", attr)

    image_nodes = soup.find_all("image")
    if image_nodes:
        logger.warning("Found %s raster 'image' element(s). Quality may not be optimal.", len(image_nodes))

    return soup


def convert_stylesheets(soup):
    css = []
    for elem in soup.find_all("style"):
        css.append(elem.string.strip())
        elem.extract()

    parser = tinycss.css21.CSS21Parser()
    stylesheet = parser.parse_stylesheet("\n".join(css))

    for rule in stylesheet.rules:
        selector = rule.selector.as_css()
        declarations = {d.name: d.value.as_css() for d in rule.declarations}
        for element in soup.select(selector):
            element_style = {}
            for decl in element.attrs.get("style", "").split(";"):
                name, sep, value = decl.partition(":")
                if name and value:
                    element_style[name.strip()] = value.strip()
            element_style.update(declarations)
            element.attrs.update(element_style)
            #element.attrs["style"] = ";".join(
            #    f"{name}:{value}" for name, value in element_style.items()
            #)

    for rule in stylesheet.rules:
        selector = rule.selector.as_css()
        for element in soup.select(selector):
            if "class" in element.attrs:
                del element.attrs["class"]

            if "style" in element.attrs:
                del element.attrs["style"]

    for elem in soup.find_all(lambda tag: "style" in tag.attrs):
        for decl in elem.attrs["style"].split(";"):
            name, sep, value = decl.partition(":")
            if name and value:
                elem.attrs[name.strip()] = value.strip()
        del elem.attrs["style"]
    return soup


def get_attributes(node):
    nodemap = node.attributes
    for index in range(nodemap.length):
        yield nodemap.item(index)


def convert_nodes(soup):
    impl = xml.dom.minidom.getDOMImplementation()
    svgt_doc = impl.createDocument("http://www.w3.org/2000/svg", "svg", None)
    svg_doc = xml.dom.minidom.parseString(str(soup))

    with importlib.resources.open_text(__package__, "rules.xml") as f:
        rules = Rules(f)

    for attr in get_attributes(svg_doc.documentElement):
        if not rules.is_acceptable_attribute(svg_doc.documentElement.nodeName, attr.name):
            continue

        svgt_doc.documentElement.setAttribute(attr.name, attr.value)

    svgt_doc.documentElement.setAttribute("baseProfile", "tiny")

    temp_svgt_root = clean_node(svgt_doc, rules, svg_doc.documentElement)
    for child in temp_svgt_root.childNodes:
        svgt_doc.documentElement.appendChild(child.cloneNode(deep=True))

    return svgt_doc


def clean_node(svgt_doc, rules, svg_node):
    logger = logging.getLogger(__name__)
    if svg_node.nodeType == xml.dom.minidom.Node.ELEMENT_NODE:
        if not rules.is_acceptable_tag(svg_node.nodeName):
            logger.warning("Removed '%s' node", svg_node.nodeName)
            return None

        svgt_node = svgt_doc.createElement(svg_node.nodeName)
        for attr in get_attributes(svg_node):
            if not rules.is_acceptable_attribute(svg_node.nodeName, attr.name):
                logger.warning("Removed '%s' attribute from '%s' node", attr.name, svg_node.nodeName)
                continue

            svgt_node.setAttribute(attr.name, attr.value)
    elif svg_node.nodeType == xml.dom.minidom.Node.TEXT_NODE:
        svgt_node = svgt_doc.createTextNode(svg_node.nodeValue)

    for child in svg_node.childNodes:
        node = clean_node(svgt_doc, rules, child)
        if node is not None:
            svgt_node.appendChild(node)

    return svgt_node


def walk_nodes(node):
    yield node
    for node in node.childNodes:
        yield from walk_nodes(node)


def convert_gradients(svgt_doc):
    for element in itertools.chain(
        svgt_doc.getElementsByTagName("linearGradient"),
        svgt_doc.getElementsByTagName("radialGradient"),
        (el for el in svgt_doc.getElementsByTagName("stop") if el.parentNode.nodeName in {"linearGradient", "radialGradient"}),
    ):
        for attr in get_attributes(element):
            if not attr.value.endswith("%"):
                continue

            value = float(int(attr.value.rstrip("%").strip()))/100
            element.setAttribute(attr.name, f"{value:.2f}")

    for element in itertools.chain(
        svgt_doc.getElementsByTagName("linearGradient"),
        svgt_doc.getElementsByTagName("radialGradient"),
    ):
        if not element.hasAttribute("xlink:href"):
            continue

        attr = element.getAttribute("xlink:href")
        ref_id = attr.lstrip("#")
        element.removeAttribute("xlink:href")
        ref_elem = svgt_doc.getElementById(ref_id)
        if ref_elem:
            for node in ref_elem.childNodes:
                element.appendChild(node.cloneNode(deep=True))


def convert_opacity(svgt_doc):
    for node in walk_nodes(svgt_doc.documentElement):
        if not node.nodeType == xml.dom.minidom.Node.ELEMENT_NODE:
            continue

        if not node.hasAttribute("opacity"):
            continue

        value = node.getAttribute("opacity")
        node.removeAttribute("opacity")
        node.setAttribute("stroke-opacity", value)
        node.setAttribute("fill-opacity", value)


def convert_fills(svgt_doc):
    for node in walk_nodes(svgt_doc.documentElement):
        if not node.nodeType == xml.dom.minidom.Node.ELEMENT_NODE:
            continue

        for attr in ("fill", "style"):
            if node.hasAttribute(attr):
                value = node.getAttribute(attr)
                matchobj = re.match(r"url.+(\s*rgb\([^\)]+\))", value)
                if matchobj:
                    node.setAttribute(attr, value.replace(matchobj.group(1), "").strip())


def convert_paths(svgt_doc):
    pass


def remove_empty_nodes(svgt_doc):
    for node in walk_nodes(svgt_doc.documentElement):
        if node.nodeType == xml.dom.minidom.Node.ELEMENT_NODE and not node.hasChildNodes() and not node.hasAttributes():
            node.parentNode.removeChild(node)
        elif node.nodeType == xml.dom.minidom.Node.TEXT_NODE:
            node.nodeValue = node.nodeValue.strip()


def convert(fp):
    soup = bs4.BeautifulSoup(fp, "xml")
    validate(soup)
    convert_stylesheets(soup)
    doc = convert_nodes(soup)
    convert_gradients(doc)
    convert_opacity(doc)
    convert_paths(doc)
    convert_fills(doc)
    remove_empty_nodes(doc)
    return doc


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=argparse.FileType("r+"))
    args = parser.parse_args(argv)

    logging.basicConfig()

    doc = convert(args.file)
    args.file.seek(0)
    args.file.truncate()
    args.file.write(doc.toxml())



if __name__ == "__main__":
    main()