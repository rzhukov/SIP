import json
import time
import datetime
import string
import calendar

from helpers import get_cpu_temp, check_login, password_hash
import web
import gv  # Gain access to sip's settings
from urls import urls  # Gain access to sip's URL list
from webpages import ProtectedPage, WebPage

##############
## New URLs ##

urls.extend([
    u"/jo", u"plugins.mobile_app.options",
    u"/jc", u"plugins.mobile_app.cur_settings",
    u"/js", u"plugins.mobile_app.station_state",
    u"/jp", u"plugins.mobile_app.program_info",
    u"/jn", u"plugins.mobile_app.station_info",
    u"/jl", u"plugins.mobile_app.get_logs",
    u"/sp", u"plugins.mobile_app.set_password"])


#######################
## Class definitions ##

class options(WebPage):  # /jo
    """Returns device options as json."""
    def GET(self):
        web.header(u"Access-Control-Allow-Origin", u"*")
        web.header(u"Content-Type", u"application/json")
        web.header(u"Cache-Control", u"no-cache")
        if check_login():
            jopts = {
                u"fwv": gv.ver_str + u"-SIP",
                u"tz": gv.sd[u"tz"],
                u"ext": gv.sd[u"nbrd"] - 1,
                u"seq": gv.sd[u"seq"],
                u"sdt": gv.sd[u"sdt"],
                u"mas": gv.sd[u"mas"],
                u"mton": gv.sd[u"mton"],
                u"mtof": gv.sd[u"mtoff"],
                u"urs": gv.sd[u"urs"],
                u"rso": gv.sd[u"rst"],
                u"wl": gv.sd[u"wl"],
                u"ipas": gv.sd[u"ipas"],
                u"reset": gv.sd[u"rbt"],
                u"lg": gv.sd[u"lg"]
            }
        else:
            jopts = {
                u"fwv": gv.ver_str + u"-SIP",
            }

        return json.dumps(jopts)

class cur_settings(ProtectedPage):  # /jc
    """Returns current settings as json."""
    def GET(self):
        web.header(u"Access-Control-Allow-Origin", u"*")
        web.header(u"Content-Type", u"application/json")
        web.header(u"Cache-Control", u"no-cache")
        jsettings = {
            u"devt": gv.now,
            u"nbrd": gv.sd[u"nbrd"],
            u"en": gv.sd[u"en"],
            u"rd": gv.sd[u"rd"],
            u"rs": gv.sd[u"rs"],
            u"mm": gv.sd[u"mm"],
            u"rdst": gv.sd[u"rdst"],
            u"loc": gv.sd[u"loc"],
            u"sbits": gv.sbits,
            u"ps": gv.ps,
            u"lrun": gv.lrun,
            u"ct": get_cpu_temp(gv.sd[u"tu"]),
            u"tu": gv.sd[u"tu"]
        }

        return json.dumps(jsettings)


class station_state(ProtectedPage):  # /js
    """Returns station status and total number of stations as json."""
    def GET(self):
        web.header(u"Access-Control-Allow-Origin", u"*")
        web.header(u"Content-Type", u"application/json")
        web.header(u"Cache-Control", u"no-cache")
        jstate = {
            u"sn": gv.srvals,
            u"nstations": gv.sd[u"nst"]
        }

        return json.dumps(jstate)


class program_info(ProtectedPage):  # /jp
    """Returns program data as json."""
    def GET(self):
        lpd = []  # Local program data
        dse = int((time.time()+((gv.sd[u"tz"]/4)-12)*3600)/86400)  # days since epoch
        for p in gv.pd:
            op = p[:]  # Make local copy of each program
            if op[1] >= 128 and op[2] > 1:
                rel_rem = (((op[1]-128) + op[2])-(dse % op[2])) % op[2]
                op[1] = rel_rem + 128
            lpd.append(op)
        web.header(u"Access-Control-Allow-Origin", u"*")
        web.header(u"Content-Type", u"application/json")
        web.header(u"Cache-Control", u"no-cache")
        jpinfo = {
            u"nprogs": gv.sd[u"nprogs"]-1,
            u"nboards": gv.sd[u"nbrd"],
            u"mnp": 9999,
            u"pd": lpd
        }

        return json.dumps(jpinfo)


class station_info(ProtectedPage):  # /jn
    """Returns station information as json."""
    def GET(self):
        disable = []

        for byte in gv.sd[u"show"]:
            disable.append(~byte&255)

        web.header(u"Access-Control-Allow-Origin", u"*")
        web.header(u"Content-Type", u"application/json")
        web.header(u"Cache-Control", u"no-cache")
        jpinfo = {
            u"snames": gv.snames,
            u"ignore_rain": gv.sd[u"ir"],
            u"masop": gv.sd[u"mo"],
            u"stn_dis": disable,
            u"maxlen": gv.sd[u"snlen"]
        }

        return json.dumps(jpinfo)


class get_logs(ProtectedPage):  # /jl
    """Returns log information for specified date range."""
    def GET(self):
        records = self.read_log()
        data = []
        qdict = web.input()

        web.header(u"Access-Control-Allow-Origin", u"*")
        web.header(u"Content-Type", u"application/json")
        web.header(u"Cache-Control", u"no-cache")

        if u"start" not in qdict or u"end" not in qdict:
            return []

        for r in records:
            event = json.loads(r)
            date = time.mktime(datetime.datetime.strptime(event[u"date"], u"%Y-%m-%d").timetuple())
            if int(qdict[u"start"]) <= int(date) <= int(qdict[u"end"]):
                pid = event[u"program"]
                if pid == u"Run-once":
                    pid = 98
                if pid == u"Manual":
                    pid = 99

                pid = int(pid)
                station = int(event[u"station"])
                duration = string.split(event[u"duration"], ":")
                duration = (int(duration[0]) * 60) + int(duration[1])
                timestamp = int(time.mktime(utc_to_local(datetime.datetime.strptime(event[u"date"] + u" " + event[u"start"], u"%Y-%m-%d %H:%M:%S")).timetuple())) + duration

                data.append([pid, station, duration, timestamp])

        return json.dumps(data)

    def read_log(self):
        try:
            with open(u"./data/log.json") as logf:
                records = logf.readlines()
            return records
        except IOError:
            return []


class set_password():
    """Save changes to device password"""
    def GET(self):
        qdict = web.input()
        web.header(u"Access-Control-Allow-Origin", u"*")
        web.header(u"Content-Type", u"application/json")
        web.header(u"Cache-Control", u"no-cache")

        if not(u"pw" in qdict) or not(u"npw" in qdict) or not(u"cpw" in qdict):
            return json.dumps({u"result":3})

        if password_hash(qdict[u"pw"], gv.sd[u"salt"]) == gv.sd[u"password"]:
            if qdict[u"npw"] == "":
                return json.dumps({u"result":3})
            elif qdict[u"cpw"] != u"" and qdict[u"cpw"] == qdict[u"npw"]:
                gv.sd[u"password"] = password_hash(qdict[u"npw"], gv.sd[u"salt"])
            else:
                return json.dumps({u"result":4})
        else:
            return json.dumps({u"result":2})

        return json.dumps({u"result":1})


def utc_to_local(utc_dt):
    # get integer timestamp to avoid precision lost
    timestamp = calendar.timegm(utc_dt.timetuple())
    local_dt = datetime.datetime.fromtimestamp(timestamp)
    assert utc_dt.resolution >= datetime.timedelta(microseconds=1)
    return local_dt.replace(microsecond=utc_dt.microsecond)
