import time


def description_view(nickname, total_online, n_connections, record_time) -> str:
    return \
        '{0} war bis jetzt {1}'.format(
            nickname,
            time_view(total_online, n_connections, record_time)
        )


def time_view(total_online, n_connections, record_time) -> str:
    return \
        '{0} online\n ' \
        '(max. {1}, Ø {2})'.format(
            sec_to_str(total_online),
            record_time,
            sec_to_str(total_online / int(n_connections))
        )


def sec_to_str(sec) -> str:
    return time.strftime('%H:%M:%S', time.gmtime(sec))
