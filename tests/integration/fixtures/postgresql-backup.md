---
title: PostgreSQL Backup and Restore Strategies
tags: postgresql,database,backup
category: database
concepts: postgresql,backup,pg_dump,restore,wal
---

## Logical Backups with pg_dump

The simplest backup method is `pg_dump`, which produces a logical snapshot of a single database. It outputs SQL statements (or a custom binary format) that can recreate the schema and data.

```bash
pg_dump -h localhost -U postgres -Fc -f /backups/mydb_$(date +%Y%m%d).dump mydb
```

The `-Fc` flag produces the custom format, which is compressed and supports parallel restore. For plain SQL output, use `-Fp` instead, but you lose the ability to selectively restore individual tables.

Restore with `pg_restore`:

```bash
pg_restore -h localhost -U postgres -d mydb --clean --if-exists /backups/mydb_20250115.dump
```

The `--clean` flag drops existing objects before recreating them. Add `--if-exists` to suppress errors when objects do not exist yet. For large databases, use `-j 4` to restore in parallel across four connections.

To back up all databases on a server (including roles and tablespaces), use `pg_dumpall`:

```bash
pg_dumpall -h localhost -U postgres > /backups/full_cluster_$(date +%Y%m%d).sql
```

This only outputs plain SQL, so there is no parallel restore option. It is most useful for small clusters or for capturing global objects (roles, permissions) that `pg_dump` does not include.

## Continuous Archiving with WAL

Logical backups have a recovery point objective (RPO) equal to the time between dumps. If the database crashes one hour before the next scheduled backup, that hour of data is gone. Write-Ahead Log (WAL) archiving solves this by continuously copying transaction log segments to a safe location.

Enable archiving in `postgresql.conf`:

```
wal_level = replica
archive_mode = on
archive_command = 'cp %p /wal_archive/%f'
```

Take a base backup as the starting point:

```bash
pg_basebackup -h localhost -U replicator -D /backups/base -Ft -z -P
```

To restore to a specific point in time, place the base backup in the data directory and create a `recovery.signal` file (PostgreSQL 12+) with the target timestamp:

```
restore_command = 'cp /wal_archive/%f %p'
recovery_target_time = '2025-01-15 14:30:00'
```

Start PostgreSQL and it will replay WAL segments up to that moment. This gives you arbitrary point-in-time recovery, which is the only reliable way to recover from accidental `DELETE` or `DROP TABLE` statements.

## Automating Backups

A production backup strategy combines both approaches. Run `pg_dump` nightly for fast, portable snapshots. Run continuous WAL archiving for point-in-time recovery between dumps.

Wrap your backup in a script that handles rotation, compression, and alerting:

```bash
#!/bin/bash
BACKUP_DIR=/backups/postgres
RETAIN_DAYS=14
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

pg_dump -h localhost -U postgres -Fc -f "$BACKUP_DIR/mydb_$TIMESTAMP.dump" mydb

if [ $? -ne 0 ]; then
    echo "Backup failed" | mail -s "PostgreSQL backup failure" admin@example.com
    exit 1
fi

find "$BACKUP_DIR" -name "*.dump" -mtime +$RETAIN_DAYS -delete
```

Schedule this via cron or a [systemd timer](./systemd-service-files.md). Always test restores periodically. A backup you have never restored is a backup that might not work. Spin up a test instance, restore the latest dump, and run a few sanity queries.

For additional monitoring of backup health, integrate with [Prometheus alerting](./prometheus-alerting.md) to detect missed or failed backup jobs. Tools like pgBackRest and Barman provide more sophisticated management, including incremental backups, backup verification, and S3/GCS storage targets. See the [pgBackRest documentation](https://pgbackrest.org/) for details.
