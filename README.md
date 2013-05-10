# SocialBot #

SocialBot is a webapp that lets you schedule tweets and facebook posts to be posted
at a later date. Use it to stagger your posts so that your friends don't get
sick of you! Or, alternatively, use it to advertise in an unobnoxious way, by
staggering sponsored posts. This app can also be used by by comapanies or even individuals
to manage their social media campaigns and schedule messages to their fans.

1. Running
2. Features
3. Code

## Running ##
Running the app is simple. Go to socialbot.herokuapp.com to access it. Click on
one of the big buttons to authenticate with either Facebook or Twitter. Then post away.

## Features ##

A lot of emphasis was put on making the app very easy to use and minimalistic. 

The app allows you to schedule posts for both Twitter and Facebook. A validation
check makes sure all tweets are under 140 characters. The app can post at any time in
the future, and can queue multiple posts for Twitter and Facebook.

All scheduled tweets are visible on the tweets page, just as all scheduled statuses
are visible on the Facebook page. These statuses and tweets can be edited or deleted
before they are published, in case the user changes his/her mind.

Once you have authorized the app with Facebook and Twitter, the app also automatically
signs you in if you are signed into both services on that computer.

## Code ##
The code is divided into app.py, scheduler.py and a series of templates for the
various webpages. app.py contains the methods that handle initial login and user
authentication, as well as the methods that add tweets and statuses to the SimpleDB
domain. It also contains the edit/delete methods for the tweets and statuses. The app maintains 
local dictionaries corresponding to the data in the database to minimize queries to the 
database and to make sure scheduled tweets, statuses display quickly.

scheduler.py contains the code responsible for posting at the scheduled times. Posting
at the exact times would be incredibly taxing, so instead scheduler.py queries the
database every 10 minutes, and checks if any posts were timed before the current time.
So it posts in waves separated by 10 minutes using Heroku's Scheduler.

The app uses uses Twitter Bootstrap for design and Jinja2 to populate the templates with data
and interact with the python code.

## TODO: ##
- Add support for different timezones
