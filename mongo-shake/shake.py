#!/usr/bin/env python3

# -*- coding:utf-8 -*-

import getopt
import json
import os
import sys
import traceback
import urllib.request
import time

MODULE_COLLECTOR = 1
MODULE_RECEIVER = 2
MODULE_UNKNOWN = 0

VERBOSE_QUEUE = False
VERBOSE_TABLE = False

# connected module
module = MODULE_UNKNOWN

# default host and port
host, port = ("127.0.0.1", "9100")

exclusive = ['who', 'tag', 'lsn.ts', 'lsn.unix', 'lsn_ack.unix', 'lsn_ack.ts', 'lsn_ckpt.ts', 'lsn_ckpt.unix', 'now.ts_unix', 'now.ts_time', 'now.unix']
queue_tag_exclusive = ['id', 'ops_counter', 'worker_id', 'last_unack']
calc = ['logs']


# read http response json
def __get_json(host, port, spec):
    try:
        resp = urllib.request.urlopen("http://%s:%s/%s" % (host, port, spec)).read()
        return json.loads(resp)
    except:
        traceback.print_exc()
        __crash("failed")


def get_json(spec):
    return __get_json(host, port, spec)


def __crash(message):
    print(message)
    exit(-1)


def usage():
    print("Usage: ./mongoshake-stat [--host=127.0.0.1] [--port=8080] [--tables] [--queue]")
    exit(0)


