from flask import Flask,render_template,request,redirect,url_for,flash,jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem, User
app = Flask(__name__)

from flask import session as login_session
import random
import string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

#end of import statements

#google plus login credentials
CLIENT_ID = json.loads(open('/var/www/restaurants/restaurants/client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Restaurant Project"


#database conncttion
engine = create_engine('postgresql://catalog:catalog@localhost/catalog')

#engine= create_engine('sqlite:///project_catalog_with_users.db')
Base.metadata.bind = engine
DBSession =sessionmaker(bind=engine)
session =DBSession()


#home page and restaurant list page
@app.route('/')
@app.route('/restaurants')
def restaurantList():
	restaurants=session.query(Restaurant).all()
	if 'username' not in login_session:
		return render_template('publicRestaurants.html',restaurants = restaurants)
	else:
		user_loggedin=login_session['username']
		user_picture=login_session['picture']
		return render_template('restaurants.html',restaurants=restaurants,user_loggedin=user_loggedin,user_picture=user_picture)

#login page
@app.route('/login')
def showLogin():
	state = ''.join(random.choice(string.ascii_lowercase + string.digits)for x in xrange(32))
	login_session['state']= state
	return render_template('login1.html', STATE = state)

#facebooklogin 
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token


    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('/var/www/restaurants/restaurants/fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]


    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.8/me"
    
    token = result.split(',')[0].split(':')[1].replace('"', '')

    url = 'https://graph.facebook.com/v2.8/me?access_token=%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
   
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    #  call to get user picture
    url = 'https://graph.facebook.com/v2.8/me/picture?access_token=%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    #result shown
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("You are now logged in as %s !" % login_session['username'])
    return output

#facebook logout
@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id,access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "You have successfully logged out!"

#google plus login
@app.route('/gconnect', methods=['POST'])
def gconnect():
	print("gconnect")
	if request.args.get('state') != login_session['state']:
		response = make_response(json.dumps('Invalid state parameter.'),402)
		response.headers['Content-Type'] = 'application/json'
		return response
	request.get_data()
	code =request.data.decode('utf-8')

	try:
		oauth_flow=flow_from_clientsecrets('client_secrets.json',scope = '')
		oauth_flow.redirect_uri = 'postmessage'
		credenetials = oauth_flow.step2_exchange(code)
	except FlowExchangeError:
		response =  make_response(json.dumps('failed to upgrade authorization code'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response
 	
 	#get access token from credentials
	access_token = credenetials.access_token
	url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
	h= httplib2.Http()
	response = h.request(url,'GET')[1]
	str_response = response.decode('utf-8')
	result = json.loads(str_response)


	if result.get('error') is not None:
		response = make_response(json.dumps(result.get('error')),500)
		response.headers['Content-Type'] = 'application/json'
		return response


	gplus_id = credenetials.id_token['sub']
	if result['user_id'] != gplus_id:
		response= make_response(json.dumps("token's user ID doesnt match with given user id"),401)
		response.headers['Content-Type'] = 'application/json'
		return response

	if result['issued_to'] != CLIENT_ID:
		response = make_response(json.dumps("token's client ID does not match app's."),401)
		response.headers['Content-Type'] = 'application/json'
		return response


	stored_access_token = login_session.get('access_token')
	stored_gplus_id = login_session.get('gplus_id')
	if stored_access_token is not None and gplus_id == stored_gplus_id:
		response = make_response(json.dumps('Current user is  already connected'),200)
		response.headers['Content-Type']= 'application/json'
		return response

	login_session['access_token']=access_token
	login_session['gplus_id']= gplus_id
	login_session['provider']= 'google'

	userinfo_url= "https://www.googleapis.com/oauth2/v1/userinfo"
	params = {'access_token':access_token, 'alt':'json'}
	answer =  requests.get(userinfo_url,params= params)

	data= answer.json()

	login_session['username']= data['name']
	login_session['picture']=data['picture']
	login_session['email']= data['email']

	#check if user exists ,if not create new user
	user_id = getUserID(login_session['email'])
	if not user_id:
		user_id = createUser(login_session)
	login_session['user_id'] = user_id

	output = ''
	output += '<h1>Welcome, '
	output += login_session['username']
	output += '!</h1>'
	output += '<img src="'
	output += login_session['picture']
	output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
	flash("You are now logged in as %s !" % login_session['username'])
	print "done!"
	return output

#common logout for third party providers
@app.route('/disconnect')
def disconnect():
	if 'provider' in login_session:
		if login_session['provider']=='google':
			gdisconnect()
			del login_session['access_token']
			del login_session['gplus_id']
		if login_session['provider']=='facebook':
			fbdisconnect()
			del login_session['facebook_id']
		del login_session['email']
		del login_session['username']
		del login_session['picture']
		del login_session['provider']
		del login_session['user_id']
		flash("You have successfully logged out!")
		return redirect(url_for('restaurantList'))
	else:
		flash("You have to login first to logout!")
		return redirect(url_for('restaurantList'))

#googleplus logout
@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response

#user function- create user, get user, get user id from user table in database
def createUser(login_session):
	newUser = User(name = login_session['username'], email = login_session['email'], picture=login_session['picture'])
	session.add(newUser)
	session.commit()
	user = session.query(User).filter_by(email= login_session['email']).one()
	return user.id

def getUserInfo(user_id):
	user = session.query(User).filter_by(id= user_id).one()
	return user

def getUserID(email):
	try:
		user = session.query(User).filter_by(email= email).one()
		return user.id
	except:
		return None

# add new restaurant
@app.route('/restaurants/new',methods=['GET', 'POST'])
def newRestaurant():
	print(login_session)
	all_restaurants=session.query(Restaurant).all()
	if 'username' not in login_session:
		return redirect('login')
	else:
		creator_name=login_session['username']
		creator_picture=login_session['picture']
		if request.method=='POST':
			newRest=Restaurant(name=request.form['restaurant_name'],user_id = login_session['user_id'])
			session.add(newRest)
			flash('New Restaurant %s successfully created!' % newRest.name)
			session.commit()
			return redirect(url_for('restaurantList'))
		else:
			return render_template('newRestaurant.html',creator_name=creator_name,all_restaurants=all_restaurants,creator_picture=creator_picture)

#show menu for selected restaurant
@app.route('/restaurants/<int:restaurant_id>/menu')
def restaurantMenu(restaurant_id):
	all_restaurants= session.query(Restaurant).all()
	restaurant=session.query(Restaurant).filter_by(id=restaurant_id).one()
	creator = getUserInfo(restaurant.user_id)
	menuitems=session.query(MenuItem).filter_by(restaurant_id=restaurant_id).all()
	if 'username' not in login_session or creator.id!=login_session['user_id']:
		return render_template('publicRestaurantMenu.html',restaurant_id = restaurant_id, items=menuitems,creator= creator,restaurant=restaurant,all_restaurants=all_restaurants)
	else:
		return render_template('restaurantMenu.html',restaurant_id=restaurant_id, items=menuitems,restaurant=restaurant,creator=creator,all_restaurants=all_restaurants)

#edit the selected restaurant
@app.route('/restaurants/<int:restaurant_id>/edit',methods=['GET','POST'])
def editRestaurant(restaurant_id):
	if 'username' not in login_session:
		return redirect('login')
	all_restaurants= session.query(Restaurant).all()
	editedRestaurant=session.query(Restaurant).filter_by(id=restaurant_id).one()
	creator = getUserInfo(editedRestaurant.user_id)
	if editedRestaurant.user_id != login_session['user_id']:
		flash("Sorry! You are not authorized to edit this restaurant!")
		return redirect(url_for('restaurantList'))
	if request.method=='POST':
		if request.form['restaurant_name']:
			editedRestaurant.name=request.form['restaurant_name']
			session.add(editedRestaurant)
			flash('Restaurant successfully edited %s !' % editedRestaurant.name)
			session.commit()
			return redirect(url_for('restaurantList'))
	else:
		return render_template('editRestaurant.html',restaurant_id=restaurant_id,restaurant=editedRestaurant,all_restaurants=all_restaurants,creator=creator)

# delete the selected restaurant
@app.route('/restaurants/<int:restaurant_id>/delete',methods=['GET','POST'])
def deleteRestaurant(restaurant_id):
	if 'username' not in login_session:
		return redirect('login')
	all_restaurants= session.query(Restaurant).all()
	deletedRestaurant=session.query(Restaurant).filter_by(id=restaurant_id).one()
	creator = getUserInfo(deletedRestaurant.user_id)
	if deletedRestaurant.user_id != login_session['user_id']:
		flash("Sorry! You are not authorized to delete this restaurant!")
		return redirect(url_for('restaurantList'))
	if request.method=='POST':
		session.delete(deletedRestaurant)
		flash('%s successfully deleted' % deletedRestaurant.name)
		session.commit()
		return redirect(url_for('restaurantList'))
	else:
		return render_template('deleteRestaurant.html', restaurant_id=restaurant_id,restaurant=deletedRestaurant,all_restaurants=all_restaurants,creator=creator)

#add menu item to selected restaurant
@app.route('/restaurants/<int:restaurant_id>/menu/new',methods=['GET','POST'])
def newMenuItem(restaurant_id):
	if 'username' not in login_session:
		return redirect('login')
	restaurant=session.query(Restaurant).filter_by(id=restaurant_id).one()
	all_menu_items = session.query(MenuItem).filter_by(restaurant_id=restaurant_id).all()
	creator = getUserInfo(restaurant.user_id)
	if login_session['user_id'] != restaurant.user_id:
		flash("Sorry! You are not authorized to add menu items to this restaurant. Please create your own restaurant in order to add items.")
		return redirect(url_for('restaurantMenu',restaurant_id=restaurant_id))
	if request.method=='POST':
		newMenuItem=MenuItem(name=request.form['item_name'],price=request.form['item_price'],description=request.form['item_desc'],course=request.form['item_course'],restaurant_id=restaurant_id,user_id = restaurant.user_id)
		session.add(newMenuItem)
		flash('New menu item - %s successfully added!' % newMenuItem.name)
		session.commit()
		return redirect(url_for('restaurantMenu',restaurant_id=restaurant_id))
	else:
		return render_template('newMenuItem.html',restaurant_id=restaurant_id,restaurant=restaurant,creator=creator,all_menu_items=all_menu_items)

#delete the selected menu item
@app.route('/restaurants/<int:restaurant_id>/<int:menu_id>/delete',methods=['GET','POST'])
def deleteMenuItem(restaurant_id,menu_id):
	if 'username' not in login_session:
		return redirect('login')
	all_menu_items = session.query(MenuItem).filter_by(restaurant_id=restaurant_id).all()
	restaurant=session.query(Restaurant).filter_by(id=restaurant_id).one()
	creator = getUserInfo(restaurant.user_id)
	deletedMenuItem=session.query(MenuItem).filter_by(id=menu_id).one()
	if login_session['user_id'] != restaurant.user_id:
		flash("Sorry! You are not authorized to delete menu items from this restaurant. Please create your own restaurant in order to delete items.")
		return redirect(url_for('restaurantMenu',restaurant_id=restaurant_id))
	if request.method=='POST':
		session.delete(deletedMenuItem)
		flash('Menu item - %s successfully deleted!' % deletedMenuItem.name)
		session.commit()
		return redirect(url_for('restaurantMenu',restaurant_id=restaurant_id))
	else:
		return render_template('deleteMenuItem.html',restaurant_id=restaurant_id,restaurant=restaurant,menu_id=menu_id,menuItem=deletedMenuItem,creator=creator,all_menu_items=all_menu_items)

#edit the selected menu item
@app.route('/restaurants/<int:restaurant_id>/<int:menu_id>/edit', methods=['GET','POST'])
def editMenuItem(restaurant_id,menu_id):
	if 'username' not in login_session:
		return redirect('login')
	all_menu_items = session.query(MenuItem).filter_by(restaurant_id=restaurant_id).all()
	restaurant=session.query(Restaurant).filter_by(id=restaurant_id).one()
	creator = getUserInfo(restaurant.user_id)
	editedMenuItem=session.query(MenuItem).filter_by(id=menu_id).one()
	if login_session['user_id'] != restaurant.user_id:
		flash("Sorry! You are not authorized to edit menu items of this restaurant. Please create your own restaurant in order to edit items.")
		return redirect(url_for('restaurantMenu',restaurant_id=restaurant_id))
	if request.method=='POST':
		if request.form['edited_menu_name']:
			editedMenuItem.name=request.form['edited_menu_name']
		if request.form['edited_menu_price']:
			editedMenuItem.price=request.form['edited_menu_price']
		if request.form['edited_menu_course']:
			editedMenuItem.course=request.form['edited_menu_course']
		if request.form['edited_menu_description']:
			editedMenuItem.description=request.form['edited_menu_description']
		session.add(editedMenuItem)
		flash('Menu item successfully edited!')
		session.commit()
		return redirect(url_for('restaurantMenu',restaurant_id=restaurant_id))
	else:
		return render_template('editMenuItem.html',menu=editedMenuItem,restaurant=restaurant,restaurant_id=restaurant_id,menu_id=menu_id,all_menu_items=all_menu_items,creator=creator)

# return json for tables in database - for restaurants,menu items, user
@app.route('/restaurants/json')
def restaurantsJson():
	restaurants = session.query(Restaurant).all()
	return jsonify(restaurants = [r.serialize for r in restaurants])

@app.route('/user/json')
def usersJson():
	users = session.query(User).all()
	return jsonify(users = [r.serialize for r in users])

@app.route('/restaurant/<int:restaurant_id>/menu/json')
def restaurantMenuJson(restaurant_id):
	restaurant= session.query(Restaurant).filter_by(id= restaurant_id).one()
	items =  session.query(MenuItem).filter_by(restaurant_id= restaurant_id).all()
	return jsonify(MenuItems = [i.serialize for i in items])

@app.route('/restaurant/<int:restaurant_id>/<int:menu_id>/itemJson')
def menuItemJson(restaurant_id,menu_id):
	menu_item = session.query(MenuItem).filter_by(id= menu_id).one()
	return jsonify(menu_item = menu_item.serialize)

if __name__=='__main__':
	app.secret_key = 'super_secret_key'
	app.debug= True
	app.run()
