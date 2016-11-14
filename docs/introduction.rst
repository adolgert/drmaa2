============
Introduction
============

DRMAA2 is version 2 of the Distributed Resource Management
Application API. It is an API for controlling unix processes
on a cluster or for controlling meta-clusters of unix processes.
The detailed API description is a document called
`GFD.194.pdf <https://www.ogf.org/ogf/doku.php/documents/documents>`_
from the `Open Grid Forum <http://ogf.org>`_.
Looking at the
`Go implementation <https://github.com/dgruber/drmaa2/blob/master/drmaa2.go>_`
can help, too.
You also might need to look at
`Daniel Gruber's blog <http://www.gridengine.eu/index.php/programming-apis/178-the-drmaa2-tutorial-introduction-1-2013-10-05>`_.
The third place for help is to use the Manual command::

   man -M $SGE_ROOT/man drmaa2_open_jsession

That will get you documentation on most commands.

.. image:: DRMAA2Job.*
   :alt: Three entry points are JobSession, JobInfo, and JobTemplate. They create Jobs or JobArrays. They interact with reservations only through the reservation ID.

The objects in red are entry points, meaning you can create one
from scratch, and then from these make the blue ones.

.. image:: DRMAA2Monitor.*
   :alt: A monitoring session lets you see QueueInfo, MachineInfo, and
         lists of jobs.

Monitoring is all about getting lists of things.

.. image:: DRMAA2Reservation.*
   :alt: Entry points are reservationtemplate and ReservationSession.
         From these you get the Reservation and ReservationInfo.

Reservations also require a session. Entry points are in red.
