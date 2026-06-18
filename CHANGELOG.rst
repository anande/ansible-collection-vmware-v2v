===================================
anande.vmware_v2v Release Notes
===================================

.. contents:: Topics

v1.0.0
======

Release Summary
---------------

Initial release of the anande.vmware_v2v collection.

Major Changes
-------------

- Add ``virt_v2v`` module to convert powered-off VMware guests to libvirt-managed KVM using ``virt-v2v``.
- Support nested ``vcenter``, ``vddk``, and ``libvirt`` dicts, parameter aliases, and environment variable fallbacks for batch migrations.
- Target RHEL KVM conversion hosts with Red Hat Ceph RBD-backed libvirt storage pools.
