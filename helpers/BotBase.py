# -*- coding: utf-8 -*-
import argparse
import datetime
import hashlib
import itertools
import os
import random
import re
import orjson
import sys
import traceback
import urllib
from contextlib import closing
import dateparser
import mysql.connector
import requests
from bs4 import BeautifulSoup
from unidecode import unidecode
import pathos
import multiprocessing
from time import sleep,time
import urllib3
import operator
import functools
import math
import pytz
import gc
from helpers.enums import *
from fuzzywuzzy import fuzz
import fcntl

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
class BotBase(object):
    def __init__(self,options):
        if options.sport is None:
            raise("Specify --sport parameter")
            
        for sprt in Sport:
            if sprt.name.lower() == options.sport.lower():
                self.sprt = sprt.value
        print("#############",self.__class__.__name__)
        self.bot_data = {"region":"it","book_name":self.__class__.__name__}
        
        self.options = options
        self.s = requests.session()
        self.event_keys = {}
        self.competition_keys = {}
        self.pinterbet_events = {}
        self.pinterbet_competitions = {}
        
        self.odds_keys = {}
        self.init_proxies()
        self.init_useragents()
        self.init_book_data()
        self.set_running()
        
        self.threads = self.options.threads or 1
        self.blacklist_proxies = []
        
        self.custom_headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.8",
            "Connection": "keep-alive",
            "User-Agent":self.get_useragent(),
        }
        self.s=requests.session()
        self.data_directory = "/tmp/Db/"+self.bot_data["book_data"]["id"]+"/"
        if not os.path.exists(self.data_directory):
            os.makedirs(self.data_directory)

    def init_useragents(self):
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_agents.txt"), "r") as f:
            self.user_agents = [line.strip() for line in f.readlines()]
            
    def init_proxies(self):
        self.proxies = []
        
        try:
            url = "http://api.buyproxies.org/?a=showProxies&pid=108979&key=15ee901de3c3b22ac319f3d6d74d5c36&port=12345"
            self.proxies = requests.get(url).text.strip().split("\n")
            if len(self.proxies) >10:
                with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "proxies.txt"), "w") as f:
                    f.write("\n".join(self.proxies))
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_obj, exc_tb)
            
        if len(self.proxies) <10:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "proxies.txt"), "r") as f:
                self.proxies = [line.strip() for line in f.readlines()]
                
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "proxies_residential.txt"), "r") as f:
            self.proxies_residential = [line.strip() for line in f.readlines()]

    def get_db(self):
        db = mysql.connector.connect(user=self.options.username, password=self.options.password, database=self.options.database, host=self.options.host)
        db.autocommit = False
        
        return db

    def init_book_data(self):
        db = self.get_db()
        try:
            sql = "SELECT id, name FROM bookies WHERE name LIKE '{0}'".format(self.bot_data["book_name"].lower())
            cur = db.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
            cur.close()

            self.bot_data["book_data"] = {
                "id": str(rows[0][0]),
                "name": rows[0][1],
            }
        finally:
            db.close()

    def set_running(self):
        db = self.get_db()
        try:
            sql = "UPDATE bookies SET status=1, start_time=NOW() WHERE id={0}".format(self.bot_data["book_data"]["id"])
            cur = db.cursor()
            cur.execute(sql)
            db.commit()
            cur.close()
        finally:
            db.close()

    def get_response(self, url, headers, proxy=None, use_residential_proxies=False, post_data=None, post_is_json=False,no_proxy=False, timeout=4, cookies=None, use_tor=False):
        if no_proxy is False:
            if use_tor:
                proxy = {"http":"socks5h://localhost:9050","https":"socks5h://localhost:9050"}
            elif use_residential_proxies:
                proxy = self.get_residential_proxy()
            else:
                proxy = self.get_proxy()
                
        elif no_proxy:
            proxy = None
            
        if self.options.noproxies:
            proxy = None
        elif self.options.usetor:
            proxy = {"http":"socks5h://localhost:9050","https":"socks5h://localhost:9050"}
        elif self.options.residentials:
            proxy = self.get_residential_proxy()
        
        response = None
        start = time()
        try:
            if post_data is None:
                response = self.s.get(url, headers=headers, proxies=proxy, cookies=cookies, verify=False,  timeout=timeout)
            else:
                if not post_is_json:
                    response = self.s.post(url, data=post_data, headers=headers, proxies=proxy, cookies=cookies, verify=False,  timeout=timeout)
                else:
                    response = self.s.post(url, json=post_data, headers=headers, proxies=proxy, cookies=cookies, verify=False,  timeout=timeout)
            #if response.status_code in [400,403,401,405,406,407]:
            #    raise Exception("error "+str(response.status_code))
                
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            #traceback.print_exception(exc_type, exc_obj, exc_tb)
            print(exc_obj)    
        return response

    def get_empty_odds_dict(self):
        empty_odds =  {'even': '','odd': '', 'no_penalty': '','penalty': '', 'sh_goal': '','sh_no_goal': '','fh_goal': '','fh_no_goal': '', 'team2_under_75': '', 'team1_over_35': '', 'team1_under_55': '', 'team1_under_35': '', 'team1_over_55': '', 'team1_under_75': '', 'team1_over_15': '', 'team2_under_55': '', 'team2_under_15': '', 'team2_under_35': '', 'team2_over_85': '', 'team1_under_85': '', 'team2_over_25': '', 'team1_over_85': '', 'team2_over_65': '', 'team2_over_05': '', 'team1_under_05': '', 'team1_over_65': '', 'team2_over_45': '', 'team1_over_45': '', 'team2_under_65': '', 'team1_under_25': '', 'team1_over_05': '', 'team2_under_25': '', 'team1_under_65': '', 'team2_under_45': '', 'team1_under_45': '', 'team1_over_25':'', 'team2_under_05': '', 'team2_under_85': '', 'team2_over_35': '', 'team2_over_15': '', 'team2_over_75': '', 'team2_over_55': '', 'team1_over_75': '', 'team1_under_15': '','sh_over_15': '', 'sh_under_35': '', 'sh_over_75': '', 'sh_over_25': '', 'sh_under_25': '', 'sh_under_55': '', 'sh_over_35': '', 'sh_over_45': '', 'sh_under_75': '', 'sh_under_65': '', 'sh_under_45': '', 'sh_under_85': '', 'sh_over_55': '', 'sh_over_85': '', 'sh_over_65': '', 'sh_under_05': '', 'sh_under_15': '', 'sh_over_05': '','sh_dc_home_draw': '','sh_dc_home_away': '','sh_dc_draw_away': '','fh_dc_home_draw': '','fh_dc_home_away': '','fh_dc_draw_away': '','dc_home_draw': '','dc_home_away': '','dc_draw_away': '', 'over_85': '', 'ht_ft_away_away': '', 'ht_ft_home_away': '', 'fh_over_35': '', 'ht_ft_draw_away': '', 'fh_away': '', 'fh_under_55': '', 'ht_ft_home_home': '', 'fh_over_75': '', 'fh_under_15': '', 'under_55': '', 'over_15': '', 'under_35': '', 'ht_ft_away_home': '', 'over_75': '', 'fh_over_05': '', 'fh_under_85': '', 'ht_ft_draw_home': '', 'ht_ft_away_draw': '', 'fh_home': '', 'fh_draw': '', 'sh_home': '', 'sh_draw': '', 'sh_away' : '', 'fh_under_65': '', 'fh_over_85': '', 'ht_ft_draw_draw': '', 'fh_under_25': '', 'over_45': '', 'under_85': '', 'under_05': '', 'over_05': '', 'fh_over_55': '', 'under_25': '', 'over_65': '', 'fh_over_15': '', 'home': '', 'fh_over_45': '', 'under_45': '', 'fh_under_75': '', 'goal': '', 'away': '', 'fh_under_35': '', 'over_35': '', 'under_75': '', 'ht_ft_home_draw': '', 'draw': '', 'under_15': '', 'fh_over_65': '', 'over_55': '', 'no_goal': '', 'fh_over_25': '', 'fh_under_45': '', 'over_25': '', 'fh_under_05': '', 'under_65': '', 'cs_00': '','cs_01': '','cs_02': '','cs_03': '','cs_04': '','cs_10': '','cs_11': '','cs_12': '','cs_13': '','cs_14': '','cs_20': '','cs_21': '','cs_22': '','cs_23': '','cs_24': '','cs_30': '','cs_31': '','cs_32': '','cs_33': '','cs_34': '','cs_40': '','cs_41': '','cs_42': '','cs_43': '','cs_44' : ''}
        return empty_odds
   
    def init_pinterbet_keys(self):
        self.pinterbet_competitions = {}
        db = self.get_db()
        try:
            sql = "select b.id,p.id from competitions b inner join competitions p on b.params=REPLACE(p.params,'|33','') where b.bookie_id = 27 and p.bookie_id = 33"
            cur = db.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
            cur.close()

            for row in rows:
                self.pinterbet_competitions[row[0]] = row[1]
                
        except Exception:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_obj, exc_tb)
        finally:
            db.close()
            
        self.pinterbet_events = {}
        db = self.get_db()
        try:
            sql = "select b.id,p.id from events b inner join events p on b.event =p.event and b.open_date = p.open_date and b.betradar_id = p.betradar_id where b.bookie_id = 27 and p.bookie_id = 33"
            cur = db.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
            cur.close()

            for row in rows:
                self.pinterbet_events[row[0]] = row[1]
                
        except Exception:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_obj, exc_tb)
        finally:
            db.close()
            
    def get_sql_file(self, file_type, book_id):
        try:
            latest_file = sorted([[os.path.join(i[0], j) for j in i[2] if file_type in j] for i in os.walk(self.data_directory)][0])[-1]
            if os.stat(latest_file).st_size > 20000:
                latest_file = os.path.join(self.data_directory, file_type+"_"+str(book_id)+"_"+str(int(time()*1000))+".sql")
        except Exception:
            latest_file = os.path.join(self.data_directory, file_type+"_"+str(book_id)+"_"+str(int(time()*1000))+".sql")

        return latest_file

        
    def commit_sql2(self,sql):
        sql_file = self.get_sql_file("save_data", self.bot_data["book_data"]["id"])
        with open(sql_file, "a+") as myfile:
            myfile.write(sql)
            
        '''
        db = self.get_db()
        try:
            cur = db.cursor()
            results = cur.execute(sql, multi=True)
            for result in results:
                pass
            db.commit()
            cur.close()
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_obj, exc_tb)
        finally:
            db.close()
        '''
        
    def commit_sql(self,sql):
        db = self.get_db()
        try:
            cur = db.cursor()
            results = cur.execute(sql, multi=True)
            for result in results:
                pass
            db.commit()
            cur.close()
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_obj, exc_tb)
        finally:
            db.close()
        
        
    def save_data(self, data):
        try:
            region = "it"
            if data and "type" in data:
                odds_data = ""
                events_data = ""
                competitions_data = ""
                update_time = datetime.datetime.now(pytz.timezone('Europe/Rome')).strftime('%Y-%m-%d %H:%M:%S')
                if data["type"] == "odds_data":
                    if str(data["bookie_id"]) == '27':
                        self.init_pinterbet_keys()
                        
                    locked_odds = []
                    for bet_type, book_odds in data["odds"].items():
                        if not book_odds:
                            continue
                        if book_odds == "-":
                            for s in Selection:
                                if s.name == bet_type.upper():
                                    locked_odds.append(s.value)
                            continue
                        try:
                            book_odds = float(book_odds)
                            if book_odds ==0:
                                for s in Selection:
                                    if s.name == bet_type.upper():
                                        locked_odds.append(s.value)
                                continue
                        except ValueError:
                            continue
                            
                        market=-1
                        selection = -1
                        if bet_type == "home":
                            market = Market.M_1X2.value
                            selection = Selection.HOME.value
                            if self.sprt != Sport.CALCIO.value:
                                market = Market.M_12.value
                        elif bet_type == "away":
                            market = Market.M_1X2.value
                            selection = Selection.AWAY.value
                            if self.sprt != Sport.CALCIO.value:
                                market = Market.M_12.value
                        elif bet_type == "draw":
                            market = Market.M_1X2.value
                            selection = Selection.DRAW.value
                        elif bet_type == "fh_home":
                            market = Market.FH_1X2.value
                            selection = Selection.FH_HOME.value
                        elif bet_type == "fh_away":
                            market = Market.FH_1X2.value
                            selection = Selection.FH_AWAY.value
                        elif bet_type == "fh_draw":
                            market = Market.FH_1X2.value
                            selection = Selection.FH_DRAW.value
                        elif bet_type == "sh_home":
                            market = Market.SH_1X2.value
                            selection = Selection.SH_HOME.value
                        elif bet_type == "sh_away":
                            market = Market.SH_1X2.value
                            selection = Selection.SH_AWAY.value
                        elif bet_type == "sh_draw":
                            market = Market.SH_1X2.value
                            selection = Selection.SH_DRAW.value
                        elif bet_type == "penalty":
                            market = Market.PENALTY_NOPENALTY.value
                            selection = Selection.PENALTY.value
                        elif bet_type == "no_penalty":
                            market = Market.PENALTY_NOPENALTY.value
                            selection = Selection.NO_PENALTY.value
                        elif bet_type == "even":
                            market = Market.EVEN_ODD.value
                            selection = Selection.EVEN.value
                        elif bet_type == "odd":
                            market = Market.EVEN_ODD.value
                            selection = Selection.ODD.value
                        elif bet_type == "goal":
                            market = Market.GNG.value
                            selection = Selection.GOAL.value
                        elif bet_type == "no_goal":
                            market = Market.GNG.value
                            selection = Selection.NO_GOAL.value
                        elif bet_type == "fh_goal":
                            market = Market.FH_GNG.value
                            selection = Selection.FH_GOAL.value
                        elif bet_type == "fh_no_goal":
                            market = Market.FH_GNG.value
                            selection = Selection.FH_NO_GOAL.value
                        elif bet_type == "sh_goal":
                            market = Market.SH_GNG.value
                            selection = Selection.SH_GOAL.value
                        elif bet_type == "sh_no_goal":
                            market = Market.SH_GNG.value
                            selection = Selection.SH_NO_GOAL.value
                        elif bet_type.startswith("dc_"):
                            market = Market.DC.value
                        elif bet_type.startswith("fh_dc_"):
                            market = Market.FH_DC.value
                        elif bet_type.startswith("sh_dc_"):
                            market = Market.SH_DC.value
                        elif bet_type.lower().startswith("under_") or bet_type.lower().startswith("over_"):
                            market = Market.OVER_UNDER.value
                        elif bet_type.lower().startswith("fh_under_") or bet_type.lower().startswith("fh_over_"):
                            market = Market.FH_OVER_UNDER.value
                        elif bet_type.lower().startswith("sh_under_") or bet_type.lower().startswith("sh_over_"):
                            market = Market.SH_OVER_UNDER.value
                        elif bet_type.lower().startswith("team1_under_") or bet_type.lower().startswith("team1_over_"):
                            market = Market.TEAM1_OVER_UNDER.value
                        elif bet_type.lower().startswith("team2_under_") or bet_type.lower().startswith("team2_over_"):
                            market = Market.TEAM2_OVER_UNDER.value
                        elif bet_type.lower().startswith("cs_"):
                            market = Market.CORRECT_SCORE.value
                        elif bet_type.lower().startswith("ht_ft_"):
                            market = Market.HT_FT.value
                        elif bet_type == "set1_home":
                            market = Market.SET1_HH.value
                        elif bet_type == "set1_away":
                            market = Market.SET1_HH.value
                        elif bet_type == "set2_home":
                            market = Market.SET2_HH.value
                        elif bet_type == "set2_away":
                            market = Market.SET2_HH.value
                        elif bet_type.lower().startswith("tb_under_") or bet_type.lower().startswith("tb_over_"):
                            market = Market.TB_OU.value
                        elif bet_type.lower().startswith("games_under_") or bet_type.lower().startswith("games_over_"):
                            market = Market.GAMES_OU.value
                        elif bet_type.lower().startswith("set1_games_under_") or bet_type.lower().startswith("set1_games_over_"):
                            market = Market.SET1_GAMES_OU.value
                        elif bet_type.lower().startswith("set2_games_under_") or bet_type.lower().startswith("set2_games_over_"):
                            market = Market.SET2_GAMES_OU.value
                        elif bet_type.lower().startswith("player1_games_under_") or bet_type.lower().startswith("player1_games_over_"):
                            market = Market.PLAYER1_GAMES_OU.value
                        elif bet_type.lower().startswith("player2_games_under_") or bet_type.lower().startswith("player2_games_over_"):
                            market = Market.PLAYER2_GAMES_OU.value
                        else:
                            continue
                         
                        if market != -1 and selection == -1:
                            for s in Selection:
                                if s.name == bet_type.upper():
                                    selection = s.value
                                    
                        book_odds = float(book_odds)
                        if selection == -1 or book_odds <1:
                            continue
                            
                        if str(data["bookie_id"]) == '27':
                            if data["event_id"] in self.pinterbet_events:
                                odds_data += 'insert into bookie_odds (event_id,bookie_id,market_id,selection_id,odds,game_play,update_time,cycle) values({0},{1},{2},{3},{4},{5},NOW(),{6}) on duplicate key update odds={4},update_time=NOW(),cycle={6},hidden=0;'.format(self.pinterbet_events[data["event_id"]], "33", market, selection, book_odds,data["game_play"],self.start_time).replace("'NULL'","NULL")
                        
                        odds_data += 'insert into bookie_odds (event_id,bookie_id,market_id,selection_id,odds,game_play,update_time,cycle) values({0},{1},{2},{3},{4},{5},NOW(),{6}) on duplicate key update odds={4},update_time=NOW(),cycle={6},hidden=0;'.format(data["event_id"], data["bookie_id"], market, selection, book_odds,data["game_play"],self.start_time).replace("'NULL'","NULL")
                        
                    
                elif data["type"] == "events_data" and len(data["events"]) >0:
                    if str(data["bookie_id"]) == '27':
                        self.init_pinterbet_keys()
                        
                    for event in data["events"]:
                        dat = datetime.datetime.strptime(event["open_date"], "%Y-%m-%d %H:%M:%S")
                        if dat < datetime.datetime.now():
                            continue
                            
                        betradar_id = event["betradar_id"]
                        if len(str(betradar_id)) <3 or betradar_id is None:
                            betradar_id = "NULL"
                        
                        params = '{\\"event_id\\":\\"'+str(event["event_id"])+'\\",\\"params\\":\\"'+str(event["params"])+'\\"}'
                        if str(data["bookie_id"]) == "27":
                            params = '{\\"event_id\\":\\"'+str(event["event_id"])+'|33\\",\\"params\\":\\"'+str(event["params"])+'\\"}'
                            if data["competition_id"] in self.pinterbet_competitions:
                                if betradar_id is None or betradar_id == "NULL":
                                    events_data += 'insert into events (event,open_date,betradar_id,bookie_id,params,competition_id,update_time) values ("{0}","{1}",{2},{3},"{4}",{5},NOW()) on duplicate key update event="{0}",open_date="{1}",update_time=NOW(),params="{4}";'.format((event["home"]+" v "+event["away"]),event["open_date"],betradar_id,"33",params,self.pinterbet_competitions[data["competition_id"]]).replace('"NULL"','NULL')
                                else:
                                    events_data += 'insert into events (event,open_date,betradar_id,bookie_id,params,competition_id,update_time) values ("{0}","{1}",{2},{3},"{4}",{5},NOW()) on duplicate key update event="{0}",open_date="{1}",betradar_id={2},update_time=NOW(),params="{4}";'.format((event["home"]+" v "+event["away"]),event["open_date"],betradar_id,"33",params,self.pinterbet_competitions[data["competition_id"]]).replace('"NULL"','NULL')
                        if betradar_id is None or betradar_id == "NULL":
                            events_data += 'insert into events (event,open_date,betradar_id,bookie_id,params,competition_id,update_time) values ("{0}","{1}",{2},{3},"{4}",{5},NOW()) on duplicate key update event="{0}",open_date="{1}",update_time=NOW(),params="{4}";'.format((event["home"]+" v "+event["away"]),event["open_date"],betradar_id,data["bookie_id"],params,data["competition_id"]).replace('"NULL"','NULL')
                        else:
                            events_data += 'insert into events (event,open_date,betradar_id,bookie_id,params,competition_id,update_time) values ("{0}","{1}",{2},{3},"{4}",{5},NOW()) on duplicate key update event="{0}",open_date="{1}",betradar_id={2},update_time=NOW(),params="{4}";'.format((event["home"]+" v "+event["away"]),event["open_date"],betradar_id,data["bookie_id"],params,data["competition_id"]).replace('"NULL"','NULL')
                    
                    if events_data:
                        self.commit_sql(events_data) 
                        sleep(1)
                        
                        
                    if "odds" in data["events"][0]:
                        self.init_event_keys()
                        if str(data["bookie_id"]) == "27":
                            self.init_pinterbet_keys()
                            
                        for event in data["events"]:
                            betradar_id = event["betradar_id"]
                            if len(str(betradar_id))<3 or betradar_id is None:
                                betradar_id = "NULL"
                                
                            game_play = 1
                            if "game_play" in event:
                                game_play = event["game_play"]
                                
                            event_id = None
                            if "id" in event:
                                event_id = event["id"]
                            else:
                                event_hash = hashlib.md5((event["home"]+" v "+event["away"]+str(data["competition_id"])+data["bookie_id"]).encode('utf-8')).hexdigest()
                                if event_hash in self.event_keys:
                                    event_id = self.event_keys.get(event_hash,None)
                            if event_id:
                                dt = {"type": "odds_data","betradar_id":betradar_id,"event_id":event_id,"odds":event["odds"],"game_play":game_play,"bookie_id":data["bookie_id"]}
                                self.save_data(dt)
                            
                elif data["type"] == "competitions_data" and len(data["competitions"]) >0:
                
                    for competition in data["competitions"]:
                        if not max([c in competition["competition_name"].lower() or c in competition["country_name"].lower() for c in ["speciali","sanzioni","minuto 1° goal","calci d'angolo"]]):
                            competitions_data += 'insert into competitions (competition,sport_id,country,bookie_id,params,update_time) values ("{0}",{1},"{2}",{3},"{4}",NOW()) on duplicate key update update_time=NOW();'.format((competition["competition_name"]),self.sprt,competition["country_name"],data["bookie_id"],(competition["params"])).replace('"NULL"','NULL')
                            if str(data["bookie_id"]) == "27":
                                competitions_data += 'insert into competitions (competition,sport_id,country,bookie_id,params,update_time) values ("{0}",{1},"{2}",{3},"{4}",NOW()) on duplicate key update update_time=NOW();'.format((competition["competition_name"]),self.sprt,competition["country_name"],"33",(competition["params"]+"|33")).replace('"NULL"','NULL')
                
                if competitions_data and odds_data:
                    self.commit_sql(competitions_data+odds_data)   
                else:
                    if competitions_data:
                        self.commit_sql(competitions_data) 
                    elif odds_data:
                        self.commit_sql(odds_data)

                if str(self.bot_data["book_data"]["id"]) == "2" and competitions_data and "events" in data["competitions"][0]:
                    self.init_competition_keys()
                    for competition in data["competitions"]:
                        competition_hash = hashlib.md5((competition["competition_name"]+str(self.bot_data["book_data"]["id"])+str(self.sprt)+competition["country_name"]).encode('utf-8')).hexdigest()
                        if len(competition["events"]) and competition_hash in self.competition_keys:
                            competition_id = self.competition_keys[competition_hash]
                            events_data = {"type": "events_data","events":competition["events"],"competition_id":competition_id,"bookie_id":self.bot_data["book_data"]["id"]}
                            self.save_data(events_data)                                
                    
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_obj, exc_tb)

    def get_proxy(self):
        random_proxy = random.choice(self.proxies)
        ip,port,username,password = random_proxy.split(":")
        url_proxy = "http://{2}:{3}@{0}:{1}".format(ip,port,username,password)
        url_proxy = "http://{0}:{1}".format(ip,port,username,password)
        return {"http":url_proxy, "https":url_proxy}
        #return {"http":url_proxy}

    def get_residential_proxy(self):
        #return self.get_proxy()
        random_proxy = random.choice(self.proxies_residential)
        return {"http":"http://" + random_proxy, "https":"http://" + random_proxy}
        #return {"http":"http://ninjabet:ninja2020@it.smartproxy.com:20000", "https":"http://ninjabet:ninja2020@it.smartproxy.com:20000"}
        
    def get_useragent(self):
        return random.choice(self.user_agents)
    
    def get_chunks(self,all_data,size):
        new_stack = []
        end = len(all_data)
        length = int(end/size)
        if end-size<self.threads:
            length=1
        for start in range(0,end,length):
            new_stack.append(all_data[start:start+length])
        return new_stack
        
    def process_leagues(self):
        self.start_time2 = 0
        all_competitions = []
        
        while 1:
            try:
                got_events = False
                if self.sprt != Sport.CALCIO.value and (time() - self.start_time2) >= 60 or self.sprt == Sport.CALCIO.value and (time() - self.start_time2) >= 600:
                    self.start_time2 = int(time())
                    all_competitions = self.get_leagues(self.sprt)
                    
                    if(len(all_competitions) > 0): 
                        data = {"type": "competitions_data","competitions":all_competitions,"bookie_id":self.bot_data["book_data"]["id"]}
                        self.save_data(data)
                        
                        for competition in all_competitions:
                            try:
                                if not max([c  in competition["competition_name"].lower() or c in competition["country_name"].lower() for c in ["speciali","sanzioni","minuto 1° goal","calci d'angolo"]]):
                                    if "events" in competition and "competition_id" in competition:
                                        self.start_time2=0
                                        bookie_id = self.bot_data["book_data"]["id"]
                                        events_data = {"type": "events_data","events":competition["events"],"competition_id":competition["competition_id"],"bookie_id":bookie_id}
                                        self.save_data(events_data)
                                        got_events = True
                            except Exception:
                                exc_type, exc_obj, exc_tb = sys.exc_info()
                                traceback.print_exception(exc_type, exc_obj, exc_tb)
                                
                    else:
                        self.start_time2 = 0
                        
                if got_events is False:
                    all_competitions = self.get_saved_competitions()
                    for competition in all_competitions:
                        try:
                            if "events" not in competition and (not max([c  in competition["competition_name"].lower() or c in competition["country_name"].lower() for c in ["speciali","sanzioni","minuto 1° goal","calci d'angolo"]])):
                                self.process_leagues_v2(competition)
                        except Exception:
                            exc_type, exc_obj, exc_tb = sys.exc_info()
                            traceback.print_exception(exc_type, exc_obj, exc_tb)
                
                sys.stdout.flush()
                sys.stderr.flush()
                gc.collect()
                sleep(2)
            except Exception:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                traceback.print_exception(exc_type, exc_obj, exc_tb)
               
    def process_leagues_v2(self,competition):
        try:
            if "params" in competition  and competition["params"] != None and competition["params"] != "NULL":
                events = self.get_league_events(competition["params"])       
                
                if events and len(events)>0:
                    bookie_id = self.bot_data["book_data"]["id"]
                    data = {"type": "events_data","events":events,"competition_id":competition["competition_id"],"bookie_id":bookie_id}
                    self.save_data(data)
                
        except Exception:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_obj, exc_tb)
            
    def process_events(self,event):
        try:
            event_odds = self.get_event_odds(event["params"])
            all_book_odds = event_odds["odds"]
            game_play = event_odds["game_play"]
            
            if all_book_odds:
                bookie_id = self.bot_data["book_data"]["id"]
                data = {"type": "odds_data","event_id":event["id"],"odds":all_book_odds,"game_play":game_play,"bookie_id":bookie_id}
                self.save_data(data)
        except Exception:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_obj, exc_tb)
    
    def get_matched_bookie_events(self):
        all_events = []
        db = self.get_db()
        try:
            sql = "select e.id,e.params,md5(CONCAT(e.event,e.competition_id,e.bookie_id)) from events as e inner join competitions as c on c.id=e.competition_id where e.bookie_id={0} and c.sport_id={1} and e.open_date>NOW()".format(self.bot_data["book_data"]["id"],self.sprt)
            cur = db.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
            cur.close()

            for row in rows:
                try:
                    param = orjson.loads(row[1].replace("'",'"'))
                    if "params" not in param or param["params"] == None or param["params"] == "NULL":
                        continue
                    all_events.append({"id":row[0],"params":param["params"]})
                    self.event_keys[row[2]] = row[0]
                except Exception:
                    pass
        except Exception:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_obj, exc_tb)
        finally:
            db.close()
        
        return all_events
        
    def get_saved_competitions(self):
        self.competition_keys = {}
        all_competitions = []
        db = self.get_db()
        try:
            sql = "select id,competition,bookie_id,sport_id,country,params from competitions where bookie_id={0} and sport_id={1} and TIMESTAMPDIFF(HOUR,update_time,NOW()) < 4 ".format(self.bot_data["book_data"]["id"],self.sprt)
            cur = db.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
            cur.close()
            if len(rows) == 0:
                sql = "select id,competition,bookie_id,sport_id,country,params from competitions where bookie_id={0} and sport_id={1} ".format(self.bot_data["book_data"]["id"],self.sprt)
                cur = db.cursor()
                cur.execute(sql)
                rows = cur.fetchall()
                cur.close()
                
            for row in rows:
                if row[4] != None and row[4] != "NULL":
                    all_competitions.append({"params":row[5],"country_name":row[4],"competition_name":row[1],"competition_id":row[0]})
                competition_hash = hashlib.md5((row[1]+str(row[2])+str(row[3])+str(row[4]).replace("None","NULL")).encode('utf-8')).hexdigest()
                self.competition_keys[competition_hash] = row[0]
                
        except Exception:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_obj, exc_tb)
        finally:
            db.close()
            
        return all_competitions
       
    def init_competition_keys(self):
        self.competition_keys = {}
        db = self.get_db()
        try:
            
            sql = "select id,competition,bookie_id,sport_id,country from competitions where bookie_id={0} and sport_id={1}".format(self.bot_data["book_data"]["id"],self.sprt)
            cur = db.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
            cur.close()

            for row in rows:
                competition_hash = hashlib.md5((row[1]+str(row[2])+str(row[3])+str(row[4]).replace("None","NULL")).encode('utf-8')).hexdigest()
                self.competition_keys[competition_hash] = row[0]                
        finally:
            db.close()
    
    def init_event_keys(self):
        self.event_keys = {}
        db = self.get_db()
        try:
            
            sql = "select e.id,e.event,e.competition_id,e.bookie_id from events as e where e.bookie_id={0}".format(self.bot_data["book_data"]["id"])
            cur = db.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
            cur.close()

            for row in rows:
                event_hash = hashlib.md5((row[1]+str(row[2])+str(row[3])).encode('utf-8')).hexdigest()
                self.event_keys[event_hash] = row[0]                
        finally:
            db.close()
    
    def hide_old_odds(self):
        sql = "update bookie_odds set hidden = 1 \
                   where bookie_id = {0} \
                     and cycle in ( \
                       select * from ( \
                         select cycle \
                         from bookie_odds \
                         where bookie_id = {1} \
                         and event_id in (select id from events where competition_id in (select id from competitions where sport_id = 1)) \
                         group by cycle order by cycle desc limit 100 offset 2 \
                       ) a)".format(self.bot_data["book_data"]["id"],self.sprt)
        self.commit_sql(sql)
                       
    def run2(self):
        all_leagues = []
        while 1:
            try:
                all_leagues = self.get_saved_competitions()
                if len(all_leagues) == 0:
                    sleep(10)
                    continue
                    
                if all_leagues:
                    self.s = requests.session()
                    self.start_time = int(time())
                    
                    if self.threads==1:
                        for league in all_leagues:
                            self.process_leagues_v2(league)
                    else:
                        try:
                            with closing(pathos.multiprocessing.Pool(processes=self.threads)) as p:
                                results = p.map_async(self.process_leagues_v2, all_leagues).get(timeout=1200)
                                p.terminate()
                        except KeyboardInterrupt:
                            p.terminate()
                            p.join()
                            sys.exit()
                    
                    #self.hide_old_odds()
                    
                sys.stdout.flush()
                sys.stderr.flush()
                gc.collect() 
            except Exception:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                traceback.print_exception(exc_type, exc_obj, exc_tb)
            
                
            sleep(2)
            
    def run(self):
        self.start_time = int(time())
        events_thread = multiprocessing.Process(target=self.process_leagues)
        events_thread.start()
        
        sleep(20)
        if "get_event_odds" in dir(self):
            while 1:
                try:
                    all_events = self.get_matched_bookie_events()
                    if len(all_events) == 0:
                        self.run2()
                        sleep(10)
                        continue
                        
                    if all_events:
                        self.s = requests.session()
                        self.start_time = int(time())
                        if self.threads==1:
                            for event in all_events:
                                self.process_events(event)
                        else:
                            try:
                                with closing(pathos.multiprocessing.Pool(processes=self.threads)) as p:
                                    results = p.map_async(self.process_events, all_events).get(timeout=1200)
                                    p.terminate()                                    
                            except KeyboardInterrupt:
                                p.terminate()
                                p.join()
                                sys.exit()
                        
                        #self.hide_old_odds()
                        
                    sys.stdout.flush()
                    sys.stderr.flush()
                    gc.collect()
                except Exception:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    traceback.print_exception(exc_type, exc_obj, exc_tb)
                
                sleep(2)
        else:
            self.run2() 
                
            sys.stdout.flush()
            sys.stderr.flush()
            gc.collect()                
            print("cycle complete")
            sleep(1)
        
        
            
