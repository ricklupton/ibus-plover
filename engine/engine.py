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

import sys
import gobject
import pango
import ibus
from ibus import keysyms
from ibus import modifier
from os.path import commonprefix

from plover.oslayer.keyboardcontrol import KeyboardEmulation
from ploverlink import Steno
# from plover import StenoEngine
import plover_machine
from key_combinations import parse_key_combinations

import aware_formatter
import plover.formatting as formatting

class Engine(ibus.EngineBase):
    def __init__(self, bus, object_path):
        super(Engine, self).__init__(bus, object_path)
        self.__is_invalidate = False
        self.__preedit_string = u""
        self.__aux_string = u""
        #self.__lookup_table = ibus.LookupTable()
        self.__prop_list = ibus.PropList()
        self.__prop_list.append(ibus.Property(u"test", icon = u"ibus-locale"))
        self.__init_plover()

    def __init_plover(self):
        print "Init plover"
        self.machine = plover_machine.Stenotype({'arpeggiate': False})
        self.steno = Steno(self.machine, self)
        self.keyboard_control = KeyboardEmulation()

        # # Patch formatter
        # formatting.Formatter = aware_formatter.AwareFormatter
        # self.steno_engine = plover.app.StenoEngine()
        # # self.steno_engine.add_callback(self.__plover_update_status)
        # self.steno_engine.full_output.change_string = self.change_string
        # self.steno_engine.full_output.send_key_combination = self.send_key_combination
        # self.steno_engine.full_output.send_engine_command = self.send_engine_command
        # self.steno_engine.set_machine(self.machine)
        # self.steno_engine.set_output(
        #     Output(self.__plover_consume_command, self.steno_engine))

        # plover.app.init_engine(self.steno_engine, self.plover_config)
        #self.steno_engine.set_is_running(True)

    def process_key_event(self, keyval, keycode, state):
        # ignore key presses with modifiers (e.g. Control-C)
        if (state & ~modifier.RELEASE_MASK):
            return False

        is_press = ((state & modifier.RELEASE_MASK) == 0)
        try:
            if is_press:
                handled = self.machine.key_down(keycode)
            else:
                handled = self.machine.key_up(keycode)

            # # Show steno keys
            if self.__aux_string:
                self.__aux_string = ""
                self.__invalidate()
            # self.__aux_string = self.steno.get_steno_string()
            # self.__invalidate()
        except:
            import traceback
            traceback.print_exc()
        
        # Don't pass through key presses corresponding to steno keys
        if not handled:
            print "...", keyval, keycode, state
        return handled

        if self.__preedit_string:
            if keyval == keysyms.Return:
                self.__commit_string(self.__preedit_string)
                return True
            elif keyval == keysyms.Escape:
                self.__preedit_string = u""
                self.__update()
                return True
            elif keyval == keysyms.BackSpace:
                self.__preedit_string = self.__preedit_string[:-1]
                self.__invalidate()
                return True
            elif keyval == keysyms.space:
                # if self.__lookup_table.get_number_of_candidates() > 0:
                #     self.__commit_string(self.__lookup_table.get_current_candidate().text)
                # else:
                #     self.__commit_string(self.__preedit_string)
                self.__commit_string(self.__preedit_string)
                return False
            elif keyval == keysyms.Left or keyval == keysyms.Right:
                return True
        if keyval in xrange(keysyms.a, keysyms.z + 1) or \
            keyval in xrange(keysyms.A, keysyms.Z + 1):
            if state & (modifier.CONTROL_MASK | modifier.ALT_MASK) == 0:
                self.__preedit_string += unichr(keyval)
                self.__invalidate()
                return True
        else:
            if keyval < 128 and self.__preedit_string:
                self.__commit_string(self.__preedit_string)

        return False

    def __invalidate(self):
        if self.__is_invalidate:
            return
        self.__is_invalidate = True
        gobject.idle_add(self.__update, priority = gobject.PRIORITY_LOW)

    def __commit_string(self, text):
        self.commit_text(ibus.Text(text))
        self.__preedit_string = u""
        self.__update()

    def __update(self):
        preedit_len = len(self.__preedit_string)
        attrs = ibus.AttrList()
        if preedit_len > 0:
            attrs.append(ibus.AttributeForeground(0xff0000, 0, preedit_len))
        self.update_auxiliary_text(
            ibus.Text(self.__aux_string, ibus.AttrList()),
            len(self.__aux_string) > 0)
        attrs.append(
            ibus.AttributeUnderline(pango.UNDERLINE_SINGLE, 0, preedit_len))
        self.update_preedit_text(ibus.Text(self.__preedit_string, attrs),
                                 preedit_len, preedit_len > 0)
        self.__is_invalidate = False

    def focus_in(self):
        print "focus in %s" % self.__proxy._object_path
        sys.stdout.flush()
        #self.register_properties(self.__prop_list)

    def focus_out(self):
        pass

    def reset(self):
        pass

    def enable(self):
        # Tell IBus we want to use surrounding text later
        print "enable %s" % self.__proxy._object_path
        sys.stdout.flush()
        self.get_surrounding_text()

    def property_activate(self, prop_name):
        print "PropertyActivate(%s)" % prop_name

    def __plover_update_status(self, state):
        print "Plover update status:", state

    def __plover_consume_command(self, command):
        print "Plover consume command:", command

    # Plover callbacks
    def change_string(self, before, after):
        # Check if surrounding text matches text to delete
        s, p = self.get_surrounding_text()
        current_text = s.get_text()[p - len(before):p]
        if current_text != before:
            print "MISMATCH: '%s' != '%s'" % (before, current_text)
            return False
        offset = len(commonprefix([before, after]))
        print "____", offset, "___", before, '->', after
        #print "Changing ok: '%s'" % t
        delete_length = len(before[offset:])
        self.delete_surrounding_text(-delete_length, delete_length)
        self.__preedit_string += after[offset:]
        self.__commit_string(self.__preedit_string)
        return True

    def send_key_combination(self, c):
        print "**** Send key comb:", c
        # Does it need to be delayed?
        # wx.CallAfter(self.keyboard_control.send_key_combination, c)

        # Does it need to be protected so it's not picked up again? In
        # theory yes; but as long as key combos aren't sending steno
        # key codes it'll be ok.
        self.keyboard_control.send_key_combination(c)


    # TODO: test all the commands now
    def send_engine_command(self, c):
        print "**** Send engine command:", c
        result = self.engine_command_callback(c)
        # if result and not self.engine.is_running:
        #     self.engine.machine.suppress = self.send_backspaces

    def show_message(self, message):
        def set_message():
            self.__aux_string = message
            self.__invalidate()
        gobject.idle_add(set_message, priority = gobject.PRIORITY_LOW)


class EngineFactory(ibus.EngineFactoryBase):
    def __init__(self, bus):
        self.__bus = bus
        super(EngineFactory, self).__init__(self.__bus)
        self.__id = 0

    def create_engine(self, engine_name):
        if engine_name == "plover":
            self.__id += 1
            print engine_name, self.__id
            bus_name = "%s/%d" % ("/org/freedesktop/IBus/Plover/Engine",
                                  self.__id)
            try:
                e = engine.Engine(self.__bus, bus_name)
            except:
                traceback.print_exc()
            return e
        return super(EngineFactory, self).create_engine(engine_name)
