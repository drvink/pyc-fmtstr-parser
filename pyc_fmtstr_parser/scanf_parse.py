# based on printf_parse from gnulib rev be7d73709d2b3bceb987f1be00a049bb7021bf87
#
# Copyright (C) 2014, Mark Laws.

# Copyright (C) 1999, 2002-2003, 2005-2007, 2009-2014 Free Software
# Foundation, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with this program; if not, see <http://www.gnu.org/licenses/>.

import ctypes
from flufl.enum import Enum
sizeof = ctypes.sizeof

Arg_type = Enum('Arg_type', [str(x.strip()) for x in '''
TYPE_NONE
TYPE_SCHAR
TYPE_UCHAR
TYPE_SHORT
TYPE_USHORT
TYPE_INT
TYPE_UINT
TYPE_LONGINT
TYPE_ULONGINT
TYPE_LONGLONGINT
TYPE_ULONGLONGINT
TYPE_FLOAT
TYPE_DOUBLE
TYPE_LONGDOUBLE
TYPE_CHAR
TYPE_WIDE_CHAR
TYPE_STRING
TYPE_WIDE_STRING
TYPE_POINTER
TYPE_COUNT_SCHAR_POINTER
TYPE_COUNT_SHORT_POINTER
TYPE_COUNT_INT_POINTER
TYPE_COUNT_LONGINT_POINTER
TYPE_COUNT_LONGLONGINT_POINTER
TYPE_CHARSEQ
TYPE_NUMREAD
'''.splitlines() if x != ''])

# arg_index value indicating that no argument is consumed.
ARG_NONE = ~0

class Argument(object):
    __slots__ = ['type', 'data']

class Arguments(object):
    __slots__ = ['count', 'arg']

    def __init__(self):
        self.count = 0
        self.arg = []

class Directive(object):
    '''A parsed directive.'''
    __slots__ = ['dir_start', 'dir_end', 'width_start', 'width_end',
                 'width_arg_index', 'precision_arg_index', 'conversion',
                 'arg_index']

    def __init__(self):
        self.width_start = None
        self.width_end = None
        self.width_arg_index = ARG_NONE
        self.arg_index = ARG_NONE

class Directives(object):
    '''A parsed format string.'''
    __slots__ = ['count', 'dir', 'max_width_length']

    def __init__(self):
        self.count = 0
        self.dir = []

def REGISTER_ARG(a, index, type):
    n = index

    while a.count <= n:
        try:
            a.arg[a.count]
        except IndexError:
            a.arg.append(Argument())
        a.arg[a.count].type = Arg_type.TYPE_NONE
        a.count += 1
    if a.arg[n].type == Arg_type.TYPE_NONE:
        a.arg[n].type = type
    elif a.arg[n].type != type:
        raise ValueError('ambiguous type for positional argument')

def conv_signed(c, flags):
    # If 'long long' exists and is larger than 'long':
    if flags >= 16 or flags & 4:
        return c, Arg_type.TYPE_LONGLONGINT
    else:
        # If 'long long' exists and is the same as 'long', we parse "lld" into
        # TYPE_LONGINT.
        if flags >= 8:
            type = Arg_type.TYPE_LONGINT
        elif flags & 2:
            type = Arg_type.TYPE_SCHAR
        elif flags & 1:
            type = Arg_type.TYPE_SHORT
        else:
            type = Arg_type.TYPE_INT
        return c, type

def conv_unsigned(c, flags):
    # If 'long long' exists and is larger than 'long':
    if flags >= 16 or flags & 4:
        return c, Arg_type.TYPE_ULONGLONGINT
    else:
        # If 'unsigned long long' exists and is the same as 'unsigned long', we
        # parse "llu" into TYPE_ULONGINT.
        if flags >= 8:
            type = Arg_type.TYPE_ULONGINT
        elif flags & 2:
            type = Arg_type.TYPE_UCHAR
        elif flags & 1:
            type = Arg_type.TYPE_USHORT
        else:
            type = Arg_type.TYPE_UINT
        return c, type

def conv_float(c, flags):
    if flags >= 16 or flags & 4:
        return c, Arg_type.TYPE_LONGDOUBLE
    elif flags >= 8:
        return c, Arg_type.TYPE_DOUBLE
    else:
        return c, Arg_type.TYPE_FLOAT

def conv_char(c, flags):
    if flags >= 8:
        return c, Arg_type.TYPE_WIDE_CHAR
    else:
        return c, Arg_type.TYPE_CHAR

def conv_string(c, flags):
    if flags >= 8:
        return c, Arg_type.TYPE_WIDE_STRING
    else:
        return c, Arg_type.TYPE_STRING

def conv_pointer(c, flags):
    return c, Arg_type.TYPE_POINTER

def conv_intpointer(c, flags):
    # If 'long long' exists and is larger than 'long':
    if flags >= 16 or flags & 4:
        return c, Arg_type.TYPE_COUNT_LONGLONGINT_POINTER
    else:
        # If 'long long' exists and is the same as 'long', we parse "lln" into
        # TYPE_COUNT_LONGINT_POINTER.
        if flags >= 8:
            type = Arg_type.TYPE_COUNT_LONGINT_POINTER
        elif flags & 2:
            type = Arg_type.TYPE_COUNT_SCHAR_POINTER
        elif flags & 1:
            type = Arg_type.TYPE_COUNT_SHORT_POINTER
        else:
            type = Arg_type.TYPE_COUNT_INT_POINTER
        return c, type

