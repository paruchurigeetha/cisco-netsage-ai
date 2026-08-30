# Responsible AI Log: Human Oversight & Verification

This log documents **at least 5 specific cases** from the NetSage AI dataset where the AI's diagnostic response was incorrect, incomplete, or flawed, and was subsequently corrected by a human reviewer. 

Implementing a human-in-the-loop validation process ensures that automated network diagnoses do not lead to destructive configuration changes in production environments, highlighting the importance of the **Human Review** safety rule.

---

## Summary of Corrected Cases

| Case ID | Concept | OSI Layer | AI Initial Diagnosis (The Error) | Human Correction (The Reality) | Impact of Error if Applied |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **16** | ACL Wildcard | L3 | Misidentified `255.255.255.0` in the ACL as a standard subnet mask and suggested it was correct, missing that Cisco standard ACLs require inverted wildcard masks. | Pointed out that Cisco IOS parses standard subnet masks in ACLs as wildcard masks, leading to security bypasses. Wildcard should be `0.0.0.255` (or host specific). | Security policy bypass, allowing incorrect subnets to access SSH. |
| **19** | NAT ACL | L3 | Diagnosed the issue as a routing table failure on the router, completely missing that the NAT ACL (ACL 1) did not permit the VLAN 20 subnet IP range. | Noted that while routing was fine, NAT translation failed because the NAT pool access list only permitted VLAN 10 (`192.168.10.0/24`) and lacked a permit for VLAN 20. | Extended, unnecessary routing table troubleshooting. |
| **22** | Duplicate IP | L3 | Classified the problem as a Spanning Tree switching loop due to the MAC address flapping messages, recommending disabling trunk ports. | Corrected the root cause to an IP address conflict (Duplicate IP `192.168.1.10` assigned to two hosts) based on the `%IP-4-DUPADDR` warning. | Network outage by shutting down valid links under the assumption of an STP loop. |
| **27** | Inter-VLAN | L3 | Stated that subinterface `G0/0.20` was invalid because the interface sub-number must match the dot1Q tag, recommending recreating the interface. | Clarified that subinterface numbers are logical and arbitrary; the issue was simply the wrong tag in `encapsulation dot1Q 30`. The fix is just changing the tag, not recreating the subinterface. | Configuration clutter and potential disruption of other subinterfaces on the same port. |
| **28** | HSRP | L3 | Diagnosed the active/active state as a physical cabling failure between the routers, recommending replacing the link. | Corrected the diagnosis to a software configuration mismatch where RouterA was in HSRP Group 10 and RouterB was in Group 20, preventing negotiation. | Unnecessary hardware replacement and downtime; the physical links were fully operational. |

---

## Detailed Case Breakdowns

### Case 16: ACL Wildcard Mask Misinterpretation
* **Symptom**: Standard Access List configured on VTY lines to restrict SSH access is permitting unauthorized clients.
* **AI Output**:
  * *Root Cause*: "The SSH access configuration is correct as access-list 101 permits the subnet 192.168.1.0 with subnet mask 255.255.255.0."
  * *Fix Steps*: "No changes needed for SSH access list. Verify SSH configuration on line vty."
* **Human Review Correction**:
  * *Correction*: The AI failed to realize Cisco IOS access lists use **inverted wildcard masks**, not standard subnet masks. In Cisco IOS, writing `access-list 101 permit ip 192.168.1.0 255.255.255.0 any` parses `255.255.255.0` as the wildcard mask. This actually permits any host where the last octet is `0` (or matches wildcards), which is a serious security risk. The correct command is `access-list 101 permit ip 192.168.1.0 0.0.0.255 any`.
  * *Review Status*: **Edited**

---

### Case 19: NAT Translation Access List Omission
* **Symptom**: VLAN 20 clients cannot connect to the internet, while VLAN 10 clients connect fine.
* **AI Output**:
  * *Root Cause*: "Router is missing static or dynamic routes to forward traffic from VLAN 20 to the internet interface GigabitEthernet0/1."
  * *Fix Steps*: "Add a static route: `ip route 192.168.20.0 255.255.255.0 GigabitEthernet0/1`."
* **Human Review Correction**:
  * *Correction*: The routing table already had directly connected routes for VLAN 20 and a default route to the WAN. The issue was that the NAT source list rule (`ip nat inside source list 1 interface G0/1 overload`) referenced Access List 1, which only permitted VLAN 10's subnet (`192.168.10.0/24`). VLAN 20's subnet (`192.168.20.0/24`) was blocked from translation. The fix is to add `access-list 1 permit 192.168.20.0 0.0.0.255`.
  * *Review Status*: **Edited**

---

### Case 22: Duplicate IP Conflict Interpreted as STP Loop
* **Symptom**: Flapping connections on the LAN and packet drop. Console logs show MAC address flapping.
* **AI Output**:
  * *Root Cause*: "A switching loop has occurred on the LAN due to Spanning Tree Protocol (STP) misconfiguration, causing MAC addresses to flap between ports."
  * *Fix Steps*: "Identify the redundant switch loop and shut down the port on the access switch."
* **Human Review Correction**:
  * *Correction*: While MAC address flapping can occur during switching loops, the router console log explicitly output `%IP-4-DUPADDR: Duplicate address 192.168.1.10`. The ARP table also showed two different hardware addresses for `192.168.1.10`. This indicates a duplicate static IP address conflict between two end-user devices, not a network loop. Shutting down switchports would cause an unnecessary outage for legitimate users.
  * *Review Status*: **Rejected**

---

### Case 27: Inter-VLAN Subinterface Logical Numbering
* **Symptom**: Clients in VLAN 20 cannot reach their gateway.
* **AI Output**:
  * *Root Cause*: "The router subinterface GigabitEthernet0/0.20 is misconfigured because the subinterface number (20) must match the encapsulation VLAN tag (30). The subinterface is invalid."
  * *Fix Steps*: "Delete subinterface G0/0.20: `no interface GigabitEthernet0/0.20`. Recreate it: `interface GigabitEthernet0/0.30`, `encapsulation dot1Q 30`, `ip address 192.168.20.1 255.255.255.0`."
* **Human Review Correction**:
  * *Correction*: Cisco IOS does *not* require the logical subinterface number to match the VLAN tag (e.g. G0/0.20 can encapsulate VLAN 30, though it is bad practice). Recreating the subinterface as `.30` with IP `192.168.20.1` is confusing and incorrect because VLAN 20 traffic is tagged as 20. The actual issue is that the subinterface meant for VLAN 20 is tagging packets as VLAN 30. The correct fix is to keep the subinterface and simply modify the encapsulation command to `encapsulation dot1Q 20`.
  * *Review Status*: **Edited**

---

### Case 28: HSRP Active/Active Split-Brain
* **Symptom**: Duplicate IP warnings on the virtual gateway and client traffic drops. Both HSRP routers show state "Active".
* **AI Output**:
  * *Root Cause*: "Physical connection link failure between RouterA and RouterB, preventing them from exchanging HSRP heartbeats."
  * *Fix Steps*: "Inspect the physical cable connecting RouterA and RouterB, and replace it if necessary."
  * *OSI Layer*: L1 (Physical)
* **Human Review Correction**:
  * *Correction*: The physical link is up and routing normally. The issue is that RouterA is configured for standby group 10 (`standby 10 ip 192.168.1.254`) and RouterB is configured for standby group 20 (`standby 20 ip 192.168.1.254`). Because they are in different groups, they do not listen to each other's standby messages. Both assume they are the sole router for their group and transition to the "Active" state for the same IP. The fix is to align the standby group numbers on both routers.
  * *Review Status*: **Edited**
