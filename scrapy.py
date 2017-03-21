#coding:utf-8
'''
Created on 2016年11月16日

@author: guoshun
'''

import io
import gzip
import urllib
import urllib2
import cookielib
import codecs
import os
import re
from bs4 import BeautifulSoup
from urllib2 import URLError
from urllib2 import HTTPError
import socket
import threading
import time
import logging
import math
import random
import sys
from nbconvert.postprocessors.serve import ProxyHandler
import numpy as np
import json
import csv

#可从文件读取，但类别不多 list存储
def getIP():
    #ipdir=os.getcwd()+"\ip.txt"
    ipdir='ip.txt'
    f=open(ipdir,'r')
    iplist=f.readlines()
    rand=random.randint(0,len(iplist)-1)
    while iplist[rand]==socket.gethostbyname(socket.gethostname()):
        rand=random.randint(0,len(iplist)-1)

    ipandport=iplist[rand].strip()
    f.close()
    return ipandport

# 日志打印管理
def logconfig():
    logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename='scrapy.log',
                    filemode='w')

    #定义一个StreamHandler，将INFO级别或更高的日志信息打印到标准错误，并将其添加到当前的日志处理对象#
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)


timeout = 10
socket.setdefaulttimeout(timeout)
def setProxy(opener,proxy):
    flag=True
    while flag:
        try:
            #handler=ProxyHandler({"http":'http://%s/' % proxy}) 必须加 urllib2 ，否则直接异常
            handler=urllib2.ProxyHandler({"http":proxy})
            opener.add_handler(handler)
            urllib2.install_opener(opener)
            #作为测试 代理可用否
            #urllib2.urlopen("http://www.baidu.com").read()
            flag=False
        except:
            proxy=getIP()
    return opener
# 向服务器发送请求，处理异常 timeout socketerror 等，重发处理
def get(opener,req,retries=10):
    #请求太快，每次请求时sleep 2秒
    sec=np.random.normal(5,3)
    if sec<=0:
        sec=1
    time.sleep(sec)
    logging.info("send request")
    if retries<=0:
        logging.info("send request times over")
        return None
    try:
        response = opener.open(req)
        data = response.read()
    except URLError as e:
        if isinstance(e.reason, socket.timeout):
            logging.info("request timeout and rerequest")
            time.sleep(5)
            return get(opener,req,retries-1)
        if hasattr(e,"reason"):
            logging.info("URLError,we fail to send to server")
            logging.debug("reason:")
            logging.debug(e.reason)
            time.sleep(5)
            return get(opener,req,retries-1)
        elif hasattr(e,"code"):
            logging.info("the server cannot fulfill the req")
            logging.debug("error code:")
            time.sleep(5)
            logging.debug(e.code)
            return  get(opener,req,retries-1)
    except socket.timeout:
        logging.debug("timeout,request again")
        time.sleep(5)
        return get(opener,req,retries-1)
    except socket.error:
        logging.debug("socket.error: request again")
        time.sleep(5)
        return get(opener,req,retries-1)
    logging.debug("get finally")
    return data
# 判断页面是否异常，访问受限
def judgeContent(htmltext,opener,req):
    flag=True
    data=htmltext
    while flag:
        m = re.search(r"\<title\>[\s\S]*\</title\>",data)
        if m:
            t=m.group().strip("\<?/title>").strip()
            if t=="访问受限":
                print "ip访问受限，change proxy"
                proxy=getIP()
                opener=setProxy(opener, proxy)
                time.sleep(10)
                html=get(opener, req, 20)
                data=decodegzip(html)
            elif t=="异常页面":
                print "异常页面，重新发送请求"
                time.sleep(10)
                html=get(opener, req, 20)
                data=decodegzip(html)
            else:
                flag=False
        else:
            flag=False
    return data
# 解压缩 从服务器返回为压缩的，需要解压
def decodegzip(rawtext):
    bi = io.BytesIO(rawtext)
    gf = gzip.GzipFile(fileobj=bi, mode="rb")
    textdecode=gf.read()
    return textdecode

