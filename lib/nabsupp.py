#!/usr/bin/env python
#
#  Copyright (c) 2012, Sean Reifschneider, tummy.com, ltd.
#  All Rights Reserved.

'''Library functions for Network Attached Backup'''

from nabdb import *


#@@@TEST
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
            except OSError:
                backup.backup_pid = None
                db.save(backup)
                db.commit()


#@@@TEST
def are_backups_currently_running(db, host):
    '''Are there any backups currently running for this host?

    :rtype: Boolean indicating whether there are any backups running
    '''
    clear_stale_backup_pids(db, host)
    return len(host.backups_with_pids()) > 0


#@@@TEST
def find_backup_generation(db, host):
    raise NotImplementedError('See harnessenv:findBackupGeneration')
