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

    def test_SchemaBasic(self):
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

        db.commit()

    def test_SchemaAdditional(self):
        '''Additional schema resources for testing.
        This schema produces additional resources, but it may conflict with
        testing of things beyond the basic schema.'''
        self.test_SchemaBasic()
        db = nabdb.session()

        client1 = db.query(Host).filter_by(hostname='client1.example.com'
                ).first()
        client2 = db.query(Host).filter_by(hostname='client2.example.com'
                ).first()
        zfs_storage = db.query(Storage).first()

        backup1_client1 = Backup(client1, 'daily', full_checksum=False)
        backup1_client1.storage = client1.backup_server.storage[0]
        backup1_client1.start_time = datetime.datetime(
                2012, 01, 02, 00, 00, 00)
        backup1_client1.end_time = datetime.datetime(2012, 01, 02, 00, 07, 32)
        backup1_client1.successful = True
        backup1_client1.harness_returncode = 0
        backup1_client1.snapshot_location = (
                '/backups/client1.example.net@2012-01-02_000000')
        db.add(backup1_client1)

        backup2_client1 = Backup(client1, 'daily', full_checksum=False)
        backup2_client1.storage = client1.backup_server.storage[0]
        backup2_client1.start_time = datetime.datetime(
                2012, 01, 01, 00, 00, 01)
        backup2_client1.end_time = datetime.datetime(2012, 01, 01, 00, 8, 11)
        backup2_client1.successful = False
        backup2_client1.harness_returncode = 1
        backup2_client1.snapshot_location = (
                '/backups/client1.example.net@2012-01-01_000001')
        db.add(backup2_client1)

        backup1_client2 = Backup(client2, 'daily', full_checksum=False)
        backup1_client2.storage = client2.backup_server.storage[0]
        backup1_client2.start_time = datetime.datetime(
                2012, 01, 02, 00, 00, 00)
        backup1_client2.end_time = datetime.datetime(2012, 01, 02, 00, 07, 32)
        backup1_client2.successful = True
        backup1_client2.harness_returncode = 0
        backup1_client2.snapshot_location = (
                '/backups/client2.example.net@2012-01-02_000000')
        db.add(backup1_client2)

        backup2_client2 = Backup(client2, 'weekly', full_checksum=False)
        backup2_client2.storage = client2.backup_server.storage[0]
        backup2_client2.start_time = datetime.datetime(
                2012, 01, 01, 00, 01, 00)
        backup2_client2.end_time = datetime.datetime(2012, 01, 01, 00, 07, 32)
        backup2_client2.successful = True
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
        self.test_SchemaAdditional()

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
            backup1_client1 = Backup(client1, 'hourly', full_checksum=True)
            backup1_client1.storage = client1.backup_server.storage[0]
            backup1_client1.start_time = datetime.datetime(
                    2012, 01, 03, 00, 00, 00)
            backup1_client1.end_time = datetime.datetime(
                    2012, 01, 03, 00, 07, 32)
            backup1_client1.successful = True
            backup1_client1.full_checksum = False
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
        self.test_SchemaAdditional()

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

    def test_MergedConfigs(self):
        '''Test the merging of global and host configurations.'''

        #  load the database with the schema test
        self.test_SchemaBasic()

        db = nabdb.session()

        client1 = db.query(Host).filter_by(hostname='client1.example.com'
                ).first()

        #  delete the old configs
        db.delete(client1.configs[0])
        db.flush()
        db.delete(db.query(HostConfig).filter_by(host_id=None).first())
        db.flush()
        db.commit()

        config_default = HostConfig()
        config_default.alerts_mail_address = 'sysadmin@example.com'
        config_default.failure_warn_after = datetime.timedelta(days=3)
        config_default.rsync_checksum_frequency = datetime.timedelta(days=30)
        config_default.rsync_do_compress = False
        config_default.use_global_filters = True
        config_default.priority = 4
        config_default.check_connectivity = False
        config_default.ping_max_ms = 30
        config_default.daily_history = 7
        config_default.weekly_history = 6
        config_default.monthly_history = 5
        db.add(config_default)

        config_client1 = HostConfig()
        config_client1.host = client1
        db.add(config_client1)
        db.commit()

        self.assertEqual(client1.merged_configs(db).monthly_history, 5)
        config_client1.monthly_history = 3
        db.commit()
        self.assertEqual(client1.merged_configs(db).monthly_history, 3)

        self.assertEqual(client1.merged_configs(db).weekly_history, 6)
        config_client1.weekly_history = 2
        db.commit()
        self.assertEqual(client1.merged_configs(db).weekly_history, 2)

        self.assertEqual(client1.merged_configs(db).daily_history, 7)
        config_client1.daily_history = 1
        db.commit()
        self.assertEqual(client1.merged_configs(db).daily_history, 1)

        self.assertEqual(client1.merged_configs(db).ping_max_ms, 30)
        config_client1.ping_max_ms = 29
        db.commit()
        self.assertEqual(client1.merged_configs(db).ping_max_ms, 29)

        self.assertEqual(client1.merged_configs(db).priority, 4)
        config_client1.priority = 8
        db.commit()
        self.assertEqual(client1.merged_configs(db).priority, 8)

        self.assertEqual(client1.merged_configs(db).alerts_mail_address,
                'sysadmin@example.com')
        config_client1.alerts_mail_address = 'rooter@example.com'
        db.commit()
        self.assertEqual(client1.merged_configs(db).alerts_mail_address,
                'rooter@example.com')

        self.assertEqual(str(client1.merged_configs(db).failure_warn_after),
                '3 days, 0:00:00')
        config_client1.failure_warn_after = datetime.timedelta(days=4)
        db.commit()
        self.assertEqual(str(client1.merged_configs(db).failure_warn_after),
                '4 days, 0:00:00')

        self.assertEqual(client1.merged_configs(db).use_global_filters, True)
        config_client1.use_global_filters = False
        db.commit()
        self.assertEqual(client1.merged_configs(db).use_global_filters, False)

        self.assertEqual(client1.merged_configs(db).check_connectivity, False)
        config_client1.check_connectivity = True
        db.commit()
        self.assertEqual(client1.merged_configs(db).check_connectivity, True)

        self.assertEqual(
                str(client1.merged_configs(db).rsync_checksum_frequency),
                '30 days, 0:00:00')
        config_client1.rsync_checksum_frequency = datetime.timedelta(days=29)
        db.commit()
        self.assertEqual(
                str(client1.merged_configs(db).rsync_checksum_frequency),
                '29 days, 0:00:00')

        self.assertEqual(client1.merged_configs(db).rsync_do_compress, False)
        config_client1.rsync_do_compress = True
        db.commit()
        self.assertEqual(client1.merged_configs(db).rsync_do_compress, True)

    def test_FindBackupGeneration(self):
        '''Test the code that finds the next generation of backup to run.'''

        #  load the database with the schema test
        self.test_SchemaBasic()

        db = nabdb.session()

        client1 = db.query(Host).filter_by(hostname='client1.example.com'
                ).first()

        #  delete the old configs
        db.delete(client1.configs[0])
        db.flush()
        db.delete(db.query(HostConfig).filter_by(host_id=None).first())
        db.flush()
        db.commit()

        config = HostConfig()
        config.host = client1
        config.daily_history = 4
        config.weekly_history = 3
        config.monthly_history = 2
        db.add(config)
        db.commit()

        self.assertEqual(client1.find_backup_generation(db), 'monthly')

        backup = Backup(client1, 'monthly', full_checksum=False)
        backup.storage = client1.backup_server.storage[0]
        backup.start_time = datetime.datetime.now()
        backup.end_time = datetime.datetime.now()
        backup.successful = True
        backup.harness_returncode = 0
        backup.snapshot_location = (
                '/backups/client1.example.net@2012-01-01_000100')
        db.add(backup)
        db.commit()

        self.assertEqual(client1.find_backup_generation(db), 'weekly')

        backup = Backup(client1, 'weekly', full_checksum=False)
        backup.storage = client1.backup_server.storage[0]
        backup.start_time = datetime.datetime.now()
        backup.end_time = datetime.datetime.now()
        backup.successful = True
        backup.harness_returncode = 0
        backup.snapshot_location = (
                '/backups/client1.example.net@2012-01-01_000100')
        db.add(backup)
        db.commit()

        self.assertEqual(client1.find_backup_generation(db), 'daily')

        backup = Backup(client1, 'daily', full_checksum=False)
        backup.storage = client1.backup_server.storage[0]
        backup.start_time = datetime.datetime.now()
        backup.end_time = datetime.datetime.now()
        backup.successful = True
        backup.harness_returncode = 0
        backup.snapshot_location = (
                '/backups/client1.example.net@2012-01-01_000100')
        db.add(backup)
        db.commit()

        self.assertEqual(client1.find_backup_generation(db), 'daily')

    def test_FindBackupGenerationNoMonthly(self):
        '''Test the code that finds the next generation of backup to run.
        This test has the monthly backups disabled.
        '''

        #  load the database with the schema test
        self.test_SchemaBasic()

        db = nabdb.session()

        client1 = db.query(Host).filter_by(hostname='client1.example.com'
                ).first()

        #  delete the old configs
        db.delete(client1.configs[0])
        db.flush()
        db.delete(db.query(HostConfig).filter_by(host_id=None).first())
        db.flush()
        db.commit()

        config = HostConfig()
        config.host = client1
        config.daily_history = 4
        config.weekly_history = 3
        config.monthly_history = 0
        db.add(config)
        db.commit()

        self.assertEqual(client1.find_backup_generation(db), 'weekly')

        backup = Backup(client1, 'monthly', full_checksum=False)
        backup.host = client1
        backup.storage = client1.backup_server.storage[0]
        backup.start_time = datetime.datetime.now()
        backup.end_time = datetime.datetime.now()
        backup.successful = True
        backup.harness_returncode = 0
        backup.snapshot_location = (
                '/backups/client1.example.net@2012-01-01_000100')
        db.add(backup)
        db.commit()

        self.assertEqual(client1.find_backup_generation(db), 'weekly')

        backup = Backup(client1, 'weekly', full_checksum=False)
        backup.storage = client1.backup_server.storage[0]
        backup.start_time = datetime.datetime.now()
        backup.end_time = datetime.datetime.now()
        backup.successful = True
        backup.harness_returncode = 0
        backup.snapshot_location = (
                '/backups/client1.example.net@2012-01-01_000100')
        db.add(backup)
        db.commit()

        self.assertEqual(client1.find_backup_generation(db), 'daily')

        backup = Backup(client1, 'daily', full_checksum=False)
        backup.storage = client1.backup_server.storage[0]
        backup.start_time = datetime.datetime.now()
        backup.end_time = datetime.datetime.now()
        backup.successful = True
        backup.harness_returncode = 0
        backup.snapshot_location = (
                '/backups/client1.example.net@2012-01-01_000100')
        db.add(backup)
        db.commit()

        self.assertEqual(client1.find_backup_generation(db), 'daily')

    def test_FindBackupGenerationNoWeeklyOrMonthly(self):
        '''Test the code that finds the next generation of backup to run.
        This test has the monthly and weekly backups disabled.
        '''

        #  load the database with the schema test
        self.test_SchemaBasic()

        db = nabdb.session()

        client1 = db.query(Host).filter_by(hostname='client1.example.com'
                ).first()

        #  delete the old configs
        db.delete(client1.configs[0])
        db.flush()
        db.delete(db.query(HostConfig).filter_by(host_id=None).first())
        db.flush()
        db.commit()

        config = HostConfig()
        config.host = client1
        config.daily_history = 4
        config.weekly_history = 0
        config.monthly_history = 0
        db.add(config)
        db.commit()

        self.assertEqual(client1.find_backup_generation(db), 'daily')

        backup = Backup(client1, 'monthly', full_checksum=False)
        backup.storage = client1.backup_server.storage[0]
        backup.start_time = datetime.datetime.now()
        backup.end_time = datetime.datetime.now()
        backup.successful = True
        backup.harness_returncode = 0
        backup.snapshot_location = (
                '/backups/client1.example.net@2012-01-01_000100')
        db.add(backup)
        db.commit()

        self.assertEqual(client1.find_backup_generation(db), 'daily')

        backup = Backup(client1, 'weekly', full_checksum=False)
        backup.storage = client1.backup_server.storage[0]
        backup.start_time = datetime.datetime.now()
        backup.end_time = datetime.datetime.now()
        backup.successful = True
        backup.harness_returncode = 0
        backup.snapshot_location = (
                '/backups/client1.example.net@2012-01-01_000100')
        db.add(backup)
        db.commit()

        self.assertEqual(client1.find_backup_generation(db), 'daily')

        backup = Backup(client1, 'daily', full_checksum=False)
        backup.storage = client1.backup_server.storage[0]
        backup.start_time = datetime.datetime.now()
        backup.end_time = datetime.datetime.now()
        backup.successful = True
        backup.harness_returncode = 0
        backup.snapshot_location = (
                '/backups/client1.example.net@2012-01-01_000100')
        db.add(backup)
        db.commit()

        self.assertEqual(client1.find_backup_generation(db), 'daily')

    def test_FindBackupGenerationNoWeekly(self):
        '''Test the code that finds the next generation of backup to run.
        This test has the weekly backups disabled.
        '''

        #  load the database with the schema test
        self.test_SchemaBasic()

        db = nabdb.session()

        client1 = db.query(Host).filter_by(hostname='client1.example.com'
                ).first()

        #  delete the old configs
        db.delete(client1.configs[0])
        db.flush()
        db.delete(db.query(HostConfig).filter_by(host_id=None).first())
        db.flush()
        db.commit()

        config = HostConfig()
        config.host = client1
        config.daily_history = 4
        config.weekly_history = 0
        config.monthly_history = 2
        db.add(config)
        db.commit()

        self.assertEqual(client1.find_backup_generation(db), 'monthly')

        backup = Backup(client1, 'monthly', full_checksum=False)
        backup.storage = client1.backup_server.storage[0]
        backup.start_time = datetime.datetime.now()
        backup.end_time = datetime.datetime.now()
        backup.successful = True
        backup.harness_returncode = 0
        backup.snapshot_location = (
                '/backups/client1.example.net@2012-01-01_000100')
        db.add(backup)
        db.commit()

        self.assertEqual(client1.find_backup_generation(db), 'daily')

        backup = Backup(client1, 'weekly', full_checksum=False)
        backup.storage = client1.backup_server.storage[0]
        backup.start_time = datetime.datetime.now()
        backup.end_time = datetime.datetime.now()
        backup.successful = True
        backup.harness_returncode = 0
        backup.snapshot_location = (
                '/backups/client1.example.net@2012-01-01_000100')
        db.add(backup)
        db.commit()

        self.assertEqual(client1.find_backup_generation(db), 'daily')

        backup = Backup(client1, 'daily', full_checksum=False)
        backup.storage = client1.backup_server.storage[0]
        backup.start_time = datetime.datetime.now()
        backup.end_time = datetime.datetime.now()
        backup.successful = True
        backup.harness_returncode = 0
        backup.snapshot_location = (
                '/backups/client1.example.net@2012-01-01_000100')
        db.add(backup)
        db.commit()

        self.assertEqual(client1.find_backup_generation(db), 'daily')

    def test_BackupsWithPids(self):
        '''Test finding backups that have PIDs and clearing them.
        '''

        #  load the database with the schema test
        self.test_SchemaBasic()

        import os
        import random
        import nabsupp
        db = nabdb.session()

        client1 = db.query(Host).filter_by(hostname='client1.example.com'
                ).first()

        def add_more_backups(db, with_known_pid=False):
            for i in range(10):
                backup = Backup(client1, 'monthly', full_checksum=False)
                if with_known_pid:
                    backup.backup_pid = os.getpid()
                    with_known_pid = False
                else:
                    for foo in range(100):
                        pid = random.randint(1000, 60000)
                        try:
                            os.kill(pid, 0)
                        except OSError:
                            backup.backup_pid = pid
                            break
                    else:
                        raise ValueError('Unable to find free PID.')
                db.add(backup)
                db.commit()

        add_more_backups(db)
        self.assertEqual(client1.are_backups_currently_running(db), False)
        self.assertEqual(len(client1.backups_with_pids()), 0)

        add_more_backups(db)
        self.assertEqual(len(client1.backups_with_pids()), 10)
        nabsupp.clear_stale_backup_pids(db, client1)
        self.assertEqual(len(client1.backups_with_pids()), 0)
        self.assertEqual(client1.are_backups_currently_running(db), False)

        add_more_backups(db, with_known_pid=True)
        self.assertEqual(len(client1.backups_with_pids()), 10)
        self.assertEqual(client1.are_backups_currently_running(db), True)
        nabsupp.clear_stale_backup_pids(db, client1)
        self.assertEqual(len(client1.backups_with_pids()), 1)
        self.assertEqual(client1.are_backups_currently_running(db), True)

    def test_BackupsWithPids(self):
        '''Test finding backups that have PIDs and clearing them.
        '''

        #  load the database with the schema test
        self.test_SchemaBasic()

        db = nabdb.session()

        client1 = db.query(Host).filter_by(hostname='client1.example.com'
                ).first()
        config = client1.configs[0]

        backup = Backup(client1, 'monthly', full_checksum=False)
        db.add(backup)
        db.commit()

        self.assertEqual(client1.ready_for_checksum(db), False)

        config.rsync_checksum_frequency = datetime.timedelta(days=30)
        db.flush()
        db.commit()
        self.assertEqual(client1.ready_for_checksum(db), True)

        client1.last_rsync_checksum = (datetime.datetime.now()
                - datetime.timedelta(days=31))
        db.flush()
        db.commit()
        self.assertEqual(client1.ready_for_checksum(db), True)

        client1.last_rsync_checksum = (datetime.datetime.now()
                - datetime.timedelta(days=29))
        db.flush()
        db.commit()
        self.assertEqual(client1.ready_for_checksum(db), False)

print unittest.main()
