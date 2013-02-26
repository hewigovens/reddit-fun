#!/usr/bin/env python
# coding: utf-8
from gevent import monkey; monkey.patch_all()
from bottle import route, run, template, redirect, request, response
from lxml import etree, html
from readability.readability import Document
import os

import gevent
import feedparser
import StringIO
import requests
import PyRSS2Gen
import logging

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(asctime)s %(message)s', datefmt='[%b %d %H:%M:%S]')

def parse_rss(url):

    feed = feedparser.parse(url)
    articles = {}

    #print feed['items'][0]

    for item in feed['items']:
        text = StringIO.StringIO('<html>%s</html>' % item['description'])
        tree = etree.parse(text)
        a = tree.xpath('//a[text()="[link]"]/@href')
        articles[''.join(a)] = item['title']

    #print articles

    jobs = [gevent.spawn(fetch_article, articles[url], url) for url in articles.keys()]
    gevent.joinall(jobs, timeout=8)

    full_items = []
    for index in xrange(len(jobs)):
        if jobs[index].value:
            item = feed['items'][index]
            full_items.append(PyRSS2Gen.RSSItem(title=item['title'],
                                                link=item['link'],
                                                description=jobs[index].value,
                                                guid=PyRSS2Gen.Guid(item['link']),
                                                pubDate=item['published']))

    full_feed = PyRSS2Gen.RSS2(title=feed['channel']['title'],
                               link=feed['channel']['link'],
                               description=feed['channel']['description'],
                               items=full_items)

    #full_feed.write_xml(open('1.xml','w'))
    return full_feed.to_xml(encoding="utf-8")

def fetch_article(title,url):
    try:
        logging.info('start fetch %s: %s' % (title, url))
        headers={'User-Agent':'happy happy bot 0.1 by /u/hewigovens'}
        data = requests.get(url, timeout=5, headers=headers).text

        readable_article = Document(data)
        readable_summary = readable_article.summary()
        readable_summary_html = html.fromstring(readable_summary)
        readable_text = readable_summary_html.text_content()

        return readable_text
    except Exception as e:
        logging.error(e.message)
        return None


@route('/')
def index():
    return template('templates/index')

@route('/add/')
def add_url():
    # url = request.forms.get('url')
    topic = request.query.get('topic')
    if not topic:
        topic = r'programming'
    return redirect('/reddit/%s' % topic)

@route('/reddit/:topic')
def full_topic(topic):
    if topic:
        url = (r'http://www.reddit.com/r/%s/.rss' % topic)
        response.set_header('Content-Type','application/xml')
        return parse_rss(url)


if __name__ == '__main__':
    run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
