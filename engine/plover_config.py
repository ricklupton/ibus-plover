"""Helper functions to load Plover config and dictionaries"""

import plover.config
from plover.dictionary.loading_manager import manager as dict_manager
from plover.exception import (InvalidConfigurationError,
                              DictionaryLoaderException)


def load_config():
    config = plover.config.Config()
    config.target_file = plover.config.CONFIG_FILE
    with open(config.target_file, 'rb') as f:
        config.load(f)
    return config


def get_dicts(config):
    """Initialize a StenoEngine from a config object."""
    dictionary_file_names = config.get_dictionary_file_names()
    try:
        dicts = dict_manager.load(dictionary_file_names)
    except DictionaryLoaderException as e:
        raise InvalidConfigurationError(unicode(e))
    return dicts
