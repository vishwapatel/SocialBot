import os
import boto
import uuid

from flask import Flask, render_template, send_from_directory

#----------------------------------------
# initialization
#----------------------------------------

app = Flask(__name__)

app.config.update(
)

sdb = boto.connect_sdb((os.environ['AWS_KEY'], os.environ['AWS_SECRET'])

domain = sdb.get_domain('socialbot')

#----------------------------------------
# controllers
#----------------------------------------

@app.errorhandler(404)
def page_not_found(e):
	return render_template('404.html'), 404

@app.route("/")
def index():
	return render_template('index.html')

#----------------------------------------
# facebook and twitter authentication
#----------------------------------------

from flask import url_for, request, session, redirect
from flask_oauth import OAuth

FACEBOOK_APP_ID = os.environ['FACEBOOK_APP_ID']
FACEBOOK_APP_SECRET = os.environ['FACEBOOK_APP_SECRET']

TWITTER_APP_ID = os.environ['TWITTER_APP_ID']
TWITTER_APP_SECRET = os.environ['TWITTER_APP_SECRET']

oauth = OAuth()

app.secret_key = os.environ['APP_SECRET_KEY']

facebook = oauth.remote_app('facebook',
	base_url='https://graph.facebook.com/',
	request_token_url=None,
	access_token_url='/oauth/access_token',
	authorize_url='https://www.facebook.com/dialog/oauth',
	consumer_key= '163882543775188',
	consumer_secret= '2dc0e273c4128ec9c6f593b06417db70',
	request_token_params={'scope': ('email, publish_actions')}
)

twitter = oauth.remote_app('twitter',
	base_url='https://api.twitter.com/1/',
	request_token_url='https://api.twitter.com/oauth/request_token',
	access_token_url='https://api.twitter.com/oauth/access_token',
	authorize_url='https://api.twitter.com/oauth/authenticate',
	consumer_key= TWITTER_APP_ID,
	consumer_secret=TWITTER_APP_SECRET
)

#---------------------------------------
# global variables
#---------------------------------------

tweets = {}
statuses = {}

@facebook.tokengetter
def get_facebook_token(token=None):
	""" Function for Flask-OAuth to get facebook oauth-token for posting on facebook"""
	return session.get('facebook_token')
	
@twitter.tokengetter
def get_twitter_token(token=None):
	""" Function for Flask-OAuth to get twitter oauth-token for posting on twitter."""   
	return session.get('twitter_token')

def pop_login_session():
	""" Function for deleting user session"""
	session.pop('logged_in', None)
	session.pop('facebook_token', None)
	session.pop('twitter_token', None)


@app.route("/facebook_login")
def facebook_login():
	""" Method for logging into Facebook. However, if you are already logged in,
		you are redirected immediately. Otherwise, you are sent to Facebook for
		authentication. 
	"""
	if get_facebook_token() is not None:

		item_iterator = domain.select("select * from socialbot where user_id = '" + session['facebook_user'] + "'")
		statuses[session['facebook_user']] = get_entries(item_iterator)

		update_facebook_token()
		return render_template('post_status.html', db = statuses[session['facebook_user']])
		
	return facebook.authorize(callback=url_for('facebook_authorized',
		next=request.args.get('next'), _external=True))

@app.route("/twitter_login")
def twitter_login():
	""" Method for logging into Twitter. However, if you are already logged in,
		you are redirected immediately. Otherwise, you are sent to Twitter for
		authentication. 
	"""
	if get_twitter_token() is not None:

		item_iterator = domain.select("select * from socialbot where user_id = '" + session['twitter_user'] + "'")
		tweets[session['twitter_user']] = get_entries(item_iterator)

		update_twitter_token()
		return render_template('post_tweet.html', db = tweets[session['twitter_user']])

	return twitter.authorize(callback=url_for('oauth_authorized',
		next=request.args.get('next') or request.referrer or None))

@app.route("/facebook_authorized")
@facebook.authorized_handler
def facebook_authorized(resp):
	""" Callback for Facebook authentication. If you are authenticated
		then you are redirected to the post_status page. 
	"""
	if resp is None or 'access_token' not in resp:
		return render_template('index.html')

	session['logged_in'] = True
	session['facebook_token'] = (resp['access_token'], '')

	data = facebook.get('/me').data
	session['facebook_user'] = data['id']

	item_iterator = domain.select("select * from socialbot where user_id = '" + session['facebook_user'] + "'")
	statuses[session['facebook_user']] = get_entries(item_iterator)

	update_facebook_token()

	return render_template('post_status.html', db = statuses[session['facebook_user']])

@app.route('/oauth_authorized')
@twitter.authorized_handler
def oauth_authorized(resp):
	""" Callback for Facebook authentication. If you are authenticated
		then you are redirected to the post_tweet page. 
	"""   
	next_url = request.args.get('next') or url_for('index')
	if resp is None:
		return render_template('index.html')

	session['logged_in'] = True
	session['twitter_token'] = (
		resp['oauth_token'],
		resp['oauth_token_secret']
	)
	session['twitter_user'] = resp['screen_name']

	current_user_item = domain.get_item(resp['screen_name'])

	item_iterator = domain.select("select * from socialbot where user_id = '" + session['twitter_user'] + "'")
	tweets[session['twitter_user']] = get_entries(item_iterator)

	update_twitter_token()

	return render_template('post_tweet.html', db = tweets[session['twitter_user']])

@app.route("/post_status", methods=['GET','POST'])
def post_status():
	"""
		Method called for scheduling facebook statuses
	"""
	item = domain.new_item(uuid.uuid4())
	item_iterator = domain.select("select * from socialbot where user_id = '" + session['facebook_user'] + "'")
	item['user_id'] = session['facebook_user']
	item['message'] = request.form['message']
	time_requested = request.form['time']

	date = time_requested.split()[0]
	time_of_date = time_requested.split()[1]

	year = date.split('/')[2]
	month = date.split('/')[1]
	day = date.split('/')[0]
	hours = time_of_date.split(':')[0]
	minutes = time_of_date.split(':')[1]
	seconds = time_of_date.split(':')[2]

	time = year + month + day + hours + minutes + seconds
	item['time'] = time
	item['type'] = 'facebook'
	item.save()

	statuses[session['facebook_user']].append((item['message'], item['time'], time_formatter(item['time'])))

	return render_template('post_status.html', message = "Sent successfully!" + str(request.form['time']), db = statuses[session['facebook_user']])

@app.route("/post_tweet", methods=['GET','POST'])
def post_tweet():
	"""
		Method called for scheduling Twitter tweets
	"""

	if len(request.form['message']) > 140 or len(request.form['message']) == 0:
		return render_template('post_tweet.html', message = "Error: Tweet length should be less than 140 and greater than 0")

	if len(request.form['time']) == 0:
		return render_template('post_tweet.html', message = "You haven't entered a scheduled time!")

	item = domain.new_item(uuid.uuid4())
	item['user_id'] = session['twitter_user']
	item['message'] = request.form['message']
	time_requested = request.form['time']

	date = time_requested.split()[0]
	time_of_date = time_requested.split()[1]

	year = date.split('/')[2]
	month = date.split('/')[1]
	day = date.split('/')[0]
	hours = time_of_date.split(':')[0]
	minutes = time_of_date.split(':')[1]
	seconds = time_of_date.split(':')[2]

	time = year + month + day + hours + minutes + seconds
	item['time'] = time
	item['type'] = 'twitter'
	item.save()

	tweets[session['twitter_user']].append((item['message'], item['time'], time_formatter(item['time'])))

	return render_template('post_tweet.html', message = "Scheduled successfully for " + str(request.form['time']), db = tweets[session['twitter_user']])

@app.route("/edit_tweet", methods=['GET', 'POST'])
def edit_tweet():
	"""
		Method called for editing a tweet
	"""
	button = request.form['action']
	item_iterator = domain.select("select * from socialbot where user_id = '" + session['twitter_user'] + "' and time = '" + request.form['t'] + "'")

	if button == 'delete':        
		try:
			domain.delete_item(item_iterator.next())
		except StopIteration:
			print "iteration stopped"

		item_iterator = domain.select("select * from socialbot where user_id = '" + session['twitter_user'] + "'", consistent_read = True)
		tweets[session['twitter_user']] = get_entries(item_iterator)
		return render_template('post_tweet.html', message = "Deleted successfully.", db = tweets[session['twitter_user']])

	elif button == 'edit':
		try:
			item = item_iterator.next()
			attributes = domain.get_attributes(item.name)
			attributes['message'] = request.form['editmessage']
			domain.put_attributes(item.name, attributes)
		except StopIteration:
			print "iteration stopped"

		item_iterator = domain.select("select * from socialbot where user_id = '" + session['twitter_user'] + "'", consistent_read = True)
		tweets[session['twitter_user']] = get_entries(item_iterator)
	return render_template('post_tweet.html', message = "Edited successfully.", db = tweets[session['twitter_user']])

@app.route("/edit_status", methods=['GET', 'POST'])
def edit_status():
	"""
		Method called for editing Facebook status
	"""
	button = request.form['action']
	item_iterator = domain.select("select * from socialbot where user_id = '" + session['facebook_user'] + "' and time = '" + request.form['t'] + "'")

	if button == 'delete':        
		try:
			domain.delete_item(item_iterator.next())
		except StopIteration:
			print "iteration stopped"

		item_iterator = domain.select("select * from socialbot where user_id = '" + session['facebook_user'] + "'", consistent_read = True)
		statuses[session['facebook_user']] = get_entries(item_iterator)
		return render_template('post_status.html', message = "Deleted successfully.", db = statuses[session['facebook_user']])

	elif button == 'edit':
		try:
			item = item_iterator.next()
			attributes = domain.get_attributes(item.name)
			attributes['message'] = request.form['editmessage']
			domain.put_attributes(item.name, attributes)
		except StopIteration:
			print "iteration stopped"
		try:
			statuses[session['facebook_user']].remove((request.form['oldmessage'], request.form['t'], time_formatter(request.form['t'])))
			statuses[session['facebook_user']].append((request.form['editmessage'], request.form['t'], time_formatter(request.form['t'])))
		except ValueError:
			item_iterator = domain.select("select * from socialbot where user_id = '" + session['facebook_user'] + "'")
			statuses[session['facebook_user']] = get_entries(item_iterator)
	return render_template('post_status.html', message = "Edited successfully.", db = statuses[session['facebook_user']])

def get_entries(iterator):
	"""
		Helper method for iterating over SimpleDB items and
		creating a dictionary from the relevant information
	"""
	entries = []
	for entry in iterator:
		entries.append((entry['message'], entry['time'], time_formatter(entry['time'])))
	return entries

def time_formatter(time):
	formatted_time = time[8:10] + ":" + time[10:12] + ":" + time[12:] + ', ' + time[6:8] + "/" + time[4:6] + "/" + time[0:4] 
	return formatted_time
	


def update_facebook_token():
	"""
		Method for updating the current user's Facebook token in the database
	"""
	current_user_item = domain.get_item(session['facebook_user'])
	if current_user_item is None:
		item = domain.new_item(session['facebook_user'])
		item['facebook_token'] = session['facebook_token'][0]
		item.save()
	elif current_user_item['facebook_token'] != session['facebook_token'][0]:
		attributes = {'facebook_token': session['facebook_token'][0]}
		domain.put_attributes(session['facebook_user'], attributes)

def update_twitter_token():
	"""
		Method for updating the current user's Twitter OAuth token in the db
	"""
	current_user_item = domain.get_item(session['twitter_user'])
	if current_user_item is None:
		item = domain.new_item(session['twitter_user'])
		item['oauth_token'] = session['twitter_token'][0]
		item['oauth_token_secret'] = session['twitter_token'][1]
		item.save()
	elif (current_user_item['oauth_token'] != session['twitter_token'][0] or 
		 current_user_item['oauth_token_secret'] != session['twitter_token'][1]):

		attributes = {'oauth_token': session['twitter_token'][0], 
					  'oauth_token_secret': session['twitter_token'][0]}
		domain.put_attributes(session['twitter_user'], attributes)


@app.route("/logout")
def logout():
	pop_login_session()
	return redirect(url_for('index'))
	
#----------------------------------------
# launch
#----------------------------------------

if __name__ == "__main__":
	port = int(os.environ.get("PORT", 5000))
	app.run(host='0.0.0.0', port=port)