#!/usr/bin/env python
#
#  Copyright (c) 2011, Sean Reifschneider, tummy.com, ltd.
#  All Rights Reserved.

'''Database model for network-attached-backup.'''

from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy import BigInteger, SmallInteger
from sqlalchemy import Interval, CheckConstraint, Boolean, DateTime, Time, Date
from sqlalchemy.orm import relationship
from sqlalchemy.exc import IntegrityError
import datetime
import nabsupp


class Metadata(Base):
    '''Global information about the installation.
    There is only one row in this table.
    '''

    __tablename__ = 'config'
    id = Column(Integer, CheckConstraint('id = 1'), primary_key=True,
            unique=True)
    database_version = Column(Integer)

    def __init__(self):
        self.id = 1
        self.database_version = 1

    def __repr__(self):
        return '<Config(id=%s, dbver=%s)>' % (self.id, self.database_version)

    @classmethod
    def get(cls, session):
        '''Return an instance of the meta-data record.
        There is only one meta-data record, this function returns it.

        :param session: Database session instance, used to access the Metadata.
        '''
        return session.query(Metadata).filter(Metadata.id == 1)[0]


class BackupServer(Base):
    '''The host which stores and runs backups of :py:class:`Host`

    .. py:attribute:: hostname

    Name of the backup server.

    .. py:attribute:: ssh_supports_y

    Does the SSH on this host support the "-y" option?  Older versions of SSH
    such as on Hardy or CentOS 5 do not support "-y".

    .. py:attribute:: scheduler_slots

    Number of backups that can run concurrently.
    '''

    __tablename__ = 'backup_servers'
    id = Column(Integer, primary_key=True)
    hostname = Column(String, nullable=False, unique=True)
    scheduler_slots = Column(Integer, nullable=False, default=6)
    ssh_supports_y = Column(Boolean, default=True)

    def __init__(self):
        pass

    def __repr__(self):
        return '<BackupServer(%s)>' % (self.hostname,)


class Storage(Base):
    '''Specifies a location for storage of backups, for example a file-system
    directory, or zfs data-set.

    .. py:attribute:: backup_server

    Reference to the :py:class:`BackupServer` that this storage is on.

    .. py:attribute:: method

    Type of backup storage, for example "zfs" or "hardlinks".

    .. py:attribute:: arg1

    Method-defined argument.
    zfs: The backup pool name.
    hardlinks: Backup directory path.

    .. py:attribute:: arg2

    Method-defined argument.
    zfs: Backup file-system name.
    hardlinks: Unused

    .. py:attribute:: arg3

    Method-defined argument.
    zfs: Backup file-system mount-point.
    hardlinks: Unused

    .. py:attribute:: arg4

    Method-defined argument.  Currently unused.

    .. py:attribute:: arg5

    Method-defined argument.  Currently unused.
    '''

    __tablename__ = 'storage'
    id = Column(Integer, primary_key=True)
    backup_server_id = Column(Integer, ForeignKey('backup_servers.id'))
    backup_server = relationship(BackupServer, order_by=id,
            backref='storage')
    method = Column(String, nullable=False)
    arg1 = Column(String, default=None)
    arg2 = Column(String, default=None)
    arg3 = Column(String, default=None)
    arg4 = Column(String, default=None)
    arg5 = Column(String, default=None)

    def __init__(self):
        pass

    def __repr__(self):
        return '<Storage(%s, %s:%s)>' % (self.backup_server.hostname,
                self.method, self.arg1)


