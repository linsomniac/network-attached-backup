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
import datetime
from nabdb import *


class TestModel(unittest.TestCase):

    @classmethod
    def setUp(self):
        nabdb.connect(connect='sqlite:///:memory:')
        nabdb.Base.metadata.create_all()

    @classmethod
    def tearDown(self):
        nabdb.close()

    def test_Metadata(self):
        '''Verify that loading the metadata table twice fails.'''
        db = nabdb.session()

        metadata1 = Metadata()
        db.add(metadata1)
        db.commit()

        #  verify that we can't insert another configuration entry
        with self.assertRaises(Exception):
            metadata2 = Metadata()
            db.add(metadata2)
            db.commit()
        db.rollback()

        #  verify that only one record is there
        self.assertEqual(len(db.query(Metadata).all()), 1)

        config = Metadata.get(db)
        self.assertEqual(config.id, 1)
        self.assertEqual(config.id, 1)

    def test_Schema(self):
        '''Test the schema by loading data into it.'''
        db = nabdb.session()

        metadata = Metadata()
        db.add(metadata)
        db.commit()

        server = BackupServer()
        server.hostname = 'server.example.com'
        db.add(server)

        zfs_storage = Storage()
        zfs_storage.backup_server = server
        zfs_storage.method = 'zfs'
        zfs_storage.arg1 = 'backups'
        zfs_storage.arg2 = 'backups'
        zfs_storage.arg3 = '/backups'
        db.add(zfs_storage)

        client1 = Host()
        client1.backup_server = server
        client1.hostname = 'client1.example.com'
        client1.window_start = datetime.time(0, 0)
        client1.window_end = datetime.time(5, 0)
        db.add(client1)

        client2 = Host()
        client2.backup_server = server
        client2.hostname = 'client2.example.com'
        client2.window_start = datetime.time(0, 0)
        client2.window_end = datetime.time(5, 0)
        db.add(client1)

        config_default = HostConfig()
        config_default.alerts_mail_address = 'sysadmin@example.com'
        config_default.failure_warn_after = datetime.timedelta(days=3)
        config_default.use_global_filters = True
        db.add(config_default)

        config_client1 = HostConfig()
        config_client1.host = client1
        config_client1.priority = 4
        db.add(config_client1)

        config_client2 = HostConfig()
        config_client2.host = client2
        config_client2.use_global_filters = False
        db.add(config_client2)

        backup1_client1 = Backup()
        backup1_client1.host = client1
        backup1_client1.storage = client1.backup_server.storage[0]
        backup1_client1.start_time = datetime.datetime(
                2012, 01, 02, 00, 00, 00)
        backup1_client1.end_time = datetime.datetime(2012, 01, 02, 00, 07, 32)
        backup1_client1.generation = 'daily'
        backup1_client1.successful = True
        backup1_client1.was_checksum_run = False
        backup1_client1.harness_returncode = 0
        backup1_client1.snapshot_location = (
                '/backups/client1.example.net@2012-01-02_000000')
        db.add(backup1_client1)

        backup2_client1 = Backup()
        backup2_client1.host = client1
        backup2_client1.storage = client1.backup_server.storage[0]
        backup2_client1.start_time = datetime.datetime(
                2012, 01, 01, 00, 00, 01)
        backup2_client1.end_time = datetime.datetime(2012, 01, 01, 00, 8, 11)
        backup2_client1.generation = 'daily'
        backup2_client1.successful = False
        backup2_client1.was_checksum_run = False
        backup2_client1.harness_returncode = 1
        backup2_client1.snapshot_location = (
                '/backups/client1.example.net@2012-01-01_000001')
        db.add(backup2_client1)

        backup1_client2 = Backup()
        backup1_client2.host = client2
        backup1_client2.storage = client2.backup_server.storage[0]
        backup1_client2.start_time = datetime.datetime(
                2012, 01, 02, 00, 00, 00)
        backup1_client2.end_time = datetime.datetime(2012, 01, 02, 00, 07, 32)
        backup1_client2.generation = 'daily'
        backup1_client2.successful = True
        backup1_client2.was_checksum_run = False
        backup1_client2.harness_returncode = 0
        backup1_client2.snapshot_location = (
                '/backups/client2.example.net@2012-01-02_000000')
        db.add(backup1_client2)

        backup2_client2 = Backup()
        backup2_client2.host = client2
        backup2_client2.storage = client2.backup_server.storage[0]
        backup2_client2.start_time = datetime.datetime(
                2012, 01, 01, 00, 01, 00)
        backup2_client2.end_time = datetime.datetime(2012, 01, 01, 00, 07, 32)
        backup2_client2.generation = 'weekly'
        backup2_client2.successful = True
        backup2_client2.was_checksum_run = False
        backup2_client2.harness_returncode = 0
        backup2_client2.snapshot_location = (
                '/backups/client2.example.net@2012-01-01_000100')
        db.add(backup2_client2)

        filter1_global = FilterRule()
        filter1_global.rsync_rule = 'exclude /tmp/'
        db.add(filter1_global)

        filter2_global = FilterRule()
        filter2_global.rsync_rule = 'exclude /var/log/'
        db.add(filter2_global)

        filter3_global = FilterRule()
        filter3_global.rsync_rule = 'exclude /home/*/.cache/'
        db.add(filter3_global)

        filter1_client1 = FilterRule()
        filter1_client1.host = client1
        filter1_client1.rsync_rule = 'exclude /dev/shm/'
        filter1_client1.priority = '4'
        db.add(filter1_client1)

        filter1_client1 = FilterRule()
        filter1_client1.host = client1
        filter1_client1.rsync_rule = 'exclude /proc/'
        filter1_client1.priority = '42'
        db.add(filter1_client1)

        usage_client1 = HostUsage()
        usage_client1.host = client1
        usage_client1.sample_date = datetime.date(2012, 1, 1)
        usage_client1.used_by_dataset = 100000
        usage_client1.used_by_snapshots = 200000
        usage_client1.compression_ratio_percent = 100
        usage_client1.runtime = datetime.timedelta(minutes=8, seconds=10)
        db.add(usage_client1)

        usage_client2 = HostUsage()
        usage_client2.host = client2
        usage_client2.sample_date = datetime.date(2012, 1, 1)
        usage_client2.used_by_dataset = 500000
        usage_client2.used_by_snapshots = 200000
        usage_client2.compression_ratio_percent = 100
        usage_client2.runtime = datetime.timedelta(minutes=6, seconds=32)
        db.add(usage_client2)

        usage_server = StorageUsage()
        usage_server.storage = zfs_storage
        usage_server.sample_date = datetime.date(2012, 1, 1)
        usage_server.total_bytes = 100000000
        usage_server.free_bytes = 90000000
        usage_server.used_bytes = 10000000
        usage_server.usage_percent = 10
        usage_server.dedup_ratio_percent = 100
        db.add(usage_server)

        db.commit()

    def test_BadSchema(self):
        '''Test for things that should fail in the schema.'''

        #  load the database with the schema test
        self.test_Schema()

        db = nabdb.session()

        #  duplicate server name
        with self.assertRaises(IntegrityError):
            server = BackupServer()
            server.hostname = 'server.example.com'
            db.add(server)
            db.commit()
        db.rollback()

        #  duplicate client name
        with self.assertRaises(IntegrityError):
            client1 = Host()
            client1.backup_server = server
            client1.hostname = 'client1.example.com'
            client1.window_start = datetime.time(0, 0)
            client1.window_end = datetime.time(5, 0)
            db.add(client1)
            db.commit()
        db.rollback()

        #  look up host for future calls
        client1 = db.query(Host).filter_by(
                hostname='client1.example.com').first()

        #  duplicate client configuration
        with self.assertRaises(IntegrityError):
            config_client1 = HostConfig()
            config_client1.host = client1
            config_client1.priority = 4
            db.add(config_client1)
            db.commit()
        db.rollback()

        #  invalid generation name
        with self.assertRaises(IntegrityError):
            backup1_client1 = Backup()
            backup1_client1.host = client1
            backup1_client1.storage = client1.backup_server.storage[0]
            backup1_client1.start_time = datetime.datetime(
                    2012, 01, 03, 00, 00, 00)
            backup1_client1.end_time = datetime.datetime(
                    2012, 01, 03, 00, 07, 32)
            backup1_client1.generation = 'daily'
            backup1_client1.successful = True
            backup1_client1.was_checksum_run = False
            backup1_client1.harness_returncode = 0
            backup1_client1.snapshot_location = (
                    '/backups/client1.example.net@2012-01-03_000000')
            db.add(backup1_client1)
            db.commit()
        db.rollback()

        #  verify that rsync_rule cannot be None
        with self.assertRaises(IntegrityError):
            filter1_global = FilterRule()
            db.add(filter1_global)
            db.commit()
        db.rollback()

        #  verify that date must be set
        with self.assertRaises(IntegrityError):
            usage_client1 = HostUsage()
            usage_client1.host = client1
            usage_client1.used_by_dataset = 500000
            usage_client1.used_by_snapshots = 200000
            usage_client1.compression_ratio_percent = 100
            usage_client1.runtime = datetime.timedelta(minutes=6, seconds=32)
            db.add(usage_client1)
            db.commit()
        db.rollback()

        #  verify that date must be set
        with self.assertRaises(IntegrityError):
            usage_server = StorageUsage()
            usage_server.storage = client1.backup_server.storage[0]
            usage_server.total_bytes = 100000000
            usage_server.free_bytes = 90000000
            usage_server.used_bytes = 10000000
            usage_server.usage_percent = 10
            usage_server.dedup_ratio_percent = 100
            db.add(usage_server)
            db.commit()
        db.rollback()

    def test_ObjectRepresentation(self):
        '''Verify that database objects can be formatted as strings.'''

        #  load the database with the schema test
        self.test_Schema()

        db = nabdb.session()

        repr(db.query(Host).first())
        repr(db.query(BackupServer).first())
        repr(db.query(FilterRule).first())
        repr(db.query(StorageUsage).first())
        repr(db.query(HostUsage).first())
        repr(db.query(Storage).first())
        repr(db.query(Metadata).first())
        repr(db.query(HostConfig).first())
        repr(db.query(Backup).first())

print unittest.main()
