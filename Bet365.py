# -*- coding: utf-8 -*-
import datetime
import pytz
import re
import sys
import traceback
from contextlib import closing
from time import sleep, time
import requests
from bs4 import BeautifulSoup
from pathos import multiprocessing
import hashlib
import dateparser
import urllib
import math
from decimal import Decimal
import os
from helpers.enums import *
from helpers.BotBase import BotBase


class Bet365(BotBase):
    def __init__(self,options):
        BotBase.__init__(self,options)
        self.config_url = "https://www.bet365.it/defaultapi/sports-configuration?_h=LXvWHr75NcwwAdQxN9vmaQ=="
        self.num = 0
        self.custom_headers.update({"referer":"https://www.bet365.it/"})

    def decrypt_odd(self,msg, TK):
        key = ord(TK[0]) ^ ord(TK[1])
        value = ''
        for char in msg:
            value += chr(ord(char) ^ key)
        numerator, denominator = value.split("/")
        return float(math.floor((Decimal(numerator) / Decimal(denominator) + 1) * 100)) / 100

    def get_response(self, url, headers, proxy=None, use_residential_proxies=False, post_data=None, post_is_json=False,no_proxy=False, timeout=5, cookies=None, use_tor=False):
        if no_proxy is False:
            if not proxy and use_residential_proxies is False and len(self.blacklist_proxies) < len(self.proxies) * 0.5:
                proxy = self.get_proxy()
                while proxy in self.blacklist_proxies:
                    proxy = self.get_proxy()

            if use_tor:
                proxy = {"http":"socks5h://localhost:9050","https":"socks5h://localhost:9050"}
            elif use_residential_proxies:
                proxy = self.get_residential_proxy()
                
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
                response = self.s.get(url, headers=headers, proxies=proxy, cookies=cookies, verify=False, allow_redirects=True, timeout=timeout)
            else:
                if not post_is_json:
                    response = self.s.post(url, data=post_data, headers=headers, proxies=proxy, cookies=cookies, verify=False, allow_redirects=True,  timeout=timeout)
                else:
                    response = self.s.post(url, json=post_data, headers=headers, proxies=proxy, cookies=cookies, verify=False, allow_redirects=True, timeout=timeout)
            #if response.status_code in [400,403,401,405,406,407]:
            #    raise Exception("error "+str(response.status_code))
                
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            #traceback.print_exception(exc_type, exc_obj, exc_tb)
            #if proxy not in self.blacklist_proxies and not use_residential_proxies and str(e) in ["error 400","error 403","error 401","error 405","error 406","error 407"]:
            #    self.blacklist_proxies.append(proxy)
                
        return response
        
    def get_sync_token(self):
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync_token.txt"), "r") as f:
            return f.read().strip()
            
    def get_leagues(self,sprt):
        all_leagues = {}
        sport_codes = {Sport.CALCIO.value:"B1",Sport.TENNIS.value:"B13",Sport.BASKET.value:"B18",Sport.TENNISTAVOLO.value:"B92",Sport.ESPORTS.value:"B151"}
        try:
            
            if self.s.cookies.get("pstk") is None:
                url = "https://www.bet365.it/"
                init_page_request = self.get_response(url, self.custom_headers, cookies={"aps03":"cf=N&cg=0&cst=0&ct=97&hd=N&lng=6&tzi=4","rmbs":"3"})
                config_url = init_page_request.headers["Link"].split(";")[0].replace("<","").replace(">","")
                if "configuration" in config_url:
                    self.config_url = "https://www.bet365.it"+config_url
                    init_page_request = self.get_response(self.config_url, self.custom_headers, cookies={"aps03":"cf=N&cg=0&cst=0&ct=97&hd=N&lng=6&tzi=4","rmbs":"3"}, use_residential_proxies = True)

            
            if self.s.cookies.get("pstk"):  
                self.custom_headers.update({"X-Net-Sync-Term": self.get_sync_token()})
                if sprt == Sport.CALCIO.value:
                    #all_leagues = [{"params":"#AC#B1#C1#D1002#E64212005#G40#H^1#","country_name":"Europa","competition_name":"Qualificazioni Coppa del Mondo"}]
                    url = "https://www.bet365.it/SportsBook.API/web?lid=6&zid=0&pd=%23AS%23B1%23&cid=97&cgid=4&ctid=97"
                    main_page_request = self.get_response(url, self.custom_headers,  use_residential_proxies = True)

                    if  main_page_request:
                        for league in re.findall("\|PA;NA=([^;]+);PD=([^;]+);IT=[^;]+;FF=;", main_page_request.content.decode().replace("\r", "").replace("\n", "")):
                            country_name = competition_name = league[0]
                            
                            if len(competition_name.split(" - ")) == 2:
                                country_name,competition_name = [c.strip() for c in competition_name.split(" - ")]
                                all_leagues["#AC"+league[1]] = {"params":"#AC"+league[1],"country_name":country_name,"competition_name":competition_name}
                            elif "UEFA" in competition_name:
                                all_leagues["#AC"+league[1]] = {"params":"#AC"+league[1],"country_name":country_name,"competition_name":competition_name}
                                
                                
                        for country in re.findall("\|MA;PD=([^;]+);IT=[^;]+;SY=sm;PY=spa;NA=([^;]+);", main_page_request.content.decode().replace("\r", "").replace("\n", "")):
                            if "UEFA" not in country[1].upper() and country[1] not in ["Popolari","Partite tra nazionali","Calcio Virtuale","Asiatiche","Cartellini","Calci d’angolo","Goal","1°/2° Tempo","Giocatore","Speciali","Minuti"]:
                                country_name = country[1] 
                                
                                url = "https://www.bet365.it/SportsBook.API/web?lid=6&zid=0&pd="+urllib.parse.quote_plus(country[0])+"&cid=97&cgid=4&ctid=97"
                                country_request = self.get_response(url, self.custom_headers,  use_residential_proxies = True)
                                if country_request:
                                    for league in re.findall("\|PA;NA=([^;]+);PD=([^;]+);IT=[^;]+;FF=;", country_request.content.decode().replace("\r", "").replace("\n", "")):
                                        competition_name = league[0]
                                        if len(competition_name.split(" - ")) == 2:
                                            country_name,competition_name = [c.strip() for c in competition_name.split(" - ")]
                                        if "UEFA" in competition_name.upper() or "UEFA" in country_name.upper() or "Elenco" in country_name or "Elenco" in competition_name:
                                            continue

                                        all_leagues["#AC"+league[1]] = {"params":"#AC"+league[1],"country_name":country_name,"competition_name":competition_name}
                        
                elif sprt == Sport.BASKET.value:
                    url = "https://www.bet365.it/SportsBook.API/web?lid=6&zid=0&pd=%23AS%23"+sport_codes[sprt]+"%23&cid=97&ctid=97"
                    main_page_request = self.get_response(url, self.custom_headers,  use_residential_proxies = True)
                    if  main_page_request:
                        for league in re.findall("\|MG;NA=([^;]+);DO=[^;]+;PD=([^;]+);", main_page_request.content.decode().replace("\r", "").replace("\n", "")):
                            competition_name = league[0].strip()
                            country_name = ""
                            if len(competition_name.split(" - ")) == 2:
                                country_name,competition_name = [c.strip() for c in competition_name.split(" - ")]
                            if "Elenco" in country_name or "Elenco" in competition_name or "D48#E1453#F10#" not in league[1][3:-3]:
                                continue    
                            all_leagues["#AC"+league[1][3:-3]] = {"params":"#AC"+league[1][3:-3],"country_name":country_name,"competition_name":competition_name}
                            
                elif sprt in [Sport.TENNIS.value]:#,Sport.TENNISTAVOLO.value]:
                    url = "https://www.bet365.it/SportsBook.API/web?lid=6&zid=0&pd=%23AC%23"+sport_codes[sprt]+"%23C1%23D50%23E2%23F163%23&cid=97&ctid=97"
                    main_page_request = self.get_response(url, self.custom_headers, use_residential_proxies = True)
                    if  main_page_request:
                        resp = main_page_request.content.decode().replace("\r", "").replace("\n", "")
                        tk = re.search(r"TK=([^;]*);", resp).group(1)[:2]
                        
                        league_container = []
                        for section1 in resp.split("|MG;ID="):
                            
                            section = re.search(";NA=([^;]+);SY=fh;IA=1;DO=1;",section1)
                            if section is None:
                                continue
                                
                            section = section.group(1)
                            competition_name = section.split(" - ")[0].strip()
                            
                            country_name = ""
                            
                            if "Elenco" in country_name or "Elenco" in competition_name:
                                continue
                                
                            if country_name+competition_name in league_container:
                                continue                           

                            league_container.append(country_name+competition_name)  
                            all_events = []
                            for event in re.findall("\|PA;ID=[^;]+;NA=([^;]+);N2=([^;]+);FD=([^;]+);FI=([^;]+);BC=([^;]+);LI=[^;]+;(.*?)\|PA;",section1):
                                home = event[0]
                                away = event[1]
                                name = event[2]
                                event_id = event[3]
                                hour_diff = int(datetime.datetime.now(pytz.timezone('Europe/Rome')).utcoffset().total_seconds()/3600)
                                open_date = (datetime.datetime.strptime(event[4].strip(), '%Y%m%d%H%M%S') + datetime.timedelta(hours=hour_diff)).strftime('%Y-%m-%d %H:%M:%S')
                                dat = datetime.datetime.strptime(open_date, "%Y-%m-%d %H:%M:%S")
                                

                                if " @ " in name:
                                    away,home = name.split(" @ ")
                                betradar_id = "NULL"
                                try:
                                    betradar_id = re.search(".*match/(\d+)~Bet365Stats.*", event[4]).group(1)
                                except Exception:
                                    pass
                                    
                                event_hash = hashlib.md5((home + away + str(event_id)).encode('utf-8')).hexdigest()
                                                                                
                                event_odds = re.findall("FI={0};OD=([^;]+);".format(event_id), resp) 

                                print(name,open_date,event_odds)
                                if len(event_odds) == 2:
                                    all_book_odds = self.get_empty_odds_dict()
                                    if " @ " in name:
                                        all_book_odds["home"] = self.decrypt_odd(event_odds[1], tk)
                                        all_book_odds["away"] = self.decrypt_odd(event_odds[0], tk)
                                    else:
                                        all_book_odds["home"] = self.decrypt_odd(event_odds[0], tk)
                                        all_book_odds["away"] = self.decrypt_odd(event_odds[1], tk)
                                    event_data = {"event_id":event_hash,"open_date":open_date,"home":home,"away":away,"betradar_id":betradar_id,"params":"NULL","odds":all_book_odds}
                                    all_events.append(event_data)

                                    #print(country_name,competition_name,name,open_date,all_book_odds["home"],all_book_odds["away"])
                            all_leagues["bet365-"+str(self.sprt)+"-"+country_name+"-"+competition_name] = {"country_name":country_name,"competition_name":competition_name,"events":all_events,"params":"bet365-"+str(self.sprt)+"-"+country_name+"-"+competition_name} 

                                    
                                
        except Exception:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_obj, exc_tb)
        print(list(all_leagues.values())) 
        return list(all_leagues.values())

    def get_event_odds(self,event_params):
        event_url,home,away = event_params.split(":")
        all_book_odds = self.get_empty_odds_dict()
        try:
            self.custom_headers.update({"X-Net-Sync-Term": self.get_sync_token()})
            self.num = self.num+1
            if self.num >6:
                self.s=requests.session()
                self.num=0

            if self.s.cookies.get("pstk") is None:
                url = "https://www.bet365.it/"
                init_page_request = self.get_response(url, self.custom_headers, cookies={"aps03":"cf=N&cg=0&cst=0&ct=97&hd=N&lng=6&tzi=4","rmbs":"3"})
                config_url = init_page_request.headers["Link"].split(";")[0].replace("<","").replace(">","")
                if "configuration" in config_url:
                    self.config_url = "https://www.bet365.it"+config_url
                    init_page_request = self.get_response(self.config_url, self.custom_headers, cookies={"aps03":"cf=N&cg=0&cst=0&ct=97&hd=N&lng=6&tzi=4","rmbs":"3"}, use_residential_proxies = True)
            
            if self.s.cookies.get("pstk"):
                for x in [1, 6]:#[1, 6, 7]:
                    try:
                        url = "https://www.bet365.it/SportsBook.API/web?lid=6&zid=0&pd={0}&cid=97&ctid=97".format(urllib.parse.quote_plus(re.sub("#F3.*$", "#F3#H0#I"+str(x)+"#R1", event_url)))
                        event_page_request = self.get_response(url, self.custom_headers, use_residential_proxies = True)
                        if event_page_request:
                            event_page_content = event_page_request.content.decode().replace("\r", "").replace("\n", "")
                            
                            event_tk = re.search(r"TK=([^;]*);", event_page_content)
                            if not event_tk:
                                event_tk = "BB"
                            else:
                                event_tk = event_tk.group(1)[:2]

                            section_search = re.search(".*(NA=Risultato finale;.*?MG;)", event_page_content)
                            if section_search:
                                section = section_search.group(1)
                                odds = re.findall("OD=([^;]+);", section)
                                if len(odds) == 3:
                                    all_book_odds["home"] = self.decrypt_odd(odds[0], event_tk)
                                    all_book_odds["draw"] = self.decrypt_odd(odds[1], event_tk)
                                    all_book_odds["away"] = self.decrypt_odd(odds[2], event_tk)
                            
                            uo_25_section_search = re.search("NA=(Goal: under/over;.*?NA=2\.5.*?MG;)", event_page_content)
                            if uo_25_section_search:
                                uo_25_section = uo_25_section_search.group(1)
                                uo_25_odds = re.findall("PA;[^(PA)]*?OD=([^;]+?);", uo_25_section)
                                if uo_25_odds:
                                    all_book_odds["under_25"] = self.decrypt_odd(uo_25_odds[1], event_tk)
                                    all_book_odds["over_25"] = self.decrypt_odd(uo_25_odds[0], event_tk)
                            
                            other_uo_section_search = re.search("(NA=Totale goal aggiuntivo;.*?MG;)", event_page_content)
                            if other_uo_section_search:
                                other_uo_section = other_uo_section_search.group(1)

                                uo_names = re.findall("PA;ID=(?:[^;])+;NA=\d\.5;\|", other_uo_section)

                                under_odds = []
                                under_section_search = re.search("(NA=Meno di;.*?\|M)", other_uo_section)
                                if under_section_search:
                                    under_section = under_section_search.group(1)
                                    under_odds = re.findall("PA;ID=(?:[^;])+;OD=(?:[^;])+;\|", under_section)

                                over_odds = []
                                over_section_search = re.search("(NA=Più di;.*?\|M)", other_uo_section)
                                if over_section_search:
                                    over_section = over_section_search.group(1)
                                    over_odds = re.findall("PA;ID=(?:[^;])+;OD=(?:[^;])+;\|", over_section)

                                if len(uo_names) == len(under_odds) and len(uo_names) == len(over_odds):
                                    for uo_name, under_odd, over_odd in zip(uo_names, under_odds, over_odds):
                                        nm = re.search("NA=(\d.5)", uo_name).group(1).replace(".", "")
                                        under = re.search("OD=([^;]+);", under_odd).group(1)
                                        over = re.search("OD=([^;]+);", over_odd).group(1)
                                        all_book_odds["under_{0}".format(nm)] = self.decrypt_odd(under, event_tk)
                                        all_book_odds["over_{0}".format(nm)] = self.decrypt_odd(over, event_tk)

                            other_uo_section_search = re.search(".*(NA=Goal nel 1° tempo;.*?MG;)", event_page_content)
                            if other_uo_section_search:
                                other_uo_section = other_uo_section_search.group(1)

                                uo_names = re.findall("PA;ID=(?:[^;])+;NA=\d\.5;\|", other_uo_section)

                                under_odds = []
                                under_section_search = re.search("(NA=Meno di;.*?\|M)", other_uo_section)
                                if under_section_search:
                                    under_section = under_section_search.group(1)
                                    under_odds = re.findall("PA;ID=(?:[^;])+;OD=(?:[^;])+;\|", under_section)

                                over_odds = []
                                over_section_search = re.search("(NA=Più di;.*?\|M)", other_uo_section)
                                if over_section_search:
                                    over_section = over_section_search.group(1)
                                    over_odds = re.findall("PA;ID=(?:[^;])+;OD=(?:[^;])+;\|", over_section)

                                if len(uo_names) == len(under_odds) and len(uo_names) == len(over_odds):
                                    for uo_name, under_odd, over_odd in zip(uo_names, under_odds, over_odds):
                                        nm = re.search("NA=(\d.5)", uo_name).group(1).replace(".", "")
                                        under = re.search("OD=([^;]+);", under_odd).group(1)
                                        over = re.search("OD=([^;]+);", over_odd).group(1)
                                        all_book_odds["fh_under_{0}".format(nm)] = self.decrypt_odd(under, event_tk)
                                        all_book_odds["fh_over_{0}".format(nm)] = self.decrypt_odd(over, event_tk)
                                        
                            other_uo_section_search = re.search(".*(NA=Goal 2° tempo;.*?MG;)", event_page_content)
                            if other_uo_section_search:
                                other_uo_section = other_uo_section_search.group(1)

                                uo_names = re.findall("PA;ID=(?:[^;])+;NA=\d\.5;\|", other_uo_section)

                                under_odds = []
                                under_section_search = re.search("(NA=Meno di;.*?\|M)", other_uo_section)
                                if under_section_search:
                                    under_section = under_section_search.group(1)
                                    under_odds = re.findall("PA;ID=(?:[^;])+;OD=(?:[^;])+;\|", under_section)

                                over_odds = []
                                over_section_search = re.search("(NA=Più di;.*?\|M)", other_uo_section)
                                if over_section_search:
                                    over_section = over_section_search.group(1)
                                    over_odds = re.findall("PA;ID=(?:[^;])+;OD=(?:[^;])+;\|", over_section)

                                if len(uo_names) == len(under_odds) and len(uo_names) == len(over_odds):
                                    for uo_name, under_odd, over_odd in zip(uo_names, under_odds, over_odds):
                                        nm = re.search("NA=(\d.5)", uo_name).group(1).replace(".", "")
                                        under = re.search("OD=([^;]+);", under_odd).group(1)
                                        over = re.search("OD=([^;]+);", over_odd).group(1)
                                        all_book_odds["sh_under_{0}".format(nm)] = self.decrypt_odd(under, event_tk)
                                        all_book_odds["sh_over_{0}".format(nm)] = self.decrypt_odd(over, event_tk)
                                        
                            ggng_section_search = re.search("(NA=Entrambe le squadre segnano;.*?MG;)", event_page_content)
                            if ggng_section_search:
                                ggng_section = ggng_section_search.group(1)
                                gg_odds = re.findall("PA;ID=(?:[^;])+;NA=Sì ;OD=([^;]+);\|", ggng_section)
                                
                                if gg_odds:
                                    all_book_odds["goal"] = self.decrypt_odd(gg_odds[0], event_tk)
                                ng_odds = re.findall("PA;ID=(?:[^;])+;NA=No ;OD=([^;]+);\|", ggng_section)
                                if ng_odds:
                                    all_book_odds["no_goal"] = self.decrypt_odd(ng_odds[0], event_tk)
                            
                            uo_section_search = re.search(".*(NA=Totale goal squadra;.*?MG;)", event_page_content)
                            if uo_section_search:
                                uo_section = uo_section_search.group(1)
                                uo_05_odds = re.findall("PA;[^(PA)]*-1;NA=.*OD=([^;]+?);SU=0;HA=0\.5;\|", uo_section)
                                if uo_05_odds:
                                    all_book_odds["team1_under_05"] = self.decrypt_odd(uo_05_odds[1], event_tk)
                                    all_book_odds["team1_over_05"] = self.decrypt_odd(uo_05_odds[0], event_tk)
                                uo_15_odds = re.findall("PA;[^(PA)]*?OD=([^;]+?);SU=0;HA=1\.5;\|", uo_section)
                                if uo_15_odds:
                                    all_book_odds["team1_under_15"] = self.decrypt_odd(uo_15_odds[1], event_tk)
                                    all_book_odds["team1_over_15"] = self.decrypt_odd(uo_15_odds[0], event_tk)
                                uo_25_odds = re.findall("PA;[^(PA)]*?OD=([^;]+?);SU=0;HA=2\.5;\|", uo_section)
                                if uo_25_odds:
                                    all_book_odds["team1_under_25"] = self.decrypt_odd(uo_25_odds[1], event_tk)
                                    all_book_odds["team1_over_25"] = self.decrypt_odd(uo_25_odds[0], event_tk)
                                uo_35_odds = re.findall("PA;[^(PA)]*?OD=([^;]+?);SU=0;HA=3\.5;\|", uo_section)
                                if uo_35_odds:
                                    all_book_odds["team1_under_35"] = self.decrypt_odd(uo_35_odds[1], event_tk)
                                    all_book_odds["team1_over_35"] = self.decrypt_odd(uo_35_odds[0], event_tk)
                                uo_45_odds = re.findall("PA;[^(PA)]*?OD=([^;]+?);SU=0;HA=4\.5;\|", uo_section)
                                if uo_45_odds:
                                    all_book_odds["team1_under_45"] = self.decrypt_odd(uo_45_odds[1], event_tk)
                                    all_book_odds["team1_over_45"] = self.decrypt_odd(uo_45_odds[0], event_tk)
                                uo_55_odds = re.findall("PA;[^(PA)]*?OD=([^;]+?);SU=0;HA=5\.5;\|", uo_section)
                                if uo_55_odds:
                                    all_book_odds["team1_under_55"] = self.decrypt_odd(uo_55_odds[1], event_tk)
                                    all_book_odds["team1_over_55"] = self.decrypt_odd(uo_55_odds[0], event_tk)
                                uo_65_odds = re.findall("PA;[^(PA)]*?OD=([^;]+?);SU=0;HA=6\.5;\|", uo_section)
                                if uo_65_odds:
                                    all_book_odds["team1_under_65"] = self.decrypt_odd(uo_65_odds[1], event_tk)
                                    all_book_odds["team1_over_65"] = self.decrypt_odd(uo_65_odds[0], event_tk)

                                uo_05_odds = re.findall("PA;.*-2;NA=.*OD=([^;]+?);SU=0;HA=0\.5;\|", uo_section)
                                if uo_05_odds:
                                    all_book_odds["team2_under_05"] = self.decrypt_odd(uo_05_odds[1], event_tk)
                                    all_book_odds["team2_over_05"] = self.decrypt_odd(uo_05_odds[0], event_tk)
                                uo_15_odds = re.findall("PA;[^(PA)]*?OD=([^;]+?);SU=0;HA=1\.5;\|", uo_section)
                                if uo_15_odds:
                                    all_book_odds["team2_under_15"] = self.decrypt_odd(uo_15_odds[1], event_tk)
                                    all_book_odds["team2_over_15"] = self.decrypt_odd(uo_15_odds[0], event_tk)
                                uo_25_odds = re.findall("PA;[^(PA)]*?OD=([^;]+?);SU=0;HA=2\.5;\|", uo_section)
                                if uo_25_odds:
                                    all_book_odds["team2_under_25"] = self.decrypt_odd(uo_25_odds[1], event_tk)
                                    all_book_odds["team2_over_25"] = self.decrypt_odd(uo_25_odds[0], event_tk)
                                uo_35_odds = re.findall("PA;[^(PA)]*?OD=([^;]+?);SU=0;HA=3\.5;\|", uo_section)
                                if uo_35_odds:
                                    all_book_odds["team2_under_35"] = self.decrypt_odd(uo_35_odds[1], event_tk)
                                    all_book_odds["team2_over_35"] = self.decrypt_odd(uo_35_odds[0], event_tk)
                                uo_45_odds = re.findall("PA;[^(PA)]*?OD=([^;]+?);SU=0;HA=4\.5;\|", uo_section)
                                if uo_45_odds:
                                    all_book_odds["team2_under_45"] = self.decrypt_odd(uo_45_odds[1], event_tk)
                                    all_book_odds["team2_over_45"] = self.decrypt_odd(uo_45_odds[0], event_tk)
                                uo_55_odds = re.findall("PA;[^(PA)]*?OD=([^;]+?);SU=0;HA=5\.5;\|", uo_section)
                                if uo_55_odds:
                                    all_book_odds["team2_under_55"] = self.decrypt_odd(uo_55_odds[1], event_tk)
                                    all_book_odds["team2_over_55"] = self.decrypt_odd(uo_55_odds[0], event_tk)
                                uo_65_odds = re.findall("PA;[^(PA)]*?OD=([^;]+?);SU=0;HA=6\.5;\|", uo_section)
                                if uo_65_odds:
                                    all_book_odds["team2_under_65"] = self.decrypt_odd(uo_65_odds[1], event_tk)
                                    all_book_odds["team2_over_65"] = self.decrypt_odd(uo_65_odds[0], event_tk)


                            # section_search = re.search(".*(NA=Risultato alla fine del 1° tempo;.*?MG;)", event_page_content)
                            # if section_search:
                            #     section = section_search.group(1)
                            #     odds = re.findall("PA;[^(PA)]*?NA="+home+";OD=([^;]+?);.*?;\|", section)
                            #     if odds:
                            #         all_book_odds["fh_home"] = self.decrypt_odd(odds[0], event_tk)
                            #     odds = re.findall("PA;[^(PA)]*?NA=Pareggio;OD=([^;]+?);.*?;\|", section)
                            #     if odds:
                            #         all_book_odds["fh_draw"] = self.decrypt_odd(odds[0], event_tk)
                            #     odds = re.findall("PA;[^(PA)]*?NA="+away+";OD=([^;]+?);.*?;\|", section)
                            #     if odds:
                            #         all_book_odds["fh_away"] = self.decrypt_odd(odds[0], event_tk)

                            # section_search = re.search(".*(NA=Risultato 2° tempo;.*?MG;)", event_page_content)
                            # if section_search:
                            #     section = section_search.group(1)
                            #     odds = re.findall("PA;[^(PA)]*?NA="+home+";OD=([^;]+?);.*?;\|", section)
                            #     if odds:
                            #         all_book_odds["sh_home"] = self.decrypt_odd(odds[0], event_tk)
                            #     odds = re.findall("PA;[^(PA)]*?NA=Pareggio;OD=([^;]+?);.*?;\|", section)
                            #     if odds:
                            #         all_book_odds["sh_draw"] = self.decrypt_odd(odds[0], event_tk)
                            #     odds = re.findall("PA;[^(PA)]*?NA="+away+";OD=([^;]+?);.*?;\|", section)
                            #     if odds:
                            #         all_book_odds["sh_away"] = self.decrypt_odd(odds[0], event_tk)
                            '''
                            section_search = re.search(".*NA=Risultato 2° tempo;PD=([^;]+);", event_page_content)
                            if section_search:
                                pd_section = section_search.group(1)
                                try:
                                    url2 = "https://www.bet365.it/SportsBook.API/web?cid=97&ctid=97&lid=6&pd={0}&zid=0".format(urllib.parse.quote_plus(pd_section))
                                    event_page_request2 = self.get_response(url2, self.custom_headers, proxy=proxy, cookies=init_page_request.cookies)
                                    if event_page_request2:
                                        event_page_content2 = event_page_request2.content.replace("\r", "").replace("\n", "")
                                        odds = re.findall("NA="+home+";OD=([^;]+);.*", event_page_content2)
                                        if odds:
                                            all_book_odds["sh_home"] = Fraction(odds[0])
                                        odds = re.findall("NA=Pareggio;OD=([^;]+);.*", event_page_content2)
                                        if odds:
                                            all_book_odds["sh_draw"] = Fraction(odds[0])
                                        odds = re.findall("NA="+away+";OD=([^;]+);.*", event_page_content2)
                                        if odds:
                                            all_book_odds["sh_away"] = Fraction(odds[0])
                                except:
                                    pass
                            '''
                            dc_section_search = re.search("(NA=Doppia chance;.*?MG;)", event_page_content)
                            if dc_section_search:
                                dc_section = dc_section_search.group(1)
                                dc_odds = re.findall("PA;[^(PA)]*?NA=[^;]+?;N2=1X;OD=([^;]+?);\|", dc_section)
                                if dc_odds:
                                    all_book_odds["dc_home_draw"] = self.decrypt_odd(dc_odds[0], event_tk)

                                dc_odds = re.findall("PA;[^(PA)]*?NA=[^;]+?;N2=12;OD=([^;]+?);\|", dc_section)
                                if dc_odds:
                                    all_book_odds["dc_home_away"] = self.decrypt_odd(dc_odds[0], event_tk)

                                dc_odds = re.findall("PA;[^(PA)]*?NA=[^;]+?;N2=X2;OD=([^;]+?);\|", dc_section)
                                if dc_odds:
                                    all_book_odds["dc_draw_away"] = self.decrypt_odd(dc_odds[0], event_tk)

                            # dc_section_search = re.search(".*(NA=Doppia chance 1° tempo;.*?MG;)", event_page_content)
                            # if dc_section_search:
                            #     dc_section = dc_section_search.group(1)
                            #     dc_odds = re.findall("PA;[^(PA)]*?NA="+home+" o pareggio;OD=([^;]+?);.*?;\|", dc_section)
                            #     if dc_odds:
                            #         all_book_odds["fh_dc_home_draw"] = self.decrypt_odd(dc_odds[0], event_tk)

                            #     dc_odds = re.findall("PA;[^(PA)]*?NA="+home+" o "+away+";OD=([^;]+?);.*?;\|", dc_section)
                            #     if dc_odds:
                            #         all_book_odds["fh_dc_home_away"] = self.decrypt_odd(dc_odds[0], event_tk)

                            #     dc_odds = re.findall("PA;[^(PA)]*?NA="+away+" o pareggio;OD=([^;]+?);.*?;\|", dc_section)
                            #     if dc_odds:
                            #         all_book_odds["fh_dc_draw_away"] = self.decrypt_odd(dc_odds[0], event_tk)
                            '''
                            dc_section_search = re.search(".*(NA=Doppia Chance 2° Tempo;.*?MG;)", event_page_content)
                            if dc_section_search:
                                dc_section = dc_section_search.group(1)
                                dc_odds = re.findall("PA;[^(PA)]*?NA="+home+" o pareggio;OD=([^;]+?);.*?;\|", dc_section)
                                if dc_odds:
                                    all_book_odds["sh_dc_home_draw"] = self.decrypt_odd(dc_odds[0], event_tk)

                                dc_odds = re.findall("PA;[^(PA)]*?NA="+home+" o "+away+";OD=([^;]+?);.*?;\|", dc_section)
                                if dc_odds:
                                    all_book_odds["sh_dc_home_away"] = self.decrypt_odd(dc_odds[0], event_tk)

                                dc_odds = re.findall("PA;[^(PA)]*?NA="+away+" o pareggio;OD=([^;]+?);.*?;\|", dc_section)
                                if dc_odds:
                                    all_book_odds["sh_dc_draw_away"] = self.decrypt_odd(dc_odds[0], event_tk)
                            '''

                            section_search = re.search(".*(NA=Goal: pari/dispari;.*?MG;)", event_page_content)
                            if section_search:
                                section = section_search.group(1)
                                odds = re.findall("PA;[^(PA)]*?NA=Dispari;OD=([^;]+?);.*?;\|", section)
                                if odds:
                                    all_book_odds["odd"] = self.decrypt_odd(odds[0], event_tk)
                                odds = re.findall("PA;[^(PA)]*?NA=Pari;OD=([^;]+?);.*?;\|", section)
                                if odds:
                                    all_book_odds["even"] = self.decrypt_odd(odds[0], event_tk)

                            ggng_section_search = re.search(".*(NA=Entrambe le squadre segnano nel 1° tempo;.*?MG;)", event_page_content)
                            if ggng_section_search:
                                ggng_section = ggng_section_search.group(1)
                                gg_odds = re.findall("PA;[^(PA)]*?NA=Sì ;OD=([^;]+?);.*?;\|", ggng_section)
                                if gg_odds:
                                    all_book_odds["fh_goal"] = self.decrypt_odd(gg_odds[0], event_tk)
                                ng_odds = re.findall("PA;[^(PA)]*?NA=No ;OD=([^;]+?);.*?;\|", ggng_section)
                                if ng_odds:
                                    all_book_odds["fh_no_goal"] = self.decrypt_odd(ng_odds[0], event_tk)

                            ggng_section_search = re.search(".*(NA=Entrambe le squadre segnano nel 2° tempo;.*?MG;)", event_page_content)
                            if ggng_section_search:
                                ggng_section = ggng_section_search.group(1)
                                gg_odds = re.findall("PA;[^(PA)]*?NA=Sì ;OD=([^;]+?);.*?;\|", ggng_section)
                                if gg_odds:
                                    all_book_odds["sh_goal"] = self.decrypt_odd(gg_odds[0], event_tk)
                                ng_odds = re.findall("PA;[^(PA)]*?NA=No ;OD=([^;]+?);.*?;\|", ggng_section)
                                if ng_odds:
                                    all_book_odds["sh_no_goal"] = self.decrypt_odd(ng_odds[0], event_tk)

                            # cs_section_search = re.search(".*(NA=Risultato esatto;.*?MG;)", event_page_content)
                            # if cs_section_search:
                            #     cs_section = cs_section_search.group(1)
                            #     for y in range(0,5):
                            #         for z in range(0,5):
                            #             cs_odds = re.findall(";NA="+str(y)+"-"+str(z)+";OD=([^;]+?);.*?;\|", cs_section)
                            #             if cs_odds:
                            #                 all_book_odds["cs_"+str(y)+str(z)] = self.decrypt_odd(cs_odds[0], event_tk)
                    except Exception:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        traceback.print_exception(exc_type, exc_obj, exc_tb)
        except Exception:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_obj, exc_tb)
            
        return {"odds":all_book_odds,"game_play":"1"}
        
    def get_league_request(self, league):
        try:
            self.custom_headers.update({"X-Net-Sync-Term": self.get_sync_token()})
            if self.s.cookies.get("pstk") is None:
                url = "https://www.bet365.it/defaultapi/sports-configuration?_h=rjewx2b5XJf0UGGo2YgHhg=="
                init_page_request = self.get_response(url, self.custom_headers, cookies={"aps03":"ct=97&lng=6"}, use_residential_proxies = True)
            
            if self.s.cookies.get("pstk"):
                url = "https://www.bet365.it/SportsBook.API/web?lid=6&zid=0&pd={0}&cid=97&ctid=97".format(urllib.parse.quote_plus(league))
                league_page_request = self.get_response(url, self.custom_headers,  use_residential_proxies = True)
                if league_page_request:
                    return league_page_request.content
        except Exception:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_obj, exc_tb)
            
        return None
                
    def get_league_events(self, league):
        all_events = []
        try:
            league_response = self.get_league_request(league)
            if league_response:
                if "invalid url" not in league_response.decode():
                    lresp = league_response.decode().replace("\r", "").replace("\n", "")
                    league_tk = re.search(r"TK=([^;]*);", league_response.decode())
                    if not league_tk:
                        league_tk = "BB"
                    else:
                        league_tk = league_tk.group(1)[:2]
                    
                    events = [event for event in re.findall("(?<=PA;)[^|]+NA=[^;]+?;.*?FI=[^;]+?;.*?BC=[^;]+?;.*?PD=[^;]+?;.*?;\|(?=PA|MA)", league_response.decode().replace("\r", "").replace("\n", "")) if "SU=1" not in event]
                    
                    x=0
                    for event in events:
                        american = False
                        event_info = re.search(".*NA=([^;]+?);.*?FI=([^;]+?);.*?BC=([^;]+?);.*?PD=([^;]+?);.*?;\|", event)
                        event_id = event_info.group(2)
                        dt = event_info.group(3)
                        
                        x=x+1
                        name = event_info.group(1)
                        try:
                            home, away = [team.strip() for team in event_info.group(1).split(" v ")]
                        except Exception:
                            if self.sprt == Sport.BASKET.value:
                                teams = re.search(".*NA=([^;]+?);.*?N2=([^;]+?);CU=;ED=;FD=([^;]+?);.*?;\|", event)
                                if teams is None:
                                    continue
                                home = teams.group(1).strip()
                                away = teams.group(2).strip()
                                name = teams.group(3).strip()
                                if " @ " in name:
                                    away,home = name.split(" @ ")
                                elif "NT=Campo neutro;" in event:
                                    away,home = name.split(" v ")
                            else:
                                teams = re.search(".*NA=([^;]+?);.*?N2=([^;]+?);.*?;\|", event)
                                home = teams.group(1).strip()
                                away = teams.group(2).strip()
                        
                        open_date = ((datetime.datetime.strptime(dt, '%Y%m%d%H%M%S')) + datetime.timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
                            
                        event_url = event_info.group(4)
                        
                        betradar_id = "NULL"
                        try:
                            betradar_id = re.search(".*match/(\d+)~Bet365Stats.*", event).group(1)
                        except Exception:
                            pass
                        
                        event_data = {"event_id":event_id,"open_date":open_date,"home":home,"away":away,"betradar_id":betradar_id,"params":event_url+":"+home+":"+away}
                        if self.sprt != Sport.CALCIO.value:
                            if self.sprt == Sport.BASKET.value:
                                event_id = str(int(event_id)+1)
                            
                            event_odds = re.findall("FI={0};OD=([^;]+);".format(event_id), league_response.decode().replace("\r", "").replace("\n", "")) 
                            all_book_odds = self.get_empty_odds_dict()
                            if len(event_odds) == 2:
                                if "NT=Campo neutro;" in event:
                                    all_book_odds["away"] = self.decrypt_odd(event_odds[0], league_tk)
                                    all_book_odds["home"] = self.decrypt_odd(event_odds[1], league_tk)
                                    away,home = name.split(" v ")
                                    
                                    event_data.update({"home":home,"away":away})
                                elif " @ " in name:
                                    all_book_odds["away"] = self.decrypt_odd(event_odds[0], league_tk)
                                    all_book_odds["home"] = self.decrypt_odd(event_odds[1], league_tk)
                                    away,home = name.split(" @ ")
                                    
                                    event_data.update({"home":home,"away":away})
                                else:
                                    all_book_odds["home"] = self.decrypt_odd(event_odds[0], league_tk)
                                    all_book_odds["away"] = self.decrypt_odd(event_odds[1], league_tk)
                                    
                                    
                            event_data.update({"params":"NULL","odds":all_book_odds})
                        else:
                            event_odds = re.findall("FI={0};OD=([^;]+);".format(event_id), league_response.decode().replace("\r", "").replace("\n", ""))
                            all_book_odds = self.get_empty_odds_dict()
                            if len(event_odds) == 3:
                                all_book_odds["home"] = self.decrypt_odd(event_odds[0], league_tk)
                                all_book_odds["away"] = self.decrypt_odd(event_odds[2], league_tk)
                                all_book_odds["draw"] = self.decrypt_odd(event_odds[1], league_tk)
                                
                                event_data.update({"odds":all_book_odds})
                        
                        #print(name,home+" v "+away,all_book_odds["home"],all_book_odds["away"])
                        all_events.append(event_data)
                        
        except Exception:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_obj, exc_tb)

        return all_events



