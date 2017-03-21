#coding:utf-8
'''
Created on 2016年11月17日
@author: guoshun
'''
import logging
from scrapy import patentSpyer
from scrapy import logconfig
import numpy as np
import time
import csv
if __name__=="__main__":
    logconfig()
    logging.info("the spyer start:")
    #createFile=open('data.txt','w')
    #tittle="Tittle ID IPC Abstract"
    #createFile.write(tittle+'\n')
    #createFile.close()
    createwriter=csv.writer(open('data.csv','ab+'))
    createwriter.writerow(['Tittle','ID','IPC','Abstract'])
    searchItem=["飞机 and B60N2",
                "飞机 and B64C1",
                "飞机 and B64C25",
                "飞机 and B64D11",
                "飞机 and B64F5",
                "飞机 and G06F17",
                "飞机 and G01M9",
                "飞机 and G05B17",
                "飞机 and B60F5"]
    counter=0
    for i in range(3,4):
        print searchItem[i].decode("utf-8")
        pa=patentSpyer(searchItem[i])
        num=pa.getPageNums()
        for j in range(1,num):
            counter=counter+1
            try:
                pa.getEncodeParams(j)
            except:
                print "func：当前请求下载页面出错，继续别的页面"
                continue
            sec=np.random.normal(8,4)
            if sec<=0:
                sec=2
            time.sleep(sec)
    print "finished"