if __name__ == "__main__":
    opts, args = getopt.getopt(sys.argv[1:], "tqh:p:", ["tables","queue", "host=", "port=", "help"])

    for key, value in opts:
        if key in ("-w", "--queue"):
            VERBOSE_QUEUE = True
        if key in ("-w", "--tables"):
            VERBOSE_TABLE = True
        if key in ("-h", "--host"):
            host = value
        if key in ("-p", "--port"):
            port = value
        if key == "--help":
            usage()

    subpage = VERBOSE_QUEUE | VERBOSE_TABLE

    # decide collector or receiver we connect to
    detail = get_json("repl")
    if not isinstance(detail, dict):
        detail = detail[0]
    if detail["tag"] is None:
        __crash("http response is not valid {%s}" % str(detail))

    module = MODULE_COLLECTOR if "collector" in detail["who"] else MODULE_RECEIVER

    if not subpage:
        # show lsn detail information. format is like :
        #
        # |--------------------------------------------------------|
        # |        lsn.ts |     lsn.ts_unix  |         lsn.ts_time |
        # |--------------------------------------------------------|
        # |           100 |        143450834 | 2017-01-19 18:56:1  |
        # |           101 |        143450890 | 2017-01-19 18:56:1  |
        # |           104 |        143450890 | 2017-01-19 18:56:1  |
        # |           120 |        143450890 | 2017-01-19 18:56:1  |
        # |---------------|------------------|---------------------|
        header = ["|"]
        banner = ["|"]
        keys = list(detail.keys())
        keys.sort()
        for k in keys:
            if isinstance(detail[k], str):
                if str(k) not in exclusive:
                    banner.append("%20s |" % k)
                    header.append(("-" * 21) + "|")
            if isinstance(detail[k], int):
                banner.append("%20s |" % (k + "/sec"))
                header.append(("-" * 21) + "|")
            elif isinstance(detail[k], dict):
                sub = detail[k]
                for key in sub:
                    if str(k) + "." + str(key) not in exclusive:
                        banner.append("%20s |" % (str(k) + "." + str(key)))
                        header.append(("-" * 21) + "|")

        banner = "".join(banner)
        header = "".join(header)

        try:
            accumulation = {}
            for i in range(0, 10000000):
                if i % 20 == 0:
                    print(header)
                    print(banner)
                    print(header)
                details = get_json("repl")
                if isinstance(details, dict):
                    # TODO : only show the first syncer !
                    details = [details]
                i = 0
                for detail in details:
                    line = ["|"]
                    keys = list(detail.keys())
                    keys.sort()
                    for k in keys:
                        mk = k + str(i)
                        if isinstance(detail[k], str):
                            if str(k) not in exclusive:
                                line.append("%20s |" % detail[k])
                        if isinstance(detail[k], int):
                            if mk not in accumulation:
                                accumulation[mk] = detail[k]
                                line.append("%20s |" % "none")
                            else:
                                previous = accumulation[mk]
                                line.append("%20s |" % (detail[k] - previous))
                                accumulation[mk] = detail[k]
                        elif isinstance(detail[k], dict):
                            sub = detail[k]
                            for key in sub:
                                if str(k) + "." + str(key) not in exclusive:
                                    line.append("%20s |" % (str(sub[key])))

                    line = "".join(line)
                    print(line)
                    i += 1
                endline = ["|"]
                for k in keys:
                    if isinstance(detail[k], str):
                        if str(k) not in exclusive:
                            endline.append("%s|" % ("-" * 21))
                    if isinstance(detail[k], int):
                        endline.append("%s|" % ("-" * 21))
                    elif isinstance(detail[k], dict):
                        for key in sub:
                            if str(k) + "." + str(key) not in exclusive:
                                endline.append("%s|" % ("-"*21))
                print("".join(endline))
                time.sleep(1)
        except:
            traceback.print_exc()
            pass

    elif VERBOSE_QUEUE:
        # show lsn detail information. format is like :
        #
        #                   jobs_in_queue        batch_size    jobs_unack_buffer
        # worker-0                    128               512                   16
        # worker-1                    256               511                    0
        # worker-2                      0               512                    0
        # worker-3                    128               512                   64
        #
        api = "worker" if module == MODULE_COLLECTOR else "replayer"

        worker = get_json(api)
        banner = ["%-11s" % ""]
        w = worker[0]
        keys = list(w.keys())
        keys.sort()
        for col in keys:
            if str(col) not in queue_tag_exclusive:
                banner.append("%20s" % col)

        banner = "".join(banner)

        try:
            while True:
                refresh = get_json(api)
                line = []
                for w in refresh:
                    seq = w["worker_id"] if module == MODULE_COLLECTOR else w['id']
                    line.append("%11s" % (api + "-" + str(seq)))
                    keys = list(w.keys())
                    keys.sort()
                    for col in keys:
                        if str(col) not in queue_tag_exclusive:
                            line.append("%20s" % (str(w[col])))
                    line.append("\n")

                os.system('clear')
                print("\n\n")
                print(banner)
                print("".join(line))

                time.sleep(1)
        except:
            traceback.print_exc()
            pass

    elif VERBOSE_TABLE:
        if module != MODULE_RECEIVER:
            print("Command `mongoshake-stat --tables` is not supported by collector")
        else:
            # show tables operations
            #
            # |----------------------------------|-----------|
            # |							   Table |       Ops |
            # |----------------------------------|-----------|
            # |                    sns.sync_item |      2288 |
            # |----------------------------------|-----------|
            # |                    sns.sync_file |         0 |
            # |----------------------------------|-----------|
            # |             bls_zb_to_sz.context |         0 |
            # |----------------------------------|-----------|
            #
            banner = []
            banner.append("|%s|" % ("-" * 41))
            banner.append("%s|\n" % ("-" * 11))
            banner.append("|%40s |" % "Table")
            banner.append("%10s |" % "Ops")

            banner.append("\n|%s|" % ("-" * 41))
            banner.append("%s|" % ("-" * 11))
            banner = "".join(banner)
            before = get_json("tables")

            try:
                while True:
                    line = []
                    time.sleep(1)
                    os.system('clear')
                    print(banner)
                    after = get_json("tables")
                    for t in after:
                        delta = after[t] - before[t]
                        #if delta > 0:
                        line.append("|%40s |" % (t))
                        line.append("%10s |" % (delta))
                        line.append("\n|%s" % ("-" * 41))
                        line.append("|%s|\n" % ("-" * 11))

                    print("".join(line))
                    before = after

            except:
                traceback.print_exc()
                pass
