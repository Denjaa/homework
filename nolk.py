from selenium import webdriver
import time
import io
from lxml import html
import sqlite3
from functools import wraps
import requests
import re
import warnings

warnings.filterwarnings('ignore')

def measure_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        end_result = func(*args, **kwargs)
        end = time.time()
        print ('Time to complete exercise: {}'.format(end - start))
        return end_result
    return wrapper

class FaireRawData:
    def __init__(self):
        self.URL = 'https://www.faire.com/all-makers'
        self.fOutput = io.open('brand_source.txt', 'w', encoding = 'utf-8')

    @measure_time
    def get_brand_source(self):
        self.driver = webdriver.Chrome()
        self.driver.get(self.URL)
        time.sleep(10)
        self.fOutput.write(self.driver.page_source)
        self.driver.close()

class Brands:
    def __init__(self, fInput):
        self.fInput = io.open(fInput, 'r', encoding = 'utf-8').readlines()
        self.source_data = html.fromstring(' '.join(self.fInput))
        self.connection = sqlite3.connect("brands.db")
        self.cursor = self.connection.cursor()
        self.cursor.execute(""" CREATE TABLE IF NOT EXISTS brands ( brand VARCHAR(255),
                                                                    web VARCHAR(255));""")
        self.connection.commit()

    @measure_time
    def extract(self):
        self.brands, self.direction = self.source_data.xpath('//*[@id="main"]/section//@title'), self.source_data.xpath('//*[@id="main"]/section//@href')
        if len(self.brands) == len(self.direction):
            for i in range(len(self.brands)):
                self.query = """ INSERT INTO brands(brand, web) VALUES ("{}", "{}") """.format(str(self.brands[i]), 'https://www.faire.com' + str(self.direction[i]))
                try:
                    self.cursor.execute(self.query)
                    self.connection.commit()
                except sqlite3.Error: print ('Unable to ingest data for company: {}'.format(self.brands[i]))

class GetBrandData:

    def __init__(self):
        self.brand_connection = sqlite3.connect("brands.db")
        self.brand_cursor = self.brand_connection.cursor()

        self.brand_additional_connection = sqlite3.connect("brands_additional.db")
        self.brand_additional_cursor = self.brand_additional_connection.cursor()
        self.brand_additional_cursor.execute("""    CREATE TABLE IF NOT EXISTS brands_additional (
                                                    brand VARCHAR(255),
                                                    story VARCHAR(500),
                                                    insta_name VARCHAR(50),
                                                    insta_web VARCHAR(255),
                                                    logo_web VARCHAR(255),
                                                    homepage VARCHAR(255),
                                                    tags VARCHAR(255),
                                                    faire_page VARCHAR(255));""")
        self.brand_additional_connection.commit()

    def google_search(self, keyword):
        self.driver = webdriver.Chrome()
        self.URL = 'https://www.google.com/search?q={}'.format(keyword.replace(' ', '+'))
        self.driver.get(self.URL)
        try: self.driver.find_element_by_xpath('//*[@id="introAgreeButton"]/span/span').click()
        except: pass
        time.sleep(1)
        self.content = html.fromstring(self.driver.page_source)
        try: self.homepage = self.content.xpath('//*[@class="iUh30 Zu0yb tjvcx"]//text()')[0]
        except: self.homepage = ''
        self.driver.close()
        return self.homepage

    def get_source(self, URL):
        self.driver = webdriver.Chrome()
        self.driver.get(URL)
        time.sleep(1)

        try: self.driver.find_element_by_xpath('//*[@id="onetrust-accept-btn-handler"]').click()
        except: pass
        self.driver.find_element_by_xpath('//*[@id="main"]/div/div[1]/div/div/div[2]/div/div[1]/div/div[3]/div[3]/button').click()
        time.sleep(2)
        self.source_data = self.driver.page_source
        self.driver.close()
        return self.source_data

    def get_data(self):
        self.brand_data = list(self.brand_cursor.execute('SELECT * FROM brands LIMIT 100;'))
        for i in range(len(self.brand_data)):
            self.fetch_data = self.brand_data[i]
            self.page_source = self.get_source(URL = self.fetch_data[-1])
            self.content = html.fromstring(self.page_source)

            try: self.story =  self.content.xpath('/html/body/div[5]/div/div/div/div/div/div[1]/div/div[3]/div[5]//text()')[0]
            except : self.story = ''

            try: self.tags = ' | '.join(self.content.xpath('/html/body/div[5]/div/div/div/div/div/div[1]/div/div[1]/div[17]//text()'))
            except: self.tags = ''

            try: self.instagram_name = self.content.xpath('/html/body/div[5]/div/div/div/div/div/div[1]/div/div[1]/div[9]/a//text()')[0]
            except: self.instagram_name = ''

            try: self.instagram_web = self.content.xpath('/html/body/div[5]/div/div/div/div/div/div[1]/div/div[1]/div[9]/a//@href')[0]
            except: self.instagram_web = ''

            try: self.image_source = self.content.xpath('/html/body/div[5]/div/div/div/div/div/div[1]/div/div[1]/img/@src')[0]
            except: self.image_source = ''

            try: self.based = ' '.join(self.content.xpath('//*[@id="main"]/div/div[1]/div/div/div[2]/div/div[1]/div/div[1]/span/span//text()')).replace(',', '').replace('.', '').replace('  ', '').strip()
            except: self.based = ''

            self.homepage = self.google_search(self.fetch_data[0] + ' ' + self.based)

            self.query = """ INSERT INTO brands_additional VALUES ("{}", "{}", "{}", "{}", "{}", "{}", "{}", "{}")""".format( self.fetch_data[0].replace('"', ''),
                                                                                                                        self.story.replace('"', ''),
                                                                                                                        self.instagram_name.replace('"', ''),
                                                                                                                        self.instagram_web.replace('"', ''),
                                                                                                                        self.image_source.replace('"', ''),
                                                                                                                        self.homepage.replace('"', ''),
                                                                                                                        self.tags.replace('"', ''),
                                                                                                                        self.fetch_data[-1].replace('"', ''))

            print (self.query)
            self.brand_additional_cursor.execute(self.query)
            self.brand_additional_connection.commit()

