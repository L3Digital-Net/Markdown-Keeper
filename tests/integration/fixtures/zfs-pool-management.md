---
title: Managing ZFS Storage Pools
tags: zfs,storage,filesystem
category: storage
concepts: zfs,pool,snapshot,raidz,scrub
---

## Creating Pools and Understanding vdevs

ZFS pools are built from virtual devices (vdevs), each of which can be a single disk, a mirror, or a RAID-Z group. The choice of vdev type determines your redundancy level and available capacity.

Create a mirrored pool from two disks:

```bash
zpool create tank mirror /dev/sda /dev/sdb
```

For larger deployments, RAID-Z provides parity-based redundancy. RAID-Z1 tolerates one disk failure, RAID-Z2 tolerates two, and RAID-Z3 tolerates three:

```bash
zpool create datastore raidz2 /dev/sda /dev/sdb /dev/sdc /dev/sdd /dev/sde /dev/sdf
```

A pool can contain multiple vdevs. ZFS stripes data across vdevs, so adding a second RAID-Z2 vdev doubles both throughput and capacity. However, you cannot add individual disks to an existing RAID-Z vdev (expansion was added in OpenZFS 2.3 but is still considered experimental). Plan your vdev layout carefully upfront.

Set basic properties at creation time:

```bash
zfs set compression=lz4 tank
zfs set atime=off tank
zfs set recordsize=128K tank
```

LZ4 compression is nearly free in terms of CPU and often improves performance because less data hits the disks. Disabling atime eliminates a write operation on every file read.

## Snapshots and Send/Receive

Snapshots are one of ZFS's most useful features. They are instantaneous, copy-on-write captures of a dataset at a point in time. They cost nothing until data diverges from the snapshot.

```bash
zfs snapshot tank/documents@2025-01-15
zfs list -t snapshot
```

Roll back to a snapshot if something goes wrong:

```bash
zfs rollback tank/documents@2025-01-15
```

For offsite replication, `zfs send` serializes a snapshot (or the incremental difference between two snapshots) into a stream that `zfs receive` applies to another pool:

```bash
zfs send tank/documents@2025-01-15 | ssh backup-server zfs receive backup/documents
```

Incremental sends transfer only changed blocks, making them efficient for daily replication:

```bash
zfs send -i tank/documents@2025-01-14 tank/documents@2025-01-15 | ssh backup-server zfs receive backup/documents
```

Automate snapshot creation and pruning with tools like sanoid/syncoid or zfs-auto-snapshot. A reasonable retention policy keeps hourly snapshots for 24 hours, daily for 30 days, and monthly for a year.

## Scrubbing and Health Monitoring

ZFS scrubs read every block in the pool and verify checksums against the metadata tree. This detects silent data corruption (bit rot) that would go unnoticed on conventional filesystems.

```bash
zpool scrub tank
zpool status tank
```

Run scrubs monthly at minimum. On pools with consumer-grade drives, biweekly is better. Schedule them via cron or a [systemd timer](./systemd-service-files.md) during off-peak hours since scrubs generate significant I/O.

Monitor pool health with `zpool status`. Look for `DEGRADED` or `FAULTED` states. A degraded pool is still functional but has lost redundancy; replace the failed disk immediately:

```bash
zpool replace tank /dev/sdc /dev/sdg
```

The resilver process (rebuilding data onto the replacement disk) can take hours for large pools. During resilvering, the pool is vulnerable to a second disk failure, which is why RAID-Z2 is strongly preferred over RAID-Z1 for pools larger than a few terabytes.

For comprehensive ZFS administration, the [OpenZFS documentation](https://openzfs.github.io/openzfs-docs/) covers advanced topics including special vdevs, L2ARC, and SLOG devices.
