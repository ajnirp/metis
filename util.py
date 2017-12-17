import datetime
import os

def ts(datetime_obj):
    return datetime_obj.strftime('%y%m%d %H:%M')

def check_db_exists(message):
    db_path = 'db/{}.db'.format(message.server.id)
    return os.path.exists(db_path)