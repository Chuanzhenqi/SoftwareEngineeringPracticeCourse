# "风行旅途"旅游管理系统用户手册

## 📋 目录
- [1. 项目概述](#1-项目概述)
- [2. 系统要求](#2-系统要求)
- [3. 环境搭建](#3-环境搭建)
- [4. 项目部署](#4-项目部署)
- [5. 系统配置](#5-系统配置)
- [6. 启动运行](#6-启动运行)
- [7. 功能使用](#7-功能使用)
- [8. 常见问题](#8-常见问题)
- [9. 维护指南](#9-维护指南)

## 1. 项目概述

### 1.1 项目简介
"风行旅途"是一个基于SpringBoot+Vue架构的综合性旅游管理系统，提供火车票预订、酒店预订、旅游规划等一站式旅游服务。

### 1.2 技术架构
- **后端框架**: Spring Boot 2.2.2
- **前端框架**: Vue.js
- **数据库**: MySQL 8.0
- **安全框架**: Apache Shiro 1.3.2
- **ORM框架**: MyBatis Plus 2.3
- **API文档**: Swagger2 2.9.2

### 1.3 项目结构
```
springboot655ms/
├── src/
│   ├── main/
│   │   ├── java/com/
│   │   │   ├── controller/     # 控制器层
│   │   │   ├── service/        # 服务层
│   │   │   ├── dao/           # 数据访问层
│   │   │   ├── entity/        # 实体类
│   │   │   ├── config/        # 配置类
│   │   │   └── utils/         # 工具类
│   │   └── resources/
│   │       ├── front/         # 用户端页面
│   │       ├── mapper/        # MyBatis映射文件
│   │       └── application.yml # 配置文件
├── db/
│   └── springboot655ms.sql    # 数据库脚本
├── pom.xml                    # Maven配置
└── README.md
```

## 2. 系统要求

### 2.1 硬件要求
- **CPU**: Intel i5 及以上或同等性能
- **内存**: 8GB 及以上
- **硬盘**: 至少 10GB 可用空间
- **网络**: 稳定的网络连接

### 2.2 软件要求
- **操作系统**: Windows 10/11, macOS 10.14+, Ubuntu 18.04+
- **Java**: JDK 1.8 或以上版本
- **数据库**: MySQL 8.0 或以上版本
- **浏览器**: Chrome 90+, Firefox 88+, Edge 90+
- **开发工具**: IntelliJ IDEA 或 Eclipse (可选)

## 3. 环境搭建

### 3.1 Java环境安装

#### Windows系统
1. 下载JDK 1.8：https://www.oracle.com/java/technologies/javase-jdk8-downloads.html
2. 运行安装程序，按默认设置安装
3. 配置环境变量：
   ```
   JAVA_HOME = C:\Program Files\Java\jdk1.8.0_xxx
   PATH = %JAVA_HOME%\bin;%PATH%
   ```
4. 验证安装：
   ```cmd
   java -version
   javac -version
   ```

#### macOS系统
```bash
# 使用Homebrew安装
brew install openjdk@8

# 配置环境变量
echo 'export PATH="/usr/local/opt/openjdk@8/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

#### Linux系统
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install openjdk-8-jdk

# CentOS/RHEL
sudo yum install java-1.8.0-openjdk-devel
```

### 3.2 MySQL数据库安装

#### Windows系统
1. 下载MySQL 8.0：https://dev.mysql.com/downloads/mysql/
2. 运行安装程序，选择"Developer Default"
3. 设置root密码：123456（与项目配置一致）
4. 完成安装并启动MySQL服务

#### macOS系统
```bash
# 使用Homebrew安装
brew install mysql

# 启动MySQL服务
brew services start mysql

# 设置root密码
mysql_secure_installation
```

#### Linux系统
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install mysql-server

# 启动MySQL服务
sudo systemctl start mysql
sudo systemctl enable mysql

# 设置root密码
sudo mysql_secure_installation
```

### 3.3 Maven环境安装

#### Windows系统
1. 下载Maven：https://maven.apache.org/download.cgi
2. 解压到指定目录，如：C:\Program Files\Apache\maven
3. 配置环境变量：
   ```
   MAVEN_HOME = C:\Program Files\Apache\maven
   PATH = %MAVEN_HOME%\bin;%PATH%
   ```

#### macOS/Linux系统
```bash
# macOS使用Homebrew
brew install maven

# Linux使用包管理器
sudo apt install maven  # Ubuntu/Debian
sudo yum install maven   # CentOS/RHEL
```

## 4. 项目部署

### 4.1 获取项目代码
```bash
# 如果使用Git
git clone [项目地址]
cd springboot655ms

# 或直接解压项目压缩包
unzip springboot655ms.zip
cd springboot655ms
```

### 4.2 数据库初始化

#### 4.2.1 创建数据库
```sql
-- 登录MySQL
mysql -u root -p

-- 创建数据库
CREATE DATABASE springboot655ms DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

-- 使用数据库
USE springboot655ms;
```

#### 4.2.2 导入数据
```bash
# 方法1：使用命令行导入
mysql -u root -p springboot655ms < db/springboot655ms.sql

# 方法2：使用MySQL客户端
在MySQL Workbench或Navicat中执行db/springboot655ms.sql文件
```

### 4.3 项目配置

#### 4.3.1 数据库配置
编辑 `src/main/resources/application.yml`：
```yaml
spring:
  datasource:
    driver-class-name: com.mysql.cj.jdbc.Driver
    url: jdbc:mysql://127.0.0.1:3306/springboot655ms?useSSL=false&allowPublicKeyRetrieval=true&useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai
    username: root
    password: 123456  # 修改为您的MySQL密码
```

#### 4.3.2 服务器配置
```yaml
server:
  tomcat:
    uri-encoding: UTF-8
  port: 8080  # 可修改为其他端口
  servlet:
    context-path: /springboot655ms
```

### 4.4 依赖安装
```bash
# 进入项目根目录
cd springboot655ms

# 安装Maven依赖
mvn clean install

# 或者跳过测试安装
mvn clean install -DskipTests
```

## 5. 系统配置

### 5.2 文件上传配置
```yaml
spring:
  servlet:
    multipart:
      max-file-size: 300MB
      max-request-size: 300MB
  resources:
    static-locations: classpath:static/,file:static/
```

### 5.3 MyBatis Plus配置
```yaml
mybatis-plus:
  mapper-locations: classpath*:mapper/*.xml
  typeAliasesPackage: com.entity
  global-config:
    id-type: 1
    field-strategy: 1
    db-column-underline: true
    refresh-mapper: true
    logic-delete-value: -1
    logic-not-delete-value: 0
    sql-injector: com.baomidou.mybatisplus.mapper.LogicSqlInjector
  configuration:
    map-underscore-to-camel-case: true
    cache-enabled: false
    call-setters-on-nulls: true
    jdbc-type-for-null: 'null'
```

## 6. 启动运行

### 6.1 IDE中运行

#### 6.1.1 IntelliJ IDEA
1. 打开IntelliJ IDEA
2. 选择 "Open" 打开项目文件夹
3. 等待Maven依赖下载完成
4. 找到 `SpringbootSchemaApplication.java`
5. 右键选择 "Run SpringbootSchemaApplication"

#### 6.1.2 Eclipse
1. 打开Eclipse
2. 选择 "File" -> "Import" -> "Existing Maven Projects"
3. 选择项目文件夹
4. 等待Maven依赖下载完成
5. 右键项目 -> "Run As" -> "Spring Boot App"

### 6.2 命令行运行

#### 6.2.1 使用Maven运行
```bash
# 进入项目根目录
cd springboot655ms

# 使用Maven运行
mvn spring-boot:run
```

#### 6.2.2 使用JAR包运行
```bash
# 打包项目
mvn clean package -DskipTests

# 运行JAR包
java -jar target/springboot655ms-0.0.1-SNAPSHOT.jar
```

### 6.3 验证启动
启动成功后，您应该看到类似以下的日志输出：
```
  .   ____          _            __ _ _
 /\\ / ___'_ __ _ _(_)_ __  __ _ \ \ \ \
( ( )\___ | '_ | '_| | '_ \/ _` | \ \ \ \
 \\/  ___)| |_)| | | | | || (_| |  ) ) ) )
  '  |____| .__|_| |_|_| |_\__, | / / / /
 =========|_|==============|___/=/_/_/_/
 :: Spring Boot ::        (v2.2.2.RELEASE)

2025-02-18 10:00:00.000  INFO --- [           main] com.SpringbootSchemaApplication         : Started SpringbootSchemaApplication in 10.123 seconds (JVM running for 11.456)
```

## 7. 功能使用

### 7.1 访问系统

#### 7.1.1 系统地址
- **前台用户端**: http://localhost:8080/#/index/home

#### 7.1.2 默认账号
- 用户名: 111
- 密码: 111

### 7.2 主要功能模块

#### 7.2.1 用户模块
- 用户注册和登录
- 个人信息管理
- 密码修改


#### 7.2.3 订票模块
- 车次信息查询
- 购买火车票
- 加购火车餐
- 预订景点门票

#### 7.2.4 酒店模块
- 酒店信息浏览
- 客房预订
- 预订状态管理

#### 7.2.5 社交模块
- 路线规划分享
- 旅行日记分享
- 讨论区和点赞收藏


## 8. 常见问题

### 8.1 启动问题

#### 8.1.1 端口占用问题
**问题**: `Port 8080 was already in use`
**解决方案**:
```bash
# 方法1：查找并终止占用端口的进程
# Windows
netstat -ano | findstr :8080
taskkill /PID [进程ID] /F

# macOS/Linux
lsof -i :8080
kill -9 [进程ID]

# 方法2：修改application.yml中的端口
server:
  port: 8081  # 改为其他端口
```

#### 8.1.2 数据库连接失败
**问题**: `Communications link failure`
**解决方案**:
1. 检查MySQL服务是否启动
2. 验证数据库连接信息
3. 检查防火墙设置
4. 确认数据库用户权限

```bash
# 启动MySQL服务
# Windows
net start mysql

# macOS
brew services start mysql

# Linux
sudo systemctl start mysql
```

#### 8.1.3 Maven依赖下载失败
**问题**: 依赖下载超时或失败
**解决方案**:
```bash
# 清理Maven缓存
mvn clean

# 强制更新依赖
mvn clean install -U

# 配置国内镜像源（修改~/.m2/settings.xml）
<mirrors>
  <mirror>
    <id>alimaven</id>
    <name>aliyun maven</name>
    <url>http://maven.aliyun.com/nexus/content/groups/public/</url>
    <mirrorOf>central</mirrorOf>
  </mirror>
</mirrors>
```

### 8.2 运行时问题

#### 8.2.1 页面无法访问
**问题**: 404错误或页面空白
**解决方案**:
1. 检查URL是否正确
2. 确认项目已正常启动
3. 检查防火墙设置
4. 清除浏览器缓存

#### 8.2.2 图片无法显示
**问题**: 上传的图片无法显示
**解决方案**:
1. 检查upload文件夹权限
2. 确认文件路径配置正确
3. 检查文件大小限制

#### 8.2.3 中文乱码问题
**问题**: 页面显示中文乱码
**解决方案**:
1. 确认数据库字符集为utf8mb4
2. 检查application.yml编码配置
3. 设置IDE文件编码为UTF-8

### 8.3 性能问题

#### 8.3.1 页面加载缓慢
**解决方案**:
1. 优化数据库查询
2. 添加适当的索引
3. 启用数据库连接池
4. 压缩静态资源

#### 8.3.2 内存占用过高
**解决方案**:
```bash
# 调整JVM内存参数
java -Xms512m -Xmx1024m -jar springboot655ms.jar

# 或在IDE中设置VM options
-Xms512m -Xmx1024m
```

## 9. 维护指南

### 9.1 日常维护

#### 9.1.1 日志管理
```bash
# 查看应用日志
tail -f logs/spring.log

# 清理过期日志
find logs/ -name "*.log" -mtime +30 -delete
```

#### 9.1.2 数据库维护
```sql
-- 定期备份数据库
mysqldump -u root -p springboot655ms > backup_$(date +%Y%m%d).sql

-- 优化数据库表
OPTIMIZE TABLE jingdianxinxi, jiudianxinxi, cantingxinxi;

-- 检查数据库状态
SHOW TABLE STATUS;
```

#### 9.1.3 系统监控
- 监控CPU和内存使用率
- 检查磁盘空间
- 监控数据库连接数
- 查看错误日志
- 检查权限控制
- 审查日志文件

### 9.2 安全维护

#### 9.2.1 定期更新
- 更新Java版本
- 更新Spring Boot版本
- 更新数据库版本
- 更新依赖包

### 9.3 备份策略

#### 9.3.1 数据备份
```bash
# 每日自动备份脚本
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
mysqldump -u root -p123456 springboot655ms > /backup/db_backup_$DATE.sql
find /backup -name "db_backup_*.sql" -mtime +7 -delete
```

#### 9.3.2 代码备份
- 使用Git版本控制
- 定期推送到远程仓库
- 创建重要版本的标签

### 9.4 性能优化

#### 9.4.1 数据库优化
```sql
-- 添加索引
CREATE INDEX idx_jingdian_name ON jingdianxinxi(jingdianmingcheng);
CREATE INDEX idx_hotel_name ON jiudianxinxi(jiudianmingcheng);
CREATE INDEX idx_user_account ON yonghu(zhanghao);

-- 分析查询性能
EXPLAIN SELECT * FROM jingdianxinxi WHERE jingdianmingcheng LIKE '%景点%';
```

#### 9.4.2 应用优化
- 启用数据库连接池
- 添加Redis缓存
- 压缩静态资源
- 使用CDN加速

## 10. 部署到生产环境

### 10.1 生产环境配置

#### 10.1.1 配置文件
创建 `application-prod.yml`:
```yaml
server:
  port: 80
  servlet:
    context-path: /

spring:
  datasource:
    url: jdbc:mysql://your-db-host:3306/springboot655ms
    username: your-username
    password: your-password

logging:
  level:
    com.controller: INFO
    com.service: INFO
  file:
    name: logs/application.log
```

#### 10.1.2 启动脚本
创建 `start.sh`:
```bash
#!/bin/bash
nohup java -jar -Dspring.profiles.active=prod springboot655ms.jar > /dev/null 2>&1 &
echo $! > app.pid
echo "Application started with PID: $(cat app.pid)"
```

创建 `stop.sh`:
```bash
#!/bin/bash
if [ -f app.pid ]; then
    PID=$(cat app.pid)
    kill $PID
    rm app.pid
    echo "Application stopped"
else
    echo "PID file not found"
fi
```

### 10.2 Nginx配置（可选）
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static/ {
        alias /path/to/static/files/;
        expires 30d;
    }
}
```

### 10.3 Docker部署（可选）
创建 `Dockerfile`:
```dockerfile
FROM openjdk:8-jre-alpine
VOLUME /tmp
COPY target/springboot655ms-0.0.1-SNAPSHOT.jar app.jar
ENTRYPOINT ["java","-jar","/app.jar"]
EXPOSE 8080
```

创建 `docker-compose.yml`:
```yaml
version: '3'
services:
  app:
    build: .
    ports:
      - "8080:8080"
    depends_on:
      - mysql
    environment:
      - SPRING_DATASOURCE_URL=jdbc:mysql://mysql:3306/springboot655ms

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: 123456
      MYSQL_DATABASE: springboot655ms
    volumes:
      - ./db/springboot655ms.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "3306:3306"
```


