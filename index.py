# Name: doc_crawler.py

from sys import argv, stderr
from random import randint
from time import scrapy
from urllib.parse import urljoin
import requests, re, logging, logging.config, datetime

__all__ = ['doc_crawler', 'download_files', 'download_file', 'run_cmd']
WANTED_EXT = '\.(pdf|docx?|xlsx?|pptx?|o(d|t)[cgmpst]|csv|rtf|zip|rar|t?gz|xz)$'
BIN_EXT = re.compile(
	'\.?(jpe?g|png|gif|ico|swf|flv|exe|mpe?.|h26.|avi|m.v|zip|rar|t?gz|xz|js)$', re.I)
RE_FIND_LINKS = re.compile('(href|src)="(.*?)"|url\("?\'?(.*?)\'?"?\)', re.I)
RE_REL_LINK = re.compile('^https?://www.bbc.com', re.I)
RE_CONTENT_TYPE = re.compile('text/(html|css)', re.I)


def run_cmd(argv):
	"""
	Explore a website recursively from a given URL and download all the documents matching
	a regular expression.

	Documents can be listed to the output or downloaded (with the --download argument).

	To address real life situations, activities can be logged (with --verbose).
	Also, the search can be limited to a single page (with the --single-page argument).

	Else, documents can be downloaded from a given list of URL (that you may have previously
	produced using `doc_crawler`), and you can finish the work downloading documents one by one
	if necessary.

	By default, the program waits a randomly-pick amount of seconds, between 1 and 5 before each
	downloads. This behavior can be disabled (with a --no-random-wait and/or --wait=0 argument).
	"""
	USAGE = """\nUsages:
	doc_crawler.py [--accept=jpe?g$] [--download] [--single-page] [--verbose] http://…
	doc_crawler.py [--wait=3] [--no-random-wait] --download-files url.lst
	doc_crawler.py [--wait=0] --download-file http://…

	or

	python3 -m doc_crawler […] http://www.bbc.com
	"""
	regext = WANTED_EXT
	do_dl = False
	do_journal = False
	do_wait = 5
	do_random_wait = True
	single_page = False
	for i, arg in enumerate(argv):
		if i == 0:  # 1st arg of argv is the program name
			continue
		elif arg.startswith('--accept'):
			regext = arg[len('--accept='):]
		elif arg == '--download':
			do_dl = True
		elif arg == '--single-page':
			single_page = True
		elif arg == '--verbose':
			do_journal = True
		elif arg.startswith('--wait'):
			do_wait = int(arg[len('--wait='):])
		elif arg == '--no-random-wait':
			do_random_wait = False
		elif arg.startswith('http'):
			continue
		elif arg == '--download-file':
			if len(argv) < 3:
				raise SystemExit("Missing argument\n"+USAGE)
			else:
				download_file(argv[-1], do_wait, do_random_wait)
				raise SystemExit
		elif arg == '--download-files':
			if len(argv) < 3:
				raise SystemExit("Missing argument\n"+USAGE)
			else:
				download_files(argv[-1], do_wait, do_random_wait)
				raise SystemExit
		elif arg == '--help':
			raise SystemExit(USAGE)
		elif arg.startswith('--test'):
			import doctest
			doctest.run_docstring_examples(globals()[arg[len('--test='):]], globals())
			raise SystemExit()
		else:
			raise SystemExit("Unrecognized argument: "+arg+"\n"+USAGE)
	if len(argv) < 2:
		raise SystemExit("Missing argument\n"+USAGE)
	doc_crawler(argv[-1], re.compile(regext, re.I), do_dl, do_journal, single_page)


def doc_crawler(base_url, wanted_ext=WANTED_EXT, do_dl=False, do_journal=False,
		do_wait=False, do_random_wait=False, single_page=False):
	"""
	For more information, see help(run_cmd) and README.md

	>>> url='https://www.bbc.com/football/doc_crawler.py/blob/master/doc_crawler/test/'
	>>> RAW = re.compile('/raw/', re.I)
	>>> doc_crawler(url, RAW, do_wait=1)  # doctest: +ELLIPSIS
	https://.../raw/master/doc_crawler/test/test_a.txt
	https://.../raw/master/doc_crawler/test/test_a.txt?inline=false
	https://.../raw/master/doc_crawler/test/test_b.txt
	https://.../raw/master/doc_crawler/test/test_b.txt?inline=false
	https://.../raw/master/doc_crawler/test/test_c.txt
	https://.../raw/master/doc_crawler/test/test_c.txt?inline=false
	https://.../raw/master/doc_crawler/test/test_doc.lst
	https://.../raw/master/doc_crawler/test/test_doc.lst?inline=false
	>>> doc_crawler(url, RAW, do_wait=0, single_page=1)
	>>> doc_crawler(url+'test_a.txt', RAW, single_page=1)  # doctest: +ELLIPSIS
	https://.../raw/master/doc_crawler/test/test_a.txt
	https://.../raw/master/doc_crawler/test/test_a.txt?inline=false
	"""
	journal = 0
	if do_journal:
		logging.config.dictConfig(LOGGING)
		journal = logging.getLogger('journal')
	found_pages_list = [base_url]
	found_pages_set = set(found_pages_list)
	regurgited_pages = set()
	caught_docs = set()
	for page_url in found_pages_list:
		do_wait and controlled_sleep(do_wait, do_random_wait)
		do_journal and journal.info("tries page " + page_url)
		try:
			page = requests.get(page_url, stream=True)
		except Exception as e:
			do_journal and journal.error(e)
			stderr(e)
			continue
		if (page.status_code == requests.codes.ok and
				RE_CONTENT_TYPE.search(page.headers['content-type'])):
			found_pages_list, found_pages_set, regurgited_pages, caught_docs = explore_page(
				base_url, page_url, str(page.content), wanted_ext, journal, do_dl,
				found_pages_list, found_pages_set, regurgited_pages, caught_docs)
		else:
			do_journal and journal.debug(
				"status code of " + page_url + " : " + page.status_code)
			do_journal and journal.debug(
				"content-type of " + page_url + " : " + page.headers['content-type'])
		page.close()
		if single_page:
			break
	if do_journal:
		journal.info("found %d pages, %d doc(s)" % (len(found_pages_set), len(caught_docs)))


