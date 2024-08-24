import os
import multiprocessing
workers = 3
chdir = "/root/Erps/erpfinal/erp/"
bind = '127.0.0.1:8000'
wsgi_app = "core.wsgi:application"
timeout = 300
accesslog = os.path.join(chdir, "logs/application/access.log")
errorlog = os.path.join(chdir, "logs/application/error.log")
pidfile = '/var/run/gunicorn.pid'