def conv_numread(c, flags):
    return c, Arg_type.TYPE_NUMREAD

def conv_none(c, flags):
    return c, Arg_type.TYPE_NONE

_conv_char = {
    'd': conv_signed,
    'i': conv_signed,
    'o': conv_unsigned,
    'u': conv_unsigned,
    'x': conv_unsigned,
    'X': conv_unsigned,
    'f': conv_float,
    'e': conv_float,
    'E': conv_float,
    'g': conv_float,
    'a': conv_float,
    'c': conv_char,
    's': conv_string,
    'p': conv_pointer,
    'n': conv_numread,
    '%': conv_none
}

def scanf_parse(fmt):
    '''Parses the format string.  Fills in the number N of directives, and fills
    in directives[0], ..., directives[N-1], and sets directives[N].dir_start to
    the end of the format string.  Also fills in the arg_type fields of the
    arguments and the needed count of arguments.'''
    cp = 0                   # index into format string
    arg_posn = 0             # number of regular arguments consumed
    max_width_length = 0

    d = Directives()
    a = Arguments()

    while True:
        try:
            c = fmt[cp]
        except IndexError:
            break

        cp += 1
        if c == '%':
            arg_index = ARG_NONE
            d.dir.append(Directive())
            dp = d.dir[d.count]
            dp.dir_start = cp - 1

            # Test for positional argument.
            if fmt[cp].isdigit():
                np = cp
                while fmt[np].isdigit():
                    np += 1
                if fmt[np] == '$':
                    n = 0

                    np = cp
                    while fmt[np].isdigit():
                        n = n * 10 + (ord(fmt[np]) - ord('0'))
                        np += 1
                    if n == 0:
                        raise ValueError('positional argument 0')
                    arg_index = n - 1
                    cp = np + 1

            # Parse the field width.
            if fmt[cp] == '*':
                dp.width_start = cp
                cp += 1
                dp.width_end = cp
                if max_width_length < 1:
                    max_width_length = 1

                # Test for positional argument.
                if fmt[cp].isdigit():
                    np = cp
                    while fmt[np].isdigit():
                        np += 1
                    if fmt[np] == '$':
                        n = 0

                        np = cp
                        while fmt[np].isdigit():
                            n = n * 10 + (ord(fmt[np]) - ord('0'))
                            np += 1
                        if n == 0:
                            raise ValueError('positional argument 0')
                        dp.width_arg_index = n - 1
                        cp = np + 1
                if dp.width_arg_index == ARG_NONE:
                    dp.width_arg_index = arg_posn
                    arg_posn += 1
                REGISTER_ARG(a, dp.width_arg_index, Arg_type.TYPE_INT)
            elif fmt[cp].isdigit():
                dp.width_start = cp
                while fmt[cp].isdigit():
                    cp += 1
                dp.width_end = cp
                width_length = dp.width_end - dp.width_start
                if max_width_length < width_length:
                    max_width_length = width_length

            # Parse argument type/size specifiers.
            flags = 0

            while True:
                if fmt[cp] == 'h':
                    flags |= (1 << (flags & 1))
                    cp += 1
                elif fmt[cp] == 'L':
                    flags |= 4
                    cp += 1
                elif fmt[cp] == 'l':
                    flags += 8
                    cp += 1
                elif fmt[cp] == 'j':
                    raise ValueError("don't know how to handle intmax_t")
                elif fmt[cp] == 'z':
                    if sizeof(ctypes.c_size_t) > sizeof(ctypes.c_long):
                        # size_t = long long
                        flags += 16
                    elif sizeof(ctypes.c_size_t) > sizeof(ctypes.c_int):
                        # size_t = long
                        flags += 8
                    cp += 1
                elif fmt[cp] == 't':
                    raise ValueError("don't know how to handle ptrdiff_t")
                else:
                    break

            # Read the conversion character.
            c = fmt[cp]
            cp += 1
            if c == '[':
                match = True
                chars = ''
                first = cp

                while True:
                    try:
                        c = fmt[cp]
                    except IndexError:
                        break
                    try:
                        c2 = fmt[cp + 2]
                    except IndexError:
                        c2 = ''

                    if cp == first and c == '^':
                        match = False
                    elif cp == first and c == ']':
                        chars += ']'
                    elif fmt[first] == '^' and cp == first + 1 and c == ']':
                        chars += ']'
                    elif c == '-':
                        if fmt[cp + 1] == ']':
                            chars += '-'
                            cp += 1
                            c = ']'
                            break
                        else:
                            chars += ''.join(chr(x) for x in xrange(
                                ord(fmt[cp - 1]), ord(fmt[cp + 1]) + 1))
                            cp += 1
                    elif c == ']':
                        break
                    elif fmt[cp + 1] == '-' and c2 != ']':
                        pass
                    else:
                        chars += c
                    cp += 1

            if c == ']':
                c = '['
                type = Arg_type.TYPE_CHARSEQ
            else:
                try:
                    c, type = _conv_char[c](c, flags)
                except KeyError:
                    raise ValueError('bad conversion character: %%%s' % c)

            if type != Arg_type.TYPE_NONE:
                dp.arg_index = arg_index
                if dp.arg_index == ARG_NONE:
                    dp.arg_index = arg_posn
                    arg_posn += 1
                REGISTER_ARG(a, dp.arg_index, type)
            dp.conversion = c
            dp.dir_end = cp

            d.count += 1

    d.dir.append(Directive())
    d.dir[d.count].dir_start = cp

    d.max_width_length = max_width_length

    return d, a