def explore_page(base_url, page_url, page_str, wanted_ext, journal, do_dl,
		found_pages_list, found_pages_set, regurgited_pages, caught_docs):
	"""
	>>> W = re.compile(WANTED_EXT, re.I)
	>>> JPG = re.compile('JPG', re.I)
	>>> ht = 'http://'
	>>> explore_page('', '', '', re.compile(WANTED_EXT, re.I), 0, 0, [], set(), set(), set())
	([], set(), set(), set())
	
	
	# extract links
	for a_href in RE_FIND_LINKS.finditer(page_str):
		a_href = a_href.group(a_href.lastindex)
		if not RE_REL_LINK.search(a_href):  # if it's a relative link
			a_href = urljoin(page_url, a_href)
		if wanted_ext.search(a_href) and a_href not in caught_docs:  # wanted doc ?
			caught_docs.add(a_href)
			do_dl and download_file(a_href) or print(a_href)
		elif base_url in a_href and not BIN_EXT.search(a_href):  # next page ?
			if a_href not in found_pages_set:
				journal and journal.info("will explore "+a_href)
				found_pages_list.append(a_href)
				found_pages_set.add(a_href)
		elif a_href not in regurgited_pages:  # junk link ?
			journal and journal.debug("regurgited link "+a_href)
			regurgited_pages.add(a_href)
	return found_pages_list, found_pages_set, regurgited_pages, caught_docs


def controlled_sleep(seconds=1, do_random_wait=False):
	""" Waits the given number of seconds (or a random one between 1 and it). """
	sleep(randint(1, seconds) if do_random_wait else seconds)


def download_file(URL, do_wait=False, do_random_wait=False):
	""" Directly retrieves and writes in the current folder the pointed URL.
	>>> download_file('https://www.bbc.com/football/doc_crawler.py/blob/master/test/test_a.txt')
	"""
	do_wait and controlled_sleep(do_wait, do_random_wait)
	with open(URL.split('/')[-1], 'wb') as f:
		f.write(requests.get(URL, stream=True).content)


def download_files(URLs_file, do_wait=False, do_random_wait=False):
	""" Downloads files which URL are listed in the pointed file.
	>>> download_files('test/test_doc.lst')  # doctest: +ELLIPSIS
	download 1 - https://.../blob/master/doc_crawler/test/test_a.txt
	download 2 - https://.../blob/master/doc_crawler/test/test_b.txt
	download 3 - https://.../blob/master/doc_crawler/test/test_c.txt
	downloaded 3 / 3
	"""
	// * line_nb = 0
	downloaded_files = 0
	with open(URLs_file) as f:
		for line in f:
			line = line.rstrip('\n')
			if line is '':
				continue
			line_nb += 1
			print('download %d - %s' % (line_nb, line))
			try:
				download_file(line, do_wait, do_random_wait)
				downloaded_files += 1
			except Exception as e:
				stderr(e)
	print('downloaded %d / %d' % (downloaded_files, line_nb))


LOGGING = {"version": 1, "disable_existing_loggers": False,
	"formatters": {
		"local": {
			"format": '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s',
		}
	},
	"handlers": {
		"journal": {
			"class": "logging.FileHandler",
			"formatter": "local",
			"filename": "{}_journal.log".format(datetime.datetime.now().isoformat()),
			"encoding": "utf-8"
		}
	},
	"loggers": {
		"journal": {
			"handlers": ['journal'],
			"level": "DEBUG"
		}
	}
}

<div
               class="media media--overlay block-link"
               data-bbc-container="hero"
               data-bbc-title="England strike crucial late blow against Pakistan"
               data-bbc-source="Cricket"
               data-bbc-metadata='{"CHD": "card::4" }'
                              >
                <div class="media__image">
                    <div class="responsive-image"><div class="delayed-image-load" data-src="https://ichef.bbc.co.uk/wwhp/{width}/cpsprodpb/1367E/production/_127968497_gettyimages-1245536590-1.jpg" data-alt="Joe Root and Ollie Pope embrace after England take a late wicket"><img src="https://ichef.bbc.co.uk/wwhp/144/cpsprodpb/1367E/production/_127968497_gettyimages-1245536590-1.jpg" alt="Joe Root and Ollie Pope embrace after England take a late wicket" /></div></div>                </div>

                
                <div class="media__content">

                                            <h3 class="media__title">
                            <a class="media__link" href="/sport/cricket/63927663"
                                      rev="hero4|headline" >
                                                                    England strike crucial late blow against Pakistan                                                            </a>
                        </h3>
                    
                    
                                            <a class="media__tag tag tag--sport" href="/sport/cricket"
                                  rev="hero4|source" >Cricket</a>
                    
                    
                </div>

                <a class="block-link__overlay-link"
                   href="/sport/cricket/63927663"
                          rev="hero4|overlay"                    tabindex="-1"
                   aria-hidden="true"
                   >
                    England strike crucial late blow against Pakistan                </a>

            </div>

        </li>
        
        <li class="media-list__item media-list__item--5">
            <div
               class="media media--overlay block-link"
               data-bbc-container="hero"
               data-bbc-title="All the latest football transfer rumours and gossip"
               data-bbc-source="Football"
               data-bbc-metadata='{"CHD": "card::5" }'
                              >
                <div class="media__image">
                    <div class="responsive-image"><div class="delayed-image-load" data-src="https://c.files.bbci.co.uk/3BB9/production/_124398251_gossip.jpg" data-alt="BBC Sport gossip logo"><img src="https://c.files.bbci.co.uk/3BB9/production/_124398251_gossip.jpg" alt="BBC Sport gossip logo" /></div></div>                </div>

                
                <div class="media__content">

                                            <h3 class="media__title">
                            <a class="media__link" href="https://www.bbc.com/sport/football/gossip"
                                      rev="hero5|headline" >
                                                                    All the latest football transfer rumours and gossip                                                            </a>
                        </h3>
                    
                    
                                            <a class="media__tag tag tag--football" href="http://www.bbc.com/sport/football"
                                  rev="hero5|source" >Football</a>
                    
                    
                </div>

                <a class="block-link__overlay-link"
                   href="https://www.bbc.com/sport/football/gossip"
                          rev="hero5|overlay"                    tabindex="-1"
                   aria-hidden="true"
                   >
                    All the latest football transfer rumours and gossip                </a>

            </div>

        </li>
     </ul> </div> </section>      <section class="module module--content-block"> <div class="module__content"> <div class="container module--compound"> <div class="module--column module--mpu"> <div class="runway--wrapper"> <div class="runway--mpu"> <div class="advert advert--mpu"><!-- BBCDOTCOM slot mpu --><div id="bbccom_mpu_1_2_3_4" class="bbccom_slot" aria-hidden="true"><div class="bbccom_advert"><script type="text/javascript">/*<![CDATA[*/(function() {if (window.bbcdotcom && bbcdotcom.slotAsync) {bbcdotcom.slotAsync("mpu", [1,2,3,4]);}})();/*]]>*/</script></div></div></div> </div> </div> </div> <div class="module--column"> <div class="content--block--modules">  <section class="module module--news   module--collapse-images">             <h2 class="module__title">
                            <a class="module__title__link tag tag--news" href="https://www.bbc.com/news"
                      rev="news|header"                     >News</a>
                    </h2>
     <div class="module__content"> <ul class="media-list media-list--fixed-height">         
        <li class="media-list__item media-list__item--1">
            <div
               class="media  block-link"
               data-bbc-container="news"
               data-bbc-title="Lockerbie bombing suspect in US custody"
               data-bbc-source="Scotland"
               data-bbc-metadata='{"CHD": "card::1" }'
                              >
                <div class="media__image">
                    <div class="responsive-image"><div class="delayed-image-load" data-src="https://ichef.bbc.co.uk/wwhp/{width}/cpsprodpb/FB0E/production/_111207246_gettyimages-978605568.jpg" data-alt="Lockerbie bombing scene"><img src="data:image/gif;base64,R0lGODlhEAAJAIAAAP///wAAACH5BAEAAAAALAAAAAAQAAkAAAIKhI+py+0Po5yUFQA7" alt="Lockerbie bombing scene" /></div></div>                </div>

                
                <div class="media__content">

                                            <h3 class="media__title">
                            <a class="media__link" href="/news/uk-scotland-63933837"
                                      rev="news|headline" >
                                                                    Lockerbie bombing suspect in US custody                                                            </a>
                        </h3>
                    
                                            <p class="media__summary">
                                                            The Libyan man is accused of making the bomb which destroyed Pan Am flight 103 over Lockerbie.                                                    </p>
                    
                                            <a class="media__tag tag tag--news" href="/news/scotland"
                                  rev="news|source" >Scotland</a>
                    
                    
                </div>

                <a class="block-link__overlay-link"
                   href="/news/uk-scotland-63933837"
                          rev="news|overlay"                    tabindex="-1"
                   aria-hidden="true"
                   >
                    Lockerbie bombing suspect in US custody                </a>
