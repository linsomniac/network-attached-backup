#!/usr/bin/env python
#
#  Copyright (c) 2011-2012, Sean Reifschneider, tummy.com, ltd.
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
import subprocess


class TestHardlinkStorage(unittest.TestCase):

    def test_Basic(self):
        '''Basic test of hardlink storage back-end.'''

        from nabstorageplugins import hardlinks

        testdirname = '/tmp/nabhardlinkstoragetest'
        subprocess.call(['rm', '-rf', testdirname])
        os.mkdir(testdirname)

        storage = hardlinks.Storage([testdirname, None,
            None, None, None])
        self.assertEqual(storage.get_backup_top_directory('example.com'),
                os.path.join(testdirname, 'example.com'))
        storage.create_host('example.com')

        self.assertEqual(storage.rsync_inplace_compatible(), False)

        stat = os.stat(os.path.join(testdirname, 'example.com'))
        self.assertEqual(stat.st_mode & 0777, 0700)
        self.assertEqual(os.path.exists(os.path.join(testdirname,
                'example.com', 'logs')), True)
        self.assertEqual(os.path.exists(os.path.join(testdirname,
                'example.com', 'keys')), True)
        self.assertEqual(os.path.exists(os.path.join(testdirname,
                'example.com', 'data')), True)
        self.assertEqual(os.path.exists(os.path.join(testdirname,
                'example.com', 'snapshots')), True)

        datafile = os.path.join(testdirname, 'example.com', 'data', 'testfile')
        with open(datafile, 'w') as fp:
            fp.write('This is a test\n')
        storage.create_snapshot('example.com', 'snap1')
        storage.mount_snapshot('example.com', 'snap1')
        with open(os.path.join(testdirname, 'example.com', 'snapshots',
                'snap1', 'data', 'testfile'), 'r') as fp:
            self.assertEqual(fp.readline(), 'This is a test\n')
        storage.unmount_snapshot('example.com', 'snap1')

        with open(datafile, 'w') as fp:
            fp.write('This is another test\n')
        storage.create_snapshot('example.com', 'snap2')
        with open(os.path.join(testdirname, 'example.com', 'snapshots',
                'snap2', 'data', 'testfile'), 'r') as fp:
            self.assertEqual(fp.readline(), 'This is another test\n')

        storage.destroy_snapshot('example.com', 'snap1')
        self.assertEqual(os.path.exists(os.path.join(testdirname,
                'example.com', 'snapshots', 'snap1')), False)

        self.assertEqual(storage.storage_usage() >= 0, True)
        self.assertEqual(storage.storage_usage() <= 100, True)

        storage.destroy_host('example.com')
        self.assertEqual(os.path.exists(os.path.join(testdirname,
                'example.com')), False)


print unittest.main()
