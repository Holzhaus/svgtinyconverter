import logging
import importlib.resources
import lxml


def schema(filename):
    with importlib.resources.open_text(__package__, filename) as f:
        return lxml.etree.RelaxNG(lxml.etree.parse(f))


def validate(doc, schema=None):
    logger = logging.getLogger(__name__)

    root = doc.documentElement
    for attr in ('width', 'height'):
        if not root.hasAttribute(attr):
            logger.warning("Attribute '%s' missing in root node", attr)

    attr = "viewBox"
    if not root.hasAttribute(attr):
        logger.warning(
            "Attribute '%s' missing in root node. "
            "This is required for S60 3rd Edition FP1 or older.", attr)

    image_nodes = doc.getElementsByTagName("image")
    if image_nodes:
        logger.warning(
            "Found %s raster 'image' element(s). "
            "Quality may not be optimal.", len(image_nodes))

    if schema is not None:
        data = doc.toprettyxml().strip()
        tree = lxml.etree.fromstring(data)
        if not schema.validate(tree):
            print(data)
            schema.assertValid(tree)

        logger.info("Document passed schema validation.")
