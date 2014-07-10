# ibus-plover - IBus engine for the Plover stenography system
#
# Copyright (c) 2014 Rick Lupton <r.lupton@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from __future__ import print_function
import re
from os.path import commonprefix

from gi.repository import IBus
from gi.repository import GLib

from plover.oslayer.keyboardcontrol import KeyboardEmulation
import plover_config
import plover_machine
import plover.steno as steno
import plover.translation as translation
import plover.formatting as formatting
import aware_formatter
from dictmode import DictMode

EVENT_HANDLED = True
EVENT_NOT_HANDLED = False


class PloverEngine(IBus.Engine):
    """IBus engine for Plover stenography"""
    def __init__(self, bus, object_path):
        super(PloverEngine, self).__init__(connection=bus.get_connection(),
                                           object_path=object_path)
        self.__dbus_path = object_path
        self.__is_invalidated = False
        self.__preedit_string = u""
        self.__aux_string = u""
        self.__input_purpose = 0
        self.__input_purpose_hints = 0
        self.__input_capabilities = 0

        # Signal handler for updated surrounding text from input context
        self.connect('set-surrounding-text', self._check_surrounding_text)

        # Lookup table, used only for showing stroke suggestions
        self.__lookup_table = IBus.LookupTable.new(
            page_size=2, cursor_pos=0, cursor_visible=True, round=True)
        self.__lookup_table.set_orientation(IBus.Orientation.VERTICAL)

        ##### Init Plover #####

        # Plover KeyboardEmulation for sending special keys (not normal text)
        self.keyboard_control = KeyboardEmulation()

        # Load the Plover config
        self.config = plover_config.load_config()

        # Set up the Plover pipeline:
        #   - Machine aggregates keypresses into strokes
        #   - Translator looks up strokes in dictionary
        #   - Formatter outputs translated text
        #
        # The machine is slightly customized from the one in Plover:
        # it accepts key press events externally rather than setting
        # up keyboard event capture internally.
        #
        # The formatter is also customized: it uses IBus's surround
        # text feature to check that text is output correctly, rather
        # than blindly backspacing over the existing text that it
        # thinks is next to the cursor.
        self.machine = plover_machine.Stenotype({'arpeggiate': False})
        self.translator = translation.Translator()
        self.formatter = aware_formatter.AwareFormatter()

        # Wire up the pipeline
        self.machine.add_stroke_callback(self._stroke_handler)
        self.translator.add_listener(self.formatter.format)
        self.formatter.set_output(self)
        self.machine.start_capture()

        # Set up the translator. This seems like a reasonable number -
        # if this becomes a problem it can be parameterized.
        self.translator.set_min_undo_length(10)
        dicts = plover_config.get_dicts(self.config)
        self.translator.get_dictionary().set_dicts(dicts)

        # XXX Logging not implemented yet
        # self.logger = Logger()
        # self.translator.add_listener(self.logger.log_translation)

        # Dictionary query/update mode
        dictmode_stroke = steno.Stroke(['H-', 'A-', '-U', '-F'])
        self.dictmode = DictMode(self, self.translator.get_dictionary(),
                                 dict(stroke=dictmode_stroke))

        # Stroke handlers
        class TranslatorProxy:
            def __init__(self, translator):
                self.translator = translator
            def handle_stroke(self, stroke):
                try:
                    self.translator.translate(stroke)
                    return True  # handled
                except aware_formatter.StateMismatch:
                    # The surrounding text didn't match expectations - just
                    # give up and reset the translator state. Then resend last
                    # stroke.
                    self.show_message("Resetting state")
                    self.translator.clear_state()
                    self.translator.translate(stroke)
                return False

        self._stroke_handlers = [
            self.dictmode,
            TranslatorProxy(self.translator)
        ]

    def _stroke_handler(self, steno_keys):
        """Forward strokes from machine to translator"""
        stroke = steno.Stroke(steno_keys)
        for handler in self._stroke_handlers:
            if handler.handle_stroke(stroke):
                return

    def do_process_key_event(self, keyval, keycode, state):
        """Handle key events from IBus"""

        # Pass through password typing
        if self.__input_purpose == IBus.InputPurpose.PASSWORD:
            return EVENT_NOT_HANDLED

        # Ignore key presses with modifiers (e.g. Control-C)
        if (state & ~IBus.ModifierType.RELEASE_MASK):
            return EVENT_NOT_HANDLED

        # Let through a few useful keys
        if keyval in (IBus.KEY_BackSpace,
                      IBus.KEY_Escape,
                      IBus.KEY_Return):
            return EVENT_NOT_HANDLED

        # Send other keypresses to the Steno machine
        is_press = ((state & IBus.ModifierType.RELEASE_MASK) == 0)
        try:
            if is_press:
                self.machine.key_down(keycode)
            else:
                self.machine.key_up(keycode)

            # if self.__aux_string:
            #     self.__aux_string = ""
            #     self.__invalidate()
        except:
            import traceback
            traceback.print_exc()
            return EVENT_NOT_HANDLED

        # Don't pass through key presses corresponding to steno keys
        return EVENT_HANDLED

    def __invalidate(self):
        """Schedule an update"""
        if self.__is_invalidated:
            return
        self.__is_invalidated = True
        GLib.idle_add(self.__update, priority=GLib.PRIORITY_LOW)

    def __commit_string(self, text):
        """Send commited text to IBus"""
        self.commit_text(IBus.Text.new_from_string(text))
        self.__preedit_string = u""
        self.__update()

    def __update(self):
        """Update preedit, auxiliary and lookup table text"""

        # Auxiliary text
        self.update_auxiliary_text(
            IBus.Text.new_from_string(self.__aux_string),
            len(self.__aux_string) > 0)

        # Show preedit text (not currently used)
        # preedit_len = len(self.__preedit_string)
        # attrs = IBus.AttrList()
        # if preedit_len > 0:
        #     attrs.append(IBus.attr_foreground_new(0xff0000, 0, preedit_len))
        #     attrs.append(
        #       IBus.AttributeUnderline(pango.UNDERLINE_SINGLE, 0, preedit_len))
        # self.update_preedit_text(ibus.Text(self.__preedit_string, attrs),
        #                          preedit_len, preedit_len > 0)

        # Lookup table
        table_visible = self.__lookup_table.get_number_of_candidates() > 0
        self.update_lookup_table(self.__lookup_table, table_visible)

        self.__is_invalidated = False

    def do_focus_in(self):
        print("focus in %s" % self.__dbus_path)

        # Signal that surrounding text is needed
        self.get_surrounding_text()

        # XXX Unused currently
        # self.register_properties(self.__prop_list)

        self._reset_translator()

    def do_reset(self):
        """Handle reset signal"""
        # XXX When is this sent by IBus?
        print("RESET %s" % self.__dbus_path)
        self._reset_translator()

    def do_enable(self):
        # Tell IBus we want to use surrounding text later
        print("enable %s" % self.__dbus_path)

    def do_property_activate(self, prop_name):
        # XXX Currently unused
        print("PropertyActivate(%s)" % prop_name)

    def _check_surrounding_text(self, engine, text, cursor_pos, anchor_pos):
        # Written as a connected signal rather than
        # do_set_surrounding_text.  (the IBus Engine implementation
        # handles this signal to store the current surrounding text;
        # defining do_set_surrounding_text here overrides that.)
        print(">>>> Set surrounding text: '%s|%s'" %
              (text.get_text()[:cursor_pos], text.get_text()[cursor_pos:]))

        # Tell formatter not to add an extra space if at the start of
        # a line or if there's already a space there.
        if (cursor_pos == 0) or (text.get_text()[cursor_pos - 1] == ' '):
            print(">>>> attaching <<<<")
            self.formatter.default_action = formatting._Action(attach=True)
        else:
            self.formatter.default_action = None

    def do_set_capabilities(self, caps):
        """Handle set-capabilities signal (store for later)"""
        self.__input_capabilities = caps

    def do_set_content_type(self, purpose, hints):
        """Handle set-content-type signal (store for later)"""
        self.__input_purpose = purpose
        self.__input_purpose_hints = hints

    def have_surrounding_text(self):
        """Return True if surrounding text is available."""
        return (self.__input_capabilities &
                IBus.Capabilite.SURROUNDING_TEXT) != 0

    def get_current_word(self):
        if not self.have_surrounding_text():
            text, cursor_pos, anchor_pos = '', 0, 0
        else:
            text, cursor_pos, anchor_pos = self.get_surrounding_text()
            text = text.get_text()
        if not text:
            return '<<NO WORD>>'
        return text[:cursor_pos].split()[-1]

    def show_message_list(self, message=None, values=None):
        if message is not None:
            self.__aux_string = message
        if values is not None:
            self.__lookup_table.clear()
            self.__lookup_table.set_page_size(max(1, min(10, len(values))))
            for v in values:
                self.__lookup_table.append_candidate(
                    IBus.Text.new_from_string(v))
        if message is not None or values is not None:
            self.__invalidate()

    # Plover output callbacks
    def change_string(self, before, after):
        """Attempt to change text from `before` to `after`.

        Return True if successful.
        """
        offset = len(commonprefix([before, after]))
        delete_length = len(before[offset:])

        # Delete the existing text. If we have surrounding text, check
        # it to make sure the before text is as expected. If it isn't
        # available, just send the right number of backspaces and hope.
        if self.have_surrounding_text():
            # Check if surrounding text matches text to delete
            s, p, p2 = self.get_surrounding_text()
            if p != p2:  # XXX
                print("Warning: selections not implemented (%s)" % s.get_text())
            current_text = s.get_text()[p - len(before):p]
            if current_text != before:
                # print "MISMATCH: '%s' != '%s'" % (before, current_text)
                return False
            self.delete_surrounding_text(-delete_length, delete_length)
        else:
            self.keyboard_control.send_backspaces(delete_length)

        # Add the new text
        self.__commit_string(after[offset:])
        return True

    def send_key_combination(self, key_combo):
        """Output a special key combination."""
        # Does it need to be delayed?
        # wx.CallAfter(self.keyboard_control.send_key_combination, c)

        # Does it need to be protected so it's not picked up again? In
        # theory yes; but as long as key combos aren't sending steno
        # key codes it'll be ok.
        self.keyboard_control.send_key_combination(key_combo)

    def send_engine_command(self, c):
        """Handle a Plover engine command"""
        # XXX not implemented yet
        print("**** Send engine command:", c)

    def show_message(self, message):
        """Show a message to the user via the auxiliary string"""
        self.__aux_string = message
        self.__invalidate()
