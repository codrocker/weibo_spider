# -*- encoding: utf-8 -*-

import MySQLdb
from logger import *

class MysqlClient(object):

    def __init__(self, masters, slaves, logger):
        """初始化
        Args:
            masters, slaves: [{"host" : "10.1.169.84",
                               "user" : "ucenter",
                               "passwd" : "ucenter",
                               "db_name" : 'ucenter',
                               "port" : 3307},
                              {"host" : "10.1.169.84",
                               "user" : "ktv",
                               "passwd" : "ktv",
                               "db_name" : 'ktv',
                               "port" : 3308}]
        """
        self.master_config = {}
        self.slave_config = {}
        self.master_conn = {}
        self.slave_conn = {}
        self.log = logger
        for master in masters:
            self.master_config[master["db_name"]] = master
            self.master_conn[master["db_name"]] = None
        for slave in slaves:
            self.slave_config[slave["db_name"]] = slave
            self.slave_conn[slave["db_name"]] = None

    def __del__(self):
        for master in self.master_conn:
            try:
                if self.master_conn[master]:
                    self.master_conn[master].close()
            except Exception, e:
               self.log.error("master del master catch exception:%s" % str(e)) 
        for slave in self.slave_conn:
            try:
                if self.slave_conn[slave]:
                    self.slave_conn[slave].close()
            except Exception, e:
                #print "slave del catch exception:", str(e)
                self.log.error("slave del slave catch exception:%s" % str(e))
    
    def __ping(self, conn):
      try:
        conn.ping()
      except Exception, e:
        return False
      return True
    
    def __get_connection(self, config, db_name):
        conn = None
        try:
            conn = MySQLdb.connect(host=config["host"],
                                   user=config["user"],
                                   passwd=config["passwd"],
                                   port=config["port"],
                                   db=db_name,
                                   charset='utf8')
            #self.log.info("db connect [host:%s user:%s passwd:%s port:%s] ok" % (config["host"], config["user"], config["passwd"], config["port"]))
        except Exception, e:
            self.log.error("db connect [host:%s user:%s passwd:%s port:%s] fail :%s" % (config["host"], config["user"], config["passwd"], config["port"], str(e)))
        return conn

    def __get_master_connection(self, db_name):
        conn = None
        if self.master_conn[db_name]:
            if self.__ping(self.master_conn[db_name]):
              return self.master_conn[db_name]
            else:
              self.__close_connection(None, self.master_conn[db_name])
              self.master_conn[db_name] = None
        if db_name not in self.master_config:
            self.log.error("db_name :%s master invalid" % db_name)
            return conn
        
        conn = self.__get_connection(self.master_config[db_name], db_name)
        if conn:
            self.master_conn[db_name] = conn
        return conn

    def __get_slave_connection(self, db_name):
        conn = None
        if self.slave_conn[db_name]:
          if self.__ping(self.slave_conn[db_name]):
            return self.slave_conn[db_name]
          else:
            self.__close_connection( None, self.slave_conn[db_name])
            self.slave_conn[db_name] = None
        if db_name not in self.slave_config:
            self.log.error("db_name:%s invalid" % db_name)
            return conn
        
        conn = self.__get_connection(self.slave_config[db_name], db_name)
        if conn:
            self.slave_conn[db_name] = conn
        return conn

    def __close_cursor(self, cursor):
        try:
            if cursor: cursor.close()
        except Exception, e:
            self.log.error("db exception :%s" % str(e))

    def __rollback(self, conn):
        try:
            if conn: conn.rollback()
        except Exception, e:
            self.log.error("db exception :%s" % str(e))

    def __close_connection(self, cursor, conn):
        try:
            if cursor: cursor.close()
            if conn:
                conn.close()
        except Exception, e:
            #LOG.Error([('topic','db_except'), ('e',e)])
            self.log.error("db exception :%s" % str(e))
        finally:
            conn = None

    def execute_query(self, db_name, sql, params=None):
        """查询
        Returns:
            失败返回[]，无结果返回[]
        """
        cursor = None
        conn = None
        rows = None
        try:
            conn = self.__get_slave_connection(db_name)
            if conn is None:
                return []
            cursor = conn.cursor()
            if params is None:
                cursor.execute(sql)
            else:
                cursor.execute(sql, params)
            if not cursor.rowcount:
                return []
            rows = cursor.fetchall()
        except Exception, e:
            #LOG.Error([('topic','db_except'), ('e',e)])
            self.log.error("db exception :%s" % str(e))
            self.__close_connection(cursor, conn)
            self.slave_conn[db_name] = None
            rows = None
        finally:
            self.__close_cursor(cursor)
        if None == rows:
            rows = []
        return rows

    def execute_update(self, db_name, sql, params=None):
        """更新,sql中dbname必须手动填写,不可使用params替换
        Returns:
            成功返回更新的条数，失败返回-1
        """
        rowcount = -1
        cursor = None
        conn = None
        try:
            conn = self.__get_master_connection(db_name)
            if conn is None:
                return -1
            cursor = conn.cursor()
            if params is None:
                cursor.execute(sql)
            else:
                cursor.execute(sql, params)
            conn.commit()
            rowcount = cursor.rowcount
        except Exception, e:
            #LOG.Error([('topic','db_except'), ('e',e)])
            self.log.error("db exception :%s" % str(e))
            self.__rollback(conn)
            self.__close_connection(cursor, conn)
            self.master_conn[db_name] = None
            rowcount = -1
        finally:
            self.__close_cursor(cursor)
        return rowcount

    def execute_batch(self, db_name, sql, params_list):
        """批处理
        Returns:
            成功返回更新的条数，失败返回-1
        """
        total_rowcount = 0
        if not params_list: return total_rowcount
        cursor = None
        conn = None
        try:
            conn = self.__get_master_connection(db_name)
            if conn is None: return None
            cursor = conn.cursor()
            counter = 0
            new_params_list = []
            total_counter = len(params_list)
            for item in params_list:
                counter += 1
                new_params_list.append(item)
                if (counter % 200 == 0 or counter == total_counter):
                    rowcount = cursor.executemany(sql, new_params_list)
                    conn.commit()
                    #LOG.Debug([('topic','batch_return'), ('cnt',rowcount)])
                    total_rowcount += rowcount
                    new_params_list = []
            #LOG.Debug([('topic','batch_total'), ('cnt',total_rowcount)])
        except Exception, e:
            #LOG.Error([('topic','db_except'), ('e',e)])
            self.log.error("db exception :%s" % str(e))
            self.__rollback(conn)
            self.__close_connection(cursor, conn)
            self.master_conn[db_name] = None
            total_rowcount = -1
        finally:
            self.__close_cursor(cursor)
        return total_rowcount


    def execute_multi_update(self, db_name, sqls):
        """更新,多个sql事务性提交
        Returns:
            成功返回更新的条数，失败返回-1
        """
        rowcount = -1
        cursor = None
        conn = None
        try:
            conn = self.__get_master_connection(db_name)
            if conn is None:
                return -1
            cursor = conn.cursor()
            for sql in sqls:
                #print sql
            	cursor.execute(sql)
            conn.commit()
            rowcount = cursor.rowcount
        except Exception, e:
            self.log.error("db exception :%s" % str(e))
            self.__rollback(conn)
            self.__close_connection(cursor, conn)
            self.master_conn[db_name] = None
            rowcount = -1
        finally:
            self.__close_cursor(cursor)
        return rowcount

