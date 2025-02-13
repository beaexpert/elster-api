import base64
import configparser
import os
import json
import requests
import glob
from datetime import datetime

__VERSION__ = "1.0"
__DEBUG__   = False

""" 
    ***************************************************
    GET THE CONFIG FROM FILE OR DEFINE CONFIG ARRAY
    ***************************************************
"""
__current_path = os.path.dirname(os.path.abspath(__file__)) #os.getcwd()
__config=[]
__config_file=__current_path+'/private.config.ini'
if os.path.exists(__config_file):
    __config = configparser.ConfigParser()
    __config.read(__config_file)    
else :
    __config["SOFTWARETOKEN"]["B64"] = "...."
    __config["SOFTWARETOKEN"]["FILE"] = "...."
    __config["SOFTWARETOKEN"]["PWD"] = "...." 
    __config["BEA_EXPERT_API"]["HOST"] = "..."
    __config["BEA_EXPERT_API"]["BEX_IDENT"] = "..."
    __config["PATH"]["LOGFILES"] = "..."

""" 
    ***************************************************
    LOW LEVEL ROUTINES
    ***************************************************
"""

def send_request(__req, __func):    
    url = __config["BEA_EXPERT_API"]["HOST"] + __func
    req_b64 = base64.b64encode(__req.encode('utf-8'))
    data = 'j=' + str(req_b64, "utf-8")
    headers = {
        'Content-type': 'application/x-www-form-urlencoded', 
        'bex-ident': __config["BEA_EXPERT_API"]["BEX_IDENT"]
    }
    
    r = requests.post(url, data=data, headers=headers)
    r.encoding = 'utf-8'

    if __DEBUG__: print(__func + ":\n" + r.text)

    try:
        ret = json.loads(r.text.encode('utf-8'))
    except ValueError as e:
        if __DEBUG__:
            print("ValueError in 'send_request'")
            print(e)
        ret = json.loads('{ "error": "Decoding JSON has failed"}')

    return ret

def bex_elster_sendmessage(sw_token, sw_pin, token_b64, msg, msg_att):

    if token_b64 == '':
        token_b64 = base64.b64encode(open(sw_token,'rb').read()).decode('ascii')

    req_json = {}
    req_json['certificate']=token_b64
    req_json["pin"]=sw_pin
    req_json.update(msg)
    req_json["anhaenge"]=[]

    for att in msg_att:
        att_b64=base64.b64encode(open(att,'rb').read()).decode('ascii')
        att_json={
            "dateibezeichnung":os.path.basename(att),
            "dateityp":"application/pdf", # SUPPORT ONLY PDF
            "dateiinhalt":att_b64
        }
        req_json["anhaenge"].append(att_json)

    req = str(json.JSONEncoder().encode(req_json))
    
    size = len(req)    
    res = send_request(req, 'bex_elster_sendmessage')
    date_time=datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    return res, size, date_time


