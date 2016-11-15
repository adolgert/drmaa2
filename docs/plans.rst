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

Design
------
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
