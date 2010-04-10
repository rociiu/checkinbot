# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
from datetime import datetime
import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext.webapp import xmpp_handlers
import re
_DEBUG = True

def string_strip(_str):
    after_strip = re.sub('^ *| *$', '', _str)
    return after_strip

class CheckIn(db.Model):
	checkin_at  = db.DateTimeProperty(auto_now_add=True)
	checkout_at = db.DateTimeProperty()
	note        = db.StringProperty()
	email       = db.StringProperty()
	
	def checkout(self):
		self.checkout_at = datetime.now()
		self.put()
	
class BaseRequestHandler(webapp.RequestHandler):
  """Supplies a common template generation function.

  When you call generate(), we augment the template variables supplied with
  the current user in the 'user' variable and the current webapp request
  in the 'request' variable.
  """
  def generate(self, template_name, template_values={}):
    values = {
      'request': self.request,
      'user': users.get_current_user(),
      'login_url': users.create_login_url(self.request.uri),
      'logout_url': users.create_logout_url(self.request.uri),
      'application_name': 'Checkin Bot',
    }
    values.update(template_values)
    directory = os.path.dirname(__file__)
    path = os.path.join(directory, os.path.join('templates', template_name))
    self.response.out.write(template.render(path, values, debug=_DEBUG))
  
  def head(self, *args):
    pass
  
  def get(self, *args):
    pass
    
  def post(self, *args):
    pass
  

class MainHandler(BaseRequestHandler):
	
  def get(self):
	user = users.get_current_user()
	if not user:
	    self.redirect('/login?return_url=' + str(self.request.uri) )
	    return
	checkins  = CheckIn.gql("WHERE email = :email AND checkout_at = NULL order by checkin_at DESC", email=user.email() )
	checkouts = CheckIn.gql("WHERE email = :email AND checkout_at != NULL order by checkout_at DESC", email=user.email() )
	self.generate('index.html', { 'checkins':checkins.fetch(10), 'checkouts':checkouts.fetch(10) })

class LoginHandler(BaseRequestHandler):
	
  def get(self):
	user = users.get_current_user()
	if	user:
		self.redirect("/")
  	self.generate('login.html', {})


class CreateHandler(BaseRequestHandler):

  def get(self):
  	self.generate('login.html', {})

  def post(self):
	check_in      = CheckIn()
	check_in.note = self.request.get('content')
	check_in.email = users.get_current_user().email()
	check_in.put()
  	self.redirect("/")

class CheckoutHandler(BaseRequestHandler):
	
	def post(self):
		check_in = CheckIn.get(self.request.get('key'))
		check_in.checkout()
		self.redirect("/")

class XmppHandler(xmpp_handlers.CommandHandler):
	
	def unhandled_command(self, message=None):
		message.reply("unknow command")
	
	def list_command(self, message=None):
		email = message.sender.split('/')[0]
		checkins  = CheckIn.gql("WHERE email = :email AND checkout_at = NULL order by checkin_at DESC", email=email )
		reply_msg = ""
		#for checkin in checkins.fetch(1):
		#  reply_msg += str(checkin.key().id()) + " : " + checkin.note + "\n"
		for checkin in checkins.fetch(10):
		    reply_msg += str(checkin.key().id()) + " : " + checkin.note + "\n"
		
		if len(reply_msg) == 0:
			reply_msg = "No checkins exist."
		
		message.reply(reply_msg)
	
	def checkout_command(self, message=None):
		checkin_id = string_strip(message.arg)
		checkin = CheckIn.get_by_id( int(checkin_id) )
		checkin.checkout()
		message.reply("Checked out (#" + str( checkin.key().id() ) +") " + checkin.note )

	def checkin_command(self, message=None):
		email = message.sender.split('/')[0]
		check_in       = CheckIn()
		check_in.note  = message.arg
		check_in.email = email
		check_in.put()
		
		message.reply("Just checked in : (#" +  str( check_in.key().id() ) + ") " + check_in.note)
	
	def wahaha_command(self, message=None):
		message.reply("我们的祖国是花园!!")
	
	def help_command(self, message=None):
		help_msg = ""
		help_msg += "/checkin your check note \n"
		help_msg += "/checkout checkin_id \n"
		help_msg += "/list list all your checkins \n"
		help_msg += "Visit checkinbot.appspot.com for web interface."
		message.reply(help_msg)
	
	def text_message(self, message=None):
		email = message.sender.split('/')[0]
		message.reply("Ya Me De!!!")

def main():
  application = webapp.WSGIApplication( [
 				('/', MainHandler), 
				('/login', LoginHandler), 
				('/create', CreateHandler), 
				('/checkout', CheckoutHandler),
				('/_ah/xmpp/message/chat/', XmppHandler)
				],
                debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()
