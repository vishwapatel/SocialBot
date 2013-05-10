import boto
import datetime
from flask import Flask
from flask_oauth import OAuth


FACEBOOK_APP_ID = os.environ['FACEBOOK_APP_ID']
FACEBOOK_APP_SECRET = os.environ['FACEBOOK_APP_SECRET']

TWITTER_APP_ID = os.environ['TWITTER_APP_ID']
TWITTER_APP_SECRET = os.environ['TWITTER_APP_SECRET']

oauth = OAuth()

app = Flask(__name__)

app.config.update(
)

app.secret_key = os.environ['APP_SECRET_KEY']

facebook = oauth.remote_app('facebook',
    base_url='https://graph.facebook.com/',
    request_token_url=None,
    access_token_url='/oauth/access_token',
    authorize_url='https://www.facebook.com/dialog/oauth',
    consumer_key= FACEBOOK_APP_ID,
    consumer_secret= FACEBOOK_APP_SECRET,
    request_token_params={'scope': ('email, publish_actions')}
)

twitter = oauth.remote_app('twitter',
    base_url='https://api.twitter.com/1/',
    request_token_url='https://api.twitter.com/oauth/request_token',
    access_token_url='https://api.twitter.com/oauth/access_token',
    authorize_url='https://api.twitter.com/oauth/authenticate',
    consumer_key= TWITTER_APP_ID,
    consumer_secret= TWITTER_APP_SECRET
)

sdb = boto.connect_sdb((os.environ['AWS_KEY'], os.environ['AWS_SECRET'])

domain = sdb.get_domain('socialbot')

@facebook.tokengetter
def get_facebook_token(token=None):
	user = domain.get_item(token)
	if user is None:
		raise Exception
	return (user['facebook_token'], '')
    
@twitter.tokengetter
def get_twitter_token(token=None):
	user = domain.get_item(token)
	if user is None:
		raise Exception
	print user.name
	return (user['oauth_token'], user['oauth_token_secret'])

def main():
	"""
		This method checks in the database if there are any tweets
		or statuses scheduled for the next 10 minutes. If there are,
		it posts those one by one.

	"""
	now = datetime.datetime.now()
	future = (now + datetime.timedelta(minutes = 10)).strftime("%Y%m%d%H%M%S")
	item_iterator = domain.select("select * from socialbot where time < '" + str(future) + "'")
	
	for item in item_iterator:
		print str(item)
		user = item['user_id']
		if item['type'] == 'facebook':
			resp = facebook.post('/me/feed', data = {'message': item['message']}, token = user)
			if resp.status != 200:
				print "Woops, something went wrong when trying to post this status #{item['message']}"
		else:
			resp = twitter.post('statuses/update.json', data={'status': item['message']}, token = user)
			if resp.status != 200:
				print "Woops, something went wrong when trying to post this tweet #{item['message']}"

		domain.delete_item(item)

if __name__ == "__main__":
	main()





