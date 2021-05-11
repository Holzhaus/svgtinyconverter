import logging
import argparse
from . import converter
from . import validation


def main(argv=None, configure_logging=True):
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=argparse.FileType("r+"))
    parser.add_argument("--validate-schema", action="store_true")
    args = parser.parse_args(argv)

    if configure_logging:
        logging.basicConfig()

    if args.validate_schema:
        schema = validation.schema("svgtiny-1.2.rng")
    else:
        schema = None

    doc = converter.convert(args.file)
    validation.validate(doc, schema=schema)
    args.file.seek(0)
    args.file.truncate()
    args.file.write(doc.toxml())
