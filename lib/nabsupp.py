#!/usr/bin/env python
#
#  Copyright (c) 2012, Sean Reifschneider, tummy.com, ltd.
#  All Rights Reserved.

'''Library functions for Network Attached Backup'''

from nabdb import *
import os
import sys


def clear_stale_backup_pids(db, host=None):
    '''Clear stale "backup_pid" on backups.
    Look at backups which have a "backup_pid" set, and if that PID is no
    longer running, clear that backup record.

    :param Host host: (Default None)  If specified, only that host is
            checked for stale backups.  Otherwise, all hosts are checked.

    :rtype: None
    '''
    if host:
        hostlist = [host]
    else:
        hostlist = db.query(Host)

    for host in hostlist:
        for backup in host.backups_with_pids():
            try:
                os.kill(backup.backup_pid, 0)
            except OSError, e:
                if e.errno == 3:
                    backup.backup_pid = None
                    db.flush()
                    db.commit()


def setup_syslog():
    '''Configure syslog, should be called before using syslog.

    :rtype: None
    '''
    import syslog
    syslog.openlog(os.path.basename(sys.argv[0]), syslog.LOG_PID,
            syslog.LOG_DAEMON)


def log_exceptions(syslog=True, stderr=True, filename=None):
    '''Trap exceptions and log them to or other destinations.

    :param boolean syslog: (default: True) Send the messages to syslog.

    :param boolean stderr: (default: True) Send the messages to stderr.

    :param string filename: (default: None) If not None, send the log
    messages to a file.

    :rtype: None
    '''
    class ExceptHook:
        def __init__(self, useSyslog=True, useStderr=False, filename=None):
            self.useSyslog = useSyslog
            self.useStderr = useStderr
            self.filename = filename

        def __call__(self, etype, evalue, etb):
            import traceback
            import syslog

            fp = None
            if self.filename:
                fp = open(self.filename, 'a')

            tb = traceback.format_exception(*(etype, evalue, etb))
            for line in '\n'.join([x.rstrip() for x in tb]).split('\n'):
                if self.useSyslog:
                    syslog.syslog(syslog.LOG_ERR, line)
                if self.useStderr:
                    sys.stderr.write(line + '\n')
                if fp:
                    fp.write(line + '\n')

            if fp:
                fp.close()

    sys.excepthook = ExceptHook(useSyslog=syslog, useStderr=stderr,
            filename=filename)