class Host(Base):
    '''A backed-up host.

    .. py:attribute:: backup_server

    Reference to the :py:class:`BackupServer` that this host is backed up to.

    .. py:attribute:: hostname

    Name of the host to be backed up.  This is also used in the rsync
    command-line, so it needs to be the name that SSH knows the host as.

    .. py:attribute:: ip_address

    The IP address of the host, if the hostname cannot be used.  If None,
    the `hostname` will be used instead.

    .. py:attribute:: active

    Is this host active in the backups, or just a place-holder.  For example,
    if the host has been decommissioned but you want the backups to remain
    available.  Alerts are not sent if inactive hosts have not been backed
    up recently, and backups are not attempted.

    .. py:attribute:: next_backup

    Date and time when the next backup will run.

    .. py:attribute:: window_start

    Time of day that the backup window starts.

    .. py:attribute:: window_start

    Time of day that the backup window ends.
    '''

    __tablename__ = 'hosts'
    id = Column(Integer, primary_key=True)
    backup_server_id = Column(Integer, ForeignKey('backup_servers.id'))
    backup_server = relationship(BackupServer, order_by=id,
            backref='hosts')
    hostname = Column(String, nullable=False, unique=True)
    ip_address = Column(String)
    active = Column(Boolean, default=True)
    next_backup = Column(DateTime)
    window_start = Column(Time)
    window_end = Column(Time)
    last_rsync_checksum = Column(DateTime)

    def ready_for_checksum(self, db):
        '''Is it time for a full checksum run?

        :rtype: Boolean, True means a backup with checksum should be run.
        '''
        frequency = self.merged_configs(db).rsync_checksum_frequency
        if frequency == None:
            return False

        if self.last_rsync_checksum == None:
            return True

        return self.last_rsync_checksum + frequency < datetime.datetime.now()

    def are_backups_currently_running(self, db):
        '''Are there any backups currently running for this host?

        :rtype: Boolean indicating whether there are any backups running
        '''
        nabsupp.clear_stale_backup_pids(db, self)
        return len(self.backups_with_pids()) > 0

    def backups_with_pids(self):
        '''Return a list of backups that have a pid != None'''
        return [backup for backup in self.backups if backup.backup_pid != None]

    def merged_configs(self, db):
        '''Return an object that combines the host and global configs.'''
        class MergedConfigs:
            def __init__(self, configs, db):
                self.configs = configs[0]
                self.global_configs = db.query(HostConfig).filter_by(
                        host_id=None).first()

            def __getattr__(self, attr):
                hostconfig = getattr(self.configs, attr)
                if hostconfig != None:
                    return hostconfig
                return getattr(self.global_configs, attr)

        return MergedConfigs(self.configs, db)

    def find_backup_generation(self, db):
        '''Return the name of the backup generation for the next backup.'''
        for history, generation, strftime in [
                (self.merged_configs(db).monthly_history, 'monthly', '%Y-%m'),
                (self.merged_configs(db).weekly_history, 'weekly', '%Y-%U'),
                ]:
            if history:
                for backup in db.query(Backup).filter_by(host=self,
                        successful=True, generation=generation):
                    if (backup.start_time.strftime(strftime)
                            == datetime.datetime.now().strftime(strftime)):
                        break
                else:
                    return generation

        return 'daily'

    def __init__(self):
        pass

    def __repr__(self):
        return '<Host(id=%s, hostname="%s")>' % (self.id, self.hostname)


