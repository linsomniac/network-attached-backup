#!/usr/bin/env python
#
#  Copyright (c) 2012, Sean Reifschneider, tummy.com, ltd.
#  All Rights Reserved.

import os
import subprocess
import re


class Storage:
    def __init__(self, args):
        '''Hardlinks storage back-end.

        :param list args: Arguments to the storage plugin, for hardlinks this
                is only a string specifying the top-level directory.
        '''
        self.top_directory = args[0]

    def rsync_inplace_compatible(self):
        '''Is this storage back-end compatible with "rsync --inplace"?

        :rtype: boolean
        '''
        return False

    def get_backup_top_directory(self, hostname):
        '''Return the top level directory that backups should be stored
        under.

        :param str hostname: Name of the host.

        :rtype: str -- The path to the top of the host's backup directory.
        '''
        return os.path.join(self.top_directory, hostname)

    def create_host(self, hostname):
        '''Create the host backup directory.

        :param str hostname: Name of the host.

        :rtype: None
        '''
        topdir = self.get_backup_top_directory(hostname)
        os.mkdir(topdir)
        os.chmod(topdir, 0700)
        os.mkdir(os.path.join(topdir, 'data'))
        os.mkdir(os.path.join(topdir, 'keys'))
        os.mkdir(os.path.join(topdir, 'logs'))
        os.mkdir(os.path.join(topdir, 'snapshots'))

    def destroy_host(self, hostname):
        '''Destroy the host backup directory.

        :param str hostname: Name of the host.

        :rtype: None
        '''
        topdir = self.get_backup_top_directory(hostname)
        if not os.path.exists(topdir):
            raise ValueError('Host directory does not exist')

        remove = topdir + '.nab-remove-in-progress'
        os.rename(topdir, remove)
        subprocess.call(['rm', '-rf', remove])

    def snapshot_name(self, host, backup):
        '''Return the name to use for the snapshot.

        :param Host host: Host of the backup.

        :param Backup backup: Backup being run.

        :rtype: str
        '''
        import datetime
        return datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S'
                ) + backup.generation

    def create_snapshot(self, hostname, snapshotname):
        '''Create a snapshot of the last backup.

        :param str hostname: Name of the host.

        :param str snapshotname: Name of the snapshot.

        :rtype: None
        '''
        topdir = self.get_backup_top_directory(hostname)
        snapshotdir = os.path.join(topdir, 'snapshots', snapshotname)

        if os.path.exists(snapshotdir):
            raise ValueError('Snapshot "%s" already exists for host "%s"' %
                    (snapshotname, hostname))

        os.mkdir(snapshotdir)
        subprocess.call(['cp', '-al', os.path.join(topdir, 'logs', '.'),
                os.path.join(snapshotdir, 'logs')])
        subprocess.call(['cp', '-al', os.path.join(topdir, 'data', '.'),
                os.path.join(snapshotdir, 'data')])

    def destroy_snapshot(self, hostname, snapshotname):
        '''Destroy a snapshot.

        :param str hostname: Name of the host.

        :param str snapshotname: Name of the snapshot.

        :rtype: None
        '''
        topdir = self.get_backup_top_directory(hostname)
        snapshotdir = os.path.join(topdir, 'snapshots', snapshotname)

        if not os.path.exists(snapshotdir):
            raise ValueError('Snapshot "%s" does not exist for host "%s"' %
                    (snapshotname, hostname))

        remove = snapshotdir + '.nab-remove-in-progress'
        os.rename(snapshotdir, remove)
        subprocess.call(['rm', '-rf', remove])

    def mount_snapshot(self, hostname, snapshotname):
        '''Mount a snapshot (noop on hardlinks backend)

        :param str hostname: Name of the host.

        :param str snapshotname: Name of the snapshot.

        :rtype: None
        '''
        return

    def unmount_snapshot(self, hostname, snapshotname):
        '''Unmount a snapshot (noop on hardlinks backend)

        :param str hostname: Name of the host.

        :param str snapshotname: Name of the snapshot.

        :rtype: None
        '''
        return

    def storage_usage(self):
        '''Get the percentage utilization of the storage.

        :rtype: int The percentage utilization of the storage.
        '''
        data = None
        for line in subprocess.check_output(
                ['df', self.top_directory]).split('\n'):
            match = re.search('(\d+)%', line)
            if match:
                data = int(match.group(1))

        return data

#  methods that are needed:
#    get host usage
