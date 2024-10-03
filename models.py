from flask import Flask, jsonify, request
from flask_restful import Resource, Api

from datetime import date
from  datetime import datetime,timedelta
from dateutil import tz
from datetime import datetime as dt
import psycopg2

# Initialize time zone
to_zone = tz.gettz('Asia/Calcutta')


def get_db_connection():
    conn = psycopg2.connect(
        dbname='mydatabase',
        user='myuser',
        password='mypassword',
        host='98.81.58.20',
        port='5432'
    )
    return conn






