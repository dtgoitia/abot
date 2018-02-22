# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import enum

import aiopg.sa as asa
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as psa
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import functions

from mosbot import config


class utcnow(functions.FunctionElement):  # noqa
    key = 'utcnow'
    type = sa.DateTime(timezone=True)


@compiles(utcnow, 'postgresql')
def _pg_utcnow(element, compiler, **kwargs):
    return "(statement_timestamp() AT TIME ZONE 'utc')::TIMESTAMP WITH TIME ZONE"


def sqlite_get_engine():
    return sa.create_engine('sqlite:///songs.sqlite3')


def create_sqlite_db():
    engine = sa.create_engine('sqlite:///songs.sqlite3')
    metadata.create_all(engine)


sqlite_metadata = sa.MetaData()

SongsHistory = sa.Table('song_history', sqlite_metadata,
                        sa.Column('id', sa.Integer, primary_key=True),
                        sa.Column('played', sa.Integer, unique=True),
                        sa.Column('skipped', sa.Boolean),
                        sa.Column('username', sa.Text),
                        sa.Column('song', sa.Text),
                        )

metadata = sa.MetaData()

User = sa.Table('user', metadata,
                sa.Column('id', sa.Integer, primary_key=True),
                sa.Column('dtid', sa.Text, unique=True),
                sa.Column('username', sa.Text),
                sa.Column('country', sa.Text),
                )


class Origin(enum.Enum):
    youtube = 1
    soundcloud = 2


Track = sa.Table('track', metadata,
                 sa.Column('id', sa.Integer, primary_key=True),
                 sa.Column('length', sa.Integer),
                 sa.Column('origin', psa.ENUM(Origin)),
                 sa.Column('extid', sa.Text),
                 sa.Column('name', sa.Text),
                 sa.UniqueConstraint('origin', 'extid')
                 )

Playback = sa.Table('playback', metadata,
                    sa.Column('id', sa.Integer, primary_key=True),
                    sa.Column('track_id', sa.ForeignKey('track.id')),
                    sa.Column('user_id', sa.ForeignKey('user.id')),
                    sa.Column('start', sa.DateTime, unique=True),
                    )


class Action(enum.Enum):
    skip = 1
    upvote = 2
    downvote = 3


UserAction = sa.Table('user_action', metadata,
                      sa.Column('id', sa.Integer, primary_key=True),
                      sa.Column('ts', sa.DateTime),
                      sa.Column('playback_id', sa.ForeignKey('playback.id')),
                      sa.Column('user_id', sa.ForeignKey('user.id'), nullable=True),
                      sa.Column('action', psa.ENUM(Action)),
                      )

ENGINE = None


async def get_engine():
    global ENGINE
    if ENGINE:
        return ENGINE
    ENGINE = await asa.create_engine(config.DATABASE_URL)
    return ENGINE