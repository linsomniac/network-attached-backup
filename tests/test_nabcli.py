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
        self.dbfile = '/tmp/nabtestdatabase'
        if os.path.exists(self.dbfile):
            os.remove(self.dbfile)

        os.environ['NAB_DBCREDENTIALSTR'] = 'sqlite:///%s' % self.dbfile
        nabdb.connect(connect='sqlite:///%s' % self.dbfile)
        nabdb.Base.metadata.create_all()

    def test_Basic(self):
        '''Test the nabcli for basic invocation ability.'''

        db = nabdb.session()
        model.schema_basic(db)

        with self.assertRaises(subprocess.CalledProcessError):
            subprocess.check_output([nabcmd])
        self.assertIn('Usage: nab', subprocess.check_output([nabcmd, 'help']))

        with open('/dev/null', 'w') as devnull:
            self.assertEqual(subprocess.check_call([nabcmd, 'hosts'],
                    stdout=devnull), 0)
        self.assertIn('client1.example.com',
                subprocess.check_output([nabcmd, 'hosts']))
        self.assertIn('client2.example.com',
                subprocess.check_output([nabcmd, 'hosts']))

    def test_InvocationErrors(self):
        '''Basic errors in the commands.'''

        r = nabsupp.run_command([nabcmd, 'unknowncommand'])
        self.assertEqual(r.exitcode, 1)
        self.assertIn('Unknown command', r.stderr)

        r = nabsupp.run_command([nabcmd, 'help'])
        self.assertEqual(r.exitcode, 0)
        self.assertEqual(r.stderr, '')

        r = nabsupp.run_command([nabcmd, '--debug', 'unknowncommand'])
        self.assertEqual(r.exitcode, 1)
        self.assertIn('Unknown command', r.stderr)

    def test_Initdb(self):
        '''Creation of the database.'''

        self.assertEqual(subprocess.check_call([nabcmd, 'initdb']), 0)
        os.remove(self.dbfile)
        self.assertEqual(subprocess.check_call([nabcmd, 'initdb']), 0)

    def test_CreateServer(self):
        '''Creation of a server.'''

        self.assertEqual(nabsupp.run_command([nabcmd, 'newserver']).exitcode,
                1)
        self.assertEqual(nabsupp.run_command([nabcmd, 'newserver', '-s', '3',
                '-y', 'auto', 'testserver.example.com']).exitcode, 0)
        self.assertEqual(nabsupp.run_command([nabcmd, 'listservers']).stdout,
                'testserver.example.com\n')

        #  try creating a second backup server
        c = nabsupp.run_command([nabcmd, 'newserver', '-s', '3',
                '-y', 'auto', 'testserver2.example.com'])
        self.assertEqual(c.exitcode, 1)
        self.assertTrue('already a backup server' in c.stderr)
        self.assertEqual(nabsupp.run_command([nabcmd, 'listservers']).stdout,
                'testserver.example.com\n')


print unittest.main()