class GetSocialMedia:

    def __init__(self):
        self.social_media_connection = sqlite3.connect("social_media.db")
        self.social_media_cursor = self.social_media_connection.cursor()
        self.social_media_cursor.execute("""    CREATE TABLE IF NOT EXISTS social_media (
                                                    brand VARCHAR(255),
                                                    facebook VARCHAR(255),
                                                    pinterest VARCHAR(500),
                                                    twitter VARCHAR(50));""")
        self.social_media_connection.commit()
        self.user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36'
        self.headers = { 'User-Agent' : self.user_agent }

        self.brand_additional_connection = sqlite3.connect("brands_additional.db")
        self.brand_additional_cursor = self.brand_additional_connection.cursor()
        self.brand_data = list(self.brand_additional_cursor.execute(""" SELECT brand, homepage FROM brands_additional WHERE homepage is NOT NULL and homepage <> ''   """))
        self.brand_additional_connection.commit()

    def get_data_media(self):
        for data in self.brand_data:
            try:
                self.response = requests.get(data[-1], headers = self.headers)
                self.content = self.response.text
                try: self.facebook = ' | '.join(re.findall(r'facebook.com\/[a-z]+', self.content))
                except: self.facebook = ''

                try: self.pinterest = ' | '.join(re.match(r'(pinterest.com\/[a-z]+', self.content))
                except: self.pinterest = ''

                try: self.twitter = ' | '.join(re.findall(r'twitter.com\/[a-z]+', self.content))
                except: self.twitter = ''


                self.social_media_cursor.execute(""" INSERT INTO social_media VALUES ("{}", "{}", "{}", "{}") """.format(data[0], self.facebook, self.pinterest, self.twitter))
                self.social_media_connection.commit()
            except: pass

### using selenium to Chrome to get source data as PhantomJS had struggles
### and saving the HTML source to seperate txt document for next class to extract
"""Switched off """
# FaireRawData().get_brand_source()

### passing in HTML source code into class and using xpath locator to extract the
### brand data and weblocation of brand

""" Switched off"""
# Brands(fInput = 'brand_source.txt').extract()

""" Switched off"""
### this code is focusing on getting details from faire_page
### it also tried to find website on google by using name and location
### as main parameters and closes matchs selected
# GetBrandData().get_data()

""" Switched off"""
### one idea I could think of getting social media
### is by going to main page if it is valid
### and using regex to get the data for social media
# GetSocialMedia().get_data_media()
