import xmlrpc.client

# 请替换为你站点的 URL 和登录凭据
url = "http://gtdaily.net/xmlrpc.php"
username = "admin"
password = "Prnasia2019qwe123!@#"

# 创建客户端
client = xmlrpc.client.ServerProxy(url)

try:
    # 尝试获取用户信息，以此验证身份是否通过
    user_info = client.wp.getUsersBlogs(username, password)
    print("连接成功！")
    print("获取到的博客信息:", user_info)
except Exception as e:
    print("连接失败，错误信息:", e)