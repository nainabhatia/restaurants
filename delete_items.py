# coding: utf8
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem


engine= create_engine('sqlite:///project_catalog.db')
Base.metadata.bind = engine
DBSession =sessionmaker(bind=engine)
session =DBSession()

restaurants= session.query(Restaurant).all()
for restaurant in restaurants:
	session.delete(restaurant)

session.commit()

print("all items deleted")
