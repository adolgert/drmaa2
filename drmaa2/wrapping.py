"""
This module makes decisions about how to wrap the interface
objects from ctypes.
"""
import atexit
from ctypes import byref
from collections.abc import Sequence
import datetime
import logging
from .interface import *
from .errors import *


LOGGER = logging.getLogger("drmaa2.wrapping")


def print_string_list(wrapped_list):
    string_cnt = DRMAA_LIB.drmaa2_list_size(wrapped_list)
    assert last_errno() is Error.success
    ptrs = list()
    vals = list()
    for string_idx in range(string_cnt):
        void_p = DRMAA_LIB.drmaa2_list_get(wrapped_list, string_idx)
        ptrs.append(void_p)
        assert last_errno() is Error.success
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
            # Quoting the man pages: When the list is freed with list_free
            # and a callback function was given then for each element
            # in the list this function is called. When lists are
            # returned as copies by DRMAA2 functions then appropriate
            # destroy functions are set.
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

    def remove_ptr(self, ptr):
        """
        A contains() method would search all entries. This asks
        whether the pointer underlying any entry matches the ptr
        value passed in.

        :param ptr: A pointer to the native type, as a POINTER(type).
        :returns bool: Whether it removed the pointer.
        """
        # Cast takes POINTER(Structure) to a c_void_p. Then .value gives int.
        void_ptr = cast(ptr, c_void_p).value
        entry_cnt = self.__len__()
        for entry_idx in range(entry_cnt):
            # This returns an integer b/c it's a c_void_p return value.
            entry_ptr = DRMAA_LIB.drmaa2_list_get(self.list_ptr, entry_idx)
            LOGGER.debug("remove_ptr {} {}".format(
                type(entry_ptr), type(void_ptr)))
            if entry_ptr == void_ptr:
                CheckError(DRMAA_LIB.drmaa2_list_del(self.list_ptr, entry_idx))
                return True
        return False

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
            assert last_errno() is Error.success
            name = cast(void_p, drmaa2_string).value.decode()
            LOGGER.debug("{} at index {}".format(name, string_idx))
            python_list.append(name)

    return python_list


def convert_and_free_string_list(string_list):
    python_list = convert_string_list(string_list)
    if string_list:
        DRMAA_LIB.drmaa2_list_free(byref(c_void_p(string_list)))  # void
    return python_list


def Extensible(impl_spec):
    """
    Some of the classes exposed by DRMAA2 have optional,
    implementation-specific parameters, all of which have
    string values. This class decorator adds those values
    as string properties to the class.

    :param impl_spec: DRMAA_LIB.drmaa2_jtemplate_impl_spec, or equivalent.
                      There are a functions specific to each class.
    :return:
    """
    def Extended(cls):
        native_specific_list = impl_spec()
        errno = last_errno()
        if native_specific_list and errno == Error.success:
            if errno != Error.success:
                warnings.warn("error is {}".format(errno))
            attributes = convert_and_free_string_list(native_specific_list)
            for attr in attributes:
                setattr(cls, attr, ExtensibleString(attr))
        elif errno == Error.unsupported_operation:
            pass  # This is OK if there is no implementation for this class.
        else:
            raise DRMAA2Exception(last_error())
        return cls
    return Extended


def Wraps(structure_type):
    """
    This class decorator makes sure that attributes know what their
    name is when they call DRMAA2. It also checks that all of the
    properties of a class are wrapped.
    """
    assert issubclass(structure_type, ctypes.Structure)
    def Wrapped(cls):
        for name, field_type in structure_type._fields_:
            if name in cls.__dict__:
                attr = cls.__dict__[name]
                if isinstance(attr, WrappedProperty):
                    attr.name = name
            elif name == "implementationSpecific":
                if __name__ == '__main__':
                    pass  # That's OK
            else:
                warnings.warn("Attribute {} not wrapped".format(name))
        return cls
    return Wrapped


class WrappedProperty(object):
    pass


# This next series of classes are properties to deal with
# modifying values written to and read from classes that
# wrap DRMAA2 objects from C.
class DRMAA2Bool(WrappedProperty):
    def __init__(self, name=None):
        self.name = name

    def __get__(self, obj, type=None):
        if not obj:
            return False
        wrapped_value = getattr(obj._wrapped.contents, self.name)
        return Bool(wrapped_value)==Bool.true

    def __set__(self, obj, value):
        setattr(obj._wrapped.contents, self.name, 1 if value else 0)


