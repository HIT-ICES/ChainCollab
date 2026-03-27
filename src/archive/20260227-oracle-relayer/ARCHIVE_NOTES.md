# Oracle & Relayer Archive Notes

Archive time: 2026-02-27
Archive root: `/home/logres/system/src/archive/20260227-oracle-relayer`

## Archived directories

- `src/oracle`
- `src/oracle-node`
- `src/oracle-data-compute-lab`
- `src/relayer-node`
- `src/crosschain-relay-lab`

Each original path is replaced by a symlink to this archive root, so existing scripts can continue to resolve historical paths.

## Restore (remove archive symlink layout)

```bash
for d in oracle oracle-node oracle-data-compute-lab relayer-node crosschain-relay-lab; do
  rm -f "/home/logres/system/src/$d"
  mv "/home/logres/system/src/archive/20260227-oracle-relayer/$d" "/home/logres/system/src/$d"
done
```

## Verify symlink targets

```bash
ls -ld /home/logres/system/src/oracle /home/logres/system/src/oracle-node /home/logres/system/src/oracle-data-compute-lab /home/logres/system/src/relayer-node /home/logres/system/src/crosschain-relay-lab
```
