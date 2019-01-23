# -*- encoding: utf-8 -*-

import time
import os
from module.logger import *
import json
import urllib
import urllib2
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

class UserTweetsSpider(object):
    def __init__(self, log):

        self._log = log

	# 用户唯一uid
        self._uid = 6560077196

	# 抓取内容存储成的文件名
        self._file_name = "./蠢左爱造谣.html"

	# 入口页抓取时间间隔
        self._homepage_interval = 3

	# 入口页抓取超时时间
        self._homepage_timeout = 10

	# 入口页抓取失败之后尝试多少次就终止抓取
        self._homepage_try_times = 10

	# 长微博抓取时间间隔
        self._longtext_interval = 11

	# 长微博抓取超时时间
        self._longtext_timeout = 10

	# 记录本次抓取的总个数,体现到日志里
        self._fetch_count = 0

	# 第几页开始抓，初始为第1页
        self._page = 1

	# 模拟用户抓取的用户cookie，会过期，过期后需要更新，获取方式见文档
        self._cookie = 'SINAGLOBAL=6078190065934.757.1507434455417; wb_cmtLike_1669574884=1; Ugrow-G0=5b31332af1361e117ff29bb32e4d8439; SSOLoginState=1542785251; wvr=6; TC-V5-G0=6fd5dedc9d0f894fec342d051b79679e; _s_tentry=login.sina.com.cn; Apache=2938205969198.1157.1542785253453; ULV=1542785253502:57:2:1:2938205969198.1157.1542785253453:1541061455490; TC-Page-G0=0dba63c42a7d74c1129019fa3e7e6e7c; wb_view_log_1669574884=2560*14401; YF-V5-G0=9717632f62066ddd544bf04f733ad50a; YF-Page-G0=c6cf9d248b30287d0e884a20bac2c5ff; SCF=As_9i-YsER57coA13wUVbBo3c1VMsj8WXG-OsvKkCUhA8PuGwK84iCzTDQY-POZeRkPIs7CUNtHnFB7bsSx3GuA.; SUB=_2A2528gJqDeRhGedI7VsU9yrEwziIHXVVhnSirDV8PUNbmtAKLVbSkW9NVsjJS6CMnCcKniDSAu_P7O_VUO3gHYac; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9Wh25X9NMEX5BzP5daxxbBcN5JpX5KMhUgL.Fo2cSo.fS0BR1hB2dJLoIEBLxKML1h.LBK.LxKML1K5L1hqLxK.L1-qLBoeLxKBLBo.L1K5t; SUHB=0N2kQfJPVyhmOm; ALF=1574413754; UOR=,www.weibo.com,fdc.longcity.net'

	# 每次启动时，清空上一次抓取的内容，所以如需保存，需要先备份
        os.system('rm -rf %s' % self._file_name) 

    # 爬虫启动
    def run(self):

	#  失败后尝试次数
	try_times = 0
        while True:
            if self._get_page_tweets(self._page) == False:
		try_times += 1
		if try_times >= self._homepage_try_times:
                    self._log.debug("%d page fetched after %d times try" % (self._page, try_times))
              	    self._page += 1
 		    try_times = 0
	    else:
                self._page += 1
 		try_times = 0


    def _get_page_tweets(self, page):

        # 入口页
        url = 'https://m.weibo.cn/api/container/getIndex?uid=%d&luicode=20000174&featurecode=20000320&type=uid&value=%d&containerid=107603%d&page=%d' % (self._uid, self._uid, self._uid, page)

        time.sleep(self._homepage_interval)

        self._log.debug("homepage url %s" % url)

        try:
            user_agent = "Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)"
            headers = {"User-Agent": user_agent, "Host":"m.weibo.cn"}
            request = urllib2.Request(url, headers = headers)
            response = urllib2.urlopen(request, timeout = self._homepage_timeout)
            content = response.read()
            json_obj = json.loads(content)

            if json_obj['ok'] != 1:
                self._log.error("homepage get err, ok code: %s" % json_obj['ok'])
                return False

            cards = json_obj['data']['cards']

            for card in cards:
                # 9表示普通微博
                if card['card_type'] != 9:
                    self._log.debug("this tweet is an adevertisement card type %s" % card['card_type'] )
                    continue
                tweet_str = card['mblog']['created_at'] + ':<br/>'

                # 补全长长微博内容
                if card['mblog']["isLongText"] == True:
                        self._log.debug("tweet is long text id:%s" % card['mblog']['id'])
                        tweet_str += self._get_long_tweets(card['mblog']['id'])
                else:
                    tweet_str += card['mblog']['text']

                if card['mblog'].has_key('pics') and (len(card['mblog']['pics']) > 0):
                    tweet_str += '<br/>'
                    for pic in card['mblog']['pics']:
                        tweet_str += '<img src="' +pic['url'] + '">'

                # 补全转发原博内容
                if card['mblog'].has_key('retweeted_status'):
                    retweet = card['mblog']['retweeted_status']
                    tweet_str += "//@" +  retweet['user']['screen_name'] + ":"
                    if retweet["isLongText"] == True:
                        self._log.debug("retweet is long text id:%s" % retweet['id'])
                        tweet_str += self._get_long_tweets(retweet['id'])
                    else:
                        tweet_str += retweet['text']

                    if retweet.has_key('pics') and (len(retweet['pics']) > 0):
                        tweet_str += '<br/>'
                        for pic in retweet['pics']:
                            tweet_str += '<img src="' +pic['url'] + '">'

                self._save_tweet(tweet_str)
                self._fetch_count += 1
                self._log.debug("第%d条 tweet content: %s" % (self._fetch_count, tweet_str))

            return True

        except Exception, e:
            self._log.error("homepage get except %s" % e)

    # 抓取长微博内容
    def _get_long_tweets(self, tweet_id):
        url = "https://m.weibo.cn/statuses/extend?id=%s" % tweet_id

        time.sleep(self._longtext_interval)

        try:
            #user_agent = "Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)"
            user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36"
            headers = {"User-Agent": user_agent, "Cookie":self._cookie, "Host":"m.weibo.cn", "Referer":url, "Accept-Language":"zh-CN,zh;q=0.9,en;q=0.8"}
            request = urllib2.Request(url, headers = headers)
            response = urllib2.urlopen(request, timeout = self._longtext_timeout)
            content = response.read()
            json_obj = json.loads(content)

            if json_obj['ok'] == 1:
                if json_obj['data']['ok'] == 1:
                    return json_obj['data']['longTextContent']
            return ""

        except Exception, e:
            self._log.error("=============== %s" % (url))
            self._log.error("long tweets get except %s" % e)
            return ""

    # 保存微博内容
    def _save_tweet(self, tweet_str):
        with open(self._file_name, 'a+') as f:
            f.write(tweet_str)
            f.write("<br/>--------------------------------------------------<br/><br/>")

if __name__ == "__main__":
    log_path = "./logs/"
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    root_logger = init_logger(log_path + "root.log")

    spider = UserTweetsSpider(root_logger)
    spider.run()