if __name__ == "__main__":
  # 初始化日志
  log = init_logger("./test.log")
  masters = [{"host" : "127.0.0.1",
               "user" : "root",
               "passwd" : "",
               "db_name" : "elaid",
               "port" : 3306}]
  slaves = [{"host" : "127.0.0.1",
              "user" : "root",
              "passwd" : "",
              "db_name" : "elaid",
              "port" : 3306}]
  db_client = MysqlClient(masters, slaves, log)
  
  table_name = "elaid"
  
  print "==>begin test multi update commit func"
  sqls = []
  sql = "insert into user(nick) values('a')"
  sqls.append(sql)
  sql = "insert into user(nn) values('b')"
  print db_client.execute_multi_update(table_name, sqls)
  
  print "==>begin test execute_update func"
  sql = "insert into test(ruleid, ruletype, message) values(%s, %s, %s)"
  param = (1, 2, "msg 1")
  table_name = 'rule'
  res = db_client.execute_update(table_name, sql, param)
  print res
  
  
  print "==>begin test execute_qurey func"
  sql = "select * from test where ruleid = %s"
  param = [1]
  table_name = 'rule'
  res = db_client.execute_query(table_name, sql, param)
  print res
  
  sql = "delete from test "
  param = None
  table_name = 'rule'
  res = db_client.execute_update(table_name, sql, param)
  print res
  

  sql = "insert into test(ruleid, ruletype, message) values(%s, %s, %s)"
  param = []
  for i in xrange(10):
    param.append((i,i,"msg %d" % i))
  table_name = 'rule'
  res = db_client.execute_batch(table_name, sql, param)
  print res
