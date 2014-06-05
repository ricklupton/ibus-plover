from gi.repository import IBus

keysyms = IBus
modifier = IBus.ModifierType

def parse_key_combinations(combo_string):
    """Emulate a sequence of key combinations.

    KeyboardCapture instance would normally detect the emulated
    key events. In order to prevent this, all KeyboardCapture
    instances are told to ignore the emulated key events.

    Argument:

    combo_string -- A string representing a sequence of key
    combinations. Keys are represented by their names in the IBus
    keysyms module. For example, the left Alt key is represented by
    'Alt_L'. Keys are either separated by a space or a left or right
    parenthesis.  Parentheses must be properly formed in pairs and may
    be nested. A key immediately followed by a parenthetical indicates
    that the key is pressed down while all keys enclosed in the
    parenthetical are pressed and released in turn. For example,
    Alt_L(Tab) means to hold the left Alt key down, press and release
    the Tab key, and then release the left Alt key.

    """
    # Convert the argument into a sequence of keycode, event type pairs
    # that, if executed in order, would emulate the key
    # combination represented by the argument.
    keysym_events = []
    key_down_stack = []
    current_command = []
    def press(k):
        keysym_events.append((k, 0))
    def release(k):
        keysym_events.append((k, modifier.RELEASE_MASK))
    for c in combo_string:
        if c in (' ', '(', ')'):
            keysym, keycode, state = _parse_key(''.join(current_command))
            # keycode means keysym here...
            keysym = keysyms.name_to_keycode(keystring)
            # keycode, mods = self._keysym_to_keycode_and_modifiers(keysym)
            current_command = []
            if keysym is keysyms.VoidSymbol:
                continue
            if c == ' ':
                # Record press and release for command's key.
                press(keysym)
                release(keysym)
            elif c == '(':
                # Record press for command's key.
                key_down_stack.append(keysym)
                press(keysym)
            elif c == ')':
                # Record press and release for command's key and
                # release previously held key.
                press(keysym)
                release(keysym)
                if len(key_down_stack):
                    release(key_down_stack.pop())
        else:
            current_command.append(c)
    # Record final command key.
    keysym = keysyms.name_to_keycode(''.join(current_command))
    #keysym, mods = self._keysym_to_keysym_and_modifiers(keysym)
    if keysym is not keysyms.VoidSymbol:
        press(keysym)
        release(keysym)

    # Release all keys.
    for keysym in key_down_stack:
        release(keysym)

    return keysym_events


def _parse_key(keystring):
    keysym = XK.string_to_keysym(keystring)
    keycode, mods = _keysym_to_keycode_and_modifiers(keysym)


def _keysym_to_keycode_and_modifiers(keysym):
    """Return a keycode and modifier mask pair that result in the keysym.

    There is a one-to-many mapping from keysyms to keycode and
    modifiers pairs; this function returns one of the possibly
    many valid mappings, or the tuple (None, None) if no mapping
    exists.

    Arguments:

    keysym -- A key symbol.

    """
    keycodes = self.display.keysym_to_keycodes(keysym)
    if len(keycodes) > 0:
        keycode, offset = keycodes[0]
        modifiers = 0
        if offset == 1 or offset == 3:
            # The keycode needs the Shift modifier.
            modifiers |= X.ShiftMask
        if offset == 2 or offset == 3:
            # The keysym is in group Group 2 instead of Group 1.
            for i, mod_keycodes in enumerate(self.modifier_mapping):
                if keycode in mod_keycodes:
                    modifiers |= (1 << i)
        return (keycode, modifiers)
    return (None, None)
