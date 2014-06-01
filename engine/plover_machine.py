"Represent the IBus engine through the Plover machine interface"

from plover.machine.base import StenotypeBase, STATE_RUNNING


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


class Stenotype(StenotypeBase):
    """
    This class implements the three methods necessary for a standard
    stenotype interface: start_capture, stop_capture, and
    add_callback.

    """

    def __init__(self, params):
        """Report IBus events to Plover."""
        StenotypeBase.__init__(self)
        self._down_keys = set()
        self._released_keys = set()
        self.arpeggiate = params['arpeggiate']

    def start_capture(self):
        """Begin listening for output from the stenotype machine."""
        self._ready()

    def stop_capture(self):
        """Stop listening for output from the stenotype machine."""
        self._stopped()

    def key_down(self, keycode):
        """Called when a key is pressed."""
        if self.state != STATE_RUNNING:
            return False  # not handled -- will type as normal
        elif keycode in KEYCODE_TO_STENO_KEY:
            self._down_keys.add(keycode)
            return True  # handled
        else:
            return False  # not handled

    # def _post_suppress(self, suppress, steno_keys):
    #     """Backspace the last stroke since it matched a command.
    #     The suppress function is passed in to prevent threading issues with
    #     the gui.
    #     """
    #     n = len(steno_keys)
    #     if self.arpeggiate:
    #         n += 1
    #     suppress(n)

    def key_up(self, keycode):
        """Called when a key is released."""
        if self.state != STATE_RUNNING:
            return False  # not handled -- will type as normal
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

            return True  # handled
        return False  # not handled

    @staticmethod
    def get_option_info():
        bool_converter = lambda s: s == 'True'
        return {
            'arpeggiate': (False, bool_converter),
        }