def bex_elster_analyse_response_and_write_logs(response,size,date_time):
    
    nbre=1
    bad_response=False
    path_for_logs=__config["PATH"]["LOGFILES"]
    for f in glob.glob(os.path.join(path_for_logs,"*")): os.remove(f) # cleanup and empty logiles directory
    
    print(date_time+" - check response and extract logfiles (path:"+path_for_logs+") - version:"+__VERSION__)

    if "error" in response:
        print(str(nbre)+": beA.expert API returned an error: "+response["error"])
        nbre+=1
        bad_response=True

    if "fehlerText" in response:
        print(str(nbre)+": fehlerText: "+response["fehlerText"])
        nbre+=1

    if "statusText" in response:
        print(str(nbre)+": statusText: "+response["statusText"])
        nbre+=1

    if "rueckgabe" in response:
        print(str(nbre)+": rueckgabe: "+response["rueckgabe"])
        nbre+=1

    if "serverantwort" in response:
        f = open(os.path.join(path_for_logs,"log_elster_serverantwort.xml"), "w")
        f.write(response["serverantwort"])
        f.close()
        print(str(nbre)+": logfile with so called 'serverantwort' ... written")
        nbre+=1

    if "ausgabedatei" in response:
        f = open(os.path.join(path_for_logs,"log_elster_ausgabedatei.xml"), "wb")
        f.write(base64.b64decode(response["ausgabedatei"]))
        f.close()
        print(str(nbre)+": XML-file with response (ausgabedatei) in full ... written")
        nbre+=1

    if "ericlog" in response:
        f = open(os.path.join(path_for_logs,"log_elster_ericlog.log"), "w")
        f.write(response["ericlog"])
        f.close()
        print(str(nbre)+": logfile with so called 'ericlog' ... written")
        nbre+=1

    if "ericprint_b64" in response:
        f = open(os.path.join(path_for_logs,"log_elster_Übertragungsprotokoll.pdf"), "wb")
        f.write(base64.b64decode(response["ericprint_b64"]))
        f.close()
        print(str(nbre)+": Übertragungsprotokoll (ericprint_b64) ... written")
        nbre+=1
    else:
        bad_response=True

    if bad_response:
        print(date_time+" - result: ❌")
    else:
        print(date_time+" - sent:"+str(size)+" bytes, result: ✅")

    return not bad_response


""" 
    ***************************************************
    MAIN
    ***************************************************
"""

sw_token = __config["SOFTWARETOKEN"]["FILE"]
sw_pin = __config["SOFTWARETOKEN"]["PWD"]
token_b64 = __config["SOFTWARETOKEN"]["B64"]

msg={

    "datenlieferant":"Kanzlei XYZ",
    "testmerker":"<Testmerker>700000001</Testmerker>",

    "ziel":"BY",
    "empfaenger":"9198",

    "steuernummer":"9198011310010",
    "steuerpflichtigertyp":"NichtNatPerson",
    "idnr":"",
    
    "name":"Name_TEST",
    "vorname":"Name_TEST",
    "strasse":"Strasse TEST",
    "hausnummer":"21",
    "postleitzahl":"99789",
    "ort":"ORT_TEST",

    "betreff":"SonstigeNachricht mit Anhang und Rückmeldewunsch",
    "text":"Diese SonstigeNachricht enthält einen Anhang im PDF-Format",
    
    "rueckmeldunggewuenscht":"true",
    "emailrueckmeldung":"rueckmeldung_elster@myemail.com"
}

msg_att=[
    "pdf/1_informationsblatt_fuehrung_2016_02_1.pdf",
    "pdf/A_KAE.pdf",
    "pdf/BAfoeG.pdf",
    "pdf/BBiG.pdf",
    "pdf/ErbStG.pdf",
    "pdf/KasseeStG1.pdf",
    "pdf/KStG.pdf",
    "pdf/MonPDF.PDF",
    "pdf/SGB-I.pdf",
    "pdf/UStG.pdf",
    #"pdf/ZPO-TEST-MIT-250-SEITEN.pdf", #->WILL BE REJECTED: MORE THAN 100 PAGES
]

response, size, date_time = bex_elster_sendmessage(sw_token, sw_pin, token_b64, msg, msg_att)

if __DEBUG__:
    print("HOST: ",__config["BEA_EXPERT_API"]["HOST"])
    print("response: " ,response)

bex_elster_analyse_response_and_write_logs(response, size, date_time)

#
# restriction seen so far: 
# only PDF files, max 100 pages per PDF, max 20 files, max size per file 10.4 MB, max size in total 14 MB.
#

    # From: ELSTER Benachrichtigung <benachrichtigung@elster.de>
    #
    # Sehr geehrte Dame, sehr geehrter Herr,
    #
    # Ihre am 02.02.2025, 21:01:19 Uhr an das Finanzamt übermittelten Anhänge konnten nicht vollständig verarbeitet werden.
    #
    # Weitere Informationen entnehmen Sie bitte Ihrem Steuerprogramm/-portal.
    #
    # Mit freundlichen Grüßen
    # Ihr Finanzamt

