import re

def check_rules(show_outputs: str, topology: str = "", symptom: str = ""):
    """
    Analyzes Cisco show command outputs, topology notes, and symptoms to detect 
    common network configuration mistakes deterministically.
    
    Returns a list of dictionaries containing found issues.
    """
    anomalies = []
    
    # 1. Check for Administrative Down or Err-Disabled Interfaces
    # Looks for lines like: "GigabitEthernet0/0.10  192.168.10.1    YES manual administratively down down"
    # Or: "FastEthernet0/5 is down, line protocol is down (err-disabled)"
    interface_brief_matches = re.findall(
        r'(\S+)\s+(?:[0-9\.]+|unassigned)\s+\w+\s+\w+\s+(administratively down|down|err-disabled)\s+(down|err-disabled)?', 
        show_outputs, 
        re.IGNORECASE
    )
    for match in interface_brief_matches:
        if "administratively down" in match[1].lower():
            anomalies.append({
                "rule": "Interface Administratively Down",
                "severity": "High",
                "details": f"Interface {match[0]} is configured but administratively shut down.",
                "fix": f"Enter configuration mode for interface {match[0]} and run 'no shutdown'."
            })
        elif "err-disabled" in match[1].lower() or "err-disabled" in (match[2] or "").lower():
            anomalies.append({
                "rule": "Interface Err-Disabled",
                "severity": "High",
                "details": f"Interface {match[0]} has entered the err-disabled state (likely due to Port Security violation).",
                "fix": f"Enter interface configuration mode for {match[0]} and run 'shutdown' followed by 'no shutdown'."
            })

    # Port Security specific check
    if "err-disabled" in show_outputs.lower() or "secure-shutdown" in show_outputs.lower():
        port_sec_match = re.search(r'port security:\s*enabled.*(?:secure-shutdown|shutdown)', show_outputs, re.IGNORECASE)
        if port_sec_match:
            anomalies.append({
                "rule": "Port Security Violation",
                "severity": "High",
                "details": "Port security violation has shut down the port because an unauthorized MAC address connected.",
                "fix": "Disable and enable the interface ('shutdown' / 'no shutdown') or configure 'switchport port-security mac-address sticky'."
            })

    # 2. Check for Duplicate IP Addresses
    # Logs: "%IP-4-DUPADDR: Duplicate address 192.168.1.10"
    # Or ARP showing multiple MACs for same IP (harder to regex, but we can search for the dupaddr message)
    dup_ip_match = re.search(r'%IP-4-DUPADDR:\s*Duplicate address\s*([0-9\.]+)', show_outputs, re.IGNORECASE)
    if dup_ip_match:
        conflict_ip = dup_ip_match.group(1)
        anomalies.append({
            "rule": "Duplicate IP Address Detected",
            "severity": "High",
            "details": f"The IP address {conflict_ip} is assigned to multiple devices on the same broadcast domain.",
            "fix": f"Change the static IP address of one of the conflicting hosts, or assign a dynamic IP using DHCP."
        })

    # 3. Check for Gateway IP and Subnet Mismatches (PC Gateway Mismatch)
    # PC IP & Gateway check from pc configurations (e.g. in show outputs or topology)
    # Extracts: IP: 192.168.1.50, Mask: 255.255.255.0, Gateway: 192.168.2.1
    # Router Interface IP: 192.168.1.1
    pc_ip_match = re.search(r'IP Address(?:\.\s*)+:\s*([0-9\.]+)', show_outputs)
    pc_mask_match = re.search(r'Subnet Mask(?:\.\s*)+:\s*([0-9\.]+)', show_outputs)
    pc_gw_match = re.search(r'Default Gateway(?:\.\s*)+:\s*([0-9\.]+)', show_outputs)
    
    if pc_ip_match and pc_gw_match:
        pc_ip = pc_ip_match.group(1)
        pc_gw = pc_gw_match.group(1)
        # Check if they are in same subnet (if mask is found, else assume /24)
        mask = pc_mask_match.group(1) if pc_mask_match else "255.255.255.0"
        
        # Convert IPs to integers to perform subnet math
        def ip_to_int(ip):
            return sum(int(octet) << (24 - 8 * i) for i, octet in enumerate(ip.split('.')))
        
        try:
            ip_int = ip_to_int(pc_ip)
            gw_int = ip_to_int(pc_gw)
            mask_int = ip_to_int(mask)
            
            if (ip_int & mask_int) != (gw_int & mask_int):
                anomalies.append({
                    "rule": "Gateway Subnet Mismatch",
                    "severity": "High",
                    "details": f"PC IP address {pc_ip} and its default gateway {pc_gw} are not in the same subnet ({mask}).",
                    "fix": f"Reconfigure PC's default gateway to match the router's interface IP in the local subnet."
                })
        except Exception:
            pass

    # 4. Check for Router Interface IP mismatches on point-to-point links (Subnet Mask Mismatch)
    # Finds multiple interfaces configured with IPs, like:
    # RouterA: 10.0.0.1 255.255.255.252
    # RouterB: 10.0.0.2 255.255.255.248
    router_ips = re.findall(r'ip address\s+([0-9\.]+)\s+([0-9\.]+)', show_outputs, re.IGNORECASE)
    if len(router_ips) >= 2:
        # Check if subnet masks are different on point-to-point links
        masks = [ip[1] for ip in router_ips]
        if len(set(masks)) > 1:
            anomalies.append({
                "rule": "Subnet Mask Mismatch on Link",
                "severity": "Medium",
                "details": f"Mismatched subnet masks detected on connecting interfaces: {', '.join(set(masks))}.",
                "fix": "Reconfigure the interfaces on the link to use matching subnet masks (e.g., both /30 255.255.255.252)."
            })

    # 5. Check for Native VLAN Mismatch on trunks
    # SwitchA trunk: native vlan 10, SwitchB trunk: native vlan 20
    native_vlans = re.findall(r'trunking\s+(\d+)|native vlan\s+(\d+)', show_outputs, re.IGNORECASE)
    # Find active native vlans in "show interfaces trunk" output style:
    native_vlan_list = []
    lines = show_outputs.split('\n')
    for line in lines:
        if 'trunking' in line.lower():
            parts = line.split()
            # In "Fa0/24      on           802.1q         trunking      10", 10 is native vlan
            if len(parts) >= 5:
                native_vlan_list.append(parts[-1])
    if len(set(native_vlan_list)) > 1:
        anomalies.append({
            "rule": "Native VLAN Mismatch",
            "severity": "High",
            "details": f"Mismatched native VLANs detected on trunk interfaces: {', '.join(set(native_vlan_list))}.",
            "fix": "Change the native VLAN on the mismatched trunk interface to match the other switch (e.g. 'switchport trunk native vlan <id>')."
        })

    # 6. Check for VLAN inactive (Inactive access VLAN)
    # "Administrative Access VLAN: 10 (Inactive)" or "Operational Access VLAN: 10 (Inactive)"
    inactive_vlan_match = re.search(r'Access VLAN:\s*(\d+)\s*\(Inactive\)', show_outputs, re.IGNORECASE)
    if inactive_vlan_match:
        inactive_vlan_id = inactive_vlan_match.group(1)
        anomalies.append({
            "rule": "Inactive Access VLAN",
            "severity": "High",
            "details": f"Port is assigned to VLAN {inactive_vlan_id}, which is inactive or missing from the VLAN database.",
            "fix": f"Create the VLAN in global configuration mode: 'vlan {inactive_vlan_id}'."
        })

    # 7. Check for DHCP Pool Subnet Mismatch
    # "ip dhcp pool VLAN10_POOL\n network 192.168.100.0 255.255.255.0\n default-router 192.168.10.1"
    dhcp_network = re.search(r'ip dhcp pool.*?\n\s*network\s+([0-9\.]+)\s+([0-9\.]+)', show_outputs, re.IGNORECASE | re.DOTALL)
    dhcp_gw = re.search(r'default-router\s+([0-9\.]+)', show_outputs, re.IGNORECASE)
    if dhcp_network and dhcp_gw:
        dhcp_net_ip = dhcp_network.group(1)
        dhcp_net_mask = dhcp_network.group(2)
        dhcp_gw_ip = dhcp_gw.group(1)
        
        # Subnet checking logic
        def ip_to_int(ip):
            return sum(int(octet) << (24 - 8 * i) for i, octet in enumerate(ip.split('.')))
        
        try:
            net_int = ip_to_int(dhcp_net_ip)
            gw_int = ip_to_int(dhcp_gw_ip)
            mask_int = ip_to_int(dhcp_net_mask)
            
            if (net_int & mask_int) != (gw_int & mask_int):
                anomalies.append({
                    "rule": "DHCP Pool Gateway Subnet Conflict",
                    "severity": "High",
                    "details": f"The default-router IP {dhcp_gw_ip} in the DHCP pool is not within the pool's network subnet {dhcp_net_ip}/{dhcp_net_mask}.",
                    "fix": f"Reconfigure the DHCP pool network to contain the default-router IP, or change the default-router address."
                })
        except Exception:
            pass

    # 8. Check for Missing Routing Route (Destination network not in table)
    # "% Network not in table" or "Gateway of last resort is not set" without static route
    if "% Network not in table" in show_outputs or "network not in table" in show_outputs.lower():
        anomalies.append({
            "rule": "Missing Route in Routing Table",
            "severity": "High",
            "details": "The destination network is not in the routing table, and no default gateway of last resort is set.",
            "fix": "Configure a static route ('ip route <dest_net> <dest_mask> <next_hop>') or enable a dynamic routing protocol (e.g. OSPF/EIGRP)."
        })

    # 9. Check for OSPF Router ID Duplicate
    # "Duplicate router ID 1.1.1.1 detected"
    ospf_dup_match = re.search(r'duplicate router id\s*([0-9\.]+)\s*detected|DUP_RTRID.*ID\s*([0-9\.]+)', show_outputs, re.IGNORECASE)
    if ospf_dup_match:
        dup_id = ospf_dup_match.group(1) or ospf_dup_match.group(2)
        anomalies.append({
            "rule": "Duplicate OSPF Router ID",
            "severity": "High",
            "details": f"Another router in the OSPF area is using the same OSPF Router ID ({dup_id}). This prevents adjacency.",
            "fix": f"Change the OSPF router ID under the OSPF process: 'router ospf <process>', 'router-id <new_id>', and clear the OSPF process."
        })

    # 10. Check for OSPF Area ID Mismatch on same link
    # RouterA: Gi0/0 in Area 0, RouterB: Gi0/0 in Area 1
    # Scan for OSPF interfaces in different areas in output (we'd have multiple outputs in text)
    # "Gi0/0        0               10.1.1.1/30" and "Gi0/0        1               10.1.1.2/30"
    ospf_areas = re.findall(r'(\S+)\s+(\d+)\s+[0-9\.]+/[0-9]+', show_outputs)
    if len(ospf_areas) >= 2:
        interfaces = [x[0] for x in ospf_areas]
        areas = [x[1] for x in ospf_areas]
        # If the same interface name (or typical connecting link) has different areas listed:
        if len(set(areas)) > 1:
            anomalies.append({
                "rule": "OSPF Area Mismatch",
                "severity": "High",
                "details": f"OSPF interfaces are configured with conflicting Area IDs: {', '.join(set(areas))}.",
                "fix": "Change the OSPF network statements or interface settings to put the connecting ports in the same OSPF Area."
            })

    # 11. Check for Switchport Mode Mismatch
    # SwitchA: mode trunk, SwitchB: mode static access
    sw_modes = re.findall(r'Administrative Mode:\s*(static access|trunk)', show_outputs, re.IGNORECASE)
    if len(sw_modes) >= 2:
        if len(set(sw_modes)) > 1:
            anomalies.append({
                "rule": "Switchport Trunk Mode Mismatch",
                "severity": "High",
                "details": f"Mismatched switchport modes: one end is configured as '{sw_modes[0]}', other end as '{sw_modes[1]}'.",
                "fix": "Reconfigure the access switchport to trunk: 'switchport mode trunk' on the access side interface."
            })

    # 12. Check for EtherChannel protocol mismatch
    # SwitchA LACP, SwitchB PAgP
    eth_protocols = re.findall(r'Po\d+\(\S+\)\s+(LACP|PAgP)', show_outputs, re.IGNORECASE)
    if len(eth_protocols) >= 2:
        if len(set(eth_protocols)) > 1:
            anomalies.append({
                "rule": "EtherChannel Protocol Mismatch",
                "severity": "High",
                "details": f"EtherChannel protocol mismatch: SwitchA uses '{eth_protocols[0]}' and SwitchB uses '{eth_protocols[1]}'.",
                "fix": "Configure both switches to use the same protocol (LACP is standard). Example: 'channel-group 1 mode active'."
            })

    # 13. Inter-VLAN Subinterface Encapsulation Mismatch
    # G0/0.20 has encapsulation dot1Q 30
    subinterface_match = re.search(r'interface\s+([a-zA-Z0-9\./\:]+\.(\d+)).*?encapsulation\s+dot1Q\s+(\d+)', show_outputs, re.IGNORECASE | re.DOTALL)
    if subinterface_match:
        sub_name = subinterface_match.group(1)
        sub_num = subinterface_match.group(2)
        vlan_tag = subinterface_match.group(3)
        if sub_num != vlan_tag:
            anomalies.append({
                "rule": "Subinterface Encapsulation VLAN Mismatch",
                "severity": "High",
                "details": f"Router subinterface {sub_name} is configured with 'encapsulation dot1Q {vlan_tag}'. The subinterface number ({sub_num}) differs from the VLAN tag ({vlan_tag}). While technically allowed, it is a high-risk misconfiguration.",
                "fix": f"Reconfigure encapsulation on subinterface {sub_name} to match the intended VLAN: 'encapsulation dot1Q {sub_num}'."
            })

    # 14. HSRP standby group mismatch
    # RouterA: Gi0/0 Grp 10 Active, RouterB: Gi0/0 Grp 20 Active
    hsrp_groups = re.findall(r'Gi\S+\s+(\d+)\s+\d+\s+(?:P\s+)?Active', show_outputs)
    if len(hsrp_groups) >= 2:
        if len(set(hsrp_groups)) > 1:
            anomalies.append({
                "rule": "HSRP Group ID Mismatch",
                "severity": "High",
                "details": f"Mismatched HSRP standby group numbers detected ({', '.join(hsrp_groups)}). This prevents routers from negotiating primary/standby states.",
                "fix": "Reconfigure standby group numbers to be identical on both routers (e.g. 'standby 10 ip ...')."
            })

    # 15. VTP Domain Name case-sensitive mismatch
    # SwitchA CISCO, SwitchB cisco
    vtp_domains = re.findall(r'VTP Domain Name\s*:\s*(\S+)', show_outputs, re.IGNORECASE)
    if len(vtp_domains) >= 2:
        if len(set(vtp_domains)) > 1:
            anomalies.append({
                "rule": "VTP Domain Name Mismatch",
                "severity": "High",
                "details": f"VTP domain names are different or have case-sensitivity differences: '{vtp_domains[0]}' vs '{vtp_domains[1]}'.",
                "fix": f"Reconfigure the VTP client's domain name to match the server exactly: 'vtp domain {vtp_domains[0]}'."
            })

    # Generic fallbacks based on symptom if no specific configuration rule matched
    if not anomalies:
        if "dns" in symptom.lower() and "resolve" in symptom.lower() and "8.8.8.8" in show_outputs:
            if "dns-server" not in show_outputs.lower() and "dns server" not in show_outputs.lower():
                anomalies.append({
                    "rule": "DNS IP Mismatch or Missing Configuration",
                    "severity": "Medium",
                    "details": "Client cannot resolve names but can ping IPs. Host DNS server IP is likely pointing to an incorrect address or missing.",
                    "fix": "Verify that client DNS configurations are correct and the DNS server is reachable."
                })
        elif "rip" in symptom.lower() and "rip" in show_outputs.lower():
            if "version 1" in show_outputs.lower() and "version 2" in show_outputs.lower():
                anomalies.append({
                    "rule": "RIP Version Mismatch",
                    "severity": "Medium",
                    "details": "RIP routers are running mismatched versions (Version 1 vs Version 2).",
                    "fix": "Configure both routers to run RIP Version 2 using 'version 2' in router configuration."
                })

    return anomalies

# A simple CLI wrapper to test the script
if __name__ == "__main__":
    import json
    import sys
    
    test_outputs_vlan_db = """
    SwitchA# show vlan brief
    VLAN Name                             Status    Ports
    ---- -------------------------------- --------- -------------------------------
    1    default                          active    Fa0/2, Fa0/3, Fa0/4, Fa0/24
    100  VLAN0100                         active
    
    SwitchA# show interfaces Fa0/1 switchport
    Name: Fa0/1
    Switchport: Enabled
    Administrative Mode: static access
    Operational Mode: static access
    Administrative Access VLAN: 10 (Inactive)
    Operational Access VLAN: 10 (Inactive)
    """
    
    print("Testing Rule Checker with inactive VLAN:")
    results = check_rules(test_outputs_vlan_db, symptom="PC1 cannot reach VLAN 10")
    print(json.dumps(results, indent=2))
