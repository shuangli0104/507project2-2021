#################################
##### Name:
##### Uniqname:
#################################

from bs4 import BeautifulSoup
import requests
import json
import my_secrets # file that contains your API key
import re
import os
from sys import exit


CACHE_FILENAME = "proj2_nps.json"


def open_cache():
    ''' Opens the cache file if it exists and loads the JSON into
    the CACHE_DICT dictionary.
    if the cache file doesn't exist, creates a new cache dictionary
    
    Parameters
    ----------
    None
    
    Returns
    -------
    The opened cache: dict
    '''
    try:
        cache_file = open(CACHE_FILENAME, 'r')
        cache_contents = cache_file.read()
        cache_dict = json.loads(cache_contents)
        cache_file.close()
    except:
        cache_dict = {}
    return cache_dict

def save_cache(cache_dict):
    ''' Saves the current state of the cache to disk
    
    Parameters
    ----------
    cache_dict: dict
        The dictionary to save
    
    Returns
    -------
    None
    '''
    dumped_json_cache = json.dumps(cache_dict)
    fw = open(CACHE_FILENAME,"w")
    fw.write(dumped_json_cache)
    fw.close() 
    
cache = open_cache()

class NationalSite:
    '''a national site

    Instance Attributes
    -------------------
    category: string
        the category of a national site (e.g. 'National Park', '')
        some sites have blank category.
    
    name: string
        the name of a national site (e.g. 'Isle Royale')

    address: string
        the city and state of a national site (e.g. 'Houghton, MI')

    zipcode: string
        the zip-code of a national site (e.g. '49931', '82190-0168')

    phone: string
        the phone of a national site (e.g. '(616) 319-7906', '307-344-7381')
    '''
    def __init__(self, category, name, address, zipcode, phone):
        self.category = category
        self.name = name
        self.address = address
        self.zipcode = zipcode
        self.phone = phone
        
    def info(self):
        return f"{self.name} ({self.category}): {self.address} {self.zipcode}"
    
    def to_dict(self):
        return self.__dict__


def build_state_url_dict():
    ''' Make a dictionary that maps state name to state page url from "https://www.nps.gov"

    Parameters
    ----------
    None

    Returns
    -------
    dict
        key is a state name and value is the url
        e.g. {'michigan':'https://www.nps.gov/state/mi/index.htm', ...}
    '''
    if cache.get('state_url'):
        print('Using cache')
        return cache['state_url']
    else:
        print('Fetching')
        home_url = 'https://www.nps.gov/index.htm'
        r = requests.get(home_url)
        soup = BeautifulSoup(r.text, 'html.parser')
        hrefs = soup.find_all('a', attrs={'href': re.compile('/state/.*?/index.htm')})
        df = {}
        for href in hrefs:
            key = href.text.lower()
            link = home_url.rstrip('/index.htm')+href['href'].strip(' ')
            df[key] = link
        cache['state_url'] = df
        return df

def get_site_instance(site_url):
    '''Make an instances from a national site URL.
    
    Parameters
    ----------
    site_url: string
        The URL for a national site page in nps.gov
    
    Returns
    -------
    instance
        a national site instance
    '''
    r = requests.get(site_url)
    soup = BeautifulSoup(r.text, 'html.parser')
    Name = soup.find_all('a', attrs={"class": "Hero-title"})[0].text
    Type = soup.find_all('span', attrs={"class": "Hero-designation"})[0].text
    try:
        Address = soup.find_all('span', attrs={"itemprop": 'addressLocality'})[0].text \
            + ', ' + soup.find_all('span', attrs={'class': 'region'})[0].text
    except:
        Address = ''
    try:
        Zip_Code =  soup.find_all('span', attrs={"class": "postal-code"})[0].text.rstrip(' ')
    except:
        Zip_Code = ''
    Phone = soup.find_all('span', attrs={'class': 'tel'})[0].text.strip('\n')
    return NationalSite(Type, Name, Address, Zip_Code, Phone)

