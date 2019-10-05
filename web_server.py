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
        file_name = ""
        ret1 = re.findall(r"Host:\s+([^:]*):.*", request)[0]    # localhost
        ret2 = re.match(r"[^/]+(/[^ ]*)", request_lines[0])     # localhost/(...)
        ret3 = re.findall(r"Host:\s+(.*)")                      # (localhost:port)
        if not os.path.exists(ret1):
            os.mkdir(ret1)
        with open(ret1 + '/access.log', 'w') as f:
            f.write(request)

        flag = False
        for singleServer in self.ng.servers:
            if ret1 == singleServer["server_name"]:
                flag = True
                neww_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            for singleBackend in singleServer["backend"]:
                if singleBackend["way"] == "=" and ret2 == singleBackend["backend_path"]:
                    neww_socket.connect((ret1, int(singleBackend["backend_ip"][-4::])))
                    new_request = request.replace(ret3, singleBackend["backend_ip"])
                    neww_socket.send(new_request)
                    response = neww_socket.recv(1024)
                    new_socket.send(response.encode("utf-8"))


        if flag is False:
            response = "HTTP/1.1 404 NOT FOUND\r\n"
            response += "\r\n"
            response += "-------file not found-------"
            new_socket.send(response.encode("utf-8"))

        if ret2:
            file_name = ret2.group(1)
            if file_name == "/":
                file_name = "/index.html"

        # 2.返回http格式的数据给客户端
            if file_name == "/ping":
                response = "HTTP/1.1 200 OK\r\n"
                response += "\r\n"
                response += "Hello World"
                new_socket.send(response.encode("utf-8"))
            else:
                try:
                    f = open(file_name, "rb")
                except:
                    response = "HTTP/1.1 404 NOT FOUND\r\n"
                    response += "\r\n"
                    response += "-------file not found-------"
                    new_socket.send(response.encode("utf-8"))
                else:
                    html_content = f.read()
                    f.close()
                    # 2.1.1 准备发送给浏览器的数据-----header
                    response = "HTTP/1.1 200 OK\r\n"
                    response += "\r\n"

                    # 2.1.2 准备发送给浏览器的数据-----body
                    # response += "hello"

                    # 将response header发送给浏览器
                    new_socket.send(response.encode("utf-8"))
                    # 将response body发送给浏览器
                    new_socket.send(html_content)

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
