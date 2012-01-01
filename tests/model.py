#!/usr/bin/env python
#
#  Copyright (c) 2011, Sean Reifschneider, tummy.com, ltd.
#  All Rights Reserved.

#  allow the test to be run from the "tests" or "tests" parent directory
import sys
import os
if os.path.basename(os.getcwd()) == 'tests':
	sys.path.append('..')
else:
	sys.path.append('.')

import unittest
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


	def test_Metadata(self):
		db = self.Session()
		c1 = Metadata()
		db.add(c1)
		db.commit()

		#  verify that we can't insert another configuration entry
		with self.assertRaises(Exception):
			c2 = Metadata()
			db.add(c2)
			db.commit()
		db.rollback()

		#  verify that only one record is there
		self.assertEqual(len(db.query(Metadata).all()), 1)

		config = Metadata.get(db)
		self.assertEqual(config.id, 1)


suite = unittest.TestLoader().loadTestsFromTestCase(TestModel)
unittest.TextTestRunner(verbosity = 2).run(suite)
