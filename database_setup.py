import sys
from sqlalchemy import Column,ForeignKey,Integer,String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()
class User(Base):
	__tablename__ ='user'

	id = Column(Integer,primary_key = True)
	name = Column(String(200),nullable=False)
	email= Column(String(250),nullable=False)
	picture =Column(String(250))

	@property
	def serialize(self):
		return{
			'id':self.id,
			'name':self.name,
			'email':self.email,
			'picture':self.picture
		}

class Restaurant(Base):
	__tablename__='restaurant'
	name=Column(String(100), nullable= False)
	id=Column(Integer, primary_key = True)
	user = relationship(User)
	items= relationship('MenuItem',cascade='all,delete')
	user_id = Column(Integer,ForeignKey('user.id'))
	

	@property
	def serialize(self):
		return {
			'name': self.name,
			'id': self.id,
			'user_id':self.user_id
		}

class MenuItem(Base):
	__tablename__='menu_item'
	name=Column(String(100),nullable=False)
	id = Column(Integer, primary_key = True)
	course = Column(String(100))
	description = Column(String(300))
	price = Column(String(10))
	restaurant_id = Column(Integer, ForeignKey('restaurant.id'))
	restaurant=relationship('Restaurant')
	user = relationship(User)
	user_id = Column(Integer,ForeignKey('user.id'))
	

	@property
	def serialize(self):
		return {
			'name':self.name,
			'description':self.description,
			'id':self.id,
			'price':self.price,
			'course':self.course,
			'user_id':self.user_id
		}


engine= create_engine('sqlite:///project_catalog_with_users_2.db')
Base.metadata.create_all(engine)
