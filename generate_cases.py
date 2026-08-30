import csv
import json
import os

# Define the 30 cases with symptoms, topology, show outputs, expected fault, OSI layer, concept, severity, next command, and fix steps.
# Also include expected_ai_output for seamless offline mode.

cases = [
    {
        "id": 1,
        "symptom": "PC1 in VLAN 10 cannot ping PC2 in VLAN 10 connected to another switch. Pings time out.",
        "topology": "PC1 (192.168.10.10/24) -> SwitchA (Fa0/1 in VLAN 10), SwitchA (Fa0/24) -> SwitchB (Fa0/24), SwitchB (Fa0/1 in VLAN 10) -> PC2 (192.168.10.20/24).",
        "show_outputs": (
            "SwitchA# show interfaces trunk\n"
            "Port        Mode         Encapsulation  Status        Native vlan\n"
            "Fa0/24      on           802.1q         trunking      10\n\n"
            "SwitchB# show interfaces trunk\n"
            "Port        Mode         Encapsulation  Status        Native vlan\n"
            "Fa0/24      on           802.1q         trunking      20\n"
        ),
        "expected_fault": "Mismatched Native VLAN on trunk link between SwitchA and SwitchB (Native VLAN 10 vs Native VLAN 20). This causes VLAN leaking and drop of tagged/untagged traffic.",
        "osi_layer": "L2",
        "concept": "VLAN",
        "severity": "High",
        "next_command": "show interfaces trunk",
        "fix_steps": "Configure Native VLAN 10 on SwitchB's Fa0/24: enter interface configuration mode, type 'switchport trunk native vlan 10'.",
        "expected_ai_output": {
            "root_cause": "Native VLAN mismatch on the trunk port Fa0/24 between SwitchA (Native VLAN 10) and SwitchB (Native VLAN 20).",
            "confidence": "High",
            "evidence": "SwitchA 'Native vlan' is 10, while SwitchB 'Native vlan' is 20 for trunk interface Fa0/24.",
            "next_command": "show interfaces trunk",
            "fix_steps": "On SwitchB:\n1. configure terminal\n2. interface Fa0/24\n3. switchport trunk native vlan 10\n4. end\n5. write memory",
            "osi_layer": "L2"
        }
    },
    {
        "id": 2,
        "symptom": "PC1 connected to SwitchA Fa0/1 cannot reach any device on VLAN 10. Port light is green but IP configuration fails.",
        "topology": "PC1 (192.168.10.15/24) -> SwitchA (Fa0/1 in VLAN 10). Default Gateway is Router (192.168.10.1).",
        "show_outputs": (
            "SwitchA# show vlan brief\n"
            "VLAN Name                             Status    Ports\n"
            "---- -------------------------------- --------- -------------------------------\n"
            "1    default                          active    Fa0/2, Fa0/3, Fa0/4, Fa0/24\n"
            "100  VLAN0100                         active\n"
            "\n"
            "SwitchA# show interfaces Fa0/1 switchport\n"
            "Name: Fa0/1\n"
            "Switchport: Enabled\n"
            "Administrative Mode: static access\n"
            "Operational Mode: static access\n"
            "Administrative Access VLAN: 10 (Inactive)\n"
            "Operational Access VLAN: 10 (Inactive)\n"
        ),
        "expected_fault": "VLAN 10 is configured on the access interface Fa0/1, but VLAN 10 does not exist in the switch's VLAN database (VLAN is inactive).",
        "osi_layer": "L2",
        "concept": "VLAN",
        "severity": "High",
        "next_command": "show vlan brief",
        "fix_steps": "Create and activate VLAN 10 on SwitchA: 'vlan 10' then 'name VLAN10' in global configuration mode.",
        "expected_ai_output": {
            "root_cause": "VLAN 10 is inactive because it does not exist in the switch's VLAN database.",
            "confidence": "High",
            "evidence": "show interfaces Fa0/1 switchport shows 'Administrative Access VLAN: 10 (Inactive)', and show vlan brief does not list VLAN 10.",
            "next_command": "vlan 10 (in config mode)",
            "fix_steps": "On SwitchA:\n1. configure terminal\n2. vlan 10\n3. name VLAN10\n4. exit",
            "osi_layer": "L2"
        }
    },
    {
        "id": 3,
        "symptom": "The trunk link between SwitchA and SwitchB is down, and VLANs are not communicating between them.",
        "topology": "SwitchA (Fa0/24) connected to SwitchB (Fa0/24). Both should be trunking.",
        "show_outputs": (
            "SwitchA# show interfaces Fa0/24 switchport\n"
            "Name: Fa0/24\n"
            "Administrative Mode: trunk\n"
            "Operational Mode: trunk\n\n"
            "SwitchB# show interfaces Fa0/24 switchport\n"
            "Name: Fa0/24\n"
            "Administrative Mode: static access\n"
            "Operational Mode: static access\n"
            "Administrative Access VLAN: 1 (default)\n"
        ),
        "expected_fault": "Switchport mode mismatch on the link connecting SwitchA and SwitchB. SwitchA is set to 'trunk' while SwitchB is configured as 'static access'.",
        "osi_layer": "L2",
        "concept": "VLAN",
        "severity": "Medium",
        "next_command": "show interfaces switchport",
        "fix_steps": "Change SwitchB's Fa0/24 mode to trunk: enter 'interface Fa0/24' and type 'switchport mode trunk'.",
        "expected_ai_output": {
            "root_cause": "Trunk negotiation failure due to switchport mode mismatch (SwitchA is 'trunk', SwitchB is 'static access').",
            "confidence": "High",
            "evidence": "SwitchA Administrative Mode: trunk, SwitchB Administrative Mode: static access on interfaces Fa0/24.",
            "next_command": "show interfaces Fa0/24 switchport",
            "fix_steps": "On SwitchB:\n1. configure terminal\n2. interface Fa0/24\n3. switchport mode trunk\n4. end",
            "osi_layer": "L2"
        }
    },
    {
        "id": 4,
        "symptom": "PC1 has static IP but cannot ping default gateway or access any resource outside its local subnet.",
        "topology": "PC1 (192.168.1.50/24) -> Switch -> Router G0/0 (192.168.1.1/24).",
        "show_outputs": (
            "PC1> ipconfig\n"
            "FastEthernet0 Connection:\n"
            "   IP Address. . . . . . . . . . . : 192.168.1.50\n"
            "   Subnet Mask . . . . . . . . . . : 255.255.255.0\n"
            "   Default Gateway . . . . . . . . : 192.168.2.1\n\n"
            "Router# show ip interface brief\n"
            "Interface              IP-Address      OK? Method Status                Protocol\n"
            "GigabitEthernet0/0     192.168.1.1     YES manual up                    up\n"
        ),
        "expected_fault": "Default gateway IP mismatch. The default gateway on PC1 is set to 192.168.2.1, but the Router interface's actual IP is 192.168.1.1.",
        "osi_layer": "L3",
        "concept": "Gateway",
        "severity": "High",
        "next_command": "ipconfig on PC1 and show ip interface brief on Router",
        "fix_steps": "Change the default gateway configuration on PC1 to 192.168.1.1.",
        "expected_ai_output": {
            "root_cause": "Incorrect Default Gateway IP configured on PC1 (192.168.2.1 instead of 192.168.1.1).",
            "confidence": "High",
            "evidence": "PC1 default gateway is 192.168.2.1, but Router GigabitEthernet0/0 is configured with 192.168.1.1.",
            "next_command": "ipconfig /all",
            "fix_steps": "On PC1:\n1. Open network configuration.\n2. Modify default gateway address to 192.168.1.1.",
            "osi_layer": "L3"
        }
    },
    {
        "id": 5,
        "symptom": "All hosts in VLAN 10 fail to ping their default gateway and cannot access the Internet.",
        "topology": "VLAN 10 hosts (192.168.10.0/24) -> SwitchA -> Router G0/0.10 (192.168.10.1) router-on-a-stick.",
        "show_outputs": (
            "Router# show ip interface brief\n"
            "Interface              IP-Address      OK? Method Status                Protocol\n"
            "GigabitEthernet0/0     unassigned      YES unset  up                    up\n"
            "GigabitEthernet0/0.10  192.168.10.1    YES manual administratively down down\n"
            "GigabitEthernet0/0.20  192.168.20.1    YES manual up                    up\n"
        ),
        "expected_fault": "Router subinterface GigabitEthernet0/0.10 is administratively down (not enabled with 'no shutdown').",
        "osi_layer": "L1",
        "concept": "Gateway",
        "severity": "High",
        "next_command": "show ip interface brief",
        "fix_steps": "Enable subinterface G0/0.10 on Router: interface GigabitEthernet0/0.10, no shutdown.",
        "expected_ai_output": {
            "root_cause": "Subinterface GigabitEthernet0/0.10 is administratively shut down.",
            "confidence": "High",
            "evidence": "GigabitEthernet0/0.10 status is 'administratively down' and protocol is 'down'.",
            "next_command": "show run interface GigabitEthernet0/0.10",
            "fix_steps": "On Router:\n1. configure terminal\n2. interface GigabitEthernet0/0.10\n3. no shutdown\n4. end",
            "osi_layer": "L1"
        }
    },
    {
        "id": 6,
        "symptom": "PC1 on VLAN 10 is configured to receive IP via DHCP but gets a 169.254.x.x autoconfiguration IP.",
        "topology": "PC1 (VLAN 10) -> Switch -> Router (G0/0.10 is 192.168.10.1) -> DHCP Server (10.0.0.5) in Management subnet.",
        "show_outputs": (
            "PC1> ipconfig\n"
            "FastEthernet0 Connection:\n"
            "   IP Address. . . . . . . . . . . : 169.254.22.45\n"
            "   Subnet Mask . . . . . . . . . . : 255.255.0.0\n"
            "   Default Gateway . . . . . . . . : 0.0.0.0\n\n"
            "Router# show running-config interface gigabitethernet 0/0.10\n"
            "Building configuration...\n\n"
            "Current configuration : 110 bytes\n"
            "!\n"
            "interface GigabitEthernet0/0.10\n"
            " encapsulation dot1Q 10\n"
            " ip address 192.168.10.1 255.255.255.0\n"
            "end\n"
        ),
        "expected_fault": "Missing DHCP helper address on the Router's VLAN 10 gateway interface. DHCP broadcast packets cannot traverse subnets without 'ip helper-address'.",
        "osi_layer": "L3",
        "concept": "DHCP",
        "severity": "High",
        "next_command": "show running-config interface gigabitethernet 0/0.10",
        "fix_steps": "Add DHCP helper address: 'ip helper-address 10.0.0.5' under Router interface GigabitEthernet0/0.10.",
        "expected_ai_output": {
            "root_cause": "Missing 'ip helper-address' configuration on Router's G0/0.10 interface, preventing DHCP broadcast requests from reaching the DHCP server (10.0.0.5) in another subnet.",
            "confidence": "High",
            "evidence": "Router interface G0/0.10 configuration lacks the 'ip helper-address' command. PC1 has an APIPA address (169.254.22.45).",
            "next_command": "show running-config interface GigabitEthernet0/0.10",
            "fix_steps": "On Router:\n1. configure terminal\n2. interface GigabitEthernet0/0.10\n3. ip helper-address 10.0.0.5\n4. end",
            "osi_layer": "L3"
        }
    },
    {
        "id": 7,
        "symptom": "DHCP clients on VLAN 10 receive IP addresses but cannot communicate with their gateway or external networks.",
        "topology": "Clients (VLAN 10) -> Router subinterface G0/0.10 (192.168.10.1/24) running DHCP server.",
        "show_outputs": (
            "PC1> ipconfig\n"
            "   IP Address. . . . . . . . . . . : 192.168.100.5\n"
            "   Subnet Mask . . . . . . . . . . : 255.255.255.0\n"
            "   Default Gateway . . . . . . . . : 192.168.10.1\n\n"
            "Router# show running-config\n"
            "ip dhcp pool VLAN10_POOL\n"
            " network 192.168.100.0 255.255.255.0\n"
            " default-router 192.168.10.1\n"
            "!\n"
            "interface GigabitEthernet0/0.10\n"
            " encapsulation dot1Q 10\n"
            " ip address 192.168.10.1 255.255.255.0\n"
        ),
        "expected_fault": "DHCP pool network subnet conflict. The DHCP pool is configured for network 192.168.100.0/24, but the gateway router IP is 192.168.10.1 (not in the pool's network subnet).",
        "osi_layer": "L3",
        "concept": "DHCP",
        "severity": "High",
        "next_command": "show running-config | section ip dhcp",
        "fix_steps": "Correct the DHCP pool network to '192.168.10.0 255.255.255.0' or update the router interface to match the subnet.",
        "expected_ai_output": {
            "root_cause": "Subnet mismatch between DHCP pool network (192.168.100.0/24) and router interface G0/0.10 IP (192.168.10.1/24). The gateway IP is not in the client subnet.",
            "confidence": "High",
            "evidence": "DHCP pool network: 192.168.100.0/24, router interface IP: 192.168.10.1/24, default-router: 192.168.10.1.",
            "next_command": "show run | section ip dhcp",
            "fix_steps": "On Router:\n1. configure terminal\n2. ip dhcp pool VLAN10_POOL\n3. no network 192.168.100.0 255.255.255.0\n4. network 192.168.10.0 255.255.255.0\n5. end",
            "osi_layer": "L3"
        }
    },
    {
        "id": 8,
        "symptom": "PC1 can ping external IP address 8.8.8.8 but fails to resolve domain names like www.google.com.",
        "topology": "PC1 (192.168.1.15) -> Switch -> Router -> Internet. DNS Server is at 192.168.1.200.",
        "show_outputs": (
            "PC1> ipconfig /all\n"
            "   IP Address. . . . . . . . . . . : 192.168.1.15\n"
            "   Subnet Mask . . . . . . . . . . : 255.255.255.0\n"
            "   Default Gateway . . . . . . . . : 192.168.1.1\n"
            "   DNS Server. . . . . . . . . . . : 192.168.1.250\n\n"
            "Router# show ip interface brief\n"
            "Interface              IP-Address      OK? Method Status                Protocol\n"
            "GigabitEthernet0/0     192.168.1.1     YES manual up                    up\n"
            "GigabitEthernet0/1     192.168.1.200   YES manual up                    up\n"
        ),
        "expected_fault": "DNS Server IP address misconfigured on client. PC1 uses 192.168.1.250, but the active DNS server interface is 192.168.1.200.",
        "osi_layer": "L7",
        "concept": "DNS",
        "severity": "Medium",
        "next_command": "ipconfig /all",
        "fix_steps": "Reconfigure PC1 DNS server setting to 192.168.1.200 (or correct DNS distribution on DHCP pool).",
        "expected_ai_output": {
            "root_cause": "Misconfigured DNS server IP on PC1 (192.168.1.250 instead of 192.168.1.200).",
            "confidence": "High",
            "evidence": "PC1 DNS Server is 192.168.1.250. Router interface GigabitEthernet0/1 is 192.168.1.200 (which hosts the DNS server).",
            "next_command": "nslookup www.google.com",
            "fix_steps": "On PC1:\n1. Change static DNS configuration to 192.168.1.200.\n2. Or update the DHCP pool dns-server configuration on the router.",
            "osi_layer": "L7"
        }
    },
    {
        "id": 9,
        "symptom": "Clients receive host-name resolution failures when trying to reach 'intranet.local'.",
        "topology": "Clients -> Switch -> Router -> DNS Server (10.1.1.100).",
        "show_outputs": (
            "DNS_Server# show running-config\n"
            "ip dns server\n"
            "ip host routerA.cisco.com 10.1.1.1\n"
            "ip host routerB.cisco.com 10.1.1.2\n"
            "ip host fileserver.local 10.1.1.50\n"
            "\n"
            "Client1> nslookup intranet.local\n"
            "*** [10.1.1.100] can't find intranet.local: Non-existent domain\n"
        ),
        "expected_fault": "Missing DNS Host A-record on the DNS Server for 'intranet.local'.",
        "osi_layer": "L7",
        "concept": "DNS",
        "severity": "Low",
        "next_command": "nslookup domain_name",
        "fix_steps": "Add DNS host record on DNS server: 'ip host intranet.local 10.1.1.60'.",
        "expected_ai_output": {
            "root_cause": "DNS database lacks a host A-record mapping 'intranet.local' to an IP address.",
            "confidence": "High",
            "evidence": "nslookup returns 'Non-existent domain' and show running-config lists other hosts but not intranet.local.",
            "next_command": "show running-config | include ip host",
            "fix_steps": "On DNS Server:\n1. configure terminal\n2. ip host intranet.local 10.1.1.60\n3. end",
            "osi_layer": "L7"
        }
    },
    {
        "id": 10,
        "symptom": "OSPF neighbor relationships fail to establish and console logs show neighbor flapping.",
        "topology": "RouterA (Gi0/0: 10.1.1.1/30) connected directly to RouterB (Gi0/0: 10.1.1.2/30).",
        "show_outputs": (
            "RouterA# show ip ospf\n"
            " Routing Process \"ospf 1\" with ID 1.1.1.1\n"
            "RouterB# show ip ospf\n"
            " Routing Process \"ospf 1\" with ID 1.1.1.1\n\n"
            "RouterA# show log\n"
            "%OSPF-4-DUP_RTRID: Duplicate router ID 1.1.1.1 detected on interface GigabitEthernet0/0\n"
        ),
        "expected_fault": "OSPF duplicate router ID. Both RouterA and RouterB have their OSPF router ID configured as 1.1.1.1, preventing neighbor establishment.",
        "osi_layer": "L3",
        "concept": "Routing",
        "severity": "High",
        "next_command": "show ip ospf",
        "fix_steps": "Change the OSPF router ID on RouterB: 'router ospf 1', 'router-id 2.2.2.2', then 'clear ip ospf process'.",
        "expected_ai_output": {
            "root_cause": "OSPF neighbor state cannot form because both RouterA and RouterB are configured with the identical Router ID (1.1.1.1).",
            "confidence": "High",
            "evidence": "RouterA OSPF ID: 1.1.1.1, RouterB OSPF ID: 1.1.1.1, and log entry: %OSPF-4-DUP_RTRID.",
            "next_command": "show ip ospf",
            "fix_steps": "On RouterB:\n1. configure terminal\n2. router ospf 1\n3. router-id 2.2.2.2\n4. end\n5. clear ip ospf process (confirm YES)",
            "osi_layer": "L3"
        }
    },
    {
        "id": 11,
        "symptom": "OSPF neighbors are stuck in DOWN state. No routing information is exchanged.",
        "topology": "RouterA (Gi0/0: 10.1.1.1/30) connected to RouterB (Gi0/0: 10.1.1.2/30).",
        "show_outputs": (
            "RouterA# show ip ospf interface brief\n"
            "Interface    Area            IP Address/Mask    Cost  State Nbrs(F/C)\n"
            "Gi0/0        0               10.1.1.1/30        1     DR    0/0\n\n"
            "RouterB# show ip ospf interface brief\n"
            "Interface    Area            IP Address/Mask    Cost  State Nbrs(F/C)\n"
            "Gi0/0        1               10.1.1.2/30        1     BDR   0/0\n"
        ),
        "expected_fault": "OSPF Area ID mismatch. RouterA's interface Gi0/0 is configured in Area 0, while RouterB's connecting interface is configured in Area 1.",
        "osi_layer": "L3",
        "concept": "Routing",
        "severity": "High",
        "next_command": "show ip ospf interface brief",
        "fix_steps": "Align the OSPF area configurations. Configure RouterB's Gi0/0 OSPF network statement or interface setting to use Area 0.",
        "expected_ai_output": {
            "root_cause": "OSPF Area Mismatch on the point-to-point link. RouterA Gi0/0 is in Area 0, but RouterB Gi0/0 is in Area 1.",
            "confidence": "High",
            "evidence": "RouterA show ip ospf interface brief shows Gi0/0 in Area 0. RouterB show ip ospf interface brief shows Gi0/0 in Area 1.",
            "next_command": "show ip ospf interface",
            "fix_steps": "On RouterB:\n1. configure terminal\n2. router ospf 1\n3. no network 10.1.1.0 0.0.0.3 area 1\n4. network 10.1.1.0 0.0.0.3 area 0\n5. end",
            "osi_layer": "L3"
        }
    },
    {
        "id": 12,
        "symptom": "RouterA cannot reach remote network 192.168.50.0/24 behind RouterB.",
        "topology": "RouterA (Gi0/0: 10.1.1.1/30) <-> RouterB (Gi0/0: 10.1.1.2/30, Gi0/1: 192.168.50.1/24).",
        "show_outputs": (
            "RouterA# show ip route\n"
            "Gateway of last resort is not set\n"
            "     10.0.0.0/8 is variably subnetted, 2 subnets, 2 masks\n"
            "C       10.1.1.0/30 is directly connected, GigabitEthernet0/0\n"
            "L       10.1.1.1/32 is directly connected, GigabitEthernet0/0\n\n"
            "RouterA# show ip route 192.168.50.10\n"
            "% Network not in table\n"
        ),
        "expected_fault": "Missing static route or dynamic routing configuration for 192.168.50.0/24 on RouterA.",
        "osi_layer": "L3",
        "concept": "Routing",
        "severity": "Medium",
        "next_command": "show ip route",
        "fix_steps": "Add a static route on RouterA: 'ip route 192.168.50.0 255.255.255.0 10.1.1.2'.",
        "expected_ai_output": {
            "root_cause": "No routing table entry for destination network 192.168.50.0/24 exists on RouterA.",
            "confidence": "High",
            "evidence": "show ip route shows only directly connected interfaces. show ip route 192.168.50.10 returns '% Network not in table'.",
            "next_command": "show running-config | include ip route",
            "fix_steps": "On RouterA:\n1. configure terminal\n2. ip route 192.168.50.0 255.255.255.0 10.1.1.2\n3. end",
            "osi_layer": "L3"
        }
    },
    {
        "id": 13,
        "symptom": "Static route configured on RouterA fails to route traffic to destination, pings time out.",
        "topology": "RouterA (Gi0/0: 10.1.1.1/24) -> RouterB (Gi0/0: 10.1.1.2/24). Destination network is 192.168.50.0/24.",
        "show_outputs": (
            "RouterA# show running-config | include ip route\n"
            "ip route 192.168.50.0 255.255.255.0 10.1.1.6\n\n"
            "RouterA# show ip route 192.168.50.0\n"
            "Routing entry for 192.168.50.0/24\n"
            "  Known via \"static\", distance 1, metric 0\n"
            "  Routing Descriptor Blocks:\n"
            "  * 10.1.1.6\n\n"
            "RouterA# show arp\n"
            "Protocol  Address          Age (min)  Hardware Addr   Type   Interface\n"
            "Internet  10.1.1.1                -   0011.2233.4455  ARPA   GigabitEthernet0/0\n"
            "Internet  10.1.1.2                5   0011.2233.abcd  ARPA   GigabitEthernet0/0\n"
        ),
        "expected_fault": "Static route configured with incorrect next-hop IP (10.1.1.6 instead of RouterB's IP 10.1.1.2). 10.1.1.6 is unresponsive or not present on the subnet.",
        "osi_layer": "L3",
        "concept": "Routing",
        "severity": "Medium",
        "next_command": "show running-config | include ip route",
        "fix_steps": "Remove incorrect route and add correct static route: 'no ip route 192.168.50.0 255.255.255.0 10.1.1.6' then 'ip route 192.168.50.0 255.255.255.0 10.1.1.2'.",
        "expected_ai_output": {
            "root_cause": "The static route points to an incorrect next-hop IP (10.1.1.6) which is unreachable or does not belong to any neighbor.",
            "confidence": "High",
            "evidence": "ip route shows destination 192.168.50.0/24 via 10.1.1.6. ARP table only lists 10.1.1.2 as a resolved neighbor.",
            "next_command": "ping 10.1.1.6",
            "fix_steps": "On RouterA:\n1. configure terminal\n2. no ip route 192.168.50.0 255.255.255.0 10.1.1.6\n3. ip route 192.168.50.0 255.255.255.0 10.1.1.2\n4. end",
            "osi_layer": "L3"
        }
    },
    {
        "id": 14,
        "symptom": "RouterA and RouterB run RIP but cannot exchange routing updates. Routes from RouterB are missing on RouterA.",
        "topology": "RouterA <-> RouterB directly connected on 10.1.1.0/30 subnet.",
        "show_outputs": (
            "RouterA# show ip protocols\n"
            "Routing Protocol is \"rip\"\n"
            "  Sending updates every 30 seconds\n"
            "  Default version control: send version 1, receive version 1\n"
            "  Routing for Networks:\n"
            "    10.0.0.0\n\n"
            "RouterB# show ip protocols\n"
            "Routing Protocol is \"rip\"\n"
            "  Sending updates every 30 seconds\n"
            "  Default version control: send version 2, receive version 2\n"
            "  Routing for Networks:\n"
            "    10.0.0.0\n"
        ),
        "expected_fault": "RIP routing protocol version mismatch. RouterA uses version 1, and RouterB uses version 2. Version 1 does not support classless updates sent by Version 2, or they ignore each other's packets.",
        "osi_layer": "L3",
        "concept": "Routing",
        "severity": "Medium",
        "next_command": "show ip protocols",
        "fix_steps": "Configure RIP version 2 on RouterA: 'router rip', 'version 2'.",
        "expected_ai_output": {
            "root_cause": "RIP version mismatch. RouterA is configured for RIP Version 1, while RouterB is configured for RIP Version 2.",
            "confidence": "High",
            "evidence": "RouterA show ip protocols: send version 1, receive version 1. RouterB: send version 2, receive version 2.",
            "next_command": "show ip protocols",
            "fix_steps": "On RouterA:\n1. configure terminal\n2. router rip\n3. version 2\n4. end",
            "osi_layer": "L3"
        }
    },
    {
        "id": 15,
        "symptom": "PC1 cannot access the intranet web server (HTTP port 80), though it can ping the server's IP address.",
        "topology": "PC1 (192.168.1.10) -> Router -> WebServer (172.16.1.100).",
        "show_outputs": (
            "Router# show access-lists\n"
            "Extended IP access list 101\n"
            "    10 deny tcp any host 172.16.1.100 eq www\n"
            "    20 deny tcp any host 172.16.1.100 eq 443\n"
            "    30 permit ip any any\n\n"
            "Router# show running-config interface GigabitEthernet0/1\n"
            "interface GigabitEthernet0/1\n"
            " ip address 172.16.1.1 255.255.255.0\n"
            " ip access-group 101 out\n"
        ),
        "expected_fault": "Access Control List (ACL 101) applied out on the server-facing interface blocks web traffic (HTTP port 80 and HTTPS port 443) destined for the server.",
        "osi_layer": "L4",
        "concept": "ACL",
        "severity": "High",
        "next_command": "show access-lists",
        "fix_steps": "Modify or remove the deny rules in ACL 101 if web traffic is authorized: 'no access-list 101 deny tcp any host 172.16.1.100 eq www' or remove ACL from interface.",
        "expected_ai_output": {
            "root_cause": "Access control list 101 is explicitly denying TCP ports 80 (www) and 443 (https) traffic to host 172.16.1.100.",
            "confidence": "High",
            "evidence": "Extended IP access list 101 lines 10 and 20 deny www/443, and the list is applied 'out' on interface G0/1.",
            "next_command": "show access-lists",
            "fix_steps": "On Router:\n1. configure terminal\n2. ip access-list extended 101\n3. no 10\n4. no 20\n5. end",
            "osi_layer": "L4"
        }
    },
    {
        "id": 16,
        "symptom": "An access list intended to permit only the management host 192.168.1.10 to SSH to the router is blocking all hosts on that subnet, or permitting everyone. SSH connectivity is inconsistent.",
        "topology": "Management host (192.168.1.10/24) -> Router G0/0 (192.168.1.1/24).",
        "show_outputs": (
            "Router# show running-config | include access-list\n"
            "access-list 101 permit ip 192.168.1.0 255.255.255.0 any\n"
            "Router# show running-config | section line vty\n"
            "line vty 0 4\n"
            " access-class 101 in\n"
            " transport input ssh\n"
        ),
        "expected_fault": "Incorrect wildcard mask used in Cisco Access Control List. The command uses '255.255.255.0' which is a subnet mask, instead of the inverted wildcard mask '0.0.0.255' or a host wildcard '0.0.0.0' for single host.",
        "osi_layer": "L3",
        "concept": "ACL",
        "severity": "High",
        "next_command": "show running-config | include access-list",
        "fix_steps": "Correct the wildcard mask: 'no access-list 101' and add 'access-list 101 permit tcp host 192.168.1.10 any eq 22' or 'access-list 101 permit ip 192.168.1.0 0.0.0.255 any' depending on the policy.",
        "expected_ai_output": {
            "root_cause": "The ACL 101 uses a standard subnet mask (255.255.255.0) instead of an inverted wildcard mask (0.0.0.255). Cisco IOS parses 255.255.255.0 as a wildcard mask, which matches hosts incorrectly.",
            "confidence": "Medium",
            "evidence": "access-list 101 permit ip 192.168.1.0 255.255.255.0 any is configured in show run.",
            "next_command": "show running-config | include access-list",
            "fix_steps": "On Router:\n1. configure terminal\n2. no access-list 101\n3. access-list 101 permit ip 192.168.1.0 0.0.0.255 any\n4. end",
            "osi_layer": "L3"
        }
    },
    {
        "id": 17,
        "symptom": "After implementing an ACL to permit web browsing, users cannot resolve any URLs, but can browse using direct IP addresses.",
        "topology": "PC1 (192.168.1.10) -> Router -> Internet. DNS server is external at 8.8.8.8.",
        "show_outputs": (
            "Router# show access-lists\n"
            "Extended IP access list 102\n"
            "    10 permit tcp any any eq www\n"
            "    20 permit tcp any any eq 443\n"
            "\n"
            "Router# show running-config interface GigabitEthernet0/1\n"
            "interface GigabitEthernet0/1\n"
            " ip access-group 102 out\n"
        ),
        "expected_fault": "The implicit deny at the end of ACL 102 is blocking DNS traffic (UDP port 53), preventing host-name resolution.",
        "osi_layer": "L4",
        "concept": "ACL",
        "severity": "High",
        "next_command": "show access-lists",
        "fix_steps": "Permit UDP port 53 in ACL 102: add 'access-list 102 permit udp any any eq 53' to allow DNS queries.",
        "expected_ai_output": {
            "root_cause": "The ACL lacks a rule to permit UDP port 53 traffic (DNS). The implicit deny at the bottom is blocking all DNS queries.",
            "confidence": "High",
            "evidence": "Extended access list 102 only permits TCP 80 (www) and 443. It has no permit statement for UDP/TCP port 53 (domain).",
            "next_command": "show access-lists",
            "fix_steps": "On Router:\n1. configure terminal\n2. ip access-list extended 102\n3. 15 permit udp any any eq 53\n4. end",
            "osi_layer": "L4"
        }
    },
    {
        "id": 18,
        "symptom": "PCs in the LAN cannot access the internet. No NAT translations are recorded on the router.",
        "topology": "LAN (192.168.1.0/24) -> Router G0/0 (LAN) & G0/1 (WAN: 203.0.113.2) -> Internet.",
        "show_outputs": (
            "Router# show running-config interface gigabitethernet 0/0\n"
            "interface GigabitEthernet0/0\n"
            " description LAN Interface\n"
            " ip address 192.168.1.1 255.255.255.0\n"
            " ip nat outside\n\n"
            "Router# show running-config interface gigabitethernet 0/1\n"
            "interface GigabitEthernet0/1\n"
            " description WAN Interface\n"
            " ip address 203.0.113.2 255.255.255.252\n"
            " ip nat inside\n"
        ),
        "expected_fault": "NAT inside/outside interfaces are reversed. GigabitEthernet0/0 (LAN) is configured as 'ip nat outside' and GigabitEthernet0/1 (WAN) is 'ip nat inside'.",
        "osi_layer": "L3",
        "concept": "NAT",
        "severity": "High",
        "next_command": "show running-config interface",
        "fix_steps": "Swap the NAT designations on the interfaces: on G0/0 configure 'ip nat inside', on G0/1 configure 'ip nat outside'.",
        "expected_ai_output": {
            "root_cause": "Reversed NAT direction commands on the interfaces. G0/0 (LAN) should be inside, and G0/1 (WAN) should be outside.",
            "confidence": "High",
            "evidence": "G0/0 (LAN) has 'ip nat outside'. G0/1 (WAN) has 'ip nat inside'.",
            "next_command": "show run | include ip nat",
            "fix_steps": "On Router:\n1. configure terminal\n2. interface GigabitEthernet0/0\n3. no ip nat outside\n4. ip nat inside\n5. interface GigabitEthernet0/1\n6. no ip nat inside\n7. ip nat outside\n8. end",
            "osi_layer": "L3"
        }
    },
    {
        "id": 19,
        "symptom": "VLAN 20 hosts (192.168.20.0/24) fail to access the internet, while VLAN 10 hosts (192.168.10.0/24) are working fine. NAT translations are empty for VLAN 20.",
        "topology": "VLAN 10 (192.168.10.0/24), VLAN 20 (192.168.20.0/24) -> Router G0/1 (WAN: 203.0.113.2).",
        "show_outputs": (
            "Router# show running-config | include ip nat\n"
            "ip nat inside source list 1 interface GigabitEthernet0/1 overload\n\n"
            "Router# show running-config | include access-list 1\n"
            "access-list 1 permit 192.168.10.0 0.0.0.255\n\n"
            "Router# show ip nat translations\n"
            "Pro Inside global      Inside local       Outside local      Outside global\n"
            "tcp 203.0.113.2:1024   192.168.10.15:8080 8.8.8.8:80         8.8.8.8:80\n"
        ),
        "expected_fault": "The NAT access-list (ACL 1) is missing a permit statement for the VLAN 20 subnet (192.168.20.0/24), preventing their source IPs from being translated.",
        "osi_layer": "L3",
        "concept": "NAT",
        "severity": "High",
        "next_command": "show running-config | include access-list",
        "fix_steps": "Add a permit statement for VLAN 20 in ACL 1: 'access-list 1 permit 192.168.20.0 0.0.0.255'.",
        "expected_ai_output": {
            "root_cause": "The access-list (ACL 1) referenced by the NAT translation rule does not permit traffic from the VLAN 20 subnet (192.168.20.0/24).",
            "confidence": "Medium",
            "evidence": "access-list 1 only permits 192.168.10.0/24. No rules permit 192.168.20.0/24. show ip nat translations lists translations only for 192.168.10.x.",
            "next_command": "show running-config | include access-list",
            "fix_steps": "On Router:\n1. configure terminal\n2. access-list 1 permit 192.168.20.0 0.0.0.255\n3. end",
            "osi_layer": "L3"
        }
    },
    {
        "id": 20,
        "symptom": "A user moved their laptop from Desk A to Desk B. Now, the network port is down, link light is amber/red, and PC shows no network connection.",
        "topology": "PC -> Switch Port F0/5. Switch port is err-disabled.",
        "show_outputs": (
            "Switch# show interfaces fastethernet 0/5\n"
            "FastEthernet0/5 is down, line protocol is down (err-disabled)\n\n"
            "Switch# show port-security interface fastethernet 0/5\n"
            "Port Security: Enabled\n"
            "Port Status: Secure-shutdown\n"
            "Violation Mode: Shutdown\n"
            "Max Addresses: 1\n"
            "Total Addresses: 1\n"
            "Last Source Address: 0011.2233.4455\n"
            "Security Violation Count: 1\n"
        ),
        "expected_fault": "Port security violation on Switch port FastEthernet0/5. The user connected a device with a different MAC address (0011.2233.4455) than the secured MAC address, causing the port to enter the err-disabled shutdown state.",
        "osi_layer": "L2",
        "concept": "VLAN",
        "severity": "Medium",
        "next_command": "show port-security interface fastethernet 0/5",
        "fix_steps": "Clear errdisable on the interface: enter config mode, type 'interface Fa0/5', then 'shutdown' followed by 'no shutdown'. Or adjust port security settings.",
        "expected_ai_output": {
            "root_cause": "Port Security violation on FastEthernet0/5 has placed the interface in the err-disabled state due to an unauthorized MAC address (0011.2233.4455).",
            "confidence": "High",
            "evidence": "FastEthernet0/5 is 'down, line protocol is down (err-disabled)'. show port-security shows Port Status 'Secure-shutdown' and Security Violation Count '1'.",
            "next_command": "show port-security interface Fa0/5",
            "fix_steps": "On Switch:\n1. configure terminal\n2. interface FastEthernet0/5\n3. shutdown\n4. no shutdown\n5. (optional) switchport port-security mac-address sticky\n6. end",
            "osi_layer": "L2"
        }
    },
    {
        "id": 21,
        "symptom": "RouterA and RouterB are connected directly on their G0/0 interfaces but cannot ping each other. The link lights are green.",
        "topology": "RouterA (Gi0/0) <-> RouterB (Gi0/0). Directly connected.",
        "show_outputs": (
            "RouterA# show running-config interface gigabitethernet 0/0\n"
            "interface GigabitEthernet0/0\n"
            " ip address 10.0.0.1 255.255.255.252\n\n"
            "RouterB# show running-config interface gigabitethernet 0/0\n"
            "interface GigabitEthernet0/0\n"
            " ip address 10.0.0.2 255.255.255.248\n"
        ),
        "expected_fault": "Mismatched subnet masks on RouterA and RouterB's directly connecting link. RouterA uses /30 (255.255.255.252) while RouterB uses /29 (255.255.255.248).",
        "osi_layer": "L3",
        "concept": "Routing",
        "severity": "Medium",
        "next_command": "show running-config interface",
        "fix_steps": "Change RouterB's G0/0 subnet mask to 255.255.255.252 to match RouterA.",
        "expected_ai_output": {
            "root_cause": "Subnet mask mismatch on the connecting link interface. RouterA is configured with 255.255.255.252 (/30) and RouterB with 255.255.255.248 (/29).",
            "confidence": "High",
            "evidence": "RouterA Gi0/0 IP: 10.0.0.1 255.255.255.252, RouterB Gi0/0 IP: 10.0.0.2 255.255.255.248.",
            "next_command": "show run interface GigabitEthernet0/0",
            "fix_steps": "On RouterB:\n1. configure terminal\n2. interface GigabitEthernet0/0\n3. ip address 10.0.0.2 255.255.255.252\n4. end",
            "osi_layer": "L3"
        }
    },
    {
        "id": 22,
        "symptom": "Hosts on the LAN report intermittent connectivity and slow speeds. Ping response times to the gateway flap and drop packets.",
        "topology": "LAN Switch -> Router G0/0 (192.168.1.1). Two hosts share IP 192.168.1.10.",
        "show_outputs": (
            "Router# show logging\n"
            "00:24:15: %IP-4-DUPADDR: Duplicate address 192.168.1.10 on GigabitEthernet0/0, sourced by MAC 0015.65c4.8912\n\n"
            "Router# show arp\n"
            "Protocol  Address          Age (min)  Hardware Addr   Type   Interface\n"
            "Internet  192.168.1.1             -   0011.85a3.2201  ARPA   GigabitEthernet0/0\n"
            "Internet  192.168.1.10            0   0015.65c4.8912  ARPA   GigabitEthernet0/0\n"
            "Internet  192.168.1.10            0   0022.48f1.88a2  ARPA   GigabitEthernet0/0\n"
        ),
        "expected_fault": "Duplicate IP address on the LAN. Two devices (MACs 0015.65c4.8912 and 0022.48f1.88a2) are configured with the same IP address 192.168.1.10.",
        "osi_layer": "L3",
        "concept": "Routing",
        "severity": "Medium",
        "next_command": "show arp",
        "fix_steps": "Identify the two physical devices. Reconfigure one of the hosts to use a unique, unused IP address on the 192.168.1.0/24 subnet.",
        "expected_ai_output": {
            "root_cause": "IP address conflict on the local network. Multiple hosts are using the identical IP 192.168.1.10.",
            "confidence": "Medium",
            "evidence": "Console log '%IP-4-DUPADDR: Duplicate address 192.168.1.10' and show arp lists two MAC addresses for the same IP (0015.65c4.8912 and 0022.48f1.88a2).",
            "next_command": "show arp",
            "fix_steps": "1. Trace MAC addresses to switch ports.\n2. Reconfigure one of the duplicate hosts to obtain IP via DHCP or change its static IP.",
            "osi_layer": "L3"
        }
    },
    {
        "id": 23,
        "symptom": "Network traffic is taking a slow path (100Mbps link) instead of the fast Gigabit link. Users report slow file transfers.",
        "topology": "Core_Switch <-> Access_Switch. Two paths: 1Gbps link and a 100Mbps redundant link.",
        "show_outputs": (
            "Core_Switch# show spanning-tree vlan 1\n"
            "Vlan 1\n"
            "  Root ID    Priority    32769\n"
            "             Address     0001.96b2.3301\n"
            "             This bridge is not the root\n\n"
            "Access_Switch# show spanning-tree vlan 1\n"
            "Vlan 1\n"
            "  Root ID    Priority    32769\n"
            "             Address     0001.1122.3344\n"
            "             This bridge is the root\n"
        ),
        "expected_fault": "Incorrect Spanning Tree Root Bridge election. The low-end Access Switch was elected as Root Bridge because priorities are left at default (32768+1) and it has a lower MAC address. This causes traffic to route suboptimally.",
        "osi_layer": "L2",
        "concept": "VLAN",
        "severity": "Medium",
        "next_command": "show spanning-tree vlan 1",
        "fix_steps": "Configure the Core_Switch to be the primary root bridge by lowering its STP priority: 'spanning-tree vlan 1 priority 4096' or 'spanning-tree vlan 1 root primary'.",
        "expected_ai_output": {
            "root_cause": "Suboptimal Spanning Tree topology because the access switch is acting as the Root Bridge due to default STP priorities.",
            "confidence": "High",
            "evidence": "Access_Switch has 'This bridge is the root'. Both switches share priority 32769. Core_Switch is not the root.",
            "next_command": "show spanning-tree vlan 1",
            "fix_steps": "On Core_Switch:\n1. configure terminal\n2. spanning-tree vlan 1 root primary\n3. end",
            "osi_layer": "L2"
        }
    },
    {
        "id": 24,
        "symptom": "The EtherChannel link between SwitchA and SwitchB is down, and ports Fa0/23 and Fa0/24 show suspended states.",
        "topology": "SwitchA (Fa0/23, Fa0/24) <-> SwitchB (Fa0/23, Fa0/24). Channel group 1 is configured.",
        "show_outputs": (
            "SwitchA# show etherchannel summary\n"
            "Flags:  D - down        P - bundled in port-channel\n"
            "        S - suspended\n"
            "Number of channel-groups in use: 1\n"
            "Group  Port-channel  Protocol    Ports\n"
            "------+-------------+-----------+-----------------------------------------------\n"
            "1      Po1(SD)         LACP      Fa0/23(D)  Fa0/24(D)\n\n"
            "SwitchB# show etherchannel summary\n"
            "Group  Port-channel  Protocol    Ports\n"
            "------+-------------+-----------+-----------------------------------------------\n"
            "1      Po1(SD)         PAgP      Fa0/23(D)  Fa0/24(D)\n"
        ),
        "expected_fault": "EtherChannel protocol mismatch. SwitchA is configured to use Link Aggregation Control Protocol (LACP), whereas SwitchB is configured to use Port Aggregation Protocol (PAgP).",
        "osi_layer": "L2",
        "concept": "VLAN",
        "severity": "High",
        "next_command": "show etherchannel summary",
        "fix_steps": "Change the EtherChannel protocol on SwitchB to LACP by reconfiguring the channel-group command: 'no channel-group 1', then 'channel-group 1 mode active' on interfaces Fa0/23 and Fa0/24.",
        "expected_ai_output": {
            "root_cause": "EtherChannel protocol mismatch. SwitchA is running LACP, while SwitchB is running PAgP.",
            "confidence": "High",
            "evidence": "SwitchA protocol: LACP, SwitchB protocol: PAgP. Channel status is down/suspended (SD) on both switches.",
            "next_command": "show etherchannel summary",
            "fix_steps": "On SwitchB:\n1. configure terminal\n2. interface range Fa0/23 - 24\n3. no channel-group 1\n4. channel-group 1 mode active\n5. end",
            "osi_layer": "L2"
        }
    },
    {
        "id": 25,
        "symptom": "Wireless clients in the branch office cannot see or connect to the 'Cisco_Guest' SSID.",
        "topology": "Wireless Clients -> APs -> Wireless LAN Controller (WLC).",
        "show_outputs": (
            "WLC# show wlan summary\n"
            "Number of WLANs: 1\n"
            "WLAN ID  WLAN Profile Name    SSID                  Status\n"
            "1        Guest_Network        Cisco-Guest           Enabled\n\n"
            "Client Profile Details:\n"
            "Target SSID: Cisco_Guest\n"
        ),
        "expected_fault": "SSID mismatch. The WLC broadcasts the SSID as 'Cisco-Guest' (hyphen), but the clients are preconfigured or trying to connect to 'Cisco_Guest' (underscore).",
        "osi_layer": "L2",
        "concept": "Wireless",
        "severity": "Medium",
        "next_command": "show wlan summary",
        "fix_steps": "Correct the SSID on WLC to 'Cisco_Guest' or update client configurations to match the broadcast SSID.",
        "expected_ai_output": {
            "root_cause": "SSID name mismatch. WLC broadcasts 'Cisco-Guest' but clients expect 'Cisco_Guest'.",
            "confidence": "High",
            "evidence": "WLC show wlan summary lists SSID as 'Cisco-Guest'. Client Target SSID is 'Cisco_Guest'.",
            "next_command": "show wlan 1",
            "fix_steps": "On WLC:\n1. Open WLAN configurations.\n2. Edit WLAN ID 1 SSID to 'Cisco_Guest'.\n3. Apply and Save configuration.",
            "osi_layer": "L2"
        }
    },
    {
        "id": 26,
        "symptom": "Wireless clients enter a looping authentication loop when attempting to connect to the corporate WLAN.",
        "topology": "Clients -> AP -> WLC -> RADIUS/Local Authentication.",
        "show_outputs": (
            "WLC# show logging\n"
            "00:15:34: *dot1xMsgTask: %SEC-6-WPA_EXTRA_KEY_MME: WPA key message 4 validation failed for client 00:24:d7:a1:b2:c3\n"
            "00:15:34: *dot1xMsgTask: %wps_msg.c:892 - Pre-shared key mismatch detected for station 00:24:d7:a1:b2:c3\n"
        ),
        "expected_fault": "Wireless security password mismatch. The client is entering the incorrect WPA2 pre-shared key (PSK), causing a WPA handshake key validation failure.",
        "osi_layer": "L2",
        "concept": "Wireless",
        "severity": "Medium",
        "next_command": "show logging on WLC",
        "fix_steps": "Verify and enter the correct WPA2 pre-shared key on the wireless client device.",
        "expected_ai_output": {
            "root_cause": "Pre-shared key (WPA/WPA2 password) mismatch on the client device.",
            "confidence": "High",
            "evidence": "Log entries: '%wps_msg.c:892 - Pre-shared key mismatch detected' and '%SEC-6-WPA_EXTRA_KEY_MME'.",
            "next_command": "show logging | include mismatch",
            "fix_steps": "1. Re-enter the correct WPA2 pre-shared key on the client device.\n2. If password is forgotten, verify/reset the PSK on the WLC WLAN security page.",
            "osi_layer": "L2"
        }
    },
    {
        "id": 27,
        "symptom": "PC1 in VLAN 20 cannot ping its default gateway Router subinterface G0/0.20.",
        "topology": "PC1 (192.168.20.10/24) -> Switch (Fa0/1 in VLAN 20, Trunk on Fa0/24) -> Router G0/0.20.",
        "show_outputs": (
            "Router# show running-config interface gigabitethernet 0/0.20\n"
            "interface GigabitEthernet0/0.20\n"
            " encapsulation dot1Q 30\n"
            " ip address 192.168.20.1 255.255.255.0\n"
        ),
        "expected_fault": "Inter-VLAN Routing subinterface encapsulation mismatch. Subinterface G0/0.20 is configured to tag and receive VLAN 30 frames ('encapsulation dot1Q 30'), instead of VLAN 20.",
        "osi_layer": "L3",
        "concept": "Routing",
        "severity": "High",
        "next_command": "show running-config interface gigabitethernet 0/0.20",
        "fix_steps": "Change encapsulation tag to 20: under interface G0/0.20, configure 'encapsulation dot1Q 20'.",
        "expected_ai_output": {
            "root_cause": "VLAN encapsulation ID mismatch on router subinterface G0/0.20 (configured for dot1Q 30 instead of dot1Q 20).",
            "confidence": "Medium",
            "evidence": "Interface GigabitEthernet0/0.20 has 'encapsulation dot1Q 30', but its IP 192.168.20.1 is the gateway for VLAN 20.",
            "next_command": "show running-config interface GigabitEthernet0/0.20",
            "fix_steps": "On Router:\n1. configure terminal\n2. interface GigabitEthernet0/0.20\n3. encapsulation dot1Q 20\n4. end",
            "osi_layer": "L3"
        }
    },
    {
        "id": 28,
        "symptom": "Console logs show HSRP IP address duplicate warnings, and hosts suffer from routing packet drops.",
        "topology": "RouterA (192.168.1.2) & RouterB (192.168.1.3) run HSRP for virtual IP 192.168.1.254.",
        "show_outputs": (
            "RouterA# show standby brief\n"
            "Interface   Grp  Pri P State    Active addr     Standby addr    Group addr\n"
            "Gi0/0       10   100   Active   local           unknown         192.168.1.254\n\n"
            "RouterB# show standby brief\n"
            "Interface   Grp  Pri P State    Active addr     Standby addr    Group addr\n"
            "Gi0/0       20   100   Active   local           unknown         192.168.1.254\n"
        ),
        "expected_fault": "HSRP Group Mismatch. RouterA is configured for standby group 10, and RouterB is in standby group 20. They do not exchange HSRP hello messages for the same group, causing both to assume the Active role.",
        "osi_layer": "L3",
        "concept": "Gateway",
        "severity": "High",
        "next_command": "show standby brief",
        "fix_steps": "Align the standby group number: configure RouterB's standby group to match RouterA: under interface G0/0, type 'no standby 20 ip...', then 'standby 10 ip 192.168.1.254'.",
        "expected_ai_output": {
            "root_cause": "HSRP Active/Active conflict due to mismatched standby group numbers (RouterA group 10, RouterB group 20).",
            "confidence": "Medium",
            "evidence": "RouterA show standby brief shows Grp 10 is Active. RouterB shows Grp 20 is Active. Both Standby addr fields are 'unknown'.",
            "next_command": "show standby",
            "fix_steps": "On RouterB:\n1. configure terminal\n2. interface GigabitEthernet0/0\n3. no standby 20 ip 192.168.1.254\n4. standby 10 ip 192.168.1.254\n5. end",
            "osi_layer": "L3"
        }
    },
    {
        "id": 29,
        "symptom": "Users cannot establish secure HTTPS connections to internal web portals. Browsers show SSL certificate expired/invalid errors.",
        "topology": "Clients -> Network -> Web Server. Clock is desynchronized.",
        "show_outputs": (
            "Router# show clock\n"
            "00:04:12.342 UTC Mon Jan 1 1993\n\n"
            "Router# show ntp status\n"
            "Clock is unsynchronized, stratum 16, no reference clock\n"
            "nominal freq is 250.0000 Hz, actual freq is 250.0000 Hz, precision is 2**18\n"
        ),
        "expected_fault": "NTP system clock desynchronization. The router's system clock is set to 1993, causing validity checks on modern SSL/TLS certificates to fail.",
        "osi_layer": "L7",
        "concept": "DNS",
        "severity": "Low",
        "next_command": "show ntp status",
        "fix_steps": "Configure correct NTP server address: 'ntp server 216.58.216.164' or manually set the system clock using 'clock set'.",
        "expected_ai_output": {
            "root_cause": "NTP synchronization failure causing system clock to fall back to 1993, which invalidates SSL certificate time validation.",
            "confidence": "High",
            "evidence": "show clock returns 1993 date, and show ntp status is 'Clock is unsynchronized, stratum 16'.",
            "next_command": "show ntp associations",
            "fix_steps": "On Router:\n1. configure terminal\n2. ntp server pool.ntp.org\n3. (optional) clock set [hh:mm:ss] [day] [month] [year]\n4. end",
            "osi_layer": "L7"
        }
    },
    {
        "id": 30,
        "symptom": "VLANs created on SwitchA (VTP Server) are not replicating to SwitchB (VTP Client). Ports on SwitchB remain unassigned.",
        "topology": "SwitchA (VTP Server) <-> SwitchB (VTP Client) via Trunk.",
        "show_outputs": (
            "SwitchA# show vtp status\n"
            "VTP Version                     : 2\n"
            "VTP Operating Mode              : Server\n"
            "VTP Domain Name                 : CISCO\n\n"
            "SwitchB# show vtp status\n"
            "VTP Operating Mode              : Client\n"
            "VTP Domain Name                 : cisco\n"
        ),
        "expected_fault": "VTP Domain Name mismatch. VTP is case-sensitive. SwitchA uses 'CISCO' (uppercase), whereas SwitchB is configured with 'cisco' (lowercase).",
        "osi_layer": "L2",
        "concept": "VLAN",
        "severity": "Medium",
        "next_command": "show vtp status",
        "fix_steps": "Reconfigure the VTP Domain name on SwitchB to match the server: 'vtp domain CISCO'.",
        "expected_ai_output": {
            "root_cause": "VTP synchronization failure due to case-sensitive VTP Domain Name mismatch ('CISCO' on Server vs 'cisco' on Client).",
            "confidence": "High",
            "evidence": "SwitchA Domain Name: CISCO. SwitchB Domain Name: cisco.",
            "next_command": "show vtp status",
            "fix_steps": "On SwitchB:\n1. configure terminal\n2. vtp domain CISCO\n3. end",
            "osi_layer": "L2"
        }
    }
]

def generate_files():
    # 1. Generate cases_db.json (used internally by Web App)
    with open('cases_db.json', 'w') as f:
        json.dump(cases, f, indent=4)
    print("Generated cases_db.json successfully.")

    # 2. Generate cases.csv (as requested in deliverables)
    csv_fields = ["id", "symptom", "topology", "show_outputs", "expected_fault", "osi_layer", "concept", "severity", "next_command", "fix_steps"]
    with open('cases.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for case in cases:
            # We filter out expected_ai_output for the CSV, keeping just the requested fields
            csv_row = {field: case[field] for field in csv_fields}
            writer.writerow(csv_row)
    print("Generated cases.csv successfully.")

if __name__ == "__main__":
    generate_files()
