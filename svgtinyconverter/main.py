import logging
import argparse
from . import converter


def main(argv=None, configure_logging=True):
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=argparse.FileType("r+"))
    args = parser.parse_args(argv)

    if configure_logging:
        logging.basicConfig()

    doc = converter.convert(args.file)
    args.file.seek(0)
    args.file.truncate()
    args.file.write(doc.toxml())
