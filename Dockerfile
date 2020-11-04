FROM rackspacedot/python37
# 禁用缓存
ARG CACHE_DATE=2019-01-01
RUN mkdir /var/www\
    && cd /var/www\
    && git clone https://github.com/hahaquanshikeng/paperSqlServer.git\
    && cd ./paperSqlServer\
    && pip install -r ./requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
# 工作目录
WORKDIR /var/www/paperSqlServer
# 默认暴露端口
EXPOSE 8686
# 容器启动后自动执行命令
CMD git fetch
CMD git pull
CMD python ./server.py