def get_sites_for_state(state_url):
    '''Make a list of national site instances from a state URL.
    
    Parameters
    ----------
    state_url: string
        The URL for a state page in nps.gov
    
    Returns
    -------
    list
        a list of national site instances
    '''
    
    r = requests.get(state_url)
    soup = BeautifulSoup(r.text, 'html.parser')
    divs = soup.find_all('div', attrs={'class': 'col-md-9 col-sm-9 col-xs-12 table-cell list_left'})
    hrefs = ['https://www.nps.gov'+div.h3.a['href']+'index.htm' for div in divs]
    sites_list = []
    for site_url in hrefs:
        print("Fetching")
        sites_list.append(get_site_instance(site_url))
    return sites_list

def get_nearby_places(site_object):
    '''Obtain API data from MapQuest API.
    
    Parameters
    ----------
    site_object: object
        an instance of a national site
    
    Returns
    -------
    dict
        a converted API return from MapQuest API
    '''
    url = 'http://www.mapquestapi.com/search/v2/radius'
    params = {
                'key': my_secrets.API_KEY,
                'origin': site_object.zipcode,
                'radius': 10,
                'maxMatches': 10,
                'ambiguities': "ignore",
                'outFormat': "json"
            }
    r = requests.get(url, params=params)
    
    return r.json()

def display_nearby_places_info(places_dict):
    '''Display the nearby places info

    Parameters
    ----------
    places_dict : dict
        dict data list

    Returns
    -------
    None.

    '''
    for place in places_dict:
        name = place['name']
        category = place['category']
        address = place['address']
        city = place['city']
        print(f'- {name} ({category}): {address}, {city}')




def display_sites_info(state_name, sites_list):
    '''Display the sites info

    Parameters
    ----------
    state_name : str
        The state name
    sites_list : list
        list of sites' info(dict)

    Returns
    -------
    None.
    '''
    print('-'*40)
    print("List of national sites in %s" % state_name)
    print('-'*40)
    num = 1
    for site in sites_list:
        print(f'{[num]} {site["name"]} ({site["category"]}): {site["address"]} {site["zipcode"]}')
        num += 1

def main():
    state_urls = build_state_url_dict()
    
    while True:
        state_name = input('Enter a state name (e.g. Michigan, michigan) or "exit": ').lower()
        if state_name not in state_urls.keys() and state_name != "exit":
            print("[Error] Enter proper state name")
            continue
        elif state_name == 'exit':
            save_cache(cache)
            exit()
        else:
            if cache.get(state_name):
                for site in cache[state_name]:
                    print('Using cache')
                sites_list = cache[state_name]
            else:
                state_url = state_urls[state_name]
                sites_list = [site.to_dict() for site in get_sites_for_state(state_url)]
                cache[state_name] = sites_list
            display_sites_info(state_name, sites_list)
        
            while True:
                site_num = input('Choose the number for detail search or "exit" or "back": ')
                if site_num in list(map(lambda x: str(x), range(1, len(sites_list)+1))):
                    site_num = int(site_num) - 1
                    if cache[state_name][site_num].get("nearby"):
                        print("Using cache")
                        sites_list_2 = cache[state_name][site_num]['nearby']
                    else:
                        print("Fetching")
                        tmp_sites_list = get_nearby_places(NationalSite(**cache[state_name][site_num]))
                        sites_list_2 = [
                                        {"name": site['name'],
                                         "category": 'no category' if site['fields']['group_sic_code_name']=='' else site['fields']['group_sic_code_name'],
                                         "address": 'no address' if site['fields']['address']=='' else site['fields']['address'],
                                         "city": 'no city' if site['fields']['city']=='' else site['fields']['city']
                                         } for site in tmp_sites_list['searchResults']]
                        cache[state_name][site_num]["nearby"] = sites_list_2
                    display_nearby_places_info(sites_list_2)
                elif site_num == "exit":
                    save_cache(cache)
                    exit()
                elif site_num == "back":
                    break
                else:
                    print("[Error] Invalid input")
    

if __name__ == "__main__":
    main()
