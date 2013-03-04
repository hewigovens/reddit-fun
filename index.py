#!/usr/bin/env python
# coding: utf-8
from gevent import monkey
monkey.patch_all()
from bottle import route, run, template, redirect, request, response
from xml.dom.minidom import Document
from lxml import etree, html
from readability.readability import Document as readableDocument
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
    articles = []

    # print feed['items'][0]

    for item in feed['items']:
        text = StringIO.StringIO('<html>%s</html>' % item['description'])
        tree = etree.parse(text)
        a = tree.xpath('//a[text()="[link]"]/@href')
        articles.append((''.join(a), item['title']))

    # print articles

    jobs = [gevent.spawn(
        fetch_article, article[1], article[0]) for article in articles]
    gevent.joinall(jobs, timeout=8)

    doc = Document()

    full_rss = doc.createElement('rss')
    full_rss.setAttribute('version', '2.0')

    channel = doc.createElement('channel')
    full_rss.appendChild(channel)

    title = doc.createElement('title')
    title.appendChild(doc.createTextNode(feed['channel']['title']))
    channel.appendChild(title)

    link = doc.createElement('link')
    link.appendChild(doc.createTextNode(feed['channel']['link']))
    channel.appendChild(link)

    description = doc.createElement('description')
    description.appendChild(doc.createTextNode(feed['channel']['description']))
    channel.appendChild(description)

    for index in xrange(len(jobs)):
        if jobs[index].successful():

            i = feed['items'][index]
            item = doc.createElement('item')
            title = doc.createElement('title')
            title.appendChild(doc.createTextNode(i['title']))

            link = doc.createElement('link')
            link.appendChild(doc.createTextNode(i['link']))

            guid = doc.createElement('guid')
            guid.appendChild(doc.createTextNode(i['link']))

            description = doc.createElement('description')
            description.appendChild(doc.createCDATASection(jobs[index].value))

            item.appendChild(title)
            item.appendChild(link)
            item.appendChild(guid)
            item.appendChild(description)

            channel.appendChild(item)

    doc.appendChild(full_rss)
    return doc.toxml()


def fetch_article(title, url):
    try:
        #logging.info('start fetch %s: %s' % (title, url))
        headers = {'User-Agent': 'happy happy bot 0.1 by /u/hewigovens'}
        data = requests.get(url, timeout=5, headers=headers).text

        readable_article = readableDocument(data)
        readable_summary = readable_article.summary()

        readable_summary_html = html.fromstring(readable_summary)
        body = readable_summary_html.xpath('/html/body/div')[0]
        # readable_text = readable_summary_html.text_content()

        return html.tostring(body)
    except Exception as e:
        logging.error(e.message)
        return ""


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
    run(host='0.0.0.0', port=int(os.environ.get('PORT', 8088)), server='gevent')
