import socket
import multiprocessing
import re
import os
from nginx import Nginx


class Server(object):

    def __init__(self, ng):

        self.ng = ng
        # 创建套接字
        self.tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # 绑定本地ip、端口
        self.tcp_server_socket.bind(("", ng.servers[0]["port"]))

        # listen变为被动/监听
        self.tcp_server_socket.listen(128)

    def service_client(self, new_socket):
        """为客户端返回数据"""
        # 1.接收客户端发来的请求，即http请求
        # GET / HTTP/1.1
        # ......
        request = new_socket.recv(1024).decode("gbk")
        request_lines = request.splitlines()

        # GET /index.html HTTP/1.1
        ret1 = re.findall(r"Host:\s+([^:]*):.*", request)[0]    # localhost 服务器名
        ret2 = re.match(r"[^/]+(/[^ ]*)", request_lines[0]).group(1)     # localhost/(...)  服务器名下的文件路径
        ret3 = re.findall(r"Host:\s+(.*)", request)[0]                      # (localhost:port)  原请求中的Host的整行信息
        if not os.path.exists(ret1):
            os.mkdir(ret1)
        with open(ret1 + '/access.log', 'w') as f:
            f.write(request)

        flag = False
        flag2 =False
        for singleServer in self.ng.servers:
            if ret1 == singleServer["server_name"]:
                flag = True
                neww_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                max_Backend = singleServer["backend"][0]             # 用于记录前缀最长匹配的后端配置
                max_length = 0                                       # 前缀匹配最长长度
                re_max_Backend = singleServer["backend"][0]          # 用于记录正则表达最长匹配的后端配置
                re_max_length = 0                        # 正则最长匹配长度
                url_max_Backend = singleServer["backend"][0]         # 普通匹配最长匹配的后端配置
                url_max_length = 0                       # 普通匹配最长长度
                for singleBackend in singleServer["backend"]:
                    if singleBackend["way"] == "=" and ret2 == singleBackend["backend_path"]:
                        flag2 = True
                        if len(re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', singleBackend["backend_ip"])[0]) == 0:
                            file_path = singleBackend["backend_ip"]
                            try:
                                f = open(file_path, "rb")
                            except:
                                response = "HTTP/1.1 404 NOT FOUND\r\n"
                                response += "\r\n"
                                response += "-------file not found-------"
                                new_socket.send(response.encode("utf-8"))
                            else:
                                response = "HTTP/1.1 200 OK\r\n"
                                response += "\r\n"
                                response += f.read()
                                f.close()
                                new_socket.send(response.encode("utf-8"))
                        else:
                            ret4 = re.match(r"(.*):(.*)", singleBackend["backend_ip"])
                            neww_socket.connect((ret4.group(1), int(ret4.group(2))))
                            new_request = request.replace(ret3, singleBackend["backend_ip"])
                            neww_socket.send(new_request.encode("utf-8"))
                            response = neww_socket.recv(1024).decode("gbk")
                            new_socket.send(response.encode("utf-8"))
                            neww_socket.close()
                            return
                    elif singleBackend["way"] == "^~" and ret2.find(singleBackend["backend_path"]) != -1:
                        flag2 = True
                        if len(singleBackend["backend_path"]) >= max_length:
                            max_length = len(singleBackend["backend_path"])
                            max_Backend = singleBackend

                    elif singleBackend["way"] == "~" and re.match(singleBackend["backend_path"], ret2) is not None:
                        flag2 = True
                        if len(re.match(singleBackend["backend_path"], ret2)[0]) >= re_max_length:
                            re_max_length = len(re.match(singleBackend["backend_path"], ret2)[0])
                            re_max_Backend = singleBackend

                    elif singleBackend["way"] == '' and ret2.find(singleBackend["backend_path"]) != -1:
                        flag2 = True
                        if len(singleBackend["backend_path"]) >= url_max_length:
                            url_max_length = len(singleBackend["backend_path"])
                            url_max_Backend = singleBackend

                    elif singleBackend["way"] == "/":
                        flag2 = True
                        if max_length != 0:
                            if len(re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', max_Backend["backend_ip"])[0]) == 0:
                                file_path = max_Backend["backend_ip"]
                                try:
                                    f = open(file_path, "rb")
                                except:
                                    response = "HTTP/1.1 404 NOT FOUND\r\n"
                                    response += "\r\n"
                                    response += "-------file not found-------"
                                    new_socket.send(response.encode("utf-8"))
                                else:
                                    response = "HTTP/1.1 200 OK\r\n"
                                    response += "\r\n"
                                    response += f.read()
                                    f.close()
                                    new_socket.send(response.encode("utf-8"))
                            else:
                                ret4 = re.match(r"(.*):(.*)", max_Backend["backend_ip"])
                                neww_socket.connect((ret4.group(1), int(ret4.group(2))))
                                new_request = request.replace(ret3, max_Backend["backend_ip"])
                                neww_socket.send(new_request.encode("utf-8"))
                                response = neww_socket.recv(1024).decode("gbk")
                                new_socket.send(response.encode("utf-8"))
                                neww_socket.close()
                                return

                        elif re_max_length != 0:
                            if len(re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', re_max_Backend["backend_ip"])[0]) == 0:
                                file_path = re_max_Backend["backend_ip"]
                                try:
                                    f = open(file_path, "rb")
                                except:
                                    response = "HTTP/1.1 404 NOT FOUND\r\n"
                                    response += "\r\n"
                                    response += "-------file not found-------"
                                    new_socket.send(response.encode("utf-8"))
                                    return
                                else:
                                    response = "HTTP/1.1 200 OK\r\n"
                                    response += "\r\n"
                                    response += f.read()
                                    f.close()
                                    new_socket.send(response.encode("utf-8"))
                                    return
                            else:
                                ret4 = re.match(r"(.*):(.*)", re_max_Backend["backend_ip"])
                                neww_socket.connect((ret4.group(1), int(ret4.group(2))))
                                new_request = request.replace(ret3, re_max_Backend["backend_ip"])
                                neww_socket.send(new_request.encode("utf-8"))
                                response = neww_socket.recv(1024).decode("gbk")
                                new_socket.send(response.encode("utf-8"))
                                neww_socket.close()
                                return

                        elif url_max_length != 0:
                            if len(re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', url_max_Backend["backend_ip"])) == 0:
                                file_path = url_max_Backend["backend_ip"]
                                try:
                                    f = open(file_path, "r")
                                except:
                                    response = "HTTP/1.1 404 NOT FOUND\r\n"
                                    response += "\r\n"
                                    response += "-------file not found-------"
                                    new_socket.send(response.encode("utf-8"))
                                    return
                                else:
                                    response = "HTTP/1.1 200 OK\r\n"
                                    response += "\r\n"
                                    response += f.read()
                                    f.close()
                                    new_socket.send(response.encode("utf-8"))
                                    return
                            else:
                                ret4 = re.match(r"(.*):(.*)", url_max_Backend["backend_ip"])
                                neww_socket.connect((ret4.group(1), int(ret4.group(2))))
                                new_request = request.replace(ret3, url_max_Backend["backend_ip"])
                                neww_socket.send(new_request.encode("utf-8"))
                                response = neww_socket.recv(1024).decode("gbk")
                                new_socket.send(response.encode("utf-8"))
                                neww_socket.close()
                                return
                        else:
                            if len(re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', singleBackend["backend_ip"])[
                                       0]) == 0:
                                file_path = singleBackend["backend_ip"]
                                try:
                                    f = open(file_path, "rb")
                                except:
                                    response = "HTTP/1.1 404 NOT FOUND\r\n"
                                    response += "\r\n"
                                    response += "-------file not found-------"
                                    new_socket.send(response.encode("utf-8"))
                                    return
                                else:
                                    response = "HTTP/1.1 200 OK\r\n"
                                    response += "\r\n"
                                    response += f.read()
                                    f.close()
                                    new_socket.send(response.encode("utf-8"))
                                    return
                            else:
                                ret4 = re.match(r"(.*):(.*)", singleBackend["backend_ip"])
                                neww_socket.connect((ret4.group(1), int(ret4.group(2))))
                                new_request = request.replace(ret3, singleBackend["backend_ip"])
                                neww_socket.send(new_request.encode("utf-8"))
                                response = neww_socket.recv(1024).decode("gbk")
                                new_socket.send(response.encode("utf-8"))
                                neww_socket.close()
                                return

                if max_length != 0:
                    if len(re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', max_Backend["backend_ip"])[0]) == 0:
                        file_path = max_Backend["backend_ip"]
                        try:
                            f = open(file_path, "rb")
                        except:
                            response = "HTTP/1.1 404 NOT FOUND\r\n"
                            response += "\r\n"
                            response += "-------file not found-------"
                            new_socket.send(response.encode("utf-8"))
                        else:
                            response = "HTTP/1.1 200 OK\r\n"
                            response += "\r\n"
                            response += f.read()
                            f.close()
                            new_socket.send(response.encode("utf-8"))
                    else:
                        ret4 = re.match(r"(.*):(.*)", max_Backend["backend_ip"])
                        neww_socket.connect((ret4.group(1), int(ret4.group(2))))
                        new_request = request.replace(ret3, max_Backend["backend_ip"])
                        neww_socket.send(new_request.encode("utf-8"))
                        response = neww_socket.recv(1024).decode("gbk")
                        new_socket.send(response.encode("utf-8"))
                        neww_socket.close()
                        return
                elif re_max_length != 0:
                    if len(re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', re_max_Backend["backend_ip"])[0]) == 0:
                        file_path = re_max_Backend["backend_ip"]
                        try:
                            f = open(file_path, "rb")
                        except:
                            response = "HTTP/1.1 404 NOT FOUND\r\n"
                            response += "\r\n"
                            response += "-------file not found-------"
                            new_socket.send(response.encode("utf-8"))
                            return
                        else:
                            response = "HTTP/1.1 200 OK\r\n"
                            response += "\r\n"
                            response += f.read()
                            f.close()
                            new_socket.send(response.encode("utf-8"))
                            return
                    else:
                        ret4 = re.match(r"(.*):(.*)", re_max_Backend["backend_ip"])
                        neww_socket.connect((ret4.group(1), int(ret4.group(2))))
                        new_request = request.replace(ret3, re_max_Backend["backend_ip"])
                        neww_socket.send(new_request.encode("utf-8"))
                        response = neww_socket.recv(1024).decode("gbk")
                        new_socket.send(response.encode("utf-8"))
                        neww_socket.close()
                        return
                elif url_max_length != 0:
                    if len(re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', url_max_Backend["backend_ip"])) == 0:
                        file_path = url_max_Backend["backend_ip"]
                        try:
                            f = open(file_path, "r")
                        except:
                            response = "HTTP/1.1 404 NOT FOUND\r\n"
                            response += "\r\n"
                            response += "-------file not found-------"
                            new_socket.send(response.encode("utf-8"))
                            return
                        else:
                            response = "HTTP/1.1 200 OK\r\n"
                            response += "\r\n"
                            response += f.read()
                            f.close()
                            new_socket.send(response.encode("utf-8"))
                            return
                    else:
                        ret4 = re.match(r"(.*):(.*)", url_max_Backend["backend_ip"])
                        neww_socket.connect((ret4.group(1), int(ret4.group(2))))
                        new_request = request.replace(ret3, url_max_Backend["backend_ip"])
                        neww_socket.send(new_request.encode("utf-8"))
                        response = neww_socket.recv(1024).decode("gbk")
                        new_socket.send(response.encode("utf-8"))
                        neww_socket.close()
                        return
            else:
                continue

        if flag is False:
            response = "HTTP/1.1 404 NOT FOUND\r\n"
            response += "\r\n"
            response += "-------Server Name not found-------"
            new_socket.send(response.encode("utf-8"))
        if flag2 is False:
            response = "HTTP/1.1 404 NOT FOUND\r\n"
            response += "\r\n"
            response += "-------File not found-------"
            new_socket.send(response.encode("utf-8"))
        with open(ret1 + '/error.log', 'w') as f:
            f.write(ret1+ret2)
            f.write("NOT FOUND")

        # 关闭套接字
        new_socket.close()

    def run_forever(self):
        """用来完成整体控制"""

        while True:
            # accept等待接受链接(并接收新生成的套接字和客户端地址)
            new_socket, client_addr = self.tcp_server_socket.accept()

            # 开始为该客户端服务
            # 为客户端提供服务
            p = multiprocessing.Process(target=self.service_client, args=(new_socket,))
            p.start()

            new_socket.close()

        # 关闭监听套接字
        self.tcp_server_socket.close()


def main():
    """控制整体，创建一个web 服务器对象，然后调用这个对象的run_forever方法运行"""
    ng = Nginx("nginx.conf")
    web_server = Server(ng)
    web_server.run_forever()


if __name__ == '__main__':
    main()
