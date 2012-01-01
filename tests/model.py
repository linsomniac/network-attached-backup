#!/usr/bin/env python
#
#  Copyright (c) 2011, Sean Reifschneider, tummy.com, ltd.
#  All Rights Reserved.

import unittest
import sys
sys.path.append('..')
from nabmodel import *
	
class TestModel(unittest.TestCase):
	@classmethod
	def setUp(self):
		from sqlalchemy import create_engine
		self.engine = create_engine('sqlite:///:memory:')
		Base.metadata.create_all(self.engine)
		Base.metadata.bind = self.engine

		from sqlalchemy.orm import sessionmaker
		self.Session = sessionmaker(bind = self.engine)


	def test_Config(self):
		db = self.Session()
		c1 = Config()
		c1.errors_mail_address = 'user@example.com'
		db.add(c1)
		db.commit()

		#  verify that we can't insert another configuration entry
		with self.assertRaises(Exception):
			c2 = Config()
			c2.errors_mail_address = 'test@example.com'
			db.add(c2)
			db.commit()
		db.rollback()

		#  verify that only one record is there
		self.assertEqual(len(db.query(Config).all()), 1)

		config = Config.get(db)
		self.assertEqual(config.errors_mail_address, 'user@example.com')


suite = unittest.TestLoader().loadTestsFromTestCase(TestModel)
unittest.TextTestRunner(verbosity = 2).run(suite)
