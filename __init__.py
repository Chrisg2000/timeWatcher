import threading

import Bot
import Moduleloader
import modules.timeWatcher.utils
from modules.timeWatcher.model_user import UserModel
from modules.timeWatcher.watchdog import WatchDog
from ts3 import Events

watchDog = None  # type: WatchDog
watchDogStopper = threading.Event()
bot = None
autoStart = True


@Moduleloader.setup
def watchdog_setup(ts3bot):
    global bot
    bot = ts3bot
    bot.ts3conn.instanceedit(serverinstance_serverquery_flood_commands=-1)
    if autoStart:
        start_watchdog()


@Moduleloader.exit
def watchdog_exit():
    global watchDog
    watchDogStopper.set()
    watchDog.join()
    watchDog = None


@Moduleloader.event(Events.ClientEnteredEvent, )
def client_enter(event: Events.ClientEnteredEvent):
    """
    Observer of ClientEnteredEvent
    Add user to watchdog's list, differentiate between user first connects and reconnects after timeout
    :param event: object of ClientEnteredEvent class
    """
    client_dbId = event.client_dbid
    if watchDog is not None and int(event.data['client_type']) is not 1:
        if client_dbId not in watchDog.users:
            watchDog.users[client_dbId] = UserModel(
                client_database_id=client_dbId,
                client_id=event.client_id,
                client_name=event.client_name,
                ts3conn=bot.ts3conn)
            watchDog.logger.info(
                '{} (id={}, dbId={}) connected'.format(event.client_name, event.client_id, client_dbId))
        else:
            watchDog.users[client_dbId].client_id.add(event.client_id)
            watchDog.users[client_dbId].update_names(event.client_name)
            watchDog.logger.info(
                '{} (id={}, dbId={}) reconnected'.format(event.client_name, event.client_id, client_dbId))


@Moduleloader.event(Events.ClientLeftEvent, )
def client_left(event: Events.ClientLeftEvent):
    """
    Observer of ClientLeftEvent
    Removes user from watchdog's list.
    Differentiate between user disconnecting and instance of client disconnecting
    :param event: object of ClientLeftEvent class
    """
    client_id = event.client_id
    if watchDog is not None and int(event.data['client_type']) is not 1:
        for user_key in watchDog.users:
            user = watchDog.users[user_key]
            if client_id in user.client_id and len(user.client_id) <= 1:
                watchDog.logger.info('User with id={} disconnected'.format(event.client_id))
                del watchDog.users[user_key]
            elif client_id in user.client_id and len(user.client_id) >= 1:
                watchDog.logger.info('Instance of User with id={} disconnected'.format(event.client_id))
                user.client_id.remove(client_id)


@Moduleloader.command('startwatchdog', 'watchdogstart', 'watchdog')
def start_watchdog(sender=None, msg=None):
    """
    Start the WatchDog by clearing the watchDogStopper signal and staring it
    Can also be used as manual command to start the WatchDog
    :param sender: in case of command usage, client of starter
    :param msg: in case of command usage, complete command
    """
    global watchDog
    if watchDog is None:
        watchDog = WatchDog(watchDogStopper, bot.ts3conn)
        watchDogStopper.clear()
        watchDog.start()


@Moduleloader.command('stopwatchdog', 'watchdogstop')
def stop_watchdog(sender=None, msg=None):
    """
    Stop the WatchDog by setting the watchDogStoppert signal and undefining it
    Can also be used as manual command to stop the WatchDog
    :param sender: in case of command usage, client of stopper
    :param msg: in case of commmand usage, complete command
    """
    global watchDog
    watchDogStopper.set()
    watchDog = None


@Moduleloader.command('updateview')
def command_update_view(sender=None, msg=None):
    """
    Function of command 'updateview' which updates the description of client(s)
    can be used in different ways: 1. Update view of :param: sender or 2. update view of all clients
    :param sender: client_id of sender
    :param msg: complete command
    """
    if watchDog is not None:
        for model_key in watchDog.users:
            user = watchDog.users[model_key]
            if sender in user.client_id or 'all' in msg:
                watchDog.users[model_key].update_view()


@Moduleloader.command('mytime', 'time')
def command_mytime(sender=None, msg=None):
    """
    Function of command 'mytime' which updates the online time and send the user a message with info
    :param sender: client_id of sender
    :param msg: complete command
    """
    if watchDog is not None:
        for model_key in watchDog.users:
            user = watchDog.users[model_key]
            if str(sender) in user.client_id:
                user.update_time()
                resp = bot.ts3conn.clientdbinfo(cldbid=user.client_database_id)
                client_totalconnections = resp['client_totalconnections']
                Bot.send_msg_to_client(
                    ts3conn=bot.ts3conn,
                    clid=sender,
                    msg='Du warst bis jetzt {}'.format(utils.time_view(
                        total_online=user['client_online_time'],
                        n_connections=client_totalconnections,
                        record_time=user['stat_record_time']
                    ))
                )


@Moduleloader.command('toptime', 'top')
def command_toptime(sender=None, msg=None):
    if watchDog is not None:
        watchDog.update_time()
        resp = bot.ts3conn.clientdblist()
        stat_times = {}
        for client in resp:
            if client['client_unique_identifier'] != 'ServerQuery':
                re = bot.ts3conn.custominfo(cldbid=client['cldbid'])
                for x in re:
                    if x['ident'] == 'client_online_time':
                        stat_times[client['client_nickname']] = int(x['value'])
                        break

        ranking = sorted(stat_times.items(), key=lambda x: x[1], reverse=True)

        Bot.send_msg_to_client(
            bot.ts3conn,
            sender,
            '\n'.join(
                ['{:5d}.   {:10s}   {:8s}'.format(i, name, utils.sec_to_str(time))
                 for i, (name, time) in enumerate(ranking, 1)]
            ))
