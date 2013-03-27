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
import subprocess


class TestSupp(unittest.TestCase):

    def test_Syslog(self):
        '''Test syslog-related functions.'''

        import nabsupp

        nabsupp.setup_syslog()

        tmpfilename = '/tmp/nabsyslogexceptiontest'
        if os.path.exists(tmpfilename):
            os.remove(tmpfilename)

        try:
            subprocess.check_output(['python', 'helper_supp_except',
                    tmpfilename], stderr=subprocess.STDOUT)
            self.fail('Return-code of helper_supp_except was not error')
        except subprocess.CalledProcessError, e:
            self.assertEqual(e.returncode, 1)
            self.assertEqual(e.output.find('ValueError: Testing') >= 0, True)
            with open(tmpfilename, 'r') as fp:
                data = fp.read()
                self.assertEqual(data.find('ValueError: Testing') >= 0, True)
                self.assertEqual(data, e.output)


print unittest.main()
