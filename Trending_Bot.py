# Framework credits: twitterbot by thricedotted

import tweepy
from keys import keys
import logging
import time
import os

class TrendingTweepy:

    def __init__(self, conf_file='config'):
        self.config = {}
        self._config_bot(conf_file)
        # Authentication
        self.auth = tweepy.OAuthHandler(self.config['CONSUMER_KEY'], self.config['CONSUMER_SECRET'])
        self.auth.set_access_token(self.config['ACCESS_TOKEN'], self.config['ACCESS_TOKEN_SECRET'])
        self.auth.secure = True
        self.api = tweepy.API(self.auth)

        # Self details
        self.followers={}
        self.id = self.api.me().id
        self.screen_name = self.api.me().screen_name
        self.followers['existing'] = self.api.followers_ids(self.id)
        self.followers['new'] = []
        self.friends = self.api.friends_ids(self.id)

        # Tweepy bot state
        self.state = {}
        self.state['last_follow_check'] = 0
        self.state['last_tweet'] = 0
        self.state['Trending items'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Tile_log')
        self._follow_all()

        self.count = 0

        logging.basicConfig(format='%(asctime)s | %(levelname)s: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',
                            filename=self.screen_name + '.log',
                            level=logging.DEBUG)

        logging.info('Initializing bot...')

    def on_follow(self,f_id):
        """
        Follow back on being followed
        """
        try:
            self.api.create_friendship(f_id, follow=True)
            self.friends.append(f_id)
            logging.info('Followed user id {}'.format(f_id))
        except tweepy.TweepError as e:
            self._log_tweepy_error('Unable to follow user', e)

    def tweet_status_trends(self):
        """
        Tweets the top trending places
        """
        try:
            self.api.update_status('test'+str(self.count))
            self.count+=1
            self.state['last_tweet']=time.time()
        except tweepy.TweepError as e:
            self._log_tweepy_error('Can\'t update status because', e)

    def on_message(self): pass

    def update_subscribers(self): pass

    def _config_bot(self,file):
        with open(file,'r') as conf_file:
            for line in conf_file:
                try:
                    configuration,value=line.split('=')
                    self.config[configuration.strip()]=value.strip()
                except ValueError as e:
                    self._log_tweepy_error('Wrong configuration parameters', e)

        check_values = ['CONSUMER_KEY','CONSUMER_SECRET', 'ACCESS_TOKEN_SECRET', 'ACCESS_TOKEN']

        if len((check_values-self.config.keys())) != 0:
            raise Exception('The configuration file is missing parameters')

    def log(self, message, level=logging.INFO):
        if level == logging.ERROR:
            logging.error(message)
        else:
            logging.info(message)

    def _log_tweepy_error(self, message, e):
        try:
            e_message = e.message[0]['message']
            code = e.message[0]['code']
            self.log("{}: {} ({})".format(message, e_message, code), level=logging.ERROR)
        except:
            self.log(message, e)

    def _follow_all(self):
        """
        follows all followers on initialization
        """
        logging.info("Following back all followers....")
        try:
            self.followers['new']=list(set(self.followers['existing'])-set(self.friends))
            self._handle_followers()
        except tweepy.TweepError as e:
            self._log_tweepy_error('Can\'t follow back existing followers', e)


    def _check_followers(self):
        """
        Checks followers.
        """
        logging.info("Checking for new followers...")

        try:
            self.followers['new'] = [f_id for f_id in self.api.followers_ids(self.id) if f_id not in self.followers['existing']]
            self.state['last_follow_check'] = time.time()

        except tweepy.TweepError as e:
            self._log_tweepy_error('Can\'t update followers', e)


    def _handle_followers(self):
        """
        Handles new followers.
        """
        for f_id in self.followers['new']:
            self.on_follow(f_id)

    def run(self):
        """
        Runs the main tweepy smallbot
        """
        while True:
            # check followers every 1 minute
            if (time.time() - self.state['last_follow_check']) > 30:
                self._check_followers()
                self._handle_followers()

            # Tweet once every 24hours
            if (time.time() - self.state['last_tweet']) > 24*60:
                self.tweet_status_trends()


if __name__ == '__main__':
    smallbot = TrendingTweepy()
    smallbot.run()


