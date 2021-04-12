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
        pika.ConnectionParameters(host=lv_config['host'], port=lv_config['port'], virtual_host='/h1', credentials=credentials)
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
        pika.ConnectionParameters(host=lv_config['host'], port=lv_config['port'], virtual_host='/h1', credentials=credentials)
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
    try:
        if paper:
            print("关联文献生成任务lid={},uid={}".format(paper["lid"],userId))
    except Exception:
        pass


# 监听消息队列 参数:  回调函数,队列名称
def msgListener(callback,queue="rel_done"):
    lv_config = getPikaConfig()
    credentials = pika.PlainCredentials(lv_config['user'], lv_config['password'])
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=lv_config['host'], port=lv_config['port'], virtual_host='/h1', credentials=credentials))
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
    #             "status": 0,
    #             "paperId": "0c0ac6a025a3da9cc71660c8b509c655",
    #             "userId": 9,
    #             "lid": "ee4a2b9cf40aba7c8e12f89679ed03d4",
    #             "references": [{"arxivId":null,"authors":[{"authorId":"1679784","name":"Fabian M. Suchanek"},{"authorId":"1686448","name":"Gjergji Kasneci"},{"authorId":"1751591","name":"G. Weikum"}],"doi":"10.1145/1242572.1242667","intent":["background"],"isInfluential":false,"paperId":"00a3f6924f90fcd77e6e7e6534b957a75d0ced07","title":"Yago: a core of semantic knowledge","url":"https://www.semanticscholar.org/paper/00a3f6924f90fcd77e6e7e6534b957a75d0ced07","venue":"WWW '07","year":2007},{"arxivId":null,"authors":[{"authorId":"1713934","name":"Antoine Bordes"},{"authorId":"1746841","name":"Nicolas Usunier"},{"authorId":"1405061488","name":"Alberto García-Durán"},{"authorId":"145183709","name":"J. Weston"},{"authorId":"2406794","name":"Oksana Yakhnenko"}],"doi":null,"intent":["methodology"],"isInfluential":true,"paperId":"2582ab7c70c9e7fcb84545944eba8f3a7f253248","title":"Translating Embeddings for Modeling Multi-relational Data","url":"https://www.semanticscholar.org/paper/2582ab7c70c9e7fcb84545944eba8f3a7f253248","venue":"NIPS","year":2013},{"arxivId":"1806.07297","authors":[{"authorId":"47733973","name":"Timothée Lacroix"},{"authorId":"1746841","name":"Nicolas Usunier"},{"authorId":"2533906","name":"G. Obozinski"}],"doi":null,"intent":["methodology"],"isInfluential":true,"paperId":"bbb2d7075141f6d638dd41c3ffe0d6bfb3d2dba9","title":"Canonical Tensor Decomposition for Knowledge Base Completion","url":"https://www.semanticscholar.org/paper/bbb2d7075141f6d638dd41c3ffe0d6bfb3d2dba9","venue":"ICML","year":2018},{"arxivId":"1712.02121","authors":[{"authorId":"38798269","name":"Dai Quoc Nguyen"},{"authorId":"3314511","name":"T. Nguyen"},{"authorId":"34691913","name":"Dat Quoc Nguyen"},{"authorId":"1749657","name":"Dinh Q. Phung"}],"doi":"10.18653/v1/N18-2053","intent":["background"],"isInfluential":false,"paperId":"41cbe3cdfee7539f8ff20144e6bd028ef762e00c","title":"A Novel Embedding Model for Knowledge Base Completion Based on Convolutional Neural Network","url":"https://www.semanticscholar.org/paper/41cbe3cdfee7539f8ff20144e6bd028ef762e00c","venue":"NAACL-HLT","year":2018},{"arxivId":null,"authors":[{"authorId":"1881550","name":"Guoliang Ji"},{"authorId":"1954845","name":"Shizhu He"},{"authorId":"8540973","name":"L. Xu"},{"authorId":"2200096","name":"Kang Liu"},{"authorId":"1390572170","name":"Jun Zhao"}],"doi":"10.3115/v1/P15-1067","intent":["methodology"],"isInfluential":false,"paperId":"18bd7cd489874ed9976b4f87a6a558f9533316e0","title":"Knowledge Graph Embedding via Dynamic Mapping Matrix","url":"https://www.semanticscholar.org/paper/18bd7cd489874ed9976b4f87a6a558f9533316e0","venue":"ACL","year":2015},{"arxivId":"1703.06103","authors":[{"authorId":"8804828","name":"M. Schlichtkrull"},{"authorId":"41016725","name":"Thomas Kipf"},{"authorId":"2789097","name":"P. Bloem"},{"authorId":"9965217","name":"R. V. Berg"},{"authorId":"144889265","name":"Ivan Titov"},{"authorId":"1678311","name":"M. Welling"}],"doi":"10.1007/978-3-319-93417-4_38","intent":[],"isInfluential":false,"paperId":"cd8a9914d50b0ac63315872530274d158d6aff09","title":"Modeling Relational Data with Graph Convolutional Networks","url":"https://www.semanticscholar.org/paper/cd8a9914d50b0ac63315872530274d158d6aff09","venue":"ESWC","year":2018},{"arxivId":"1707.01476","authors":[{"authorId":"3239480","name":"Tim Dettmers"},{"authorId":"3051815","name":"Pasquale Minervini"},{"authorId":"1918552","name":"Pontus Stenetorp"},{"authorId":"145941664","name":"S. Riedel"}],"doi":null,"intent":["methodology","background"],"isInfluential":true,"paperId":"9697d32ed0a16da167f2bdba05ef96d0da066eb5","title":"Convolutional 2D Knowledge Graph Embeddings","url":"https://www.semanticscholar.org/paper/9697d32ed0a16da167f2bdba05ef96d0da066eb5","venue":"AAAI","year":2018},{"arxivId":null,"authors":[{"authorId":"144096985","name":"G. Miller"}],"doi":"10.1145/219717.219748","intent":["background"],"isInfluential":false,"paperId":"68c03788224000794d5491ab459be0b2a2c38677","title":"WordNet: a lexical database for English","url":"https://www.semanticscholar.org/paper/68c03788224000794d5491ab459be0b2a2c38677","venue":"CACM","year":1995},{"arxivId":"1810.06546","authors":[{"authorId":"46279045","name":"A. Tifrea"},{"authorId":"9940262","name":"Gary Bécigneul"},{"authorId":"1882451","name":"Octavian-Eugen Ganea"}],"doi":null,"intent":["background"],"isInfluential":false,"paperId":"e8fa823c17aeb8d08fe9aa5fc2bc0eaacb9edcdf","title":"Poincaré GloVe: Hyperbolic Word Embeddings","url":"https://www.semanticscholar.org/paper/e8fa823c17aeb8d08fe9aa5fc2bc0eaacb9edcdf","venue":"ICLR","year":2019},{"arxivId":"1901.09590","authors":[{"authorId":"3451828","name":"Ivana Balazevic"},{"authorId":"4054662","name":"Carl Allen"},{"authorId":"1697755","name":"Timothy M. Hospedales"}],"doi":"10.18653/v1/D19-1522","intent":["methodology","background"],"isInfluential":true,"paperId":"05dc5fb3a3bdefdf181aafcc42cd80ff6b7704e7","title":"TuckER: Tensor Factorization for Knowledge Graph Completion","url":"https://www.semanticscholar.org/paper/05dc5fb3a3bdefdf181aafcc42cd80ff6b7704e7","venue":"EMNLP/IJCNLP","year":2019},{"arxivId":null,"authors":[{"authorId":"2427350","name":"Yankai Lin"},{"authorId":"49293587","name":"Zhiyuan Liu"},{"authorId":"1753344","name":"M. Sun"},{"authorId":"38057121","name":"Yang Liu"},{"authorId":"144809121","name":"Xuan Zhu"}],"doi":null,"intent":["methodology"],"isInfluential":false,"paperId":"994afdf0db0cb0456f4f76468380822c2f532726","title":"Learning Entity and Relation Embeddings for Knowledge Graph Completion","url":"https://www.semanticscholar.org/paper/994afdf0db0cb0456f4f76468380822c2f532726","venue":"AAAI","year":2015},{"arxivId":null,"authors":[{"authorId":null,"name":"Zhen Wang"},{"authorId":"38030790","name":"J. Zhang"},{"authorId":"2592554","name":"Jianlin Feng"},{"authorId":"48354590","name":"Z. Chen"}],"doi":null,"intent":["methodology"],"isInfluential":false,"paperId":"2a3f862199883ceff5e3c74126f0c80770653e05","title":"Knowledge Graph Embedding by Translating on Hyperplanes","url":"https://www.semanticscholar.org/paper/2a3f862199883ceff5e3c74126f0c80770653e05","venue":"AAAI","year":2014},{"arxivId":"1412.6980","authors":[{"authorId":"1726807","name":"Diederik P. Kingma"},{"authorId":"2503659","name":"Jimmy Ba"}],"doi":null,"intent":[],"isInfluential":false,"paperId":"a6cb366736791bcccc5c8639de5a8f9636bf87e8","title":"Adam: A Method for Stochastic Optimization","url":"https://www.semanticscholar.org/paper/a6cb366736791bcccc5c8639de5a8f9636bf87e8","venue":"ICLR","year":2015},{"arxivId":null,"authors":[{"authorId":"98738738","name":"D. Krackhardt"}],"doi":"10.4324/9781315806648-11","intent":[],"isInfluential":false,"paperId":"281f763f3c5aa28bd179d7484292cefa9a7e9d1b","title":"Graph theoretical dimensions of informal organizations","url":"https://www.semanticscholar.org/paper/281f763f3c5aa28bd179d7484292cefa9a7e9d1b","venue":"","year":1994},{"arxivId":null,"authors":[{"authorId":"2454800","name":"F. Mahdisoltani"},{"authorId":"2301985","name":"J. Biega"},{"authorId":"1679784","name":"Fabian M. Suchanek"}],"doi":null,"intent":["methodology"],"isInfluential":true,"paperId":"6c5b5adc3830ac45bf1d764603b1b71e5f729616","title":"YAGO3: A Knowledge Base from Multilingual Wikipedias","url":"https://www.semanticscholar.org/paper/6c5b5adc3830ac45bf1d764603b1b71e5f729616","venue":"CIDR","year":2015},{"arxivId":"1111.5280","authors":[{"authorId":"144699172","name":"S. Bonnabel"}],"doi":"10.1109/TAC.2013.2254619","intent":[],"isInfluential":false,"paperId":"7450d8d30a82362b22d83d634ec1c5696855cdf9","title":"Stochastic Gradient Descent on Riemannian Manifolds","url":"https://www.semanticscholar.org/paper/7450d8d30a82362b22d83d634ec1c5696855cdf9","venue":"IEEE Transactions on Automatic Control","year":2013},{"arxivId":"1805.09112","authors":[{"authorId":"1882451","name":"Octavian-Eugen Ganea"},{"authorId":"9940262","name":"Gary Bécigneul"},{"authorId":"143936663","name":"Thomas Hofmann"}],"doi":null,"intent":["background"],"isInfluential":true,"paperId":"562fa7faef812294bb1f235c97584f8560fb5cc0","title":"Hyperbolic Neural Networks","url":"https://www.semanticscholar.org/paper/562fa7faef812294bb1f235c97584f8560fb5cc0","venue":"NeurIPS","year":2018},{"arxivId":null,"authors":[{"authorId":"1734693","name":"John C. Duchi"},{"authorId":"34840427","name":"Elad Hazan"},{"authorId":"1740765","name":"Y. Singer"}],"doi":null,"intent":["methodology"],"isInfluential":false,"paperId":"413c1142de9d91804d6d11c67ff3fed59c9fc279","title":"Adaptive Subgradient Methods for Online Learning and Stochastic Optimization","url":"https://www.semanticscholar.org/paper/413c1142de9d91804d6d11c67ff3fed59c9fc279","venue":"J. Mach. Learn. Res.","year":2011},{"arxivId":"1910.12892","authors":[{"authorId":"15872772","name":"Q. Liu"},{"authorId":"144929567","name":"M. Nickel"},{"authorId":"1743722","name":"Douwe Kiela"}],"doi":null,"intent":["methodology"],"isInfluential":false,"paperId":"784b018c87c7dcbbe772374e45d5191bae9938ee","title":"Hyperbolic Graph Neural Networks","url":"https://www.semanticscholar.org/paper/784b018c87c7dcbbe772374e45d5191bae9938ee","venue":"NeurIPS","year":2019},{"arxivId":"1902.10197","authors":[{"authorId":"48064856","name":"Zhiqing Sun"},{"authorId":"123580511","name":"Zhihong Deng"},{"authorId":"143619007","name":"Jian-Yun Nie"},{"authorId":"145357803","name":"Jian Tang"}],"doi":null,"intent":["methodology","background"],"isInfluential":true,"paperId":"8f096071a09701012c9c279aee2a88143a295935","title":"RotatE: Knowledge Graph Embedding by Relational Rotation in Complex Space","url":"https://www.semanticscholar.org/paper/8f096071a09701012c9c279aee2a88143a295935","venue":"ICLR","year":2019},{"arxivId":null,"authors":[{"authorId":"1729762","name":"M. Nickel"},{"authorId":"1700754","name":"Volker Tresp"},{"authorId":"1688561","name":"H. Kriegel"}],"doi":null,"intent":["methodology"],"isInfluential":false,"paperId":"f6764d853a14b0c34df1d2283e76277aead40fde","title":"A Three-Way Model for Collective Learning on Multi-Relational Data","url":"https://www.semanticscholar.org/paper/f6764d853a14b0c34df1d2283e76277aead40fde","venue":"ICML","year":2011},{"arxivId":null,"authors":[{"authorId":"3259253","name":"Kristina Toutanova"},{"authorId":"50536468","name":"Danqi Chen"}],"doi":"10.18653/v1/W15-4007","intent":[],"isInfluential":true,"paperId":"b5c29457a90ee9af7c3b2985e9f665ce4b5b97d6","title":"Observed versus latent features for knowledge base and text inference","url":"https://www.semanticscholar.org/paper/b5c29457a90ee9af7c3b2985e9f665ce4b5b97d6","venue":"","year":2015},{"arxivId":null,"authors":[{"authorId":"1583098764","name":"Shuai Zhang"},{"authorId":"144447820","name":"Yi Tay"},{"authorId":"46518251","name":"L. Yao"},{"authorId":"15872772","name":"Q. Liu"}],"doi":null,"intent":["methodology"],"isInfluential":false,"paperId":"f78894c38cfd6404220b2b55b7f0f8c4fecbc34f","title":"Quaternion Knowledge Graph Embeddings","url":"https://www.semanticscholar.org/paper/f78894c38cfd6404220b2b55b7f0f8c4fecbc34f","venue":"NeurIPS","year":2019},{"arxivId":"1412.6575","authors":[{"authorId":"7324641","name":"B. Yang"},{"authorId":"144105277","name":"Wen-tau Yih"},{"authorId":"144137069","name":"X. He"},{"authorId":"1800422","name":"Jianfeng Gao"},{"authorId":"144718788","name":"L. Deng"}],"doi":null,"intent":["methodology"],"isInfluential":false,"paperId":"86412306b777ee35aba71d4795b02915cb8a04c3","title":"Embedding Entities and Relations for Learning and Inference in Knowledge Bases","url":"https://www.semanticscholar.org/paper/86412306b777ee35aba71d4795b02915cb8a04c3","venue":"ICLR","year":2015},{"arxivId":"1910.12933","authors":[{"authorId":"3442125","name":"Ines Chami"},{"authorId":"83539859","name":"Rex Ying"},{"authorId":"1803218","name":"Christopher Ré"},{"authorId":"1702139","name":"J. Leskovec"}],"doi":null,"intent":["methodology"],"isInfluential":false,"paperId":"97ebd482a78e6e6c1ba51da5e1b2f8e7640cc8b5","title":"Hyperbolic Graph Convolutional Neural Networks","url":"https://www.semanticscholar.org/paper/97ebd482a78e6e6c1ba51da5e1b2f8e7640cc8b5","venue":"NeurIPS","year":2019},{"arxivId":"1606.06357","authors":[{"authorId":"2057146","name":"T. Trouillon"},{"authorId":"1851564","name":"Johannes Welbl"},{"authorId":"145941664","name":"S. Riedel"},{"authorId":"1732180","name":"Éric Gaussier"},{"authorId":"1684865","name":"Guillaume Bouchard"}],"doi":null,"intent":["background"],"isInfluential":false,"paperId":"2218e2e1df2c3adfb70e0def2e326a39928aacfc","title":"Complex Embeddings for Simple Link Prediction","url":"https://www.semanticscholar.org/paper/2218e2e1df2c3adfb70e0def2e326a39928aacfc","venue":"ICML","year":2016},{"arxivId":null,"authors":[{"authorId":"1858169","name":"Trapit Bansal"},{"authorId":"144854012","name":"Da-Cheng Juan"},{"authorId":"35014893","name":"Sujith Ravi"},{"authorId":"143753639","name":"A. McCallum"}],"doi":"10.18653/v1/P19-1431","intent":["methodology","background"],"isInfluential":false,"paperId":"634c747829bb4529370775180cc254883e418ae9","title":"A2N: Attending to Neighbors for Knowledge Graph Inference","url":"https://www.semanticscholar.org/paper/634c747829bb4529370775180cc254883e418ae9","venue":"ACL","year":2019},{"arxivId":null,"authors":[{"authorId":"39499001","name":"A. Gu"},{"authorId":"82449565","name":"F. Sala"},{"authorId":"7653327","name":"Beliz Gunel"},{"authorId":"144988097","name":"C. Ré"}],"doi":null,"intent":["background"],"isInfluential":true,"paperId":"779ad52e8c27b77c10d14d536133da61c2c1f9b2","title":"Learning Mixed-Curvature Representations in Product Spaces","url":"https://www.semanticscholar.org/paper/779ad52e8c27b77c10d14d536133da61c2c1f9b2","venue":"ICLR","year":2019},{"arxivId":"1804.03329","authors":[{"authorId":"14123214","name":"Frederic Sala"},{"authorId":"1801197","name":"Christopher De Sa"},{"authorId":"39499001","name":"A. Gu"},{"authorId":"1803218","name":"Christopher Ré"}],"doi":null,"intent":["background"],"isInfluential":false,"paperId":"33618275fcb19b0535d1b25d02b1d3f3d058de04","title":"Representation Tradeoffs for Hyperbolic Embeddings","url":"https://www.semanticscholar.org/paper/33618275fcb19b0535d1b25d02b1d3f3d058de04","venue":"ICML","year":2018},{"arxivId":"1906.01195","authors":[{"authorId":"51130642","name":"Deepak Nathani"},{"authorId":"134145671","name":"Jatin Chauhan"},{"authorId":"50312463","name":"C. Sharma"},{"authorId":"38723417","name":"Manohar Kaul"}],"doi":"10.18653/v1/P19-1466","intent":["methodology"],"isInfluential":false,"paperId":"fddd3dab90c243ab7fc038bc6449ef62c0e06037","title":"Learning Attention-based Embeddings for Relation Prediction in Knowledge Graphs","url":"https://www.semanticscholar.org/paper/fddd3dab90c243ab7fc038bc6449ef62c0e06037","venue":"ACL","year":2019},{"arxivId":null,"authors":[{"authorId":"3451828","name":"Ivana Balazevic"},{"authorId":null,"name":"Carl Allen"},{"authorId":"1697755","name":"Timothy M. Hospedales"}],"doi":null,"intent":["methodology","background"],"isInfluential":true,"paperId":"a059785b56f0f285422c098e972baed062f93661","title":"Multi-relational Poincaré Graph Embeddings","url":"https://www.semanticscholar.org/paper/a059785b56f0f285422c098e972baed062f93661","venue":"NeurIPS","year":2019},{"arxivId":"1906.00687","authors":[{"authorId":"11721481","name":"Canran Xu"},{"authorId":"48881709","name":"Ruijiang Li"}],"doi":"10.18653/v1/P19-1026","intent":[],"isInfluential":false,"paperId":"f7b42a7d2d1b7098362b2243d6f1c5650d683985","title":"Relation Embedding with Dihedral Group in Knowledge Graph","url":"https://www.semanticscholar.org/paper/f7b42a7d2d1b7098362b2243d6f1c5650d683985","venue":"ACL","year":2019},{"arxivId":"1705.08039","authors":[{"authorId":"1729762","name":"M. Nickel"},{"authorId":"1743722","name":"Douwe Kiela"}],"doi":null,"intent":["background"],"isInfluential":false,"paperId":"1590bd1bca945fc6ff50b8cdf2da14ea2061c79a","title":"Poincaré Embeddings for Learning Hierarchical Representations","url":"https://www.semanticscholar.org/paper/1590bd1bca945fc6ff50b8cdf2da14ea2061c79a","venue":"NIPS","year":2017}],
    #             "abstract": "Knowledge graph (KG) embeddings learn low-dimensional representations of entities and relations to predict missing facts. KGs often exhibit hierarchical and logical patterns which must be preserved in the embedding space. For hierarchical data, hyperbolic embedding methods have shown promise for high-fidelity and parsimonious representations. However, existing hyperbolic embedding methods do not account for the rich logical patterns in KGs. In this work, we introduce a class of hyperbolic KG embedding models that simultaneously capture hierarchical and logical patterns. Our approach combines hyperbolic reflections and rotations with attention to model complex relational patterns. Experimental results on standard KG benchmarks show that our method improves over previous Euclidean- and hyperbolic-based efforts by up to 6.1% in mean reciprocal rank (MRR) in low dimensions. Furthermore, we observe that different geometric transformations capture different types of relations while attention-based transformations generalize to multiple relations. In high dimensions, our approach yields new state-of-the-art MRRs of 49.6% on WN18RR and 57.7% on YAGO3-10.",
    #             "data": [
    #     {
    #         "id": null,
    #         "doi": null,
    #         "arxivId": null,
    #         "semanticId": "2582ab7c70c9e7fcb84545944eba8f3a7f253248",
    #         "title": "Translating Embeddings for Modeling Multi-relational Data",
    #         "authStr": "Antoine Bordes,Nicolas Usunier,Alberto Garc\u00eda-Dur\u00e1n,J. Weston,Oksana Yakhnenko",
    #         "year": 2013,
    #         "venue": "NIPS",
    #         "abstract": "We consider the problem of embedding entities and relationships of multi-relational data in low-dimensional vector spaces. Our objective is to propose a canonical model which is easy to train, contains a reduced number of parameters and can scale up to very large databases. Hence, we propose TransE, a method which models relationships by interpreting them as translations operating on the low-dimensional embeddings of the entities. Despite its simplicity, this assumption proves to be powerful since extensive experiments show that TransE significantly outperforms state-of-the-art methods in link prediction on two knowledge bases. Besides, it can be successfully trained on a large scale data set with 1M entities, 25k relationships and more than 17M training samples.",
    #         "auth": [
    #             {
    #                 "authorId": "1713934",
    #                 "name": "Antoine Bordes",
    #                 "url": "https://www.semanticscholar.org/author/1713934"
    #             },
    #             {
    #                 "authorId": "1746841",
    #                 "name": "Nicolas Usunier",
    #                 "url": "https://www.semanticscholar.org/author/1746841"
    #             },
    #             {
    #                 "authorId": "1405061488",
    #                 "name": "Alberto Garc\u00eda-Dur\u00e1n",
    #                 "url": "https://www.semanticscholar.org/author/1405061488"
    #             },
    #             {
    #                 "authorId": "145183709",
    #                 "name": "J. Weston",
    #                 "url": "https://www.semanticscholar.org/author/145183709"
    #             },
    #             {
    #                 "authorId": "2406794",
    #                 "name": "Oksana Yakhnenko",
    #                 "url": "https://www.semanticscholar.org/author/2406794"
    #             }
    #         ],
    #         "view_count": null,
    #         "star_count": null,
    #         "cited_by": 2612,
    #         "cited_in_field": 19,
    #         "cited_in_field_norm": 0.576,
    #         "source": "Semantic"
    #     },
    #     {
    #         "id": null,
    #         "doi": null,
    #         "arxivId": null,
    #         "semanticId": "f6764d853a14b0c34df1d2283e76277aead40fde",
    #         "title": "A Three-Way Model for Collective Learning on Multi-Relational Data",
    #         "authStr": "M. Nickel,Volker Tresp,H. Kriegel",
    #         "year": 2011,
    #         "venue": "ICML",
    #         "abstract": "Relational learning is becoming increasingly important in many areas of application. Here, we present a novel approach to relational learning based on the factorization of a three-way tensor. We show that unlike other tensor approaches, our method is able to perform collective learning via the latent components of the model and provide an efficient algorithm to compute the factorization. We substantiate our theoretical considerations regarding the collective learning capabilities of our model by the means of experiments on both a new dataset and a dataset commonly used in entity resolution. Furthermore, we show on common benchmark datasets that our approach achieves better or on-par results, if compared to current state-of-the-art relational learning solutions, while it is significantly faster to compute.",
    #         "auth": [
    #             {
    #                 "authorId": "1729762",
    #                 "name": "M. Nickel",
    #                 "url": "https://www.semanticscholar.org/author/1729762"
    #             },
    #             {
    #                 "authorId": "1700754",
    #                 "name": "Volker Tresp",
    #                 "url": "https://www.semanticscholar.org/author/1700754"
    #             },
    #             {
    #                 "authorId": "1688561",
    #                 "name": "H. Kriegel",
    #                 "url": "https://www.semanticscholar.org/author/1688561"
    #             }
    #         ],
    #         "view_count": null,
    #         "star_count": null,
    #         "cited_by": 1069,
    #         "cited_in_field": 17,
    #         "cited_in_field_norm": 0.515,
    #         "source": "Semantic"
    #     }
    # ],
    #             "msg": "Success"
    #         }
    # '''
    data = json.loads(body)
    state = data["status"]
    paperId = data["paperId"]
    userId = data["userId"]
    phpCid = data["lid"]
    references = data["references"]
    abstract = data["abstract"]
    print("关联文献已生成lid:{},pid:{},uid:{},state:{}".format(phpCid,paperId,userId,state))

    if state!=0 :
        # 如果生成失败
        state = 1
        response =  requests.post(
            phpConfig['host']+'/addons/ask/detail/notice?user_id={}&paper_id={}&lid={}&state={}'.format(userId,paperId,phpCid,state),
            files=(
                ('data', (None, '')),
                ('references', (None, '')),
                ('abstract', (None, '')),
                ('message', (None, data["message"])),
            ),
            timeout = (20,20)
        )
        if response.status_code != 200:
            print("php服务出错paperId={} userId={}".format(paperId,userId))
        return



    # #向php中发消息(不包含生成的文献信息)
    # response =  requests.get(
    #     phpConfig['host']+'/addons/ask/detail/notice?user_id={}&paper_id={}'.format(userId,paperId),
    #     timeout=(20,20)
    # )

    #向php中发消息(包含生成的文献信息)
    response =  requests.post(
        phpConfig['host']+'/addons/ask/detail/notice?user_id={}&paper_id={}&lid={}&state={}'.format(userId,paperId,phpCid,state),
        files=(
            ('data', (None, demjson.encode(data["data"]))),
            ('references', (None, demjson.encode(references))),
            ('abstract', (None, abstract)),
        ),
        timeout = (20,20)
    )
    if response.status_code != 200:
        print("php服务出错paperId={} userId={}".format(paperId,userId))




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

def debugSend(data):
    config = configparser.ConfigParser()
    config.read("config.ini")
    return requests.post(config['DEBUG']['debug_host']+'/debuglog',data=data)

@app.route('/debuglog',methods = ['POST'])
def debuglog():
    data = dict(request.form)
    print(data)
    return "0"

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