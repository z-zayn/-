import re
import os


class Nginx(object):

    def __init__(self, conf_path):
        self.conf_path = conf_path
        self.serverBlock = list()  # 保存解析后端每个server块
        self.servers = list()
        self.parse_server_block()

    def parse_server_block(self):
        """解析server语句块"""
        flag = False
        serverblock = ''
        num_of_quote = 0

        with open(self.conf_path, 'r', encoding="utf-8") as fp:
            for line in fp.readlines():
                x = line.replace(' ', '')
                if x.startswith('server{'):
                    num_of_quote += 1
                    flag = True
                    serverblock += line
                    continue
                # 发现{，计数加1.发现}，计数减1，直到计数为0
                if flag and '{' in line:
                    num_of_quote += 1

                if flag and num_of_quote != 0:
                    serverblock += line

                if flag and '}' in line:
                    num_of_quote -= 1

                if flag and num_of_quote == 0:
                    self.serverBlock.append(serverblock)
                    flag = False
                    serverblock = ''
                    num_of_quote = 0

        for singleServer in self.serverBlock:
            port = re.findall(r'listen\s*((?:\d|\s)*)[^;]*;', singleServer)[0]  # port

            r = re.findall(r'server_name\s+([^;]*);', singleServer)  # server_name

            # 可能存在没有server_name的情况
            if len(r) > 0:
                servername = r[0]
            else:
                continue

            # location
            locations = re.findall(r'location\s*([\^~\*=]*)\s*([^{ ]*)\s*\{[^}]*proxy_pass\s+https?://([^;/]*)[^;]*;',
                                   singleServer)
            locations += re.findall(r'location\s*([\^~\*=]*)\s*([^{ ]*)\s*\{[^}]*root\s+([^;]*)[^;]*;', singleServer)
            locations += re.findall(r'location\s*([\^~\*=]*)\s*([^{ ]*)\s*\{[^}]*index\s+([^;]*)[^;]*;', singleServer)

            backend_list = list()
            backend_ip = ''

            # 可能存在多个location
            if len(locations) > 0:
                for location in locations:
                    way = location[0]
                    backend_path = location[1]
                    poolname = location[2]
                    backend_ip = poolname

                    backend_list.append({"way": way, "backend_path": backend_path, "backend_ip": backend_ip})

            # error_log
            error_log = re.findall(r"error_log\s+([^;]*)/error.log;", singleServer)[0]
            # access_log
            access_log = re.findall(r"access_log\s+([^;]*)/access.log;", singleServer)[0]

            server = {
                        'port': int(port),
                        'server_name': servername,
                        'backend': backend_list,
                        'error_log': error_log,
                        'access_log': access_log
                     }

            self.servers.append(server)
