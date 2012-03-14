#!/usr/bin/env python
#
#  Copyright (c) 2012, Sean Reifschneider, tummy.com, ltd.
#  All Rights Reserved.

'''Library functions for Network Attached Backup'''

from nabdb import *
import os
import sys
import subprocess
import datetime


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


def run_backup_for_host(db, hostname):
    '''Code for performing the backup.  Returns True if the backup completed
    (successful or not).

    :param DatabaseHandle db: Handle to the database.

    :param str hostname: Name of the host to do the backup of.

    :rtype: Boolean
    '''
    from nabmodel import Host, Backup
    import tempfile

    host = db.query(Host).filter_by(hostname=hostname).first()
    extra_rsync_arguments = []
    if host.merged_configs(db).rsync_compression:
        extra_rsync_arguments.append('-z')

    if host.are_backups_currently_running(db):
        sys.stderr.write('ERROR: Backups are already running.  Aborting.\n')
        return False

    if not host.active:
        sys.stderr.write('This host is not enabled for backups '
                '(active=False)\n')
        return False

    backup = Backup(host, host.find_backup_generation(db),
            full_checksum=host.ready_for_checksum(db))
    backup.backup_pid = os.getpid()
    db.add(backup)
    db.commit()

    import nabstorageplugins
    storage_plugin = getattr(nabstorageplugins,
            host.backup_server.storage[0].method)
    storage = storage_plugin.Storage([
                host.backup_server.storage[0].arg1,
                host.backup_server.storage[0].arg2,
                host.backup_server.storage[0].arg3,
                host.backup_server.storage[0].arg4,
                host.backup_server.storage[0].arg5,
            ])
    if storage.rsync_inplace_compatible():
        extra_rsync_arguments.append('--inplace')
    backup.snapshot_name = storage.snapshot_name(host, backup)

    os.chdir(storage.get_backup_top_directory(host.hostname))
    subprocess.check_call(['rm', '-rf', 'logs'])
    os.mkdir('logs')

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    with open(os.path.join('logs', 'status.out'), 'w') as fp:
        sys.stdout = fp
        sys.stderr = fp

        os.chdir('data')

        if backup.full_checksum:
            print '*** DOING FULL CHECKSUM RUN ***'
            print
            extra_rsync_arguments.append('--ignore-times')
            backup.full_checksum = True

        rules_tmp = tempfile.mkstemp()
        with open(rules_tmp[1], 'w') as rules_fp:
            rules_fp.write(host.get_filter_rules(db))
        print repr(host.get_filter_rules(db))
        rules_fp = open(rules_tmp[1], 'r')
        os.unlink(rules_tmp[1])

        print 'Backing up host %s' % host.hostname
        start_time = datetime.datetime.now()
        backup.start_time = start_time
        print 'Starting rsync on %s' % (
                start_time.strftime('%a %b %d, %Y at %H:%M:%S'))

        backup.backup_pid = os.getpid()

        db.commit()

        #  do not run remote rsync if hostname is 'localhost'
        #  mostly used for tests
        remote_part = ['-e', 'ssh -i %s'
                % os.path.join('..', 'keys', 'backup-identity')]
        source = 'root@%s:/' % host.hostname
        if host.hostname == 'localhost':
            remote_part = []
            source = '/'

        with open(os.path.join('..', 'logs', 'rsync.out'), 'w') as rsync_fp:
            backup.harness_returncode = subprocess.call([
                    'rsync',
                    '-av',
                    ] + remote_part + [
                    '--delete', '--delete-excluded',
                    '--filter=merge -',
                    '--ignore-errors',
                    '--hard-links',
                    '--itemize-changes',
                    '--timeout=3600',
                    '--numeric-ids',
                    ] + extra_rsync_arguments + [
                    source,
                    '.'
                    ],
                    stdin=rules_fp,
                    stdout=rsync_fp, stderr=rsync_fp)
        end_time = datetime.datetime.now()
        rsync_fp.close()

        backup.successful = backup.harness_returncode in [0, 23, 24]
        backup.backup_pid = None
        db.commit()

        print 'RSYNC_RETURNCODE=%s' % backup.harness_returncode
        print 'Completed rsync on %s' % (
                end_time.strftime('%a %b %d, %Y at %H:%M:%S'))

        start_time = datetime.datetime.now()
        print
        print 'Starting snapshot on %s' % (
                start_time.strftime('%a %b %d, %Y at %H:%M:%S'))

        storage.create_snapshot(host.hostname, backup.snapshot_name)

        end_time = datetime.datetime.now()
        print 'Completed snapshot on %s' % (
                end_time.strftime('%a %b %d, %Y at %H:%M:%S'))

        backup.end_time = end_time
        db.commit()

    sys.stdout = old_stdout
    sys.stderr = old_stderr
    return True


def run_command(args):
    '''Call the command and get the stdout and stderr.
    This is like `subprocess.call()`, but it returns an object with the
    output of stdout, stderr, and the process return-code.

    .. py:attribute:: args

    Command suitable to pass to `subprocess.call()`, typically a list of
    the command and its arguments.

    :rtype: Object Includes attributes "stdout", "stderr", and "exitcode".
    '''
    class Return:
        def __init__(self, stdout, stderr, exitcode):
            self.stdout = stdout
            self.stderr = stderr
            self.exitcode = exitcode

    with os.tmpfile() as fpout:
        with os.tmpfile() as fperr:
            exitcode = subprocess.call(args, stdout=fpout, stderr=fperr)
            fpout.seek(0)
            stdout = fpout.read()
            fperr.seek(0)
            stderr = fperr.read()
    return Return(stdout, stderr, exitcode)
