#!/usr/bin/env python
#
#  Copyright (c) 2011, Sean Reifschneider, tummy.com, ltd.
#  All Rights Reserved.

'''Database model for network-attached-backup.'''

from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy.orm import relationship, backref


class Metadata(Base):
    '''Global information about the installation.
    There is only one row in this table.
    '''

    __tablename__ = 'config'
    id = Column(Integer, primary_key = True)
    database_version = Column(Integer)

    def __init__(self):
        self.id = 1
        self.database_version = 1

    def __repr__(self):
        return '<Config(id=%s, dbver=%s)>' % ( self.id, self.database_version )

    @classmethod
    def get(cls, session):
        '''Return an instance of the meta-data record.
        There is only one meta-data record, this function returns it.

        :param session: Database session instance, used to access the Metadata.
        '''
        return session.query(Metadata).filter(Metadata.id == 1)[0]


class Host(Base):
    '''A backed-up host.

    .. py:attribute:: hostname

    Name of the host to be backed up.  This is also used in the rsync
    command-line, so it needs to be the name that SSH knows the host as.
    '''

    __tablename__ = 'hosts'
    id = Column(Integer, primary_key = True)
    hostname = Column(String)

    def __init__(self):
        pass

    def __repr__(self):
        return '<Host(%s)>' % ( self.hostname, )


class HostConfig(Base):
    '''Configurable values for the backed-up hosts.
    A :py:class:HostConfig that does not reference a :py:class:Host is a
    global configuration, which other hosts use if they have not overridden
    those values.

    .. py:attribute:: host

    Reference to the :py:class:Host: that this record corresponds to, or None
    for the default configuration record.

    .. py:attribute:: alerts_mail_address

    E-mail address to send messages to when there is something that needs
    human attention.
    '''

    __tablename__ = 'host_configs'
    id = Column(Integer, primary_key = True)
    host_id = Column(Integer, ForeignKey('hosts.id'))
    host = relationship(Host, order_by = id, backref = 'configs')
    errors_mail_address = Column(String)

    def __init__(self):
        pass

    def __repr__(self):
        return '<HostConfig(%s)>' % ( self.id, )
