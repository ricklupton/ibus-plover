from plover.steno import normalize_steno


class DictMode(object):
    def __init__(self, engine, dictionary, options):
        self._engine = engine
        self._dictionary = dictionary
        self._special_stroke = options['stroke']
        self._state = WaitingState(self)

    def change_state(self, state_class):
        self._state.exit()
        self._state = state_class(self)
        self._state.enter()

    def handle_stroke(self, stroke):
        return self._state.handle_stroke(stroke)


class DictModeState(object):
    def __init__(self, mode):
        self._mode = mode

    def enter(self):
        pass

    def exit(self):
        pass


class WaitingState(DictModeState):
    def handle_stroke(self, stroke):
        # Activate on the 'special' stroke
        if stroke == self._mode._special_stroke:
            self._mode.change_state(ActiveState)
            return True
        return False


class ActiveState(DictModeState):
    def __init__(self, mode):
        super(ActiveState, self).__init__(mode)
        self._strokes = []
        self._active_word = None

    def enter(self):
        # Show message with existing definitions
        self._active_word = self._mode._engine.get_current_word()
        existing_defs = self._mode._dictionary.reverse_lookup(self._active_word)
        entries = ['/'.join(strokes) for strokes in existing_defs]
        if entries:
            self._mode._engine.show_message_list(
                message='Definitions for "%s":' % self._active_word,
                values=entries)
        else:
            self._mode._engine.show_message_list(
                message='(no definitions for "%s")' % self._active_word)

    def exit(self):
        # Clear message
        self._mode._engine.show_message_list('', [])

    def handle_stroke(self, stroke):
        if stroke.is_correction:
            if self._strokes:
                # Undo last stroke
                self._strokes.pop()
                self._update_message()
            else:
                # No strokes in list, exit
                self._mode.change_state(WaitingState)

        elif stroke == self._mode._special_stroke:
            # Finish, adding strokes to dictionary
            if self._strokes:
                self._mode._dictionary.set(normalize_steno(self.strokes_string),
                                           self._active_word)
            self._mode.change_state(WaitingState)

        else:
            # Any other stroke is added to the list
            self._strokes.append(stroke)
            self._update_message()

        return True  # handled

    def _update_message(self):
        self._mode._engine.show_message_list(
            message='New definition for "%s":' % self._active_word,
            values=[self.strokes_string])

    @property
    def strokes_string(self):
        return '/'.join(s.rtfcre for s in self._strokes)
