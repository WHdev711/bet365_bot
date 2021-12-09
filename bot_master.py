import argparse
import importlib
import importlib.util
from helpers.enums import *
from time import sleep,time
import multiprocessing
import os
import requests
import subprocess
import mysql.connector
import traceback
import orjson
import sys
  
        
class BotMaster():
    def __init(self):
        self.init_options()
        self.running_bots = []
        self.all_bots = {}
        
    def start_bot(self,bot_filename,options):
        print('1111111111111111',bot_filename)
        bookie_name = bot_filename.replace(".py","")
        #spec = importlib.util.spec_from_file_location(bookie_name, "./bookies/"+bot_filename)
        #bot_module = importlib.util.module_from_spec(spec)
        print('222222222222222222',bookie_name)
        bot_module = getattr(importlib.import_module(bookie_name),bookie_name)
        print('333333333333333',bot_module)

        while 1:
            try:   
                print("12222222222",options)
                bot = bot_module(options)
                bot.run()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                traceback.print_exception(exc_type, exc_obj, exc_tb)
    
    def start_all(self,options):
        self.running_bots = []
        for bot_filename in os.listdir("./"):
            if ".py" in bot_filename and "bot_master" not in bot_filename and "enums" not in bot_filename:
                bookie_name = bot_filename.replace(".py","")
                if bookie_name.lower() == "betfairexchange":
                    os.system("python3 bot_master.py {0} &> /dev/null &".format("--bookie="+bot_filename.replace(".py","")))
                    continue
                for sprt in Sport:
                    if sprt.name != "CALCIO":
                        continue
                    options.sport = sprt.name
                    cmd="python3 bot_master.py {0} {1} &> /dev/null &".format("--bookie="+bot_filename.replace(".py",""),"--sport="+sprt.name)
                    if options.noproxies:
                        cmd="python3 bot_master.py {0} {1} --noproxies &> /dev/null &".format("--bookie="+bot_filename.replace(".py",""),"--sport="+sprt.name)
                    elif options.usetor:
                        cmd="python3 bot_master.py {0} {1} --usetor &> /dev/null &".format("--bookie="+bot_filename.replace(".py",""),"--sport="+sprt.name)

                    os.system(cmd)
 
def init_options():
    parser = argparse.ArgumentParser()
    parser.add_argument("-b", "--bookie", type=str)
    parser.add_argument("-t", "--threads", type=int)
    parser.add_argument("-c", "--cycle", type=int)
    parser.add_argument("-s", "--sport", type=str)
    parser.add_argument("-o", "--host", type=str)
    parser.add_argument("-u", "--username", type=str)
    parser.add_argument("-p", "--password", type=str)
    parser.add_argument("-d", "--database", type=str)
    parser.add_argument("-n", "--noproxies", action="store_true")
    parser.add_argument("-r", "--usetor", action="store_true")
    parser.add_argument("-l", "--residentials", action="store_true")
    parser.add_argument("-a", "--allstart", action="store_true")
    
    return parser.parse_args()
    
def get_database_params():
    url = "http://odds.ninjabet.it/get_ip.php?region=it"
    return orjson.loads('{"username":"prodev","password":"","database":"ninjabet_test","host":"localhost"}')
    # return orjson.loads('{"username":"83fdd02e71","password":"4e59d10211ad4d477b3","database":"ninjabet_dev","host":"localhost"}')
    
    
    
if __name__ == '__main__':
    options = init_options()
    
    bot = BotMaster()
    if options.allstart:
        bot.start_all(options)
    elif options.bookie and (options.bookie.lower() == "betfairexchange" or options.sport):
        
        params = get_database_params()
        options.host = params["host"]
        options.username = params["username"]
        options.password = params["password"]
        options.database = params["database"]
        
        bot.start_bot(options.bookie,options)
        
    elif options.bookie and options.sport is None:
        for sprt in Sport:
            if sprt.name == "ESPORTS":
                continue
            cmd="nohup python3 bot_master.py {0} {1} &> /dev/null &".format("--bookie="+options.bookie,"--sport="+sprt.name)
            if options.noproxies:
                cmd="nohup python3 bot_master.py {0} {1} --noproxies &> /dev/null &".format("--bookie="+options.bookie,"--sport="+sprt.name)
            elif options.usetor:
                cmd="nohup python3 bot_master.py {0} {1} --usetor &> /dev/null &".format("--bookie="+options.bookie,"--sport="+sprt.name)

            os.system(cmd)        
                
                
                    
            
