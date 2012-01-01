#!/usr/bin/env python
#
#  Copyright (c) 2011, Sean Reifschneider, tummy.com, ltd.
#  All Rights Reserved.

from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy.orm import relationship, backref


class Config(Base):
	__tablename__ = 'config'
	id = Column(Integer, primary_key = True)
	errors_mail_address = Column(String)
	database_version = Column(Integer)

	def __init__(self):
		self.id = 1
		self.database_version = 1

	def __repr__(self):
		return '<Config(id=%s, dbver=%s)>' % ( self.id, self.database_version )

	@classmethod
	def get(cls, session):
		return session.query(Config).filter(Config.id == 1)[0]


class Host(Base):
	__tablename__ = 'hosts'
	id = Column(Integer, primary_key = True)
	hostname = Column(String)

	def __init__(self):
		pass

	def __repr__(self):
		return '<Host(%s)>' % ( self.hostname, )


class HostConfig(Base):
	__tablename__ = 'host_configs'
	id = Column(Integer, primary_key = True)
	host_id = Column(Integer, ForeignKey('hosts.id'))
	host = relationship(Host, order_by = id, backref = 'configs')

	def __init__(self):
		pass

	def __repr__(self):
		return '<HostConfig(%s)>' % ( self.id, )
