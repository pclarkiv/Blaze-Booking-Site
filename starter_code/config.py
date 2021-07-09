import os
SECRET_KEY = os.urandom(32)
# Grabs the folder where the script runs.
basedir = os.path.abspath(os.path.dirname(__file__))

# Enable debug mode.
DEBUG = True

# Connect to the database

# TODO IMPLEMENT DATABASE URL
SQLALCHEMY_DATABASE_URI = 'postgres://fhxlfxikvgzcyl:8d24f7a4391f7f186c469b979ef9a829da372f95c28e3b218958268a3ea3c77f@ec2-54-158-232-223.compute-1.amazonaws.com:5432/d33696mespvvav'
SQLALCHEMY_TRACK_MODIFICATIONS = False
