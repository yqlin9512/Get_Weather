#encoding: utf-8
import time
from requests import get
import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm
import json
import datetime
import numpy as np
import sys
import random



def get_json_value(json_data, key_name,citynumber):
    '''获取到json中任意key的值,结果为list格式[city name,city id]'''
    values_list = pd.DataFrame(columns=['name','areaid'])
    namelist,areaidlist=[],[]
    for item, values in json_data.items():
        for key in list(values.keys())[0:citynumber]:
            for i,v in values[key].items():
                areaid=v[key_name]
                areaname = item+str('_')+key+str('_')+i
                if i==key:
                    areaidlist.append(areaid)
                    namelist.append(areaname)
    values_list['name']=namelist
    values_list['areaid']=areaidlist
    # key的值不为空字符串或者为empty（用例中空固定写为empty）返回对应值，否则返回empty
    return values_list


##{'od21': '时间', 'od22': '温度', 'od23': '7', 'od24': '风向', 'od25': '风力级', 'od26': '降水量mm', 'od27': '相对湿度%', 'od28': '空气质量AQI'}
def Get_weatherinfo(city_list,savefile):
    '''根据城市id从网站获取近24h实况天气数据'''
    city_before = pd.read_csv(savefile)     #读取之前已保存的过往数据
    city_pd = []
    city_pd.append(city_before)
    daystart = datetime.datetime.now()
    print('\n查询时间：',daystart.strftime('%Y-%m-%d %Hh:%Mm:%Ss'))
    for i in tqdm(range(city_list.shape[0])):
        cityid = city_list.loc[i,'areaid']
        city = city_list.loc[i,'name']
        print("\n开始查询城市：%s，城市id为：%s"%(city,cityid))
        # 进入查询主界面爬取基础信息
        url = list_url % {'key': cityid}
        res = get(url, headers=headers)
        res.encoding = 'utf-8'
        html = res.text
        soup = BeautifulSoup(html, 'html.parser')
        script = soup.find("script", text=lambda text: text and "var observe24h_data" in text)
        text = script.string[1:-1].split(' = ')[1].split(';')[0]        #将字符串形式的“observe24h_data从script中剥离出来”
        od = json.loads(text)
        # daynow = datetime.strftime(datetime.now(), '%Y%m%d-%Hh%Mm%Ss')
        winfo = reformat_weather(city,cityid,od,daystart)
        city_pd.append(winfo)
        time.sleep(random.randint(3,10))
    city_weather = pd.concat(city_pd,ignore_index=True)     #合并各城市结果，和过往天气结果
    city_weather_single = city_weather.drop_duplicates(['area_id','date','od21'],keep='first',inplace=False)       #对过往天气结果进行去重处理，保留最新爬取结果
    city_weather_sorted = city_weather_single.sort_values(by=['area_id','date','od21'],ascending=[True,True,True])      #对数据重排序，以城市>日期>整点时间升序排列
    city_weather_sorted.to_csv(savefile,encoding="utf_8_sig",index=False)
    print('天气数据已保存：',savefile)
    dayend = datetime.datetime.now()
    print('查询 %d 个城市，共耗时：%s'%(city_list.shape[0],dayend-daystart))
    return city_weather_sorted


##[{'od21': '08', 'od22': '23', 'od23': '62', 'od24': '东北风', 'od25': '2', 'od26': '0', 'od27': '75', 'od28': ''},{...},{...}]
def reformat_weather(name,id,weather_info,daynow):
    '''将网站获取的数据重整理，加上日期序列区分近24h的具体时间'''
    today = daynow.strftime('%Y-%m-%d')
    yesterday = (daynow +datetime.timedelta(days=-1)).strftime('%Y-%m-%d')
    col=['area_name','area_id','date','od21','od22','od23','od24','od25','od26','od27','od28','acquisition_time']
    weather_pd = pd.DataFrame(columns=col)
    temp=[]
    weather_list = weather_info['od']['od2']
    for i in range(len(weather_list)):
        info = weather_list[i]
        for c in col:
            if c.startswith('od'):
                weather_pd.loc[i,c]=info[c]
    index0 = weather_pd[weather_pd['od21']==str('00')].index.values[0]
    weather_pd['area_name']=name
    weather_pd['area_id'] = id
    for j in weather_pd.index.values:
        if j<=index0:
            weather_pd.loc[j,'date']=str(today)+str(' ')+str(weather_pd.loc[j,'od21']).zfill(2)+str('h')
        else:
            weather_pd.loc[j,'date']=str(yesterday)+str(' ')+str(weather_pd.loc[j,'od21']).zfill(2)+str('h')
    weather_pd['acquisition_time'] = daynow.strftime('%Y-%m-%d %Hh:%Mm')
    return weather_pd




if __name__ == '__main__':
    # 定义参数
    headers = {'Host': 'www.weather.com.cn',
               'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36',
               'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
               'Accept-Language': 'zh-CN,zh;q=0.9',
               'Accept-Encoding': 'gzip, deflate',
               'Connection': 'keep-alive'}
    list_url = 'http://www.weather.com.cn/weather1d/%(key)s.shtml'  # 气象网，查询实况天气，近24小时天气，以城市id查询

    ##路径配置
    citypath = r'F:\python_project\weather\China_Weather_Website\city.json'
    savefile = r'F:\python_project\weather\weather_data\city_weather.csv'

    #去重
    city_weather = pd.read_csv(savefile)
    city_weather_single = city_weather.drop_duplicates(['area_id','date','od21'],keep='first',inplace=False)       #对过往天气结果进行去重处理，保留最新爬取结果
    city_weather_sorted = city_weather_single.sort_values(by=['area_id','date','od21'],ascending=[True,True,True])      #对数据重排序，以城市>日期>整点时间升序排列
    city_weather_sorted.to_csv(savefile,encoding="utf_8_sig",index=False)


    ##内置城市id库测试
    with open(citypath, 'r', encoding='utf-8') as fp:
        cityjson = json.load(fp)
    arealist = get_json_value(cityjson, 'AREAID',1)
    citycode = arealist['areaid']
    arealist.to_csv(citypath.split('.')[0] + str('_info.csv'), index=False)
    # city = {"北京": "101010100", "上海": "101020100", "广州": "101280101", "海口": "101310101"}
    # pcode = city.values()

    weather_result=Get_weatherinfo(arealist,savefile)