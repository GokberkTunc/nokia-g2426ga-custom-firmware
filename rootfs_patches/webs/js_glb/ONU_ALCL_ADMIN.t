var all_nodes= { 
     name:"all_nodes",
     target:0,
     nodes:[
        {
            name:"<%T('Status')%>",
            target:0,
            nodes:[
                { name:"<%T('Overview')%>", target:"overview.cgi" },
                { name:"<%T('Device Information')%>", target:"device_status.cgi" },
                { name:"<%T('LAN Status')%>", target:"lan_status.cgi?lan" },
                { name:"<%T('WAN Status')%>", target:"show_wan_status.cgi?ipv4" },
                { name:"<%T('WAN Status IPv6')%>", target:"show_wan_status.cgi?ipv6" },
                { name:"<%T('STA Information')%>", target:"sta_info.cgi" },
                { name:"<%T('Neighboring AP')%>", target:"neighboring_AP.cgi" },
                { name:"<%T('Home Networking')%>", target:"lan_status.cgi?wlan" },
                { name:"<%T('Optics Module Status')%>", target:"wan_status.cgi?gpon" },
                { name:"<%T('Statistics')%>", target:"statistics.cgi" },
                { name:"<%T('L2 Forwarding Table')%>", target:"forwarding_table.cgi" },
                { name:"<%T('Voice Information')%>", target:"voice_info.cgi" }
            ]
        },
        {
            name:"<%T('Network')%>",
            target:0,
            nodes:[
                { name:"<%T('LAN')%>", target:"lan_ipv4.cgi" },
                { name:"<%T('LAN_IPv6')%>", target:"lan_ipv6.cgi" },
                { name:"<%T('WAN')%>", target:"wan_config_glb.cgi" },
                { name:"<%T('WAN DHCP')%>", target:"wan_dhcp.cgi" },
                { name:"<%T('Wireless (2.4GHz)')%>", target:"wlan_config.cgi" },
                { name:"<%T('Wireless (5GHz)')%>", target:"wlan_config.cgi?v=11ac" },
                { name:"<%T('Wireless Schedule')%>", target:"wifi_schedule.cgi" },
                { name:"<%T('IP Routing')%>", target:"route.cgi" },
                { name:"<%T('DNS')%>", target:"dns.cgi" },
                { name:"<%T('TR-069')%>", target:"tr69.cgi" },
                { name:"<%T('TR-369')%>", target:"tr369.cgi" },
                { name:"<%T('GRE Tunnel')%>", target:"gre_tunnel.cgi" },
                { name:"<%T('US Classifier')%>", target:"us_classifier.cgi" },
                { name:"<%T('QoS Config')%>", target:"qos.cgi" },
                { name:"<%T('Port Binding')%>", target:"portbinding.cgi" },
                { name:"<%T('Rate Limiting')%>", target:"rate_limit.cgi" },
                { name:"<%T('MESH')%>", target:"mesh.cgi" }
            ]
        },
        {
            name:"<%T('Security')%>",
            target:0,
            nodes:[
                { name:"<%T('Firewall')%>", target:"firewall.cgi?fire" },
                { name:"<%T('MAC Filter')%>", target:"macfilter.cgi" },
                { name:"<%T('IP Filter')%>", target:"ipfilter.cgi" },
                { name:"<%T('URL Filter')%>", target:"urlfilter.cgi" },
                { name:"<%T('Port Filter')%>", target:"portfilter.cgi" },
                { name:"<%T('NAT Session Limit')%>", target:"nat_session.cgi" },
                { name:"<%T('Parental Control')%>", target:"parental_control.cgi" },
                { name:"<%T('DMZ and ALG')%>", target:"nat_glb.cgi?v=alg" },
                { name:"<%T('Access Control')%>", target:"access_control.cgi" }
            ]
        },
        {
            name:"<%T('Application')%>",
            target:0,
            nodes:[
                { name:"<%T('Port Forwarding')%>", target:"nat_glb.cgi?v=vhost" },
                { name:"<%T('Port Triggering')%>", target:"nat_glb.cgi?v=thost" },
                { name:"<%T('DDNS')%>", target:"ddns.cgi" },
                { name:"<%T('NTP')%>", target:"sntp.cgi" },
                { name:"<%T('USB / Storage')%>", target:"storage.cgi" },
                { name:"<%T('UPNP and DLNA')%>", target:"upnp.cgi" },
                { name:"<%T('Voice Setting')%>", target:"voice_setting.cgi?v=cfg_line" },
                { name:"<%T('LED')%>", target:"led.cgi" }
            ]
        },
        {
            name:"<%T('Maintenance')%>",
            target:0,
            nodes:[
                { name:"<%T('Password')%>", target:"user_glb.cgi" },
                { name:"<%T('Speed Test')%>", target:"speed_test.cgi" },
                { name:"<%T('Speed Test History')%>", target:"speedtest_ookla.cgi" },
                { name:"<%T('Packet Capture (tcpdump)')%>", target:"tcp_dump.cgi" },
                { name:"<%T('RF Video')%>", target:"rf_video.cgi" },
                { name:"<%T('LOID Configuration')%>", target:"reg.cgi?loidcfg" },
                { name:"<%T('SLID Configuration')%>", target:"gpon_config.cgi" },
                { name:"<%T('Device Management')%>", target:"device_name.cgi" },
                { name:"<%T('Backup and Restore')%>", target:"usb.cgi?backup" },
                { name:"<%T('Firmware Upgrade')%>", target:"upgrade.cgi" },
                { name:"<%T('Reboot Device')%>", target:"reboot.cgi" },
                { name:"<%T('Factory Default')%>", target:"restore.cgi" },
                { name:"<%T('Diagnostics')%>", target:"diag.cgi?ping" },
                { name:"<%T('Log')%>", target:"log.cgi" },
                { name:"<%T('Delta CFG Tool')%>", target:"delta.cgi" },
                { name:"<%T('ONU Mode Switch')%>", target:"onu_mode_switch.cgi" }
            ]
        },
        {
            name:"<%T('RG Troubleshooting')%>",
            target:0,
            nodes:[
                { name:"<%T('RG Troubleshoot Counters')%>", target:"rgtroubleshooting.cgi?ping" }
            ]
        },
        {
            name:"<%T('SmartHome')%>",
            target:0,
            nodes:[
                { name:"<%T('Status')%>", target:"iotstatus.cgi" },
                { name:"<%T('Configuration')%>", target:"iot_config.cgi" },
                { name:"<%T('Maintenance')%>", target:"smarthome.cgi" }
            ]
        }
     ]
};