class HostConfig(Base):
    '''Configurable values for the backed-up hosts.
    A :py:class:`HostConfig` that does not reference a :py:class:`Host` is a
    global configuration, which other hosts use if they have not overridden
    those values.

    .. py:attribute:: host

    Reference to the :py:class:`Host` that this configuration corresponds to,
    or None for the default configuration record.

    .. py:attribute:: alerts_mail_address

    E-mail address to send messages to when there is something that needs

    .. py:attribute:: failure_warn_after

    Interval that warnings are sent if the host has not been backed up in
    this long.

    .. py:attribute:: use_global_filters

    Are global filters applied to this host?

    .. py:attribute:: check_connectivity

    Attempt to ping the host before running a backup, and only start the
    backup when the pings succeed.  This can be useful for backing up
    intermittantly connected machines such as laptops.

    . py:attribute:: ping_max_ms

    If not None, the host will be pinged before a backup, and backups
    will only be done if the average ping-time is below this value.  This
    is useful if you have laptops and only want to back them up when they
    are at the same location as the backup server.

    .. py:attribute:: daily_history

    Number of daily backup copies to keep.

    .. py:attribute:: weekly_history

    Number of weekly backup copies to keep.

    .. py:attribute:: monthly_history

    Number of monthly backup copies to keep.

    .. py:attribute:: priority

    Hosts with a lower priority are backed up first, if multiple hosts are
    eligible for backup.

    .. py:attribute:: rsync_checksum_frequency

    Length of time between doing full rsync checksum runs, or None to disable
    full checksum runs.

    .. py:attribute:: rsync_compression

    If true, compress the rsync stream.  This should only be used for remote
    machines, it will dramatically slow down backups over a LAN.
    '''

    __tablename__ = 'host_configs'
    id = Column(Integer, primary_key=True)
    host_id = Column(Integer, ForeignKey('hosts.id'), unique=True)
    host = relationship(Host, order_by=id, backref='configs')
    alerts_mail_address = Column(String)
    failure_warn_after = Column(Interval)
    use_global_filters = Column(Boolean)
    check_connectivity = Column(Boolean)
    ping_max_ms = Column(Integer)
    daily_history = Column(Integer)
    weekly_history = Column(Integer)
    monthly_history = Column(Integer)
    priority = Column(Integer)
    rsync_checksum_frequency = Column(Interval)
    rsync_do_compress = Column(Boolean)

    def get_hostname(self):
        '''Return the hostname or "<GLOBAL>" for the global config.'''
        if self.host_id == None:
            return '<GLOBAL>'
        return self.host.hostname

    def as_string(self):
        '''Return a string of the values of this record'''
        s = ''
        for attr in (
                'alerts_mail_address',
                'failure_warn_after',
                'use_global_filters',
                'check_connectivity',
                'ping_max_ms',
                'daily_history',
                'weekly_history',
                'monthly_history',
                'priority',
                'rsync_checksum_frequency',
                'rsync_do_compress',
                ):
            s += '%s=%s ' % (attr, getattr(self, attr))
        return s

    def __init__(self):
        pass

    def __repr__(self):
        return '<HostConfig(id=%s, hostname=%s)>' % (self.id,
                self.get_hostname())


class Backup(Base):
    '''Information about each backed-up data-set.

    .. py:attribute:: host

    Reference to the :py:class:`Host` that this is a backup of.

    .. py:attribute:: backup_server

    Reference to the :py:class:`BackupServer` that this backup is on.

    .. py:attribute:: storage

    Reference to the :py:class:`Storage` that this backup uses.

    .. py:attribute:: start_time

    When the backup started.

    .. py:attribute:: end_time

    When the backup completed.

    .. py:attribute:: backup_pid

    Process ID of the backup, or None if the backup is no longer running.

    .. py:attribute:: generation

    Generation of backup this was.

    .. py:attribute:: successful

    Was this backup considered successful?

    .. py:attribute:: was_checksum_run

    Trus if this backup did a full checksum run.

    .. py:attribute:: harness_returncode

    Return-code from the harness (which runs the rsync) process.

    .. py:attribute:: snapshot_location

    Storage-specific location of the backup snapshot.
    '''

    __tablename__ = 'backups'
    id = Column(Integer, primary_key=True)
    host_id = Column(Integer, ForeignKey('hosts.id'))
    host = relationship(Host, order_by=id, backref='backups')
    storage_id = Column(Integer, ForeignKey('storage.id'))
    storage = relationship(Storage, order_by=id, backref='backups')
    start_time = Column(DateTime, default=None)
    end_time = Column(DateTime, default=None)
    backup_pid = Column(Integer, default=None)
    generation = Column(String,
            CheckConstraint("generation = 'daily' or generation = 'weekly' "
                "or generation = 'monthly'"),
            nullable=False)
    successful = Column(Boolean, default=None)
    was_checksum_run = Column(Boolean, nullable=False)
    harness_returncode = Column(Integer, default=None)
    snapshot_location = Column(String)

    def __init__(self):
        pass

    def __repr__(self):
        return '<Backup(%s: %s@%s)>' % (self.id, self.host.hostname,
                self.start_time)


