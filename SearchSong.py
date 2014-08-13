import os, requests, simplejson as json, Utils, Constants
from bs4 import BeautifulSoup
from flask import Blueprint, request

search_song = Blueprint('search_song', __name__)

URL_FORMAT = 'http://www.hymnal.net/en/search/all/all/%s/%d'
SEARCH_RESULTS = 'search_results'
IS_LAST_PAGE = 'is_last_page'

# for error messages
SEARCH_PARAMETER = 'search_parameter'
EMPTY_LIST_MESSAGE = 'empty_list_message'
EMPTY_RESULT_ERROR_MESSAGE = 'Did not find any songs matching:\n\"%s\"\nPlease try a different request'

# maximum number of times we can loop, to avoid infinite loops
MAX_LOOP_COUNT = 100

debug = False

def log(msg):
    if (debug):
        print msg

def is_last_page(soup, current_page):
    
    pages = soup.find('ul', {'class':'pagination'})
    
    # if pages is None, return True
    if not pages:
        return True
    
    for string in pages.stripped_strings:
        try:
            num = int(string)
            if num > current_page:
                return False
        except ValueError:
            continue
    return True

# extracts search results from a single soup page
def extract_results_single_page(soup):
    
    # finds div element with class as 'list-group'
    list_group = soup.find('div',{'class':'list-group'})
    
    # if there is no 'list-group' class, then return empty list
    if list_group is None:
        return []
    
    # extract all links from the div
    return Utils.extract_links(list_group)

# fetches the results from a single results page
def fetch_single_results_page(search_parameter, page_num):
    # make http GET request to search page
    r = requests.get(URL_FORMAT % (search_parameter, page_num))
    log('request sent for: %s, Page %d' % (search_parameter, page_num))

    # create BeautifulSoup object out of html content
    soup = BeautifulSoup(r.content)

    # extract results from the single page along with whether page_num is the last page
    return (extract_results_single_page(soup), is_last_page(soup, page_num))

@search_song.route('/search')
def search_hymn():
    
    # initialize arguments
    search_parameter = request.args.get('search_parameter', type=str)
    page_num = request.args.get('page_num', type=int)
    
    # error checking
    if search_parameter is None:
        message = {Constants.PUBLIC : Constants.ERROR_MESSAGE % SEARCH_PARAMETER}
        message['status_code'] = 400
        return (json.dumps(message), 400)

    if page_num is None:
        return search_hymn_all(search_parameter)
    else:
        return search_hymn_page(search_parameter, page_num)

def search_hymn_all(search_parameter):
    # data to be returned as json
    json_data = {}
    
    # start at page 1.
    # This is here because Hymnal.net returns the results in pages, so to find all search results, we need to keep track and go through every page
    page_num = 1
    
    search_results = []
    
    # whether or not we are at the end of the results list
    end_of_results = False
        
    while not end_of_results:
        # extract results from the single page and whether or not we're on the last page
        page_results, is_last_page = fetch_single_results_page(search_parameter, page_num)

        if is_last_page or is_last_page is None:
            # end of results, so set to True
            end_of_results = True
        else:
            # otherwise  increment page_num
            page_num += 1

        # append results to search_results list
        search_results.extend(page_results)

    json_data[SEARCH_RESULTS] = search_results
    
    # search results is empty return bad search parameter message
    if len(search_results) == 0:
        json_data[EMPTY_LIST_MESSAGE] = EMPTY_RESULT_ERROR_MESSAGE % search_parameter

    return json.dumps(json_data, sort_keys=False)

def search_hymn_page(search_parameter, page_num):
    # data to be returned as json
    json_data = {}
    
    # extract results from the single page and whether or not it's the last page
    search_results, is_last_page = fetch_single_results_page(search_parameter, page_num)
    
    json_data[SEARCH_RESULTS] = search_results
    json_data[IS_LAST_PAGE] = is_last_page
    
    # search results is empty return bad search parameter message
    if len(search_results) == 0:
        json_data[EMPTY_LIST_MESSAGE] = EMPTY_RESULT_ERROR_MESSAGE % search_parameter
    
    return json.dumps(json_data, sort_keys=False)

#test paths: search/Drink, search/Drink/3, search/Drink/6, search/Christ