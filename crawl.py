# coding=UTF-8
# Copyright (C) 2019 yongming <yongming_zhu@berkeley.edu>

import json
import os
import re
import requests
from queue import Queue
from threading import Thread
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities


urls = Queue()
thread_count = 4
timeout_second = 20

print("Loading URLs...")

# check all the urls, if some are badly formed, do not add it to our queue
with open('urls.txt') as f:
    while True:
        line = f.readline()
        if not line:
            break
        if line.startswith('#'):
            continue
        url = line.rstrip('\n')
        try:
            request = requests.get(url)
            urls.put(url)
        except:
            print("badly formed URL: %s" % url)

print("Loading Complete")

# set up the user agent
caps = DesiredCapabilities.PHANTOMJS
caps["phantomjs.page.settings.userAgent"] = \
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) \
     AppleWebKit/537.36 (KHTML, like Gecko) \
     Chrome/78.0.3904.108 \
     Safari/537.36"

# define the thread
def worker(arg):

    # open one file for each thread
    f = open("%s.result" % arg, 'w')

    # set up the web driver
    driver = webdriver.PhantomJS(desired_capabilities=caps)

    # set the timeout
    driver.set_page_load_timeout(timeout_second)

    while True:
        # get one URL from the queue
        url = urls.get()

        # if the queue is empty, exit
        if url is None:
            driver.quit()
            f.close()
            break

        print('Analyzing %s' % url)

        # get the page content
        try:
            driver.get(url)
        except:
            print("Timeout, give up. %s" % url)
            urls.task_done()
            continue
        page_source = driver.page_source

        result = {}

        # ios
        ios = re.search("https?://apps.apple.com/app/.*?/id(\d+)",
                        page_source)
        if ios is not None:
            result['ios'] = ios.group(1)
        else:
            ios = re.search("https?://itunes.apple.com/.*?/id(\d+)",
                            page_source)
            if ios is not None:
                result['ios'] = ios.group(1)

        # google
        google = re.search("https?://play.google.com/store/apps"
                           "/details\?.*?id=([\w\.]+)",
                           page_source)
        if google is not None:
            result['google'] = google.group(1)

        # twitter
        twitters = re.findall("https?://(www.)?twitter.com/(.*?)\"",
                              page_source)
        for twitter in twitters:
            if '?' not in twitter[1]:
                result['twitter'] = twitter[1].rstrip("/")

        # facebook
        facebooks = re.findall("https?://(www.)?facebook.com/(.*?)\"",
                               page_source)
        for facebook in facebooks:
            if '?' not in facebook[1]:
                result['facebook'] = facebook[1].rstrip("/")

        # output the result and write it into a file
        json_result = json.dumps(result, indent=4)
        f.write("\"%s\":\n" % url)
        f.write(json_result)
        f.write(",\n")
        urls.task_done()


if __name__ == '__main__':

    # start
    threads = []
    for i in range(thread_count):
        t = Thread(target=worker, args=(i,))
        t.start()
        threads.append(t)

    urls.join()

    # stop
    for i in range(thread_count):
        urls.put(None)

    for t in threads:
        t.join()

    # combine the results
    os.system("echo { > instances.json")
    os.system("cat *.result >> instances.json")
    os.system("rm *.result")
    os.system("sed '$s/,$//g' instances.json > instances.json1")
    os.system("echo } >> instances.json1")
    os.system("mv instances.json1 instances.json")
