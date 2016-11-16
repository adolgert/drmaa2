"""
This module makes decisions about how to wrap the interface
objects from ctypes.
"""
from ctypes import byref
from collections.abc import Sequence
import datetime
import logging
from .interface import *
from .errors import *


LOGGER = logging.getLogger("drmaa2.wrapping")


def print_string_list(wrapped_list):
    string_cnt = DRMAA_LIB.drmaa2_list_size(wrapped_list)
    assert last_errno() < 1
    ptrs = list()
    vals = list()
    for string_idx in range(string_cnt):
        void_p = DRMAA_LIB.drmaa2_list_get(wrapped_list, string_idx)
        ptrs.append(void_p)
        assert last_errno() < 1
        name = cast(void_p, drmaa2_string).value.decode()
        vals.append(name)
    print(", ".join(vals))
    print(", ".join([str(x) for x in ptrs]))


# Conversion strategies represent our rules for how to translate
# pointers into Python objects when we work with lists of things
# that are returned from DRMAA2 or sent to DRMAA2
STRATEGIES = dict()


def conversion_strategy(list_type):
    """This class decorator marks that class as being a
    strategy for converting items of a type to and from
    list entries. Use it as::

       @conversion_strategy(ListType.joblist)
       class JobStrategy(object):
           ...

    :param list_type: This is from the ListType enum.
    """
    def conversion(cls):
        global STRATEGIES
        STRATEGIES[list_type] = cls
        return cls
    return conversion


@conversion_strategy(ListType.stringlist)
class StringStrategy:
    @staticmethod
    def from_void(void_ptr):
        """Makes a Python object which is a copy of the value."""
        return cast(void_ptr, drmaa2_string).value.decode()

    @staticmethod
    def to_void(name_str):
        """Sets up the Python object so that ctypes can convert it
        to be passed to the library. You have to keep a copy of this
        object around, meaning keep a reference to it within Python
        for the duration of its use in the library."""
        return name_str.encode()

    @staticmethod
    def compare_pointers(a, b):
        return StringStrategy.from_void(a) == StringStrategy.from_void(b)


class DRMAA2List(Sequence):
    """A DRMAAList owns a DRMAA list of things. This is the Python wrapper.
    The design choice is to keep the wrapped items as a native pointer
    and return individual items when requested. It also lets
    you set all of the items at instantiation but not modify that
    list of items. It's read-only. This will suffice for passing
    around a list efficiently without copies, but it also lets
    you make a copy with list(DRMAA2List instance) if that's what
    you need."""
    def __init__(self, python_entries, list_type=ListType.stringlist):
        """If a pointer is passed to this class, then this class
        is responsible for freeing that list pointer. If none is passed,
        then this class creates a list pointer."""
        self.list_type = self.hint_type(list_type)
        self.strategy = STRATEGIES[self.list_type]
        self.list_ptr = DRMAA_LIB.drmaa2_list_create(
            self.list_type.value, DRMAA2_LIST_ENTRYFREE())
        self._pin = [self.strategy.to_void(x) for x in python_entries]
        for add_item in self._pin:
            CheckError(DRMAA_LIB.drmaa2_list_add(self.list_ptr, add_item))

    @staticmethod
    def hint_type(list_type):
        if isinstance(list_type, ListType):
            return list_type
        elif isinstance(list_type, str):
            return ListType[list_type]
        else:
            return ListType(list_type)

    @classmethod
    def from_existing(cls, list_ptr, list_type):
        obj = cls.__new__(cls)
        obj.list_ptr = list_ptr
        obj.list_type = obj.hint_type(list_type)
        obj.strategy = STRATEGIES[obj.list_type]
        return obj

    def __getitem__(self, item):
        if item >= self.__len__():
            raise IndexError()
        void_p = DRMAA_LIB.drmaa2_list_get(self.list_ptr, item)
        return self.strategy.from_void(void_p)

    def __len__(self):
        return DRMAA_LIB.drmaa2_list_size(self.list_ptr)

    def __del__(self):
        """This isn't called when you call del but when garbage collection
        happens."""
        if self.list_ptr:
            DRMAA_LIB.drmaa2_list_free(byref(c_void_p(self.list_ptr)))
            self.list_ptr = None

    def __eq__(self, other):
        """Compares two DRMAA2Lists"""
        self_cnt = self.__len__()
        other_cnt = other.__len__()
        if self_cnt != other_cnt:
            return False
        for cmp_idx in range(self_cnt):
            self_p = DRMAA_LIB.drmaa2_list_get(self.list_ptr, cmp_idx)
            other_p = DRMAA_LIB.drmaa2_list_get(other.list_ptr, cmp_idx)
            if not self.strategy.compare_pointers(self_p, other_p):
                return False
        return True

    @staticmethod
    def return_list(string_ptr, list_type):
        l_ptr = DRMAA2List.from_existing(string_ptr, list_type)
        l_py = list(l_ptr)
        l_ptr.__del__()
        return l_py


