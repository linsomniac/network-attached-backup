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
os.environ['PYTHONPATH'] = sys.path[-1]
for bindir in ['bin', '../bin']:
    nabcmd = os.path.join(bindir, 'nab')
    if os.path.exists(nabcmd):
        break
else:
    sys.stderr.write('Unable to find "nab" command.\n')
    sys.exit(1)

import unittest
import subprocess
import model
from nabdb import *


class TestNabCli(unittest.TestCase):
    def setUp(self):
        dbfile = '/tmp/nabtestdatabase'
        if os.path.exists(dbfile):
            os.remove(dbfile)

        os.environ['NAB_DBCREDENTIALSTR'] = 'sqlite:///%s' % dbfile
        nabdb.connect(connect='sqlite:///%s' % dbfile)
        nabdb.Base.metadata.create_all()

    def test_Basic(self):
        '''Test the nabcli for basic invocation ability.'''

        db = nabdb.session()
        model.schema_basic(db)

        with self.assertRaises(subprocess.CalledProcessError):
            subprocess.check_output([nabcmd])
        subprocess.check_output([nabcmd, 'help'])
        subprocess.check_call([nabcmd, 'hosts'])


print unittest.main()
