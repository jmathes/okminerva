#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import inspect

primitives = [tuple, list, set, int, long, float, str, unicode, bool]
#Listen up, you primitives! This is my BOOM stick

prod = False  # override with some logic for deciding whether we're in dev or production

if not prod:
    import os
    import logging
    import traceback
    import re
    import __builtin__
    from pprint import pformat
    try:
        from lxml import etree
    except:
        etree = None

dev_logger = None


def devlog(*a, **k):
    dev_logger.error(*a, **k)


def get_instancemethod_source(method):
    try:
        fn = inspect.getmodule(method).__file__
        if fn.endswith("pyc"):
            fn = fn[:-1]
        definition = "from %s:%s" % (fn,
                      method.im_func.func_code.co_firstlineno)
    except AttributeError:
        definition = ("This function has no metadata. Usually that means "
                         "it was created in an unusual way, like lambda or "
                         "functools.partial")
    return definition


def get_pretty_debug_output(tb, value=None, my_name=None, my_type=None):
    def get_attribute(value, attr):
        try:
            return getattr(value, attr)
        except:
            try:
                return value.__getattribute__(attr)
            except:
                return "*** getattr and __getattribute__ both failed **"

    filename = tb[-2][0].split("/")[-1]
    lines = []
    try:
        my_type = value.__class__.__name__
    except AttributeError:
        pass
    if my_type is None:
        my_type = type(value).__name__
    if my_name is None:
        my_name = tb[-1][2]
    call = tb[-2][3] or my_name + "(<from repl>)"
    exp = re.search(my_name + r"\((.*)\)", call)
    if exp:
        exp = exp.groups()[0]
        exp = "%s(%s)" % (my_name, exp)
    else:
        exp = call

    docstring_lines = []
    try:
        if isinstance(value.__doc__, basestring):
            docstring_lines = ['#  ' + l for l in value.__doc__.split("\n")]
    except AttributeError:
        pass

    if value is not None and isinstance(value, dict):
        lines += pformat(dict(value)).split("\n")
        if lines[0].startswith('OrderedDict('):
            lines[0] = lines[0][12:]
            lines[-1] = lines[-1][:-1]
    elif any([isinstance(value, t) for t in primitives]):
        lines += pformat(value).split("\n")
    elif my_type == 'function':
        lines += docstring_lines
        lines.append("%s(%s)" % (value.__name__,
                ', '.join(value.func_code.co_varnames)))
        lines.append("from %s:%s" % (value.func_code.co_filename,
                                            value.func_code.co_firstlineno))
    elif my_type == 'instancemethod':
        lines += docstring_lines
        try:
            lines.append("%s.%s(%s)" % (
                    value.im_class.__name__,
                    value.im_func.__name__,
                    ', '.join(value.im_func.func_code.co_varnames)))
        except AttributeError:
            pass
        lines.append(get_instancemethod_source(value))
    elif my_type == 'type':
        lines += docstring_lines
        lines.append("class %s from %s" % (value.__name__, value.__module__))
        try:
            lines.append("%s" % value.__implemented__)
        except:
            pass
    else:
        lines += docstring_lines

        max_len = 0
        callables = []
        uncallables = []
        attributes = [v for v in dir(value) if not v.startswith("__")]
        for attr_name in attributes:
            attr = get_attribute(value, attr_name)
            if (True
                    and type(attr).__name__ != 'classobj'
                    and callable(attr)):
                if attr_name in ['tostring', 'dump', 'repr']:
                    try:
                        lines += ".%s():" % attr_name
                        lines += "%s" % attr()
                    except:
                        pass
                else:
                    max_len = max(max_len, len(attr_name))
                    callables.append((attr, attr_name))
            else:
                max_len = max(max_len, len(attr_name))
                uncallables.append((attr, attr_name))
        if etree is not None and my_type == '_Element':
            max_len = max(max_len, len('etree.tostring()') + 2)

        for attr, attr_name in uncallables:
            spaces = " " * (max_len - len(attr_name) + 3)
            fyi = (attr_name, spaces, pformat(attr))
            lines += (".%s:%s%s" % fyi).split("\n")
        for attr, attr_name in callables:
            spaces = " " * (max_len - len(attr_name))
            if attr.__doc__ is not None:
                docstring = attr.__doc__.split("\n")
                docstring.reverse()
                first_line = docstring.pop().lstrip()
                while first_line == "" and docstring:
                    first_line = docstring.pop().lstrip()
                info = "# " + first_line
            else:
                try:
                    info = get_instancemethod_source(attr)
                except AttributeError:
                    info = pformat(attr)
            lines.append(".%s(): %s%s" % (attr_name, spaces, info))
        if etree is not None and my_type == '_Element':
            spaces = " " * (max_len - len('etree.tostring()') + 2)
            fyi = ('etree.tostring()', spaces, etree.tostring(value))
            lines += ("%s:%s%s" % fyi).split("\n")
    if len(lines) == 0:
        try:
            lines += pformat(value.__dict__).split("\n")
        except AttributeError:
            lines += pformat(value).split("\n")
    if any([isinstance(value, t) for t in [list, tuple, dict, basestring]]):
        my_type += "[%s]" % len(value)

    ad_for_self = " %s :: %s @ %s:%s " % (exp, my_type, filename, tb[-2][1])
    delim_bar_len = min(max(len(lines[0]) + 3, len(ad_for_self) + 10), 150)
    delim_bar_chunk = "=" * ((delim_bar_len - len(ad_for_self) - 2))
    delim_bar = "==" + ad_for_self + delim_bar_chunk
    if delim_bar_len >= 150:
        delim_bar += " ... "

    var_dump = "\n/" + delim_bar + "\\\n"
    for line in lines:
        sub_lines = ["| " + subline for subline in line.split("\n")]
        var_dump += "\n".join(sub_lines) + "\n"
    var_dump += "\\" + delim_bar + "/\n"
    return var_dump


