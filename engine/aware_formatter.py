"""Plover Formatter which is aware of the surrounding text
"""

from plover.formatting import (Formatter, OutputHelper, _get_last_action,
                               _translation_to_actions, _raw_to_actions)
from os.path import commonprefix
from collections import namedtuple


class AwareFormatter(Formatter):
    """Convert translations into output.

    This overrides the OutputHelper to call delete_backwards instead
    of send_backspaces.
    """

    output_type = namedtuple(
        'output', ['change_string', 'send_key_combination',
                   'send_engine_command'])

    def format(self, undo, do, prev):
        """Format the given translations.

        This duplicates Formatter's logic - it would be better if
        there was a render(old, new) method that could be overridden.
        """
        for t in do:
            last_action = _get_last_action(prev.formatting if prev else None)
            if t.english:
                t.formatting = _translation_to_actions(t.english, last_action)
            else:
                t.formatting = _raw_to_actions(t.rtfcre[0], last_action)
            prev = t

        old = [a for t in undo for a in t.formatting]
        new = [a for t in do for a in t.formatting]
        print "old:", old
        print "new:", new

        min_length = min(len(old), len(new))
        for i in xrange(min_length):
            if old[i] != new[i]:
                break
        else:
            i = min_length

        self.render(old[i:], new[i:])

    def render(self, old, new):
        AwareOutputHelper(self._output).render(old, new)


class StateMismatch(Exception):
    pass


class AwareOutputHelper(OutputHelper):
    def commit(self):
        if self.before != self.after:
            success = self.output.change_string(self.before, self.after)
            if not success:
                raise StateMismatch()
        self.before = ''
        self.after = ''
