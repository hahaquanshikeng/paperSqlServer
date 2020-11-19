from flask import Flask, escape, request, abort
from gevent import pywsgi
import pymysql
import json
import demjson
# 打开数据库连接
def getDb():
    # 学校
    return pymysql.connect("210.30.97.164","papers","issme316","papers" )
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
        C.starNum,
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
            'start_count':data[9],
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
            'start_count':data[9],
            'source':data[10],
        })
    db.close()
    return json.dumps(result,indent=4)


if __name__ == '__main__':
    # app.run('0.0.0.0',8686,True)
    server = pywsgi.WSGIServer(('0.0.0.0',8686), app)
    server.serve_forever()