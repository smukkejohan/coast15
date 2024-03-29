#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  2015 giulio <giulioungaretti@me.com> johan <public@jhoan.cc>
"""
scrape le data
"""
from bs4 import BeautifulSoup
import requests
import requests_cache
from datetime import datetime
from datetime import timedelta
from urlparse import urlparse, parse_qs
from decimal import *

import pymongo
from pymongo import MongoClient, GEO2D

requests_cache.install_cache('tide_cache')

client = MongoClient('localhost', 27017)

db = client.uk_tide
locations = db.locations
tide_logs = db.tide_logs

def get_data_for_date(date=None):

    if date is None:
        date = datetime.today()

    # append date to url  YYYYMMDD -20150516
    base_url = "http://www.tidetimes.org.uk"
    req  = requests.get(base_url + "/all", verify=False)


    soup = BeautifulSoup(req.text)

    listEl = soup.find(id="allports")
    for el in listEl.find_all('a'):
        loc_url = el.get('href')

        url = base_url+loc_url+"-"+date.strftime("%Y%m%d")
        req = requests.get(url, verify=False)

        soup = BeautifulSoup(req.text)
        table = soup.find('table', attrs={'id':'tidetimes'})

        name = soup.title.string[0:-len(" Tide Times | Tide Times")]
        #name = url[1:-len("-tide-times")]

        print(url)
        print("Tide time for: " + name + " on " + date.strftime("%Y%m%d"))

        # looks like
        # https://www.google.com/maps/embed/v1/place?
        # key=AIzaSyCgQfiN2Un_MS06vMa0b4vS-73hw1U0xLA
        # &q=60.5,-1.5667
        # &zoom=12
        # &center=60.5,-1.5667

        iframe_map = soup.find('iframe', attrs={'id':'gmap_small'})
        embed_google_map = iframe_map.get('src')
        qs = parse_qs(urlparse(embed_google_map)[4])
        latlng = qs['center'][0].split(',');

        lat = latlng[0]
        lng = latlng[1]
        print("latitude: " + lat + ", longitude: " + lng)

        locations.update({"name": name}, {"$set": {"latlng": [float(lat), float(lng)]}}, True) #upsert
        location = locations.find_one({"name": name})

        for row in table.find_all("tr"):
            cells = row.find_all("td")

            if len(cells) == 3:
                label = cells[0].find(text=True)

                if label == "Low Tide" or label == "High Tide":
                    time = cells[1].find(text=True)
                    height = cells[2].find(text=True)[1:-2] # remove parentheses and m

                    t = datetime.strptime(time, "%H:%M")
                    logDate = date.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)

                    #log = tide_logs.find_one({"timestamp": logDate, "location": location_id})
                    tide_logs.update({"timestamp": logDate, "location": location['_id']}, {"$set": {"type": label, "height": float(height)}}, True) #upsert

                    print(label + " at " + logDate.strftime("%Y%m%d - %H:%M") + " water was at " + height + "m")


if __name__ == "__main__":
    # fetch 5 days ahead and 5 days back in time
    for day in range(-5,5):
        get_data_for_date(datetime.today() + timedelta(days=day))


