from flask import Flask, escape, request, abort
from gevent import pywsgi
import pymysql
import json
import demjson
import pika
import configparser
from  datetime import datetime
import time
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


# 消息入队 仅paperId
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

# 消息入队 传入完整paper数据
def sendMsgFullPaperData(queue='rel_to_do',*,userId,paper=None):
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
    if paper:
        msg["paper"] = paper
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
# def onRefGenerate():
    phpConfig = getPhpConfig()
    # body = '''
    #         {
    #         "status": 0,
    #         "message": "success/error message",
    #         "timestamp": "202101261135",
    #         "paperId": "000df741-8a61-4e0e-865d-fc3e72375dce",
    #         "lid":"000df741-8a61-4e0e-865d-fc3e72375dce",
    #         "userId": "9",
    #         "data": [
    #             {
    #                 "id": "12345",
    #                 "doi": "12345",
    #                 "title": "hello",
    #                 "authStr": "Aa,Bb,Cc",
    #                 "year": 2020,
    #                 "venue": "venue sample",
    #                 "abstract": "abstract sample",
    #                 "auth": "auth sample",
    #                 "view_count": 20,
    #                 "star_count": 30,
    #                 "source": "source sample"
    #             },
    #             {
    #                 "id": "12345",
    #                 "doi": "12345",
    #                 "title": "hello",
    #                 "authStr": "Aa,Bb,Cc",
    #                 "year": 2020,
    #                 "venue": "venue sample",
    #                 "abstract": "abstract sample",
    #                 "auth": "auth sample",
    #                 "view_count": 20,
    #                 "star_count": 30,
    #                 "source": "source sample"
    #             }
    #         ]
    #     }
    # '''
    data = json.loads(body)
    state = data["status"]
    if state!=0 :
        # 如果生成失败
        return
    paperId = data["paperId"]
    userId = data["userId"]
    phpCid = data["lid"]
    relData = data["data"]

    # #向php中发消息(不包含生成的文献信息)
    # response =  requests.get(
    #     phpConfig['host']+'/addons/ask/detail/notice?user_id={}&paper_id={}'.format(userId,paperId),
    #     timeout=(20,20)
    # )

    #向php中发消息(包含生成的文献信息)
    response =  requests.post(
        phpConfig['host']+'/addons/ask/detail/notice?user_id={}&paper_id={}&lid={}'.format(userId,paperId,phpCid),
        None,
        relData,
        headers = {'Content-Type': 'application/json', 'Accept':'application/json'},
        timeout = (20,20)
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

@app.route('/lulu')
def lulu():
    requests.post(
    "http://192.168.193.141:8686"+'/gugu',data={
        "actionList":123
    })
    return 123

@app.route('/gugu',methods = ['POST'])
def gugu():
    data = json.loads(list(request.form)[0])
    print(data)
    return 0

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
    cursor.execute("SELECT count(*) FROM clusterRelevance WHERE cid = %s", (id))
    db.close()
    relPaperCount = cursor.fetchone()[0]
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
    # db = getDb()
    # cursor = db.cursor()
    # sql = """
    # SELECT 
    #     A.cid,
    #     A.cdoi,
    #     A.ctitle,
    #     A.cauth,
    #     A.cyear,
    #     A.cvenue,
    #     A.cabstract,
    #     A.nread,
    #     COUNT(DISTINCT D.id),
    #     C.starNum,
    #     C.githubUrl,
    #     E.score
    # FROM
    #     clusterRelevance as E
    # INNER JOIN
    #     clusters as A
    # ON
    #     E.relCid = A.cid
    # LEFT JOIN 
    #     papers as B 
    # ON 
    #     E.relCid = B.cid 
    # LEFT JOIN 
    #     github_info as C 
    # ON 
    #     B.id = C.paperID
    # LEFT JOIN
    #     refs as D
    # ON
    #     E.relCid = D.cid
    # WHERE 
    #     E.cid = {id}
    # GROUP BY 
    #     E.relCid
    # """.format(id=id)
    # cursor.execute(sql)
    # listData = cursor.fetchall()
    # result = []
    # for data in listData:
    #     try:
    #         authData = demjson.decode(data[3])
    #         authStr = ",".join([x.get("name","") for x in authData])
    #     except Exception:
    #         authData = []
    #         authStr = None
    #     result.append({
    #         'id':data[0],
    #         'doi':data[1],
    #         'title':data[2],
    #         'authStr':authStr,
    #         'year':data[4],
    #         'venue':data[5],
    #         'abstract':data[6],
    #         'auth':demjson.encode(authData),
    #         'view_count':data[7],
    #         'star_count':data[9],
    #         'source':data[10],
    #         'rel_score':data[11]
    #     })
    # db.close()
    result = [
        {
            "id": "006132c7b2679b342a7c262520c2a027",
            "doi": "10.1109/ASSCC.2007.4425687",
            "title": "A 622Mb/s BPSK demodulator with mixed-mode demodulation scheme",
            "authStr": "Duho  Kim,Young-kwang  Seo,Hyunchin  Kim,Woo-young  Choi",
            "year": 2007,
            "venue": "2007 IEEE Asian Solid-State Circuits Conference",
            "abstract": "A new mixed-mode binary phase shift keying (BPSK) demodulator is demonstrated using a half-rate bang-bang phase detector commonly used in clock and data recovery (CDR) applications. This demodulator can be used for new home networking applications based on cable TV lines. A prototype chip is realized that can demodulate up to 622 Mb/s data at 1.4 GHz carrier frequency.",
            "auth": "[{\"ids\":[\"1792011\"],\"name\":\"Duho  Kim\"},{\"ids\":[\"11494965\"],\"name\":\"Young-kwang  Seo\"},{\"ids\":[\"31196486\"],\"name\":\"Hyunchin  Kim\"},{\"ids\":[\"145536154\"],\"name\":\"Woo-young  Choi\"}]",
            "view_count": None,
            "star_count": None,
            "source": None,
            "rel_score":0.5
        },
        {
            "id": "017faaeb8b85994fde34bdfccdad5598",
            "doi": "10.1016/j.str.2019.10.011",
            "title": "Modeling Antibody-Antigen Complexes by Information-Driven Docking.",
            "authStr": "Francesco  Ambrosetti,Brian  Jim\u00e9nez-Garc\u00eda,Jorge  Roel-Touris,Alexandre M J J Bonvin",
            "year": 2019,
            "venue": "Structure",
            "abstract": "Antibodies are Y-shaped proteins essential for immune response. Their capability to recognize antigens with high specificity makes them excellent therapeutic targets. Understanding the structural basis of antibody-antigen interactions is therefore crucial for improving our ability to design efficient biological drugs. Computational approaches such as molecular docking are providing a valuable and fast alternative to experimental structural characterization for these complexes. We investigate here how information about complementarity-determining regions and binding epitopes can be used to drive the modeling process, and present a comparative study of four different docking software suites (ClusPro, LightDock, ZDOCK, and HADDOCK) providing specific options for antibody-antigen modeling. Their performance on a dataset of 16 complexes is reported. HADDOCK, which includes information to drive the docking, is shown to perform best in terms of both success rate and quality of the generated models in both the presence and absence of information about the epitope on the antigen.",
            "auth": "[{\"ids\":[\"1413239125\"],\"name\":\"Francesco  Ambrosetti\"},{\"ids\":[\"1399365163\"],\"name\":\"Brian  Jim\\u00e9nez-Garc\\u00eda\"},{\"ids\":[\"1412783506\"],\"name\":\"Jorge  Roel-Touris\"},{\"ids\":[\"144959482\"],\"name\":\"Alexandre M J J Bonvin\"}]",
            "view_count": None,
            "star_count": None,
            "source": None,
            "rel_score":0.7
        },
        {
            "id": "01b3bc6aa945f698aab8912b0c6c2e33",
            "doi": "10.1016/j.ejor.2008.06.011",
            "title": "Feature cluster: Planning and scheduling in industrial and logistic systems",
            "authStr": "St\u00e9phane  Dauz\u00e8re-P\u00e9r\u00e8s,Nathalie  Sauer",
            "year": 2009,
            "venue": "Eur. J. Oper. Res.",
            "abstract": "The goal of this Feature Issue was to present new operational research results on ''Planning and Scheduling in Industrial and Logistic Systems\". Fifteen papers were submitted to the issue and, after a long and tedious refereeing process, only four papers were finally accepted. Three of the papers are on scheduling, but in rather different settings, and the last one proposes a novel algorithm for calculating safety stocks.",
            "auth": "[{\"ids\":[\"1398414105\"],\"name\":\"St\\u00e9phane  Dauz\\u00e8re-P\\u00e9r\\u00e8s\"},{\"ids\":[\"2434956\"],\"name\":\"Nathalie  Sauer\"}]",
            "view_count": None,
            "star_count": None,
            "source": None,
            "rel_score":0.3
        },
        {
            "id": "02b2cc62e7bfe742bf64ee5ea40fef9e",
            "doi": "10.14875/cogpsy.2009.0.123.0",
            "title": "\u30b0\u30e9\u30d5\u306e 3-D \u5316\u304c\u8aad\u307f\u53d6\u308a\u30d7\u30ed\u30bb\u30b9\u306b\u53ca\u307c\u3059\u5f71\u97ff(2)",
            "authStr": "\u5353\u53f8  \u4e0a\u7530,\u5b5d  \u5b89\u7530",
            "year": 2008,
            "venue": "",
            "abstract": "",
            "auth": "[{\"ids\":[\"71865472\"],\"name\":\"\\u5353\\u53f8  \\u4e0a\\u7530\"},{\"ids\":[\"72316738\"],\"name\":\"\\u5b5d  \\u5b89\\u7530\"}]",
            "view_count": None,
            "star_count": None,
            "source": None,
            "rel_score":0.9
        },
        {
            "id": "03cee2d60d9083b2e3341438efab06fd",
            "doi": "10.3788/ope.20202803.0671",
            "title": "Search area and target scale adaptive sea surface object tracking for unmanned surface vessel",
            "authStr": "\u5218 \u5a1c Liu Na,\u5cb3\u742a\u742a Yue Qi-qi,\u9648\u52a0\u5b8f Chen Jia-hong,\u5b59 \u5065 Sun Jian",
            "year": 2020,
            "venue": "",
            "abstract": "",
            "auth": "[{\"ids\":[\"90210921\"],\"name\":\"\\u5218 \\u5a1c Liu Na\"},{\"ids\":[\"1742269235\"],\"name\":\"\\u5cb3\\u742a\\u742a Yue Qi-qi\"},{\"ids\":[\"1742269237\"],\"name\":\"\\u9648\\u52a0\\u5b8f Chen Jia-hong\"},{\"ids\":[\"89692111\"],\"name\":\"\\u5b59 \\u5065 Sun Jian\"}]",
            "view_count": None,
            "star_count": None,
            "source": None,
            "rel_score":0.42
        },
        {
            "id": "0761806a953134c5461fa1dd457dec20",
            "doi": "10.1109/TC.1984.1676480",
            "title": "The Design of Easily Testable VLSI Array Multipliers",
            "authStr": "John Paul Shen,F. Joel Ferguson",
            "year": 1984,
            "venue": "IEEE Transactions on Computers",
            "abstract": "Array multipliers are well suited for VLSI implementation because of the regularity in their iterative structure. However, most VLSI circuits are difficult to test. This correspondence shows that, with appropriate cell design, array multipliers can be designed to be very easily testable. An array multiplier is called C-testable if all its adder cells can be exhaustively tested while requiring only a constant number of test patterns. The testability of two well-known array multiplier structures is studied in detail. The conventional design of the carry\u2013save array multiplier is modified. The modified design is shown to be C-testable and requires only 16 test patterns. Similar results are obtained for the Baugh\u2013Wooley two's complement array multiplier. A modified design of the Baugh\u2013Wooley array multiplier is shown to be C-testable and requires 55 test patterns. The C-testability of two other array multipliers, namely the carry\u2013propagate and the TRW designs, is also presented.",
            "auth": "[{\"ids\":[\"1760699\"],\"name\":\"John Paul Shen\"},{\"ids\":[\"145175552\"],\"name\":\"F. Joel Ferguson\"}]",
            "view_count": None,
            "star_count": None,
            "source": None,
            "rel_score":0.21
        },
        {
            "id": "0919ed89b9f38539fb4ecc131875e539",
            "doi": "10.1109/ARFTG.2015.7162896",
            "title": "Calibration of channel mismatch in time-interleaved real-time digital oscilloscopes",
            "authStr": "Chihyun  Cho,Joo-Gwang  Lee,Paul D. Hale,Jeffrey A. Jargon,Peter  Jeavons,John  Schlager,Andrew  Dienstfrey",
            "year": 2015,
            "venue": "2015 85th Microwave Measurement Conference (ARFTG)",
            "abstract": "A novel method is proposed for the calibration of channel mismatch in a time-interleaved real-time digital oscilloscope (RTDO). A simple simultaneous equation is derived from the Fourier transform of the time-interleaved signals. Thus, it only requires a transfer function of time-interleaved ADCs (TIADCs), while most of previous works have employed additional filters. A measurement method for the transfer function of a commercial RTDO is also proposed. The accuracy of the calibration method is determined by the noise produced after the interleaving process. To validate the proposed method, we measure two-tone signals using a commercial RTDO. The calibrated results clearly show signals at spurious frequencies are substantially reduced.",
            "auth": "[{\"ids\":[\"3219858\"],\"name\":\"Chihyun  Cho\"},{\"ids\":[\"2344667\"],\"name\":\"Joo-Gwang  Lee\"},{\"ids\":[\"2040522\"],\"name\":\"Paul D. Hale\"},{\"ids\":[\"1782739\"],\"name\":\"Jeffrey A. Jargon\"},{\"ids\":[\"144922784\"],\"name\":\"Peter  Jeavons\"},{\"ids\":[\"35128235\"],\"name\":\"John  Schlager\"},{\"ids\":[\"2682560\"],\"name\":\"Andrew  Dienstfrey\"}]",
            "view_count": None,
            "star_count": None,
            "source": 0.75
        },
        {
            "id": "0d09cf11fc95247cf97a5fd4351c047a",
            "doi": "10.1186/1471-2202-14-S1-P417",
            "title": "Realistic simulations of local field potentials in a slice",
            "authStr": "Hanuma C Chintaluri,Helena  G\u0142\u0105bska,Torbj\u00f8rn B\u00e6k\u00f8 Ness,Gaute T Einevoll,Daniel K W\u00f3jcik",
            "year": 2013,
            "venue": "BMC Neuroscience",
            "abstract": "The two key elements of realistic simulation of LFP are plausible model of neural activity, and the physical properties of the setup, tissue, and electrodes. To reduce the computational burden yet obtain a trustful rendering of LFP in specific experimental context different strategies have been tried. For instance, using total synaptic activity from a population of spiking neurons as a proxy for LFP, or hybrid strategies with network simulations of spiking neurons followed by computation of contributions to LFP from single cells driven by pre-calculated network dynamics. Tests of those strategies are impossible without ground-truth data including all the necessary components. \n \nWorking towards a framework providing ground truth data for validating methods of analysis of extracellular potentials in cortical slices, we investigated how the use of increasingly detailed physical models of slice tissue affects the resulting model LFPs. Traub's model of thalamo-cortical loop [1] was simulated in NEURON and the extracellular potentials in uniform, homogeneous medium (Vhom) were computed post-hoc from tracked trans-membrane currents. To verify the need for inclusion of experimental setup context we modeled the field in the tissue and saline using finite-element approach (FEM) with FENICS package with mesh generated with gmsh. The slice (yellow parallelogram) was placed in a saline solution (Figure \u200b(Figure1A)1A) and the cortical column was put in the middle of the slice, and we computed the extracellular potentials it generated at the electrode plane under the slice. \n \n \n \nFigure 1 \n \nA. The mesh in the Petri dish with saline (cylinder), slice is the yellow bar. B. Average L1 norm of difference |k*Vhom - V| as a function of k where V is the potential on the electrode plane in the three cases i)-iii). \n \n \n \nWe modeled 3 different conductivity profiles within the slice and the saline: \n \ni) 'no saline' case: slice and saline with the same conductivity of 0.3 mS/cm \n \nii) 'hom+iso+saline': homogeneous and isotropic slice of conductivity 0.3 mS/cm, saline: 3.0 mS/cm \n \niii) 'inhom+anis+saline': inhomogeneous and anisotropic slice with conductivity profiles for the layers taken as mean values from [2]. \n \nWe see that the inclusion of slice setup noticeably modifies the observed activity as both the amplitude and shape of the potential profile is changed (Figure \u200b(Figure1B).1B). However, inclusion of inhomogeneity and anisotropy in the computations does not lead to substantial changes of the profile. Indeed, inaccurate estimation of conductivity (see variability of results in [2]) will in general introduce bigger errors than in assuming homogeneous and isotropic tissue.",
            "auth": "[{\"ids\":[\"6901132\"],\"name\":\"Hanuma C Chintaluri\"},{\"ids\":[\"3402212\"],\"name\":\"Helena  G\\u0142\\u0105bska\"},{\"ids\":[\"6493011\"],\"name\":\"Torbj\\u00f8rn B\\u00e6k\\u00f8 Ness\"},{\"ids\":[\"3000237\"],\"name\":\"Gaute T Einevoll\"},{\"ids\":[\"2352879\"],\"name\":\"Daniel K W\\u00f3jcik\"}]",
            "view_count": None,
            "star_count": None,
            "source": 0.88
        },
        {
            "id": "0f21589522a4819a6de2ef62c444ddfc",
            "doi": "10.1007/3-540-63138-0_4",
            "title": "On Computing All Maximal Cliques Distributedly",
            "authStr": "F\u00e1bio  Protti,Felipe Maia Galv\u00e3o Fran\u00e7a,Jayme Luiz Szwarcfiter",
            "year": 1997,
            "venue": "IRREGULAR",
            "abstract": "A distributed algorithm is presented for generating all maximal cliques in a network graph, based on the sequential version of Tsukiyama et al. [TIAS77]. The time complexity of the proposed approach is restricted to the induced neighborhood of a node, and the communication complexity is O(md) where m is the number of connections, and d is the maximum degree in the graph. Messages are O(log n) bits long, where n is the number of nodes (processors) in the system. As an application, a distributed algorithm for constructing the clique graph K (G) from a given network graph G is developed within the scope of dynamic transformations of topologies.",
            "auth": "[{\"ids\":[\"121569394\"],\"name\":\"F\\u00e1bio  Protti\"},{\"ids\":[\"2089536\"],\"name\":\"Felipe Maia Galv\\u00e3o Fran\\u00e7a\"},{\"ids\":[\"1696569\"],\"name\":\"Jayme Luiz Szwarcfiter\"}]",
            "view_count": None,
            "star_count": None,
            "source": 0.71
        },
        {
            "id": "1109256232e82e137b5d4301fa6507ab",
            "doi": "10.4271/2015-01-2363",
            "title": "Methods for Measuring, Analyzing and Predicting the Dynamic Torque of an Electric Drive Used in an Automotive Drivetrain",
            "authStr": "Albert  Albers,Jan  Fischer,Matthias  Behrendt,Dirk  Lieske",
            "year": 2015,
            "venue": "",
            "abstract": "",
            "auth": "[{\"ids\":[\"34726080\"],\"name\":\"Albert  Albers\"},{\"ids\":[\"145285971\"],\"name\":\"Jan  Fischer\"},{\"ids\":[\"40687427\"],\"name\":\"Matthias  Behrendt\"},{\"ids\":[\"93381144\"],\"name\":\"Dirk  Lieske\"}]",
            "view_count": None,
            "star_count": None,
            "source": 0.6
        },
    ]
    return json.dumps(result,indent=4)

@app.route('/full_text_search',methods = ['POST'])
def fullTextSearch():
    phpConfig = getPhpConfig()
    actionList = json.loads(request.form['actionList'])
    for actionDict in actionList:
        authData = demjson.decode(actionDict["data"]["cauth"]) if actionDict["data"]["cauth"] != None else None
        actionDict["data"]["cauthStr"] = ",".join([x.get("name","") for x in authData])
    #转发请求至php
    try:
        response = requests.post(
            phpConfig['host']+'/addons/xunsearch/paper_full_text_search',data={
                "actionList":json.dumps(actionList)
            },timeout=(20,20)
        )
    except Exception as e:
        return json.dumps({
            "code":500,
            "msg":"php 服务器出错",
            "time":str(int(time.time())),
            "data":str(e)
        },indent=4)
    # 直接转发php响应
    return response.content

@app.route('/rel_paper_task/user/<userId>',methods = ['POST'])
def rel_paper_task(userId):
# {'id': 20, 'doi': None, 'title': '这是一个标题', 'authStr': '', 'year': 1998, 'venue': '', 'abstract': None, 'auth': 
# '[{"name":"Black Li"}]', 'view_count': 0, 'ref_count': 0, 'start_count': 0, 'question_count': 0, 'article_count': 0, 
# 'explain_count': 0, 'source': '', 'pid': '', 'lid': 'b7deda2eaa44e88820e6c240ca9c97ee', 'arxivId': None}
    paper = json.loads(list(request.form)[0])
    try:
        sendMsgFullPaperData(userId=userId,paper=paper)
    except Exception:
        return json.dumps({
                "state":0
        },indent=4)
    return json.dumps({
            "state":1
    },indent=4)




if __name__ == '__main__':
    # app.run('0.0.0.0',8686,True)
    _thread.start_new_thread(msgListener, (onRefGenerate,'rel_done',) )
    server = pywsgi.WSGIServer(('0.0.0.0',8686), app)
    server.serve_forever()