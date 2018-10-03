import logging
from threading import Thread
from typing import Dict

from modules.timeWatcher import UserModel

updateInterval = 5  # Unit: Minutes


class WatchDog(Thread):
    """
    WatchDog class. Updates online time for every client
    """
    logger = logging.getLogger('timeWatchdog')
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler('watchdog.log', mode='a+')
    formatter = logging.Formatter('Time Watchdog %(asctime)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.info('Configured time logger')
    logger.propagate = 0

    def __init__(self, event, ts3conn):
        """
        Create new WatchDog object
        :param event: Event to signalize the WatchDog to stop updating
        :type event: threading.Event
        :param ts3conn: Connection to use
        :type ts3conn TS3Connection:
        """
        Thread.__init__(self)
        self.stopped = event
        self.ts3conn = ts3conn
        self.users: Dict[str, UserModel] = {}
        self._populate_users()

    def run(self):
        """
        Thread run method. Starts the watchdog
        """
        WatchDog.logger.info('TimeWatchDog Thread started')
        while not self.stopped.wait(updateInterval * 60.0):
            WatchDog.logger.debug('TimeWatchDog running')
            self.update_nicknames()
            self.update_time()
            self.commit()

    def commit(self):
        """
        commits all changes of the usermodel to ts3server
        """
        for model_key in self.users:
            self.stopped.wait(1.0)
            self.users[model_key].commit()

    def update_time(self):
        """
        Starts updating the total time of client
        """
        for model_key in self.users:
            self.users[model_key].update_time()

    def update_nicknames(self):
        """
        Starts updating the nicknames of any client
        """
        resp = self.ts3conn.clientlist('uid')
        for user in resp:
            if int(user['client_type']) is not 1:
                client_dbId = user['client_database_id']
                self.users[client_dbId].update_names(
                    user['client_nickname'])

    def _populate_users(self):
        """
        Supposed to only be called once
        Scans the server for users and putting them into user_list
        """
        resp = self.ts3conn.clientlist('uid')
        for user in resp:
            if int(user['client_type']) is not 1:  # sort out serverquery users
                self.users[user['client_database_id']] = UserModel(
                    client_database_id=user['client_database_id'],
                    client_id=user['clid'],
                    client_name=user['client_nickname'],
                    ts3conn=self.ts3conn)
                self.logger.info(
                    '{} (id={}, dbId={}) added to users'.format(
                        user['client_nickname'], user['clid'], user['client_database_id']))