class DRMAA2String(WrappedProperty):
    """A descriptor for wrapped strings on structs.
    There is no drmaa2_string_create, so we use ctypes' own allocation
    and freeing, which happens by default."""
    def __init__(self, name=None):
        self.name = name
        self.was_set = False

    def __get__(self, obj, type=None):
        if not obj:  # Case of building docs.
            return None
        base = obj._wrapped.contents
        wrapped_value = getattr(base, self.name).value
        if wrapped_value is None:  # Exclude case where it is "".
            return wrapped_value
        else:
            return wrapped_value.decode()

    def __set__(self, obj, value):
        base = obj._wrapped.contents
        wrapped_value = getattr(base, self.name)
        if wrapped_value.value and not self.was_set:
            DRMAA_LIB.drmaa2_string_free(byref(wrapped_value))
        else:
            pass  # No need to free it if it's null.
        if value is not None:
            setattr(base, self.name,
                    drmaa2_string(str(value).encode()))
            self.was_set = True
        else:
            setattr(base, self.name, UNSET_STRING)

    def free(self):
        pass


class DRMAA2StringList(WrappedProperty):
    def __init__(self, list_type, name=None):
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


class DRMAA2Dict(WrappedProperty):
    def __init__(self, name=None):
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


class DRMAA2LongLong(WrappedProperty):
    def __init__(self, name=None):
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


class DRMAA2Enum(WrappedProperty):
    def __init__(self, enum_cls, name=None):
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


class DRMAA2Time(WrappedProperty):
    def __init__(self, name=None):
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


class ExtensibleString(WrappedProperty):
    """A descriptor for wrapped strings on structs.
    There is no drmaa2_string_create, so we use ctypes' own allocation
    and freeing, which happens by default."""
    def __init__(self, name=None):
        self.name = name
        self.was_set = False
        # Cannot get documentation here because the DRMAA2 describe
        # function can only get documentation from an instance of
        # the object, and that doesn't exist yet.

    def __get__(self, obj, type=None):
        if not obj:  # Case of building docs.
            return None
        d_string = DRMAA_LIB.drmaa2_get_instance_value(
            cast(obj._wrapped, c_void_p), self.name.encode()
        )
        # This can sometimes cast a spurious error that the value isn't
        # specified, even though the value is just currently unset.
        if last_errno() == Error.success:
            return return_str(d_string)
        else:
            raise DRMAA2Exception(last_error())

    def __set__(self, obj, value):
        if value is None:
            value = "".encode()
        else:
            value = value.encode()
        DRMAA_LIB.drmaa2_set_instance_value(
                cast(obj._wrapped, c_void_p),
                self.name.encode(), value)
        check_errno()


class Notification:
    """Represents a notification, which is passed back to a callback.
    This wrapps a DRMAA2Notification."""
    def __init__(self, notification_struct):
        self._wrapped = notification_struct

    event = DRMAA2Enum("event", Event)
    jobId = DRMAA2String("jobId")
    sessionName = DRMAA2String("sessionName")
    jobState = DRMAA2Enum("jobState", JState)


def drms_name():
    if DRMAA_LIB:
        return return_str(DRMAA_LIB.drmaa2_get_drms_name())
    else:
        return None


def drms_version():
    if not DRMAA_LIB:
        return None
    LOGGER.debug("enter drms_version")
    version_ptr = DRMAA_LIB.drmaa2_get_drms_version()
    version = version_ptr.contents
    value = (version.major.value.decode(), version.minor.value.decode())
    DRMAA_LIB.drmaa2_version_free(ctypes.byref(version_ptr))
    LOGGER.debug("leave drms_version")
    return value


def event_callback(cb):
    """You don't want to have to write a callback function that
    decodes the C structs, so this decodes the values and sends
    them gently to the actual callback."""
    def wrapper(notification_ptr):
        notification = Notification(notification_ptr.contents)
        cb(notification.event, notification.jobId, notification.sessionName,
           notification.jobState)
        DRMAA_LIB.drmaa2_notification_free(notification_ptr)
    return wrapper


def register_event_notification(callback):
    """Register to receive notifications of events for new states,
    migration, or change of attributes.
    Unsupported in Univa Grid Engine"""
    callback_ptr = DRMAA2_CALLBACK(event_callback(callback))
    LOGGER.debug("callback is {}".format(callback_ptr))
    CheckError(DRMAA_LIB.drmaa2_register_event_notification(callback_ptr))
    atexit.register(unset_event_notification)


def unset_event_notification():
    LOGGER.debug("unset event notification")
    CheckError(DRMAA_LIB.drmaa2_register_event_notification(DRMAA2_CALLBACK()))
