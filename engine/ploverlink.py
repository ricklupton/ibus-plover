#import plover.app
import plover.config
import plover.steno as steno
import plover.translation as translation
#import plover.formatting as formatting
import aware_formatter
from plover.dictionary.loading_manager import manager as dict_manager
from plover.exception import InvalidConfigurationError,DictionaryLoaderException



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

    # log_file_name = config.get_log_file_name()
    # if log_file_name:
    #     engine.set_log_file_name(log_file_name)

    # engine.enable_stroke_logging(config.get_enable_stroke_logging())
    # engine.enable_translation_logging(config.get_enable_translation_logging())

    # engine.set_is_running(config.get_auto_start())


class Steno(object):
    def __init__(self, machine, output):
        """Creates and configures a single steno pipeline."""

        self.config = load_config()

        # self.subscribers = []
        # self.stroke_listeners = []
        self.is_running = False
        self.machine = machine

        self.translator = translation.Translator()
        self.machine.add_stroke_callback(self._stroke_notify)
        self.machine.start_capture()

        self.formatter = aware_formatter.AwareFormatter()
        self.output = output
        self.formatter.set_output(output)
        # self.logger = Logger()
        # self.translator.add_listener(self.logger.log_translation)
        self.translator.add_listener(self.formatter.format)
        # This seems like a reasonable number. If this becomes a problem it can
        # be parameterized.
        self.translator.set_min_undo_length(10)

        self.translator.get_dictionary().set_dicts(get_dicts(self.config))


        # self.full_output = SimpleNamespace()
        # self.command_only_output = SimpleNamespace()
        # self.running_state = self.translator.get_state()
        # self.set_is_running(False)

        # self.machine.add_state_callback(self._machine_state_callback)
        # self.machine.add_stroke_callback(self.logger.log_stroke)
        # self.machine.add_stroke_callback(self._translator_machine_callback)

    def _stroke_notify(self, steno_keys):
        s = steno.Stroke(steno_keys)
        try:
            self.translator.translate(s)
        except aware_formatter.StateMismatch:
            self.output.show_message("Resetting state")
            self.translator.clear_state()
            # Resend last stroke
            self.translator.translate(s)
