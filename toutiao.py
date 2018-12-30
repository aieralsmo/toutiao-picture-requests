import re
import json
import random
import time
import os
import hashlib
from urllib.parse import urlencode


import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException, Timeout
import pymongo
from toutiao_mongo_config import * 


client = pymongo.MongoClient(MONGOD_URL)
db = client[MONGOD_DB]

def get_page_index(offset):
	"""请求初始页面，得到关键字ajax请求页面返回的结果"""
	headers = {
		'User-Agent': random.choice(user_agent),
		'Referer':"http://www.toutiao.com"
	}
	# 构造请求参数
	data = {
		'offset': offset,
		'format': 'json',
		'keyword': keyword,
		'autoload': 'true',
		'count': 30,
		'cur_tab': 3,
		'from': 'cur_tab',
		'pd': 'synthesis'
	}
	# 构造请求路径
	url = "https://www.toutiao.com/search_content/?"+urlencode(data)
	
	# import ipdb ;ipdb.set_trace()
	try:
		resp = requests.get(url, headers=headers)

		if resp.status_code == requests.codes.ok:

			return resp.text
		print(resp.status_code,'请求失败')
		
	except Timeout:
		print("Timeout")
		
	except RequestException:
		print('请求异常RequestException')
		
def parse_page_index(html):
	"""解析ajax返回的json格式数据"""
	data = json.loads(html)
	# print('data',data)
	if data and 'data' in data.keys():
		for item in data.get("data"):
			# 返回具体文章的url
			print(item.get("article_url"))
			yield item.get("article_url")

def get_page_detail(url):
	"""获取详细文章"""
	headers = {'User-Agent': random.choice(user_agent),
				'Referer':"http://www.toutiao.com"
				}
				headers = {'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50"'}
	try:
		resp = requests.get(url,headers=headers)
		if resp.status_code == 200:
			return resp.text
		print(resp.status_code,'请求失败')
		
	except Timeout:
		print("Timeout")
		
	except RequestException:
		print('请求异常RequestException')
		

def parse_page_detail(html,url):
	"""解析详情页"""

	soup = BeautifulSoup(html, 'lxml')# html.parser

	# 获取文章标题
	title = soup.select('title')
	if title:
		title = title[0].get_text()
	else:
		title_pattern = re.compile(r'.*?article-title">(.*?)</h1>', re.S)
		title=re.search(title_pattern, html)
		if title:
			
			title = title.group(1)
		else:
			title = '无标题'
		
	# 匹配图片路劲
	images_pattern = re.compile(r'var gallery = (.*?);', re.S)
	result = re.search(images_pattern, html)
	
	if result:
		data = json.loads(result.group(1))
		

		if data and "sub_images" in data.keys():
			sub_images = data.get("sub_images")
			images = ["http:"+item.get('url') for item in sub_images]
			for image in images: download_image(image)
			return {
				'title':title,
				'url':url,
				'images':images
			}


def save_to_mongo(result):
	"""保存到数据库"""

	old_data = [item['url'] for item in db[MONGOD_TABLE].find() ]
	if not result['url'] in old_data:
		if db[MONGOD_TABLE].insert(result):
			print("成功保存到MONGODB")
			return True
		return False	
	print("mongodb中已经存在")

def download_image(img_url):
	"""下载图片"""

	if img_url in [item['images'] for item in db[MONGOD_TABLE].find() ]:
		return None

	headers = {'User-Agent': random.choice(user_agent),'Referer':"https://www.toutiao.com"}
	try:
		resp = requests.get(img_url,headers=headers)
		if resp.status_code == 200:
			print("正在加载图片url:", img_url)
			save_image(resp.content)

	except Timeout:
		print("Timeout")
		
	except RequestException:
		print('请求异常RequestException')
		



def save_image(content):
	"""保存图片到本地"""


	md5 = hashlib.md5()
	md5.update(content)
	
	base_path = os.path.join(os.getcwd(), 'MeiTu',keyword)
	if not os.path.exists(base_path):
		os.makedirs(base_path)

	file_path = os.path.join(base_path,md5.hexdigest()+'.png')
	if not os.path.exists(file_path):
		with open(file_path, 'wb') as wf:
			wf.write(content)
			print("保存图片成功")
	else:
		print("该图片在库中已经存在")
		

			
def main(offset):
	html = get_page_index(offset=offset)
	
	if html:
		for url in parse_page_index(html): 
			html = get_page_detail(url)
			if html:
				ret = parse_page_detail(html,url)
				if ret:
					save_to_mongo(ret)

if __name__ == '__main__':

	
	keyword = input("请输入要爬取的主题：")

	b_num = int(input("请输入从第几页开始(有效数字)："))
	e_num = int(input("请输入到第几页结束(有效数字)："))
	
	for i in range(b_num,e_num+1):print("offset--->",str(i)+"/"+str(e_num)) ,main(offset=i)
	

