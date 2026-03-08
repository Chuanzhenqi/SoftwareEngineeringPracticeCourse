## 1.调用skill生成需求描述文档的情况：

![image-20260308194454384](C:\Users\chuanzhenqi\AppData\Roaming\Typora\typora-user-images\image-20260308194454384.png)

![image-20260308194545102](C:\Users\chuanzhenqi\AppData\Roaming\Typora\typora-user-images\image-20260308194545102.png)

从提问到生成文档共计5m40s，本过程不需要调用rag数据库查询。时间长感觉主要是因为api key反映比较慢

## 2. 调用rag库但没有收索到结果的情况

![image-20260308194930682](C:\Users\chuanzhenqi\AppData\Roaming\Typora\typora-user-images\image-20260308194930682.png)

多次反复查询

![image-20260308222600968](C:\Users\chuanzhenqi\AppData\Roaming\Typora\typora-user-images\image-20260308222600968.png)

![image-20260308222730363](C:\Users\chuanzhenqi\AppData\Roaming\Typora\typora-user-images\image-20260308222730363.png)

两次查询向量数据库没有结果，转而直接根据skill目录下的报告模版和example示例文档生成软件概要说明书。本次总共用时9m8s，但是考虑到上次在没有查询数据库的情况花费5m多，其实也就大约是普通生成任务的两倍，而且这个api key调用起来本来就慢，真实如果换用其他反应快的模型速度肯定没这么慢。（过程中有报错，其实是本地使用python虚拟环境，因为没有激活，所以claude code运行脚本指令的时候出现了报错）

## 3.调用rag库生成回答的情况

![image-20260308230431789](C:\Users\chuanzhenqi\AppData\Roaming\Typora\typora-user-images\image-20260308230431789.png)

![image-20260308230526490](C:\Users\chuanzhenqi\AppData\Roaming\Typora\typora-user-images\image-20260308230526490.png)

![image-20260308230553533](C:\Users\chuanzhenqi\AppData\Roaming\Typora\typora-user-images\image-20260308230553533.png)

本次生成任务总共用时10m10s，相比之前没有查到rag信息的生成任务慢了一分钟左右，考虑到模型需要处理返回的查询结果和该任务的模版信息，时间比较合理。但感觉这接口调用得本来就有一点慢，如果模型调用速度快的话其实时间也就多了10%左右，是能接受的。毕竟如果假设不依赖rag数据库能1min输出，算上有rag搜索结果的时候也就最多2min