#主要的spyder类，负责发送，返回，多次处理
class patentSpyer:
    def __init__(self,requestData='手机'):
		self.url="http://www.pss-system.gov.cn/sipopublicsearch/patentsearch/smartSearch-executeSmartSearch.shtml"
		self.PatentClass=requestData
		self.Header={
		'Host':'www.pss-system.gov.cn',
		'Connection':'keep-alive',
		#'Content-Length':'150',
		'Accept':'*/*',
		'Origin':'http://www.pss-system.gov.cn',
		'X-Requested-With':'XMLHttpRequest',
		'User-Agent':'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36',
		'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
		'Referer':'http://www.pss-system.gov.cn/sipopublicsearch/patentsearch/searchHomeIndex-searchHomeIndex.shtml',
		'Accept-Encoding':'gzip, deflate',
		'Accept-Language':'zh-CN,zh;q=0.8'
		}
		self.post={
		'searchCondition.searchExp':requestData,
		'searchCondition.dbId':'VDB',
		#'resultPagination.limit':'12',
		'searchCondition.searchType':'Sino_foreign',
		'wee.bizlog.modulelevel':'0200101'
		}
		self.parseFlag=True
		self.postParserData=None
		self.cookie = cookielib.CookieJar()
		self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie))
    """发送post请求，搜索：得到基本页面
    # the first send request (post)
    #get the undecodegzip the content
    # params: opener,post ,url,header
    # return html(need to decodezip)
    #返回为解码的页面源码
    """
    def readHtml(self,opener,post,url,header):
        #需要POST的数据
        postdata=urllib.urlencode(post)
        #自定义一个请求
        req = urllib2.Request(
            url = url,
            data = postdata,
            headers = header
        )
        #访问该链接
        logging.debug("readHtml send req start")
        html=get(opener, req, 20)
        #请求次数达到20次 ，返回none ，sleep 20秒，重复请求20次，得到html页面的全部信息
        while html==None:
            logging.info("重复请求20次")
            time.sleep(20)
            html=get(opener, req, 20)
        #解码
        text=decodegzip(html)
        #判断是否返回异常页面
        judgeContent(text, opener, req)
        logging.debug("readHtml get the response")
        #打印返回的内容
        return html
    """
    get the abract content need to post param,then the server encode param before it send to client.
    we use the param that encoded ,join the url end ,then send the server (get)
    #要得到简要信息，需要post param 我们需要，用服务器编码后的post param，加入url尾部，然后发送get请求
    params post request header
    """
    def paramHeader(self):
        Header={
        'Host':'www.pss-system.gov.cn',
        'Connection':'keep-alive',
        #'Content-Length':'113',
        'Accept':'application/json, text/javascript, */*; q=0.01',
        'Origin':'http://www.pss-system.gov.cn',
        'X-Requested-With':'XMLHttpRequest',
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36',
        'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
        'Referer':'http://www.pss-system.gov.cn/sipopublicsearch/patentsearch/showViewList-jumpToView.shtml',
        'Accept-Encoding':'gzip, deflate',
        'Accept-Language':'zh-CN,zh;q=0.8'
        }
        return Header

    def paramHeaderNext(self):
        HeaderNext={
                'Host':'www.pss-system.gov.cn',
                'Connection':'keep-alive',
                #'Content-Length':'263',
                'Accept':'text/html, */*; q=0.01',
                'Origin':'http://www.pss-system.gov.cn',
                'X-Requested-With':'XMLHttpRequest',
                'User-Agent':'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36',
                'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer':'http://www.pss-system.gov.cn/sipopublicsearch/patentsearch/searchHomeIndex-searchHomeIndex.shtml',
                'Accept-Encoding':'gzip, deflate',
                'Accept-Language':'zh-CN,zh;q=0.8'
        }
        return HeaderNext

    """
    pages 需要readhtml() parse after get the total of pages
    return pagenums :total pages
    #从readHtml（）得到页面，解析出总共的页码数
    """
    def getPageNums(self):
        logging.debug("parser function:get the nums of pages:")
        # 解析第一页得到总页数
        all_the_text=self.readHtml(self.opener,self.post,self.url,self.Header)
        all_the_text_decode=decodegzip(all_the_text)
        soup=BeautifulSoup(all_the_text_decode,"lxml")
        logging.debug("get the html soup")
        TagsContext = soup.select('.page_top input')[0].attrs['onkeydown'].split(",")[3].strip("'")
        pagenums = int(TagsContext)
        return pagenums

    """
    1.readHtml get params(首页),or parse(其他页面) get params
    2. post params get params and construct url+parmas  发送请求得到编码后的param
    3.send get request 发送get请求
    4.store in sql but now we first write into files 写入文件
    """
    def getEncodeParams(self,currentpage=1):# the function name need to change ,
        #and need to update to
        #1.increase the deparser the content
        #2.and save it to sqllite
        #search first page
        if currentpage==1:
            logging.debug("readHtml function start:")
            rawtext=self.readHtml(self.opener,self.post,self.url,self.Header)
            logging.debug("readHtml end")
            rawtext_decode=decodegzip(rawtext)
            logging.debug("getEncoParamSendreq function start:")
            self.getEncoParamSendreq(currentpage,rawtext_decode)
            logging.debug("getEncoParamSendreq function end")
        else:
            pagestart=currentpage*12-12
            logging.debug("parser function start")
            rawtext_decode=self.parser(pagestart)
            logging.debug("parser function end")
            logging.debug("getEncoParamSendreq function start:")
            self.getEncoParamSendreq(currentpage,rawtext_decode)
            logging.debug("getEncoParamSendreq function end")

    """
     1 解析 得到 nrdan id 构造post param ，然后发送出去，得到编码后的param
     2 发送get请求 得到简要信息页面
     3 写入文件 html源码
    """
    #用正则表达式来匹配信息存入文件中
    def getEncoParamSendreq(self,currentpage,rawtext_decode):
        contextPath="http://www.pss-system.gov.cn"
        #contextPath="http://www.pss-system.gov.cn/sipopublicsearch"
        logging.debug("html to soup")
        soup=BeautifulSoup(rawtext_decode,"lxml")
        nrdAn=soup.findAll("input",attrs={"name":re.compile("^nrdAn")})
        sid=soup.findAll("input",attrs={"name":re.compile("^idHidden")})
        logging.debug("start to page"+str(currentpage)+" get each item")
        for j in range(0,len(nrdAn)):# range len(nrdAn) each page has len(nrdAn) items
            params={'nrdAn':nrdAn[j]["value"],
                    'cid':sid[j]["value"],
                    'sid':sid[j]["value"],
                    'wee.bizlog.modulelevel':'0201101'
                    }
            urlpost=contextPath+"/sipopublicsearch/patentsearch/showAbstractInfo-viewAbstractInfo.shtml"
            postdata=urllib.urlencode(params)
            #自定义一个请求#
            req = urllib2.Request(
                url = urlpost,
                data = postdata,
                headers=self.paramHeader()
            )
            cookie = cookielib.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie))
            urllib2.install_opener(opener)
            #访问该链接#
            logging.debug("send the param to server(to get the paramDeal that server dealed)")
            #原来是result = urllib2.urlopen(req)
            openresponse = opener.open(req)
            hjson = json.loads(decodegzip(openresponse.read()))
            if hjson==None:
                print '没有获取到该专利信息，继续下一个'
                continue
            else:
                #用txt文件来存储
                '''
                getContext=hjson['abstractInfoDTO']['abIndexList'][0]['value']
                getContextSoup=BeautifulSoup(getContext,'lxml')
                getContextText=getContextSoup.get_text().encode('UTF-8').strip().replace('\n','')
                getIPCNum=hjson['abstractInfoDTO']['abstractItemList'][4]['value'].encode('UTF-8').strip().split(';')[0].strip()
                getTittle=hjson['abstractInfoDTO']['tioIndex']['value'].encode('UTF-8').strip()
                getIDNum=hjson['abstractInfoDTO']['abstractItemList'][2]['value'].encode('UTF-8').strip()
                result=getTittle+" "+getIDNum+" "+getIPCNum+" "+getContextText
                try:
                    patentFile=open('data.txt','a+')
                    patentFile.write(result+'\n')
                except IOError:
                    print '文件操作错误'
                finally:
                    patentFile.close()
                '''
                #使用csv文件存储
                writer=csv.writer(open('data.csv','ab+'))
                getContext=hjson['abstractInfoDTO']['abIndexList'][0]['value']
                getContextSoup=BeautifulSoup(getContext,'lxml')
                getContextText=getContextSoup.get_text().encode('UTF-8').strip().replace('\n','')
                getIPCNum=hjson['abstractInfoDTO']['abstractItemList'][4]['value'].encode('UTF-8').strip().split(';')[0].strip()
                getTittle=hjson['abstractInfoDTO']['tioIndex']['value'].encode('UTF-8').strip()
                getIDNum=hjson['abstractInfoDTO']['abstractItemList'][2]['value'].encode('UTF-8').strip()
                writer.writerow([getTittle,getIDNum,getIPCNum,getContextText])



    """
        解析读取的页面：
        返回页面的信息：
        返回：
    dicts：（key ,value）对
    for d,x in dicts.items():
        print "key:"+d+",value:"+x

    def getAbContent(self,content):
        soup=BeautifulSoup(content)
        descont=soup.select(".content")
        # 摘要简介
        des=descont[0].getText().strip()
        # 其他信息
        divcont=soup.select("#abstractItemList")
        trs=divcont[0].findAll("tr",recursive=True)
        tds=divcont[0].findAll("td",recursive=True)
        tdkey=[]
        tdvalue=[]
        for i in range(len(trs)):
            tdcont=trs[i].contents
            #for t in range(len(tdcont)):
            #    str=tdcont[t].string.strip()
            #    print str,t
            tdkey.append(tdcont[1].string.strip())
            tdvalue.append(tdcont[3].string.strip())
        #转换为字典类型，key,value对
        dicts={}
        for i in range(len(tdkey)):
            logging.debug(tdkey[i])
            logging.debug(tdvalue[i])
            dicts[tdkey[i]]=tdvalue[i]

        # 标题
        titlecont=soup.select(".fmbt")
        title=titlecont[0].string.strip()
        dicts[u'发明名称']=title
        dicts[u'摘要']=des
        # dicts 里面所有类型统一为unicode类型
        for d,x in dicts.items():
            logging.debug(type(d),type(x))
            if type(d)=="str":
                d=d.decode("utf-8")
            if type(x)=="str":
                x=x.decode("utf-8")
            logging.debug("key:"+d+",value:"+x)
        return dicts
    """

    def getParserPostData(self):
        logging.debug(" parser function: readHtml start and parse:")
        # 解析第一页得到总页数和跳转页的请求参数，发送请求得到相应页面
        all_the_text=self.readHtml(self.opener,self.post,self.url,self.Header)
        logging.debug("parser function: readHtml end:")
        all_the_text_decode=decodegzip(all_the_text)
        logging.debug("the html to  soup")
        soup=BeautifulSoup(all_the_text_decode,'lxml')
        #form里面有post的name value ，commandsearchnum 里面有总pages数
        form=soup.select("#resultlistForm")
        """get the post data"""
        logging.debug("form got and start to parse and construct the postData:")
        contents= form[0].contents
        postData={}
        for i in range(len(contents)):
            postData[contents[i]['name']]=contents[i]['value']
        postData["searchCondition.searchExp"]=postData["searchCondition.searchExp"].encode("utf-8")
        self.postParserData=postData
        return self.postParserData
    """
    parser function: parse html to get the pages and post pagestart to get the content of \
    you request :pagestart represent the page
    parser 函数解析html 读取下一页
    param:需要修改 增加参数 添加 0 12 24 ... 作为页面开始, 当前函数默认值12为第二页resultlist
    return :请求的页面源码（已经解码过的）
    """
    def parser(self,pagestart=12):
        if self.parseFlag==True:
            self.getParserPostData()
            self.parseFlag=False
        #pagestart=10
        postData=self.postParserData
        #以上得到的是其他页面请求的固定信息
        postData["resultPagination.start"]=str(pagestart)
        logging.debug("the startpage %d of the htmls is: ",pagestart/12+1)
        logging.debug("postdata is:")
        logging.debug(postData)
        nextpage='showSearchResult-startWa.shtml'
        nextpageurl= 'http://www.pss-system.gov.cn/sipopublicsearch/patentsearch/'+nextpage
        post=urllib.urlencode(postData)
        req=urllib2.Request(
            url=nextpageurl,
            data=post,
            headers=self.paramHeaderNext()
        )
        logging.debug("parser function: send get:(req:showserchResult-startWa.shtml)")
        html2=get(self.opener, req, retries=10)
        #请求次数达到20次 ，返回none ，sleep 20秒，重复请求20次
        while html2==None:
            logging.info("重复请求20次")
            time.sleep(20)
            html2=get(self.opener, req, 20)
        #解码
        text=decodegzip(html2)
        #判断是否返回异常页面
        text=judgeContent(text, self.opener, req)
        logging.debug("parser function: send return (response:showsearchResult_startWa.shtml)")
        html2src=text
        return html2src