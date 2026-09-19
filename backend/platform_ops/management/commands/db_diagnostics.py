import json
from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = "Muestra diagnóstico básico de PostgreSQL para capacidad y performance."

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            self.stdout.write(json.dumps({"vendor": connection.vendor}))
            return
        result = {}
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), version()")
            db, version = cursor.fetchone()
            result["database"] = db
            result["version"] = version

            cursor.execute("""
                SELECT state, count(*)
                FROM pg_stat_activity
                WHERE datname = current_database()
                GROUP BY state
            """)
            result["connections_by_state"] = {
                str(state): count for state, count in cursor.fetchall()
            }

            cursor.execute("""
                SELECT relname, seq_scan, idx_scan,
                       pg_total_relation_size(relid) AS bytes
                FROM pg_stat_user_tables
                ORDER BY pg_total_relation_size(relid) DESC
                LIMIT 20
            """)
            result["largest_tables"] = [
                {
                    "table": row[0],
                    "seq_scan": row[1],
                    "idx_scan": row[2],
                    "bytes": row[3],
                }
                for row in cursor.fetchall()
            ]

            cursor.execute("""
                SELECT indexrelname, idx_scan
                FROM pg_stat_user_indexes
                ORDER BY idx_scan ASC
                LIMIT 20
            """)
            result["least_used_indexes"] = [
                {"index": row[0], "idx_scan": row[1]}
                for row in cursor.fetchall()
            ]

        self.stdout.write(json.dumps(result, indent=2, ensure_ascii=False))
