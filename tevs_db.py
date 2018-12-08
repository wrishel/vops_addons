try:
    import psycopg2 as DB
    DatabaseError = DB.DatabaseError
except ImportError:
    DatabaseError = Exception
    pass
import psycopg2.extras
import re
import string


class PostgresDB(object):
    def __init__(self, database, user, password):
        """Will not create tables if they already exist."""
        try:
            self.conn = DB.connect(database=database, user=user, port=5432, password=password)
        except Exception, e:
            # try to connect to user's default database
            try:
                self.conn = DB.connect(database=user, user=user)
            except Exception, e:
                    print "Could not connect to database %s specified in tevs.cfg,\nor connect to default database %s for user %s \nin order to create and initialize new database %s" % (
                    database, user, user, database)

    def close(self):
        try:
            self.conn.close()
        except DatabaseError:
            pass

    def query_no_returned_values(self, q, *a):
        "returns a list of all results of q parameterized with a"
        cur = self.conn.cursor()
        try:
            cur.execute(q, *a)
            self.conn.commit()
        except DatabaseError, e:

            self.conn.rollback()
        return

    def query(self, q, *a):
        "returns a list of all results of q parameterized with a"
        cur = self.conn.cursor(cursor_factory=DB.extras.NamedTupleCursor)
        cur.execute(q, *a)
        r = list(cur)
        cur.close()
        return r

    def query1(self, q, *a):
        "return one result from q parameterized with a"
        cur = self.conn.cursor()
        cur.execute(q, *a)
        r = cur.fetchone()
        cur.close()
        return r




    def allfromdb(self):
        sql = """SELECT choice, contest, was_voted, file1
                 FROM tempbrc
                 ORDER BY file1, choice, contest;"""

        return self.query(sql, ())


if __name__ == '__main__':
    db = PostgresDB('tevs', 'tevs', 'tevs')
    list = db.qfcontch(('001152.jpg', 'GOVERNOR', 'JOHN H. COX'))
    print list



