#!/usr/bin/env python
#
#  Copyright (c) 2012, Sean Reifschneider, tummy.com, ltd.
#  All Rights Reserved.

'''Database connection wrapper for network-attached-backup.
'''

from nabmodel import *


class DbWrapper:
    '''Wrapper around SQLAlchemy and NAB model.  For example:

        nabdb = DbWrapper()
        session = nabdb.session()
        session.add(Metadata())
        session.commit()

    Or:

        nabdb = DbWrapper()
        session = nabdb.connect(connect='sqlite:///:memory:', echo=True)
        session.add(Metadata())
        session.commit()
        session2 = nabdb.session()   # uses connection from above
        session2.add(Host([...]))
        session2.commit()
    '''

    def __init__(self):
        self.close()

    def session(self):
        '''Get a session handle.
        This returns a new Session() handle, calling `connect()` if it has
        not previously been called.  Note: The `connect()` method also
        returns a Session(), for convenience.  `connect()` will always make
        a new SQL connection from the ground up.  Call `session()` if you
        do not need to specify connection options.

        :rtype: SQLAlchemy Session() instance.
        '''

        if not self.Sessions:
            self.connect()

        return self.Sessions()

    def connect(self, path_list=None, connect=None, echo=False):
        '''Create a session to the database.
        The database connect string is read from a configuration file, and
        a SQLAlchemy Session() to that database is returned.

        :param list path_list: (Default None)  A list of file names to check
        for the database connect string.  If `path_list` is `None`, then a
        standard list of paths is used.  If NAB_DBCREDENTIALS environment
        variable is set, that is used for the credentials file.

        The `path_list` is walked, stopping when the listed file exists,
        and that is loaded as Python code.  Any files after the first
        existing file are ignored.

        :param str connect: (Default None)  If a string, the `path_list`
        will be ignored and this string will be used as the connect string.

        :param bool echo: (Default False)  Are database commands echoed
        to stdout?

        :rtype: SQLAlchemy Session() instance.
        '''
        import os
        import sys

        if path_list == None:
            if 'NAB_DBCREDENTIALS' in os.environ:
                path_list = [
                        os.path.expanduser(os.environ['NAB_DBCREDENTIALS'])]
            else:
                path_list = [
                        '/etc/network-attached-backup/dbcredentials',
                        'dbcredentials',
                        ]

        if connect == None:
            namespace = {}
            for path in path_list:
                if not os.path.exists(path):
                    continue
                execfile(path, {}, namespace)
                break
            else:
                sys.stderr.write('ERROR: Unable to find "dbcredentials" '
                        'file.\n')
                sys.exit(1)
            if not 'connect' in namespace:
                sys.stderr.write('ERROR: Could not find "connect" value in '
                        '"%s"\n' % path)
                sys.exit(1)
            connect = namespace['connect']

        from sqlalchemy import create_engine
        self.engine = create_engine(connect, echo=echo)

        self.Base = Base        # Base is from nabmodel
        self.Base.metadata.bind = self.engine

        from sqlalchemy.orm import sessionmaker
        self.Sessions = sessionmaker(bind=self.engine)

        return self.Sessions()

    def close(self):
        '''Clean up database object, return to brand-new state.

        :rtype: None
        '''
        self.engine = None
        self.Base = None
        self.Sessions = None


nabdb = DbWrapper()
