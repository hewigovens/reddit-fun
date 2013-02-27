#!/usr/bin/env python
# coding: utf-8
from gevent import monkey; monkey.patch_all()
from bottle import route, run, template, redirect, request, response
from lxml import etree
# from readability.readability import Document
import os

import gevent
import feedparser
import StringIO
import requests
import logging

logging.basicConfig(
    level=logging.DEBUG, format='%(levelname)s - %(asctime)s %(message)s',
    datefmt='[%b %d %H:%M:%S]')


def parse_rss(url):

    feed = feedparser.parse(url)
    articles = {}

    # print feed['items'][0]

    for item in feed['items']:
        text = StringIO.StringIO('<html>%s</html>' % item['description'])
        tree = etree.parse(text)
        a = tree.xpath('//a[text()="[link]"]/@href')
        articles[''.join(a)] = item['title']

    # print articles

    jobs = [gevent.spawn(fetch_article, articles[url], url) for url in articles.keys()]
    gevent.joinall(jobs, timeout=8)

    full_rss = etree.Element('rss', attrib={'version': '2.0'})
    channel = etree.SubElement(full_rss, 'channel')

    title = etree.SubElement(channel, 'title')
    title.text = feed['channel']['title']

    link = etree.SubElement(channel, 'link')
    link.text = feed['channel']['link']

    description = etree.SubElement(channel, 'description')
    description.text = feed['channel']['description']

    for index in xrange(len(jobs)):
        if jobs[index].value:

            i = feed['items'][index]
            item = etree.Element('item')
            title = etree.Element('title')
            title.text = i['title']

            link = etree.Element('link')
            link.text = i['link']

            guid = etree.Element('guid')
            guid.text = i['link']

            description = etree.Element('description')
            description.text = r'<![CDATA[ %s ]]' % jobs[index].value

            item.append(title)
            item.append(link)
            item.append(guid)
            item.append(description)

            channel.append(item)

    root = etree.ElementTree(full_rss)
    return etree.tostring(root)


def fetch_article(title, url):
    try:
        logging.info('start fetch %s: %s' % (title, url))
        headers = {'User-Agent': 'happy happy bot 0.1 by /u/hewigovens'}
        data = requests.get(url, timeout=5, headers=headers).text

        return data
        # readable_article = Document(data)
        # readable_summary = readable_article.summary()
        # readable_summary_html = html.fromstring(readable_summary)
        # readable_text = readable_summary_html.text_content()

        # return readable_text
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
        response.set_header('Content-Type', 'application/xml')
        return parse_rss(url)


if __name__ == '__main__':
    run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
