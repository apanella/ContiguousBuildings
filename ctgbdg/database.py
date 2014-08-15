import os
import re
from flask import request
import psycopg2
from sqlalchemy import create_engine, types
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.declarative import declarative_base
from psycopg2.extensions import adapt, register_adapter, AsIs

engine = create_engine(os.environ['DB_CONN'], convert_unicode=True)
session = scoped_session(sessionmaker(bind=engine,
                                      autocommit=False,
                                      autoflush=False))
Base = declarative_base()
Base.query = session.query_property()
