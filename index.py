#!/usr/bin/env python
# coding: utf-8

from gevent import monkey; monkey.patch_all()
from bottle import route, run, template, redirect, request, response, default_app
from xml.dom.minidom import Document
from lxml import etree, html
from readability.readability import Document as readableDocument

import os
import gevent
import feedparser
import StringIO
import requests
import logging
import json
import time

__user_agent__ = 'happy happy bot 0.1 by /u/hewigovens'
__fetch_interval__ = 3600
__last_timestamp__ = 0
__last_burt_rss__ = None

MIME_TEMPLATE = {
    'image/jpeg': """<img width="100" height="100" alt="__placeholder__" src="__placeholder__">""",
    'image/png': """<img width="100" height="100" alt="__placeholder__" src="__placeholder__">""",
    'application/pdf': """<object data="__placehoder__" type="application/pdf" width=100% height=100%>
        alt : <a href="__placehoder__">__placehoder__</a>
    </object>"""
}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)


def parse_reddit_rss(reddit_rss_url, minimum_score):
    feed = feedparser.parse(reddit_rss_url)
    reddit_itmes = []
    feed_info = {
        'title': feed['channel']['title'],
        'link': feed['channel']['link'],
        'description': feed['channel']['description']
    }

    for item in feed['items']:
        text = StringIO.StringIO('<html>%s</html>' % item['description'])
        tree = etree.parse(text)
        ref_link = tree.xpath('//a[text()="[link]"]/@href')
        reddit_itmes.append(
            {
                'ref_link': ''.join(ref_link),
                'ref_title': item['title'],
                'link': item['link']
            }
        )
    filter_with_score(reddit_itmes, minimum_score)
    return reddit_itmes, feed_info


def burn_rss(reddit_rss_url, minimum_score):
    global __last_burt_rss__
    global __last_timestamp__
    if int(time.time()) - __last_timestamp__ > __fetch_interval__:
        reddit_items, feed_info = parse_reddit_rss(reddit_rss_url, minimum_score)

        jobs = [gevent.spawn(fetch_article, item['ref_link']) for item in reddit_items]
        gevent.joinall(jobs, timeout=15)

        for job in jobs:
            index = jobs.index(job)
            if not job.value:
                reddit_items[index]['content'] = '<a href="%s">%s</a>' % (reddit_items[index]['ref_link'], reddit_items[index]['ref_link'])
            else:
                reddit_items[index]['content'] = job.value

        __last_burt_rss__ = construct_feed(reddit_items, feed_info)
        __last_timestamp__ = int(time.time())

    return __last_burt_rss__


def construct_feed(reddit_items, feed_info):
    doc = Document()

    full_rss = doc.createElement('rss')
    full_rss.setAttribute('version', '2.0')

    channel = doc.createElement('channel')
    full_rss.appendChild(channel)

    title = doc.createElement('title')
    title.appendChild(doc.createTextNode(feed_info['title']))
    channel.appendChild(title)

    link = doc.createElement('link')
    link.appendChild(doc.createTextNode(feed_info['link']))
    channel.appendChild(link)

    description = doc.createElement('description')
    description.appendChild(doc.createTextNode(feed_info['description']))
    channel.appendChild(description)

    for i in reddit_items:
        item = doc.createElement('item')
        title = doc.createElement('title')
        title.appendChild(doc.createTextNode(i['ref_title']))

        link = doc.createElement('link')
        link.appendChild(doc.createTextNode(i['ref_link']))

        guid = doc.createElement('guid')
        guid.appendChild(doc.createTextNode(i['link']))

        description = doc.createElement('description')
        description.appendChild(doc.createCDATASection(i['content']))

        item.appendChild(title)
        item.appendChild(link)
        item.appendChild(guid)
        item.appendChild(description)

        channel.appendChild(item)

    doc.appendChild(full_rss)
    return doc.toxml()


def filter_with_score(reddit_itmes, minimum_score):
    remove_list = []
    for item in reddit_itmes:
        score = fetch_reddit_score(item['ref_link'])
        if score < minimum_score:
            remove_list.insert(0, reddit_itmes.index(item))
        else:
            item['score'] = score
    for index in remove_list:
        reddit_itmes.pop(index)


def fetch_reddit_score(ref_link):
    reddit_info_api_url = r'http://www.reddit.com/api/info.json?url=%s' % ref_link
    headers = {'User-Agent': __user_agent__}
    try:
        data = requests.get(reddit_info_api_url, timeout=10, headers=headers).text
    except requests.ConnectionError:
        logging.warning('query reddit info api failed:%s' % ref_link)
        #let it go...
        return 1000
    try:
        link_info = json.loads(data)
        return link_info['data']['children'][0]['data']['score']
    except (ValueError, IndexError, KeyError):
        logging.warning('error json response')
        return 0


def fetch_article(url):
    try:
        headers = {'User-Agent': __user_agent__}
        response = requests.get(url, timeout=10, headers=headers)

        content_type = response.headers['Content-Type']

        if content_type in MIME_TEMPLATE:
            html_template = MIME_TEMPLATE[content_type]
            return html.tostring(html_template.replace('__placeholder__', url))
        else:
            readable_article = readableDocument(response.text)
            readable_summary = readable_article.summary()
            readable_summary_html = html.fromstring(readable_summary)
            body = readable_summary_html.xpath('/html/body/div')[0]
            #readable_text = readable_summary_html.text_content()
            return html.tostring(body)
    except Exception as e:
        logging.error(e.message)
        return '<a href="%s">%s</a>' % (url, url)

# Routes

@route('/')
def index():
    return template('templates/index')


@route('/add/')
def add_url():
    topic = request.query.get('topic')
    minimum_score = request.query.get('minimum_score')
    if not topic:
        topic = r'programming'
    if not minimum_score:
        minimum_score = '25'
    return redirect('/reddit/%s/%s' % (topic, minimum_score))


@route('/reddit/<topic>/<minimum_score:int>')
def full_reddit_rss(topic, minimum_score):
    reddit_rss_url = (r'http://www.reddit.com/r/%s/.rss' % topic)
    response.set_header('Content-Type', 'application/xml')
    return burn_rss(reddit_rss_url, minimum_score)

if __name__ == '__main__':
    run(host='0.0.0.0', port=int(os.environ.get('PORT', 8088)), server='gevent')

app = default_app()
