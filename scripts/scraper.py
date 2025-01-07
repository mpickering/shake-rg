#! /usr/bin/env nix-shell
#! nix-shell -i python3 shell.nix


from selenium import webdriver
#from selenium import selenium
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from os.path import basename, splitext
import time
import json


from pyvirtualdisplay import Display

import sys
import os
import subprocess
from urllib.request import urlretrieve, urlopen
from bs4 import BeautifulSoup
import pickle
import hashlib
import collections

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


output_path = sys.argv[1]
world_files = sys.argv[2]

def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text

def remove_suffix(text, prefix):
    if text.endswith(prefix):
        return text[:-len(prefix)]
    return text

# World file is always in projection EPSG:4326
def write_world_file(filename, world_dict):
    world_filename = splitext(filename)[0] + ".pgw"
    f = open(os.path.join(output_dir, world_filename), "w")
    def write_line(key):
        f.write("%.30f\n" % world_dict[key])
    for index in ['A', 'D', 'B', 'E', 'C', 'F']:
        write_line(index)
    f.close()

manual_list = { "clok.routegadget.co.uk/gadget/" : "clok"
              , "https://routegadget.fvo.org.uk/" : "fvo"
              , "nocuk.org/gadget/" : "noc"
              , "nocuk.org/gadget/rg2/index.php" : "noc"
               , "http://rg.cascadeoc.org/" : "cascadeoc"
              , "helgao.com/routegadget/" : "helgao"
               , "http://rg.mtfsz.hu/" : "mtfszhu"
               , "ardoc.be/routegadget/" : "ardoc"
               , "http://routegadget.copaca.info/" : "copaca"
               , "rmoc.org/gadget/" : "rmoc"
               , "http://orientering.stbik.no/" : "stbik"
               , "http://rg.orienteering.sk/" : "sk"
               , 'http://reittiharveli.sotkamonjymy.fi/' : "sotkamonjymy"
               , 'https://desktop.orienter.co.za/' : 'southafrica'
               , 'turenginsarastus.net/' : 'turenginsarastus'
              }

def normalise_base_url(base_url):
    t0 = remove_suffix(base_url, "rg2")
    t1 = remove_prefix(t0, "https://www.")
    t2 = remove_prefix(t1, "http://www.")
    t3 = remove_suffix(t2, ".routegadget.co.uk/")
    t_f = t3.replace("-", '')
    t_final = manual_list.get(t_f, t_f)
    if '/' in t_final: raise Exception(base_url, t_final)
    if '-' in t_final: raise Exception(base_url, t_final)
    print(base_url, t_final)
    return t_final

def make_hash(o):

  return hashlib.sha256(repr(o).encode('utf-8')).hexdigest()

# Other instances of routegadgets
# Turned off for now due to https problem
#inj_urls = [

# Get the list of available routegadgets from the main page
eprint("Starting scraper")
page = urlopen("http://www.routegadget.co.uk/")
soup = BeautifulSoup(page, 'html.parser') # .find(class_="sitesContainer_gQl6")
urls_raw = [li.find('a').get('href') for li in soup.find_all(class_="siteName_sfLL")]
# They all end with rg2, stripping that off is more convenient.
rg_urls = list(map((lambda x: remove_suffix(x, "rg2")), urls_raw))

manual_url_list = { 'https://desktop.orienter.co.za/gadget/' : 'https://desktop.orienter.co.za/' }

urls = [ manual_url_list[key] if key in manual_url_list else key for key in rg_urls ]

eprint ("{} URLS fetched".format(len(urls)))
normed = set(list(map(normalise_base_url, urls)))
if len(normed) > len(set(normed)): raise ValueError ("Duplicate key", list(sorted(normed)))

eprint ("Starting scraper")
#display = Display(visible=0, size=(800, 600))
#display.start()

constructorStr = '''function c(a){void 0===a.A?(this.valid=!1,this.A=0,this.B=0,this.C=0,this.D=0,this.E=0,this.F=0):(this.A=parseFloat(a.A),this.B=parseFloat(a.B),this.C=parseFloat(a.C),this.D=parseFloat(a.D),this.E=parseFloat(a.E),this.F=parseFloat(a.F),this.valid=!0,this.AEDB=a.A*a.E-a.D*a.B,this.xCorrection=a.B*a.F-a.E*a.C,this.yCorrection=a.D*a.C-a.A*a.F)}'''

getLatStr = '''function (a,b){return this.D*a+this.E*b+this.F}'''

getLonStr = '''function (a,b){return this.A*a+this.B*b+this.C}'''

getXStr = '''function (a,b){return Math.round((this.E*a-this.B*b+this.xCorrection)/this.AEDB)}'''