def convert_string_list(string_list):
    python_list = list()
    if string_list:
        string_cnt = DRMAA_LIB.drmaa2_list_size(string_list)
        check_errno()
        for string_idx in range(string_cnt):
            void_p = DRMAA_LIB.drmaa2_list_get(string_list, string_idx)
            assert last_errno() < 1
            name = cast(void_p, drmaa2_string).value.decode()
            LOGGER.debug("{} at index {}".format(name, string_idx))
            python_list.append(name)

    return python_list


def convert_and_free_string_list(string_list):
    python_list = convert_string_list(string_list)
    if string_list:
        DRMAA_LIB.drmaa2_list_free(byref(c_void_p(string_list)))  # void
    return python_list



# This next series of classes are properties to deal with
# modifying values written to and read from classes that
# wrap DRMAA2 objects from C.
class DRMAA2Bool:
    def __init__(self, name):
        self.name = name

    def __get__(self, obj, type=None):
        if not obj:
            return False
        wrapped_value = getattr(obj._wrapped.contents, self.name)
        return Bool(wrapped_value)==Bool.true

    def __set__(self, obj, value):
        setattr(obj._wrapped.contents, self.name, 1 if value else 0)


class DRMAA2String:
    """A descriptor for wrapped strings on structs.
    There is no drmaa2_string_create, so we use ctypes' own allocation
    and freeing, which happens by default."""
    def __init__(self, name):
        self.name = name.split(".")
        self.was_set = False

    def __get__(self, obj, type=None):
        if not obj:  # Case of building docs.
            return None
        if len(self.name) > 1:
            base = getattr(obj._wrapped.contents, self.name[0])
        else:
            base = obj._wrapped.contents
        wrapped_value = getattr(base, self.name[-1]).value
        if wrapped_value is None:  # Exclude case where it is "".
            return wrapped_value
        else:
            return wrapped_value.decode()

    def __set__(self, obj, value):
        if len(self.name) > 1:
            base = getattr(obj._wrapped.contents, self.name[0])
        else:
            base = obj._wrapped.contents
        wrapped_value = getattr(base, self.name[-1])
        if wrapped_value.value and not self.was_set:
            DRMAA_LIB.drmaa2_string_free(byref(wrapped_value))
        else:
            pass  # No need to free it if it's null.
        if value is not None:
            setattr(base, self.name[-1],
                    drmaa2_string(str(value).encode()))
            self.was_set = True
        else:
            setattr(base, self.name[-1], UNSET_STRING)

    def free(self):
        pass


class DRMAA2StringList:
    def __init__(self, name, list_type):
        """Name is the name of the member of the instance.
        list_type is the ListType enum for this list.
        If there isn't a list, we make one, so we free it, too."""
        assert isinstance(list_type, ListType)
        self.name = name
        self.list_type = list_type
        self.allocated = None

    def __get__(self, obj, type=None):
        if not obj:
            return []
        wrapped_list = getattr(obj._wrapped.contents, self.name)
        if wrapped_list:
            string_list = list()
            string_cnt = DRMAA_LIB.drmaa2_list_size(wrapped_list)
            for string_idx in range(string_cnt):
                void_p = DRMAA_LIB.drmaa2_list_get(wrapped_list, string_idx)
                if void_p:
                    name = cast(void_p, drmaa2_string).value.decode()
                    LOGGER.debug("{} at index {}".format(name, string_idx))
                    string_list.append(name)
                else:
                    check_errno()
                    string_list.append(None)
            return string_list
        else:
            return []

    def __set__(self, obj, value):
        wrapped = getattr(obj._wrapped.contents, self.name)
        if wrapped:
            name_cnt = DRMAA_LIB.drmaa2_list_size(wrapped)
            LOGGER.debug("Emptying string {} len {}".format(
                self.name, name_cnt))
            while name_cnt > 0:
                LOGGER.debug("Deleting from list")
                CheckError(DRMAA_LIB.drmaa2_list_del(wrapped, 0))
                name_cnt = DRMAA_LIB.drmaa2_list_size(wrapped)
        else:
            LOGGER.debug("Creating string {}".format(self.name))
            wrapped = DRMAA_LIB.drmaa2_list_create(
                self.list_type.value, DRMAA2_LIST_ENTRYFREE())
            self.allocated = wrapped
            setattr(obj._wrapped.contents, self.name, wrapped)

        if value:
            # In order to manage memory, attach the list to this object.
            self.value = [x.encode() for x in value]
            LOGGER.debug("Adding string {} values {}".format(self.name, value))
            string_obj = drmaa2_string()
            for idx in range(len(value)):
                LOGGER.debug("value going in {} at {} for {}".format(
                    string_obj.value, string_obj, self.name))
                CheckError(DRMAA_LIB.drmaa2_list_add(
                    wrapped, self.value[idx]))


    def free(self):
        if self.allocated:
            DRMAA_LIB.drmaa2_list_free(byref(self.allocated))