def decide_value(args):
    if len(args) == 0:
        return None
    elif len(args) > 1:
        return args
    else:
        return args[0]

def log(*args):
    tb = traceback.extract_stack()
    devlog(get_pretty_debug_output(tb, decide_value(args)))


def dump(*args):
    tb = traceback.extract_stack()
    print get_pretty_debug_output(tb, decide_value(args))


def die(*args, **kwargs):
    exit_code = 1
    if 'exit_code' in kwargs:
        exit_code = kwargs['exit_code']
    tb = traceback.extract_stack()
    devlog(get_pretty_debug_output(tb, decide_value(args)))
    exit(exit_code)


def format(*args):
    tb = traceback.extract_stack()
    return get_pretty_debug_output(tb, decide_value(args))


def trace():
    tb = traceback.extract_stack()
    devlog(get_pretty_debug_output(tb, tb[:-1]))


# def under_investigation(f, *a, **k):
#     if prod:
#         return f(*a, **k)

#     e = None
#     r = None
#     try:
#         r = f(*a, **k)
#     except Exception as e:
#         pass

#     tb = traceback.extract_stack()
#     flat_tb = ["%s in %s() @ %s:%s" % (
#                                 frame[3],
#                                 frame[2],
#                                 frame[0],
#                                 frame[1],
#                                )
#                 for frame in tb[:-2]]
#     value = {'args': a,
#            'kwargs': k,
#            'stack': flat_tb,
#            }
#     if e is not None:
#         value['raised'] = e
#     else:
#         value['returned'] = r
#     info = get_pretty_debug_output(tb[:-1],
#         value=value,
#         my_name=f.func_name,
#         my_type="*call to under_investigation function*")
#     devlog(info)

#     if e is not None:
#         raise e
#     return r

class SometimesIThinkImStillInJavascript(object):
    def log(self, *a, **k):
        return log(*a, **k)

console = SometimesIThinkImStillInJavascript()

def setup_builtins():
    __builtin__.console = console
    __builtin__.log = log
    __builtin__.die = die
    __builtin__.format = format
    __builtin__.trace = trace
    __builtin__.dump = dump
    # __builtin__.under_investigation = under_investigation

if not prod:
    setup_builtins()
