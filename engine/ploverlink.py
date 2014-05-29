#import plover.app
import plover.config
import plover.steno as steno
import plover.translation as translation
#import plover.formatting as formatting
import aware_formatter
from plover.dictionary.loading_manager import manager as dict_manager
from plover.exception import InvalidConfigurationError,DictionaryLoaderException


KEYCODE_TO_STENO_KEY = {
    16: "S-",  # Q
    30: "S-",  # A
    17: "T-",  # W
    31: "K-",  # S
    18: "P-",  # E
    32: "W-",  # D
    19: "H-",  # R
    33: "R-",  # F
    46: "A-",  # C
    47: "O-",  # V
    20: "*",   # T
    34: "*",   # G
    21: "*",   # Y
    35: "*",   # H
    49: "-E",  # N
    50: "-U",  # M
    22: "-F",  # U
    36: "-R",  # J
    23: "-P",  # I
    37: "-B",  # K
    24: "-L",  # O
    38: "-G",  # L
    25: "-T",  # P
    39: "-S",  # ;
    26: "-D",  # [
    40: "-Z",  # '
    2: "#",    # 1
    3: "#",    # 2
    4: "#",    # 3
    5: "#",    # 4
    6: "#",    # 5
    7: "#",    # 6
    8: "#",    # 7
    9: "#",    # 8
    10: "#",   # 9
    11: "#",   # 0
    12: "#",   # -
    13: "#",   # =
}


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
    def __init__(self, output):
        """Creates and configures a single steno pipeline."""

        self.config = load_config()

        # self.subscribers = []
        # self.stroke_listeners = []
        self.is_running = False
        # self.machine = None

        self.translator = translation.Translator()
        #self.formatter = formatting.Formatter()

        self.formatter = aware_formatter.AwareFormatter()
        self.output = output
        self.formatter.set_output(output)
        #self.translator.add_listener(self._translated)
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

        # Keys currently down
        self._down_keys = set()
        self._released_keys = set()
        self.arpeggiate = False

    def key_down(self, keycode):
        if keycode in KEYCODE_TO_STENO_KEY:
            self._down_keys.add(keycode)
            return True
        return False

    def key_up(self, keycode):
        if keycode in KEYCODE_TO_STENO_KEY:
            self._released_keys.add(keycode)
            # Remove invalid released keys
            self._released_keys = \
                self._released_keys.intersection(self._down_keys)

            # A stroke is complete if all pressed keys have been released.
            # If we are in arpeggiate mode then only send stroke when
            # spacebar is pressed.
            send_strokes = bool(self._down_keys and
                                self._down_keys == self._released_keys)
            # if self.arpeggiate:
            #     send_strokes &= event.keystring == ' '
            if send_strokes:
                steno_keys = [KEYCODE_TO_STENO_KEY[k] for k in self._down_keys]
                self._down_keys.clear()
                self._released_keys.clear()
                self._notify(steno_keys)

            return True
        return False

    def get_steno_string(self):
        s = steno.Stroke([KEYCODE_TO_STENO_KEY[k] for k in self._down_keys])
        return s.rtfcre

    def _notify(self, steno_keys):
        s = steno.Stroke(steno_keys)
        try:
            self.translator.translate(s)
        except aware_formatter.StateMismatch:
            self.output.show_message("Resetting state")
            self.translator.clear_state()
            # Resend last stroke
            self.translator.translate(s)

    def _translated(self, undo, do, last):
        # print
        # print undo
        # print do
        # print last

        # Reproducing _translate_stroke()
        do = []
        # Figure out how much of the translation buffer can be involved in this
        # stroke and build the stroke list for translation.
        num_strokes = 1
        translation_count = 0
        for t in reversed(state.translations):
            num_strokes += len(t)
            if num_strokes > dictionary.longest_key:
                break
            translation_count += 1
        translation_index = len(state.translations) - translation_count
        translations = state.translations[translation_index:]
        t = _find_translation(translations, dictionary, stroke)
        do.append(t)
        undo.extend(t.replaced)
        
        all_do = self.translator._state.translations + do
        self.formatter.format([], all_do, self.translator._state.tail)