class DRMAA2Dict:
    def __init__(self, name):
        self.name = name

    def __get__(self, obj, type=None):
        # Allow for obj=None in case of building docs.
        wrapped = getattr(obj._wrapped.contents, self.name) if obj else None
        if wrapped:
            key_list = DRMAA_LIB.drmaa2_dict_list(wrapped)
            if key_list:
                result = dict()
                key_cnt = DRMAA_LIB.drmaa2_list_size(key_list)
                for key_idx in range(key_cnt):
                    void_ptr = DRMAA_LIB.drmaa2_list_get(key_list, key_idx)
                    key_ptr = cast(void_ptr, drmaa2_string).value
                    value_ptr = DRMAA_LIB.drmaa2_dict_get(wrapped, key_ptr)
                    LOGGER.debug("{} {}".format(
                        key_ptr.decode(), value_ptr.decode()))
                    result[key_ptr.decode()] = value_ptr.decode()
                return result
            else:
                return dict()
        else:
            return dict()

    def __set__(self, obj, value):
        wrapped = getattr(obj._wrapped.contents, self.name)
        if not wrapped:
            wrapped = DRMAA_LIB.drmaa2_dict_create(DRMAA2_DICT_ENTRYFREE())
            setattr(obj._wrapped.contents, self.name, wrapped)
        else:
            key_list = DRMAA_LIB.drmaa2_dict_list(wrapped)
            if key_list:
                key_cnt = DRMAA_LIB.drmaa2_list_size(key_list)
                for key_idx in range(key_cnt):
                    void_ptr = DRMAA_LIB.drmaa2_list_get(key_list, key_idx)
                    key_ptr = cast(void_ptr, drmaa2_string).value
                    CheckError(DRMAA_LIB.drmaa2_dict_del(wrapped, key_ptr))

        self.dict = {(k.encode(), v.encode()) for (k, v) in value.items()}
        for key, value in self.dict:
            CheckError(DRMAA_LIB.drmaa2_dict_set(wrapped, key, value))


class DRMAA2LongLong:
    def __init__(self, name):
        self.name = name

    def __get__(self, obj, type=None):
        val = getattr(obj._wrapped.contents, self.name) if obj else UNSET_NUM
        if val == UNSET_NUM:
            return None
        else:
            return val

    def __set__(self, obj, value):
        if value is None:
            value = UNSET_NUM
        else:
            value = value
        setattr(obj._wrapped.contents, self.name, value)


class DRMAA2Enum:
    def __init__(self, name, enum_cls):
        self.name = name
        self.enum_cls = enum_cls

    def __get__(self, obj, type=None):
        if not obj:
            return None
        name = self.enum_cls(getattr(obj._wrapped.contents, self.name)).name
        if name == "unset":
            return None
        else:
            return name

    def __set__(self, obj, value):
        value = value or "unset"
        setattr(obj._wrapped.contents, self.name, self.enum_cls[value].value)


class DRMAA2Time:
    def __init__(self, name):
        self.name = name

    def __get__(self, obj, type=None):
        if not obj:
            return None
        when = getattr(obj._wrapped.contents, self.name)
        LOGGER.debug("time is {}".format(when))
        try:
            message = Times(when)
            if message == Times.unset:
                return None
            else:
                return message.name
        except ValueError:
            return datetime.datetime.fromtimestamp(when)

    def __set__(self, obj, value):
        LOGGER.debug("set time for {} to {}".format(self.name, value))
        if value is None:
            when = Times["unset"].value
        elif isinstance(value, str):
            when = Times[value].value
        else:
            when = int(value.timestamp())
        setattr(obj._wrapped.contents, self.name, when)

