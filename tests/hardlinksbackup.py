#!/usr/bin/env python
#
#  Copyright (c) 2012, Sean Reifschneider, tummy.com, ltd.
#  All Rights Reserved.

#  allow the test to be run from the "tests" or "tests" parent directory
import sys
import os
if os.path.basename(os.getcwd()) == 'tests':
    sys.path.append('../lib')
else:
    sys.path.append('./lib')

import unittest
import os
import time
from nabdb import *


class TestHardlinksStorage(unittest.TestCase):
    def create_database(self):
        nabdb.connect(connect='sqlite:///:memory:')
        nabdb.Base.metadata.create_all()

        db = nabdb.session()

        metadata = Metadata()
        db.add(metadata)
        db.commit()

        server = BackupServer()
        server.hostname = 'localhost'
        db.add(server)

        zfs_storage = Storage()
        zfs_storage.backup_server = server
        zfs_storage.method = 'hardlinks'
        zfs_storage.arg1 = '/tmp/nabhardlinksbackuptest/backups/'
        db.add(zfs_storage)

        client1 = Host()
        client1.backup_server = server
        client1.hostname = 'localhost'
        db.add(client1)

        config_default = HostConfig()
        config_default.failure_warn_after = datetime.timedelta(days=3)
        config_default.use_global_filters = True
        db.add(config_default)

        config_client1 = HostConfig()
        config_client1.host = client1
        config_client1.priority = 4
        db.add(config_client1)

        counter = 0
        for rule_data in [
                'include /tmp/',
                'include /tmp/nabhardlinksbackuptest/',
                'include /tmp/nabhardlinksbackuptest/root/',
                'include /tmp/nabhardlinksbackuptest/root/**',
                'exclude /**',
                ]:
            rule = FilterRule()
            rule.rsync_rule = rule_data
            rule.priority = '%09d' % counter
            counter += 1
            db.add(rule)

        db.commit()

        return db

    def test_Basic(self):
        '''Test the backup running harness code.'''

        os.system('rm -rf /tmp/nabhardlinksbackuptest/')
        os.mkdir('/tmp/nabhardlinksbackuptest/')
        os.mkdir('/tmp/nabhardlinksbackuptest/backups')
        os.mkdir('/tmp/nabhardlinksbackuptest/backups/localhost')
        os.mkdir('/tmp/nabhardlinksbackuptest/backups/localhost/data')
        os.mkdir('/tmp/nabhardlinksbackuptest/backups/localhost/snapshots')
        os.mkdir('/tmp/nabhardlinksbackuptest/root')
        with open('/tmp/nabhardlinksbackuptest/root/testfile', 'w') as fp:
            fp.write('This is a test')

        db = self.create_database()
        host = db.query(Host).filter_by(hostname='localhost').first()

        nabsupp.run_backup_for_host(db, 'localhost')
        first_snapshotname = host.backups[0].snapshot_name

        filename = '/tmp/nabhardlinksbackuptest/root/testfile'
        with open(filename, 'r') as fp:
            self.assertEqual(fp.readline(), 'This is a test')

        filename = ('/tmp/nabhardlinksbackuptest/backups/localhost/snapshots'
                '/%s/data/tmp/nabhardlinksbackuptest/root/testfile'
                % first_snapshotname)
        with open(filename, 'r') as fp:
            self.assertEqual(fp.readline(), 'This is a test')

        with open('/tmp/nabhardlinksbackuptest/root/testfile', 'w') as fp:
            fp.write('This is another test')

        nabsupp.run_backup_for_host(db, 'localhost')
        second_snapshotname = host.backups[-1].snapshot_name

        #  wait long enough that a new name snapshot will be made
        time.sleep(2)

        filename = '/tmp/nabhardlinksbackuptest/root/testfile'
        with open(filename, 'r') as fp:
            self.assertEqual(fp.readline(), 'This is another test')

        filename = ('/tmp/nabhardlinksbackuptest/backups/localhost/snapshots'
                '/%s/data/tmp/nabhardlinksbackuptest/root/testfile'
                % second_snapshotname)
        with open(filename, 'r') as fp:
            self.assertEqual(fp.readline(), 'This is another test')

        filename = ('/tmp/nabhardlinksbackuptest/backups/localhost/snapshots'
                '/%s/data/tmp/nabhardlinksbackuptest/root/testfile'
                % first_snapshotname)
        with open(filename, 'r') as fp:
            self.assertEqual(fp.readline(), 'This is a test')


print unittest.main()
