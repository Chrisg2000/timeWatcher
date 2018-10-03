import time

from modules.timeWatcher import utils


class UserModel(object):

    def __init__(self, client_database_id, client_id, client_name, ts3conn):
        ts3conn.customset(cldbid=client_database_id, ident='last_joined', value=round(time.time()))
        resp = ts3conn.custominfo(cldbid=client_database_id)

        self._user = {
            'client_online_time': 0,
            'stat_record_time': 0,
            'client_nicknames': {client_name},
        }
        self.client_id = {client_id}
        self.client_database_id = client_database_id
        self.client_recent_name = ''
        self.stat_time = time.time()
        self.stat_record_time = 0
        self.ts3conn = ts3conn

        for x in resp:
            ident = x['ident']
            value = eval(x['value'])
            self._user[ident] = value

        self.update_names(client_name)

    def update_and_commit(self):
        self.update_time()
        self.commit()

    def commit(self):
        for prop in self._user:
            self.ts3conn.customset(cldbid=self.client_database_id, ident=prop, value=repr(self._user[prop]))

    def update_time(self):
        abs_time = round(time.time() - self.stat_time)
        self.stat_time = time.time()
        self._user['client_online_time'] += abs_time

        self.stat_record_time += abs_time
        if self.stat_record_time > self._user['stat_record_time']:
            self._user['stat_record_time'] = self.stat_record_time

    def update_names(self, name):
        self._user['client_nicknames'] |= {name}
        self.client_recent_name = name

    def update_view(self):
        resp = self.ts3conn.clientdbinfo(cldbid=self.client_database_id)
        client_totalconnections = resp['client_totalconnections']

        msg = utils.description_view(
            nickname=self.client_recent_name,
            total_online=self._user['client_online_time'],
            n_connections=client_totalconnections,
            record_time=self._user['stat_record_time']
        )

        self.ts3conn.clientdbedit(cldbid=self.client_database_id, client_description=msg)

    def __getitem__(self, item):
        return self._user[item]

    def __setitem__(self, key, value):
        self._user[key] = value

    def __del__(self):
        self.update_and_commit()
        self.update_view()
