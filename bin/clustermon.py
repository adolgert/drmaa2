"""
This is a quick little program to monitor job sessions.
"""
import cmd
import logging
import os
import sys
import drmaa2


LOGGER = logging.getLogger("clustermon")


class ClusterMonitor(cmd.Cmd):
    def __init__(self):
        super().__init__()

    def do_help(self, *args):
        """Show help."""
        if any(args):
            for arg in args:
                try:
                    msg = getattr(self, "do_{}".format(arg)).__doc__
                    print(msg)
                except AttributeError:
                    print("Can't find help for {}".format(arg))
        else:
            print(
"""sessions=print all sessions
destroy=get rid of sessions in the scheduler
help=this message
quit=exit this program""")

    def do_quit(self, *args):
        """Exit the program. Or use Control-d"""
        sys.exit()

    def do_EOF(self, *args):
        print()
        sys.exit()

    def do_sessions(self, *args):
        """Show all sessions."""
        names = drmaa2.JobSession.names()
        print("There are {} open sessions".format(len(names)))
        print(("  "+os.linesep).join(names))

    def do_destroy(self, *args):
        """
        Remove sessions from the scheduler's memory.
        :param session_names: Either a list of session names or "all"
                              to destroy all of them.
        """
        if ("all",) == args:
            names = drmaa2.JobSession.names()
        else:
            names = list(args)
        success = list()
        fail = list()
        for n in names:
            try:
                full_name = n.split("@")
                drmaa2.JobSession.destroy_named(full_name[-1])
                success.append(n)
            except Exception as exc:
                fail.append((n, exc))
        if success:
            print("Destroyed:")
            for s in success:
                print("  "+s)
        if fail:
            for name, why in fail:
                print("{}: {}".format(name, str(why)))

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    cm = ClusterMonitor()
    cm.cmdloop()
