from flask import Flask, escape, request, abort
from gevent import pywsgi
import pymysql
import json
import demjson
import requests
import pika
import configparser
from  datetime import datetime
import _thread
import requests

def getPikaConfig():
    config = configparser.ConfigParser()
    config.read("config.ini")
    return {
            'host': config['PIKA']['pika_host'],
            'port': config['PIKA']['pika_port'],
            'user': config['PIKA']['pika_user'],
            'password': config['PIKA']['pika_password']
        }
def getPhpConfig():
    config = configparser.ConfigParser()
    config.read("config.ini")
    return {
            'host': config['PHP']['php_host'],
        }


# 消息入队
def sendMsg(queue='rel_to_do',*,userId,paperId=None,paperDoi=None,paperArxiv=None):
    lv_config = getPikaConfig()
    credentials = pika.PlainCredentials(lv_config['user'], lv_config['password'])
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=lv_config['host'], port=lv_config['port'], virtual_host='/', credentials=credentials)
    )
    channel = connection.channel()

    channel.queue_declare(queue=queue, durable=True)
    msg = {
        "start_datetime":datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    if userId:
       msg["user_id"] = userId
    if paperId:
        msg["paper_id"] = paperId
    if paperDoi:
        msg["paper_doi"] = paperDoi
    if paperArxiv:
        msg["paper_arxiv_id"] = paperArxiv
    channel.basic_publish(exchange='', routing_key=queue, body=json.dumps(msg))
    connection.close()

# 监听消息队列 参数:  回调函数,队列名称
def msgListener(callback,queue="rel_done"):
    lv_config = getPikaConfig()
    credentials = pika.PlainCredentials(lv_config['user'], lv_config['password'])
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=lv_config['host'], port=lv_config['port'], virtual_host='/', credentials=credentials))
    channel = connection.channel()
    channel.queue_declare(queue = queue,durable=True)
    channel.basic_qos(prefetch_count=1)
    # callback(ch, method, properties, body)
    channel.basic_consume(queue=queue, on_message_callback=callback, auto_ack=True)

    print('Waiting for messages. To exit press CTRL+C')

    channel.start_consuming()

# 关联文献生成成功回调
def onRefGenerate(ch, method, properties, body):
    phpConfig = getPhpConfig()
    data = json.loads(body)
    paperId = data["paper_id"]
    userId = data["user_id"]
    #向php中发消息
    response =  requests.get(
        phpConfig['host']+'/addons/ask/detail/notice?user_id={}&paper_id={}'.format(userId,paperId),
        timeout=(20,20)
    )
    if response.status_code != 200:
        print("php服务出错paperId={} userId={}".format(userId,paperId))



# 打开数据库连接
def getDb():
    # 学校
    return pymysql.connect("210.30.97.163","root","123456","matrix" )
    # 容器内
    #return pymysql.connect("172.17.0.1","root","Issme316","papers" )
 
# # 使用 cursor() 方法创建一个游标对象 cursor
# cursor = db.cursor()
 
# # 使用 execute()  方法执行 SQL 查询 
# cursor.execute("SELECT VERSION()")
 
# # 使用 fetchone() 方法获取单条数据.
# data = cursor.fetchone()

app = Flask(__name__)

@app.route('/')
def hello():
    return f'服务启动正常'