getYStr = '''function (a,b){return Math.round((-1*this.D*a+this.A*b+this.yCorrection)/this.AEDB)}'''



def api(base_url):
    ret = json.load(urlopen(base_url + "/rg2/rg2api.php?type=events"))
    all_events = []
    for res in ret['data']['events']:
        event = {}
        event['club'] = res['club']
        event['date'] = res['date']
        event['format'] = res['format']
        event['kartatid'] = res['id']
#        event['base_url'] = base_url
#        event['map_url']
        suffix = res['suffix'] if 'suffix' in res else "jpg"
        event['mapfilename'] = str(res['mapid']) + "." + suffix
        event['mapid'] = res['mapid']
        event['name'] = res['name']
        event['rawtype'] = res['type']
        event['worldfile'] = {}
        if 'A' in res:
            event['worldfile']['A'] = res['A']
            event['worldfile']['B'] = res['B']
            event['worldfile']['C'] = res['C']
            event['worldfile']['D'] = res['D']
            event['worldfile']['E'] = res['E']
            event['worldfile']['F'] = res['F']
            event['worldfile']['valid'] = True
        else:
            event['worldfile']['A'] = 0
            event['worldfile']['B'] = 0
            event['worldfile']['C'] = 0
            event['worldfile']['D'] = 0
            event['worldfile']['E'] = 0
            event['worldfile']['F'] = 0
            event['worldfile']['valid'] = False
        all_events.append(event)
    return all_events

remap_urls = { 'turenginsarastus' : "https://www.turenginsarastus.net/rg2/img/"
             , 'stbik': 'http://orientering.stbik.no/gadget/kartat/' }

def get_map_url(base_key, base_url):
    if base_key in remap_urls:
        return remap_urls[base_key]
    else:
        return base_url + '/kartat/'


all_events = {}
hashes = {}
for base_url in urls:
    base_key = normalise_base_url(base_url)
    all_events[base_key] = {}
    print(base_url)
    if True:
        try:
            v = api(base_url)
        except Exception as e:
            eprint(e)
            continue
    else:
        driver = webdriver.Firefox()
        eprint ("Processing {}".format(base_url))
        driver.get(base_url + 'rg2')
        time.sleep(10)
        WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, 'rg2-event-list')))
        # Query information about the georeferenced events.
        try:
            v = driver.execute_script("return rg2.events.events")
        except Exception as e:
            eprint(e)
            v = api(base_url)
        driver.close()
    eprint(base_key, len(v))
    for event in v:
        mfn = event['mapfilename']
        club = event['club']
        name = event['name']

        file_name = (club  + "-" + mfn).replace("/","-").replace(" ","-")
        map_url = get_map_url(base_key, base_url)
        event['map_url'] = map_url + mfn

        event['base_url'] = base_url

        # Use an ordered structure here so the serialisation is consistent.
        res = collections.OrderedDict([(k, event[k]) for k in ['kartatid', 'worldfile','mapid','date', 'map_url','mapfilename'
                                      , 'base_url', 'name', 'club', 'format', 'rawtype'] ])

        # Need this to be ordered as well so it always serialises in the same order
        res['worldfile'] = collections.OrderedDict(sorted(res['worldfile'].items()))
        res['worldfile']['Constructor'] = constructorStr
        res['worldfile']['getLat'] = getLatStr
        res['worldfile']['getLon'] = getLonStr
        res['worldfile']['getX']   = getXStr
        res['worldfile']['getY']   = getYStr

        h = make_hash([res['name'], res['date'], res['base_url'].replace("https", "http"), sorted(res['worldfile'].items()), res['club']])
        hashes[h] = base_key + "-" + str(res['kartatid'])


        if res['worldfile']['valid']:
            res['worldfile']['proj'] = "4326"
        else:
            try:
                with open(world_files + '/' + base_key + '-' + str(res['kartatid']) + '.pgw', 'r') as wf:
                    ls = wf.read().splitlines()
                    res['worldfile']['A'] = float(ls[0])
                    res['worldfile']['D'] = float(ls[1])
                    res['worldfile']['B'] = float(ls[2])
                    res['worldfile']['E'] = float(ls[3])
                    res['worldfile']['C'] = float(ls[4])
                    res['worldfile']['F'] = float(ls[5])
                    res['worldfile']['valid'] = True
                    res['worldfile']['proj'] = "3857"
            except Exception as e:
                res['worldfile']['proj'] = ""
                pass

        #pickle.dump(res, open(os.path.join(output_dir, "{}.pickle".format(h)), 'wb'))
        all_events[base_key][res['kartatid']] = res

    json.dump(all_events, open(output_path, 'w'))
    json.dump(hashes, open("hashes.json", 'w'))

