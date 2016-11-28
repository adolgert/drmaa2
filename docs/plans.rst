=====
Plans
=====

Problems Ahead
--------------

1. Does UGE clean up all of the old job sessions, now that they are named?

2. Will there be threading problems?

3. How do callbacks from DRMAA2 work?

4. Design of the futures interface.

5. Memory consumption is the hardest part about this library and the most
   likely to cause failure.

6. How do we support not only UGE but also other backends?

Design
------

There is a "language binding and reference implementation"
called `drmaa2-python <https://github.com/troeger/drmaa2-python>`_.
I heard from the Univa folks that they hope this library will use
that Python module as the interface. That might make sense if there
were to be one interface with multiple implementations, but I'd like
to get the implementation done here, so I don't understand why there
would be multiple implementations with the same interface.
In addition, Python works by duck typing. It uses abstract metaclasses,
such as are in drmaa2-python, only for a precious few types
defined by the core library. I get the feeling someone was thinking
that Python metaclasses are equivalent to Java interfaces.
Lastly, it's apparent that drmaa2-python doesn't address the two
main design problems, how to handle memory allocation and how
to load multiple DRMAA2 backends at the same time. In short,
I'm not finding drmaa2-python helpful.

Looking at the images for how sessions work, the only link among sessions
is using string IDs, so we can consider them separately. Multiple
sessions can be concurrent, though, even multiple Job Sessions.
For each session, there are a few kinds of objects.

 - The session itself
 - The main unit of interest (Job, JobArray, Reservation)
 - Templates for creating the main unit.
 - Info-objects about the main unit.
 - Lists of things.

The lists of things are almost exclusively for output, meaning
they are created by DRMAA, and you are responsible for freeing
them. You can't create a MachineInfo struct using methods
from DRMAA. The List<Job> is an exception to this rule. You
can query the Job Session or Monitor Session for lists of
Jobs and then act on them individually, for instance
to release a hold, or act on them as a group by
waiting until any are started or until any are terminated.

Thoughts on memory.

- Can use weakref.finalize to ensure things are called during deletion.
- There are callbacks for creation of strings and other to do freeing of members.
- In hold.c, when you free the job template, it auto-frees the list in the template.

A bit on loading multiple libraries. The idea is that a single
computer has both UGE and SGE installed, each running different
clusters. Therefore the Python library should load both
versions of libdrmaa2.so, each with its own customized Python
wrapper.

One way to do this is to make a class that returns the main
objects. Then each object retains a pointer to the loaded library
and appropriate implementation specifics::

   class _DRMS(object):
       def __init__(self, lib):
           self._lib = lib

       def JobSession(self, name=None, contact=None, keep=False):
           return JobSession(name, contact, keep, lib=self._lib)

Another approach might be to create a module on the fly.::

   code = """
   DRMAA_IMP = load("uge/libdrmaa2.so")
   class JobSession: pass
   """
   def get_drms():
       mod = imp.new_module("uge")
       exec(code, mod.__dict__)
       sys.modules["uge"] = mod
       return mod

My problem with any of these now is that I only have one implementation
to work with, UGE, so that I'm not sure exactly how different
versions might vary in their implementation. Maybe best
to leave it for now.

Which objects have only a free, and which have a create? (j is job,
r is reservation.) The plus sign marks the four UGE-specific
structures.

 * string free, but it's a char*, returned, arg, in lots of structs
 * list create, free

   * string_list returned, arg, in structs
   * j_list returned, arg, in jarray
   * r_list returned
   * queueinfo_list returned
   * machineinfo_list returned
   * slotinfo list in rinfo struct

 * dict create, free, in structs
 * jinfo create, free, arg
 * slotinfo free
 * rinfo free, returned
 * jtemplate create, free, returned, arg
 * rtemplate create, free, returned, arg
 * notification free
 * queueinfo free
 * version free
 * machineinfo free
 * jsession+ create, open, close, free, destroy, returned, arg
 * rsession create, open, close, free, destroy, returned, arg
 * msession+ open, close, free, returned, arg
 * j+ free, returned, arg
 * jarray+ free, returned, arg
 * r free, returned, arg