@app.route('/papers',methods = ['POST'])
def papers():
    paperIds = request.form['paperIds']
    
    if paperIds.strip()=="":
        return '[]'
    paperIds =  ",".join(["'"+x+"'" for x in paperIds.split(",")]) 
    db = getDb()
    cursor = db.cursor()
    sql = """
    SELECT 
        A.cid,
        A.cdoi,
        A.ctitle,
        A.cauth,
        A.cyear,
        A.cvenue,
        A.cabstract,
        A.nread,
        COUNT(DISTINCT D.id),
        C.startNum,
        C.githubUrl 
    FROM 
        clusters as A 
    LEFT JOIN 
        papers as B 
    ON 
        A.cid = B.cid 
    LEFT JOIN 
        github_info as C 
    ON 
        B.id = C.paperID
    LEFT JOIN
        refs as D
    ON
        A.cid = D.cid
    WHERE 
        A.cid in ({paperIds})
    GROUP BY 
        A.cid""".format(paperIds=paperIds)
    cursor.execute(sql)
    # try:
    #     cursor.execute(sql)
    # except pymysql.err.ProgrammingError:
    #     abort(400)
    listData = cursor.fetchall()
    result = []
    for data in listData:
        try:
            authData = demjson.decode(data[3])
            authStr = ",".join([x.get("name","") for x in authData])
        except Exception:
            authData = []
            authStr = None
        result.append({
            'id':data[0],
            'doi':data[1],
            'title':data[2],
            'authStr':authStr,
            'year':data[4],
            'venue':data[5],
            'abstract':data[6],
            'auth':demjson.encode(authData),
            'view_count':data[7],
            'star_count':data[9],
            'source':data[10],
        })
    db.close()
    # return sql
    return json.dumps(result,indent=4)
# 测试id d4a88a01-36e2-4c41-b0b8-43de835244c8
@app.route('/refs/<id>',methods = ['GET'])
def reference(id):
    db = getDb()
    cursor = db.cursor()
    sql = """
    SELECT 
        C.cid,
        C.cdoi,
        C.ctitle,
        C.cauth,
        C.cyear,
        C.cvenue,
        C.cabstract,
        C.nread,
        COUNT(DISTINCT D.id),
        F.starNum,
        F.githubUrl
    FROM 
        clusters as A
    INNER JOIN
        refs as B
    ON
        A.cid = B.cid
    INNER JOIN
        clusters as C
    ON
        B.selfcid = C.cid
    LEFT JOIN
        refs as D
    ON
        C.cid = D.cid
    LEFT JOIN
        papers as E
    ON 
        C.cid = E.cid 
    LEFT JOIN 
        github_info as F
    ON 
        E.id = F.paperID
    WHERE 
        A.cid = '{id}'
    GROUP BY
		C.cid
    """.format(id=id)
    cursor.execute(sql)
    listData = cursor.fetchall()
    result = []
    for data in listData:
        try:
            authData = demjson.decode(data[3])
            authStr = ",".join([x.get("name","") for x in authData])
        except Exception:
            authData = []
            authStr = None
        result.append({
            'id':data[0],
            'doi':data[1],
            'title':data[2],
            'authStr':authStr,
            'year':data[4],
            'venue':data[5],
            'abstract':data[6],
            'auth':demjson.encode(authData),
            'view_count':data[7],
            'star_count':data[9],
            'source':data[10],
        })
    db.close()
    return json.dumps(result,indent=4)

@app.route('/rel_paper_state/<id>/user/<userId>',methods = ['GET'])
def relPaperState(id,userId):
    db = getDb()
    cursor = db.cursor()
    relPaperCount = cursor.execute("SELECT count(*) FROM clusterRelevance WHERE cid = %s", (id))
    db.close()

    # state: 1存在 2不存在
    if relPaperCount > 0:
        return json.dumps({
            "state":1
        },indent=4)
    else:
        sendMsg(userId=userId,paperId=id)
        return json.dumps({
            "state":2
        },indent=4)

@app.route('/rel_paper_info/<id>',methods = ['GET'])
def relPaperInfo(id):
    sendMsg('rel_done',paperId='08365c1f-0aef-43f1-8307-4af54f2c2b3b',userId=1)
    return "123"


if __name__ == '__main__':
    # app.run('0.0.0.0',8686,True)
    _thread.start_new_thread(msgListener, (onRefGenerate,'rel_done',) )
    server = pywsgi.WSGIServer(('0.0.0.0',8686), app)
    server.serve_forever()