class FilterRule(Base):
    '''Rsync filter rules for the various backups.

    .. py:attribute:: host

    Reference to the :py:class:`Host` that this rule applies to,
    or None if it is a global rule.

    .. py:attribute:: priority

    Priority of this rule in relation to other rules, usually a string of
    digits, where "45" comes halfway between "4" and "5".  Think "dewey
    decimal system".

    .. py:attribute:: rsync_rule

    Text representing an rsync rule.
    '''

    __tablename__ = 'filter_rules'
    id = Column(Integer, primary_key=True)
    host_id = Column(Integer, ForeignKey('hosts.id'))
    host = relationship(Host, order_by=id, backref='filter_rules')
    priority = Column(String, default='5', nullable=False)
    rsync_rule = Column(String, nullable=False)

    def __init__(self):
        pass

    def __repr__(self):
        return '<FilterRule(%s: %s@%s)>' % (self.id, self.priority,
                self.rsync_rule)


class HostUsage(Base):
    '''Historic space usage of a particular host.
    This depends on the backend, some backends do not support quick
    querying of usage of snapshots or individual hosts.

    .. py:attribute:: host

    Reference to the :py:class:`Host` that this usage relates to.

    .. py:attribute:: sample_date

    Date that this usage information is related to.

    .. py:attribute:: used_by_dataset

    Number of bytes used by the current backup, or None if not available.

    .. py:attribute:: used_by_snapshot

    Number of bytes used by the snapshot, or None if not available.

    .. py:attribute:: compression_ratio_percent

    Compression ratio in percent.

    .. py:attribute:: runtime

    Length of time the backup ran for.
    '''

    __tablename__ = 'host_usage'
    id = Column(Integer, primary_key=True)
    host_id = Column(Integer, ForeignKey('hosts.id'))
    host = relationship(Host, order_by=id, backref='usage')
    sample_date = Column(Date, nullable=False)
    used_by_dataset = Column(BigInteger, default=None)
    used_by_snapshots = Column(BigInteger, default=None)
    compression_ratio_percent = Column(SmallInteger, default=None)
    runtime = Column(Interval)

    def __init__(self):
        pass

    def __repr__(self):
        return '<HostUsage(%s: %s@%s)>' % (self.id, self.host.hostname,
                self.sample_date)


class StorageUsage(Base):
    '''Historic space usage of a particular backup server.

    .. py:attribute:: storage

    Reference to the :py:class:`Storage` that this backup uses.

    .. py:attribute:: sample_date

    Date that this usage information is related to.

    .. py:attribute:: total_bytes

    Total of bytes of storage.

    .. py:attribute:: free_bytes

    Bytes that are unused.

    .. py:attribute:: used_bytes

    Bytes that are used.

    .. py:attribute:: usage_percent

    Usage percentage.

    .. py:attribute:: dedup_ratio_percent

    Deduplication ratio as percentage, if available for this backend.
    100 means no deduplication, 200 means a 2:1 deduplication, values less
    than 100 indicate negative deduplication.  None if not available for
    this storage.
    '''

    __tablename__ = 'storage_usage'
    id = Column(Integer, primary_key=True)
    storage_id = Column(Integer, ForeignKey('storage.id'))
    storage = relationship(Storage, order_by=id, backref='usage')
    sample_date = Column(Date, nullable=False)
    total_bytes = Column(BigInteger, default=None)
    free_bytes = Column(BigInteger, default=None)
    used_bytes = Column(BigInteger, default=None)
    usage_percent = Column(SmallInteger, default=None)
    dedup_ratio_percent = Column(SmallInteger, default=None)

    def __init__(self):
        pass

    def __repr__(self):
        return '<StorageUsage(%s: %s@%s)>' % (self.id, self.storage_id,
                self.sample_date)
