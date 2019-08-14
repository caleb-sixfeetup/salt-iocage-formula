iocage_package:
    pkg.installed:
        - name: py36-iocage

fdescfs_mount:
    mount.mounted:
        - name: /dev/fd
        - fstype: fdescfs
        - device: fdesc
