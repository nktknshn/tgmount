import logging


def init_logging(debug=False):
    formatter = logging.Formatter(
        '%(levelname)s\t[%(name)s]\t%(message)s', datefmt="%Y-%m-%d %H:%M:%S")

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()

    if (root_logger.hasHandlers()):
        root_logger.handlers.clear()

    root_logger.addHandler(handler)

    if debug:
        handler.setLevel(logging.DEBUG)
        root_logger.setLevel(logging.DEBUG)
        logging.getLogger('tgvfs').setLevel(logging.DEBUG)
        logging.getLogger('tgclient').setLevel(logging.DEBUG)
        logging.getLogger('telethon').setLevel(logging.INFO)
    else:
        handler.setLevel(logging.INFO)
        root_logger.setLevel(logging.INFO)
        logging.getLogger('tgvfs').setLevel(logging.INFO)
        logging.getLogger('tgclient').setLevel(logging.INFO)
        logging.getLogger('telethon').setLevel(logging.ERROR)
