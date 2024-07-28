|Stable| |Tag| |License| |Build| |Coverage|

.. raw:: html

  <div align="center">
    <h1><code>hackinsdn/mirror</code></h1>

    <strong>Kytos-ng Napp that implements traffic mirroring</strong>
  </div>


Overview
========

This Napp implements traffic mirroring capabilities on Kytos-ng SDN Orchestrator, 
enabling the network operator to mirror packets being sent through an EVC or 
through an Interface into a target port. Mirroring capability can be used for 
troubleshooting, monitoring, cybersecurity, etc. On the context of the HackInSDN 
project, we are leveraging the Mirror Napp to integrate Security Monitoring tools 
like Suricata and Zeek IDS into Kytos-ng Mef E-line EVCs, adding the capability 
of identifying cyberthreats on the network.

Getting started
===============

To install this NApp, first, make sure to have the same venv activated as you have ``kytos`` installed on:

.. code:: shell

   $ git clone https://github.com/hackinsdn/mirror.git
   $ cd mirror
   $ python3 setup.py develop

The easiest way of using this Napp is through the Docker container:

.. code:: shell

   $ docker pull hackinsdn/kytos:latest
   $ docker run -d --name mongo mongo:7.0
   $ docker exec -it mongo mongo --eval 'db.getSiblingDB("kytos").createUser({user: "kytos", pwd: "kytos", roles: [ { role: "dbAdmin", db: "kytos" } ]})'
   $ docker run -d --name kytos --link mongo -v /lib/modules:/lib/modules --privileged -e MONGO_DBNAME=kytos -e MONGO_USERNAME=kytos -e MONGO_PASSWORD=kytos -e MONGO_HOST_SEEDS=mongo:27017 -p 8181:8181  hackinsdn/kytos:latest

Requirements
============

- `kytos/flow_manager <https://github.com/kytos-ng/flow_manager>`_
- `kytos/mef_eline <https://github.com/kytos-ng/mef_eline>`_


General Information
===================

The Mirror Napp supports creating mirror per EVC and per Interface. When creating the mirror you have to choose the source switch, from which the traffic will be mirrored from, and the target port, where the traffic will be mirrored to. Target port can be local (same switch where the mirror was created) or remote (aka remote span -- a port in a remote switch).

To create a mirror for an existing EVC (XXXXXX) on switch 2 (00:00:00:00:00:00:00:02) and target port switch 2 port 1 (00:00:00:00:00:00:00:02:1), one would have to run the following command:

.. code-block:: shell

  curl -s -X POST -H 'Content-type: application/json' http://127.0.0.1:8181/api/hackinsdn/mirror/v1/ -d '{"circuit_id": "XXXXXX", "switch": "00:00:00:00:00:00:00:02", "target_port": "00:00:00:00:00:00:00:02:1", "name": "my first mirror"}'



.. TAGs

.. |Stable| image:: https://img.shields.io/badge/stability-stable-green.svg
   :target: https://github.com/hackinsdn/mirror
.. |Build| image:: https://github.com/hackinsdn/mirror/actions/workflows/test.yml/badge.svg
  :alt: Build status
.. |Coverage| image:: https://coveralls.io/repos/github/hackinsdn/mirror/badge.svg
  :alt: Code coverage
.. |Tag| image:: https://img.shields.io/github/tag/hackinsdn/mirror.svg
   :target: https://github.com/hackinsdn/mirror/tags
.. |License| image:: https://img.shields.io/github/license/hackinsdn/mirror.svg
   :target: https://github.com/hackinsdn/mirror/blob/master/LICENSE
