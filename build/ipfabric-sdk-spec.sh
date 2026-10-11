#!/bin/sh
# Vypise pozadavky pro pip/uv: SDK ipfabric k verzi IP Fabricu (major.minor), napr. "7.5".
# Pouziva Containerfile pri stavbe i configure-ipfabric.py pri prepnuti verze bez internetu
# (v obrazu jako /opt/ipfabric-wheels/sdk-spec.sh).
v=${1:?verze IP Fabricu, napr. 7.5}
m=${v#7.}
echo "ipfabric>=${v}.0,<7.$((m + 1)).0"
case "$v" in
  # SDK 7.5.x s niquests 3.16+ pada na "IPFClient is not fully defined ... LifeCycleHook" (CHANGES c. 91)
  7.5) echo "niquests<3.16" ;;
esac
