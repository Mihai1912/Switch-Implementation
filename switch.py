#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name


def parse_ethernet_header(data):
    # Unpack the header fields from the byte array
    #dest_mac, src_mac, ethertype = struct.unpack('!6s6sH', data[:14])
    dest_mac = data[0:6]
    src_mac = data[6:12]
    
    # Extract ethertype. Under 802.1Q, this may be the bytes from the VLAN TAG
    ether_type = (data[12] << 8) + data[13]

    vlan_id = -1
    # Check for VLAN tag (0x8100 in network byte order is b'\x81\x00')
    if ether_type == 0x8200:
        vlan_tci = int.from_bytes(data[14:16], byteorder='big')
        vlan_id = vlan_tci & 0x0FFF  # extract the 12-bit VLAN ID
        ether_type = (data[16] << 8) + data[17]

    return dest_mac, src_mac, ether_type, vlan_id

def create_vlan_tag(vlan_id):
    # 0x8100 for the Ethertype for 802.1Q
    # vlan_id & 0x0FFF ensures that only the last 12 bits are used
    return struct.pack('!H', 0x8200) + struct.pack('!H', vlan_id & 0x0FFF)

def is_unicast(mac):
    return mac[0] & 0x01 == 0

def send_bdpu_every_sec(own_bridge_id, trunk_ports):
    while True:
        # TODO Send BDPU every second if necessary
        for i in trunk_ports:
            root_bridge_id = struct.pack('!q', int(own_bridge_id))
            sender_bridge_id = struct.pack('!q', int(own_bridge_id))
            sender_path_cost = struct.pack('!q', 0)
            # send_to_link
            data = bytes([0x01, 0x80, 0xc2, 0x00, 0x00, 0x00]) + root_bridge_id + sender_bridge_id + sender_path_cost
            send_to_link(i, data, len(data))
        time.sleep(1)


def main():
    # init returns the max interface number. Our interfaces
    # are 0, 1, 2, ..., init_ret value + 1
    switch_id = sys.argv[1]

    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)

    root_port = None

    # print("# Starting switch with id {}".format(switch_id), flush=True)
    # print("[INFO] Switch MAC", ':'.join(f'{b:02x}' for b in get_switch_mac()))

    # # Printing interface names
    # for i in interfaces:
    #     print(get_interface_name(i))
    
    # Read config file 
    
    path = "configs/switch" + str(switch_id) + ".cfg"

    file = open(path, "r")

    priotity = file.readline()
    trunk_ports = []
    access_ports = []

    for i in interfaces:
        line = file.readline()
        list = line.split(" ")
        if list[1].strip() == "T":
            trunk_ports.append(i)
        else:
            access_ports.append((i , int(list[1].strip())))

    file.close()

    Table = {}

    port_state = {}

    for i in interfaces:
        if i in trunk_ports:
            port_state[i] = "blocking"
        else:
            port_state[i] = "listening"

    own_bridge_id = int(priotity)
    root_bridge_id = int(own_bridge_id)
    root_path_cost = 0

    if own_bridge_id == root_bridge_id:
        for i in trunk_ports:
            port_state[i] = "listening"

    # Create and start a new thread that deals with sending BDPU
    t = threading.Thread(target=send_bdpu_every_sec, args=(own_bridge_id, trunk_ports))
    t.start()

    while True:
        
        # Note that data is of type bytes([...]).
        # b1 = bytes([72, 101, 108, 108, 111])  # "Hello"
        # b2 = bytes([32, 87, 111, 114, 108, 100])  # " World"
        # b3 = b1[0:2] + b[3:4].
        interface, data, length = recv_from_any_link()

        dest_mac, src_mac, ethertype, vlan_id = parse_ethernet_header(data)

        # Print the MAC src and MAC dst in human readable format
        dest_mac1 = ':'.join(f'{b:02x}' for b in dest_mac)
        src_mac1 = ':'.join(f'{b:02x}' for b in src_mac)

        # Note. Adding a VLAN tag can be as easy as
        # tagged_frame = data[0:12] + create_vlan_tag(10) + data[12:]

        # print(f'Destination MAC: {dest_mac1}')
        # print(f'Source MAC: {src_mac1}')
        # print(f'EtherType: {ethertype}')

        # print("Received frame of size {} on interface {}".format(length, interface), flush=True)

        # TODO: Implement forwarding with learning

        # TODO: Implement VLAN support

        if dest_mac == bytes([0x01, 0x80, 0xc2, 0x00, 0x00, 0x00]):

            were_root_bridge = own_bridge_id == root_bridge_id

            BPDU_root_bridge_id = int.from_bytes(data[6:14], byteorder='big')
            BPDU_sender_bridge_id = int.from_bytes(data[14:22], byteorder='big')
            BPDU_sender_path_cost = int.from_bytes(data[22:30], byteorder='big')

            if BPDU_root_bridge_id < root_bridge_id:
                root_bridge_id = BPDU_root_bridge_id
                root_path_cost = BPDU_sender_path_cost + 10
                root_port = interface

                if were_root_bridge:
                    for i in trunk_ports:
                        if i != root_port:
                            port_state[i] = "blocking"

                if port_state[root_port] == "blocking":
                    port_state[root_port] = "listening"

                new_bpdu_root_bridge_id = struct.pack('!q', int(root_bridge_id))
                new_bpdu_sender_bridge_id = struct.pack('!q', int(own_bridge_id))
                new_bpdu_sender_path_cost = struct.pack('!q', int(root_path_cost))
                new_bpdu = bytes([0x01, 0x80, 0xc2, 0x00, 0x00, 0x00]) + new_bpdu_root_bridge_id + new_bpdu_sender_bridge_id + new_bpdu_sender_path_cost

                for i in trunk_ports:
                    if port_state[i] == "listening":
                        send_to_link(i, new_bpdu, len(new_bpdu))

            elif BPDU_root_bridge_id == root_bridge_id:
                if interface == root_port and BPDU_sender_path_cost + 10 < root_path_cost:
                    root_path_cost = BPDU_sender_path_cost + 10

                else:
                    if BPDU_sender_path_cost > root_path_cost:
                        if interface == "blocking":
                            port_state[interface] = "listening"

            elif BPDU_sender_bridge_id == own_bridge_id:
                port_state[interface] = "blocking"

            else:
                continue

            if own_bridge_id == root_bridge_id:
                for i in trunk_ports:
                    port_state[i] = "listening"

        else:

            Table[src_mac] = interface

            if port_state[interface] == "blocking":
                continue

            if interface in trunk_ports: # coming from trunk port
                if is_unicast(dest_mac):
                    if dest_mac in Table:
                        if Table[dest_mac] in trunk_ports:
                            send_to_link(Table[dest_mac], data, length)
                            continue
                        else:
                            if vlan_id == access_ports[Table[dest_mac]][1]:
                                data1 = data[0:12] + data[16:]
                                send_to_link(Table[dest_mac], data1, length - 4)
                                continue
                            else:
                                continue
                    else:
                        # Flood
                        for i in interfaces:
                            if i != interface:
                                if port_state[i] == "listening":
                                    if i in trunk_ports:
                                        send_to_link(i, data, length)
                                        continue
                                    elif vlan_id == access_ports[i][1]:
                                        data1 = data[0:12] + data[16:]
                                        send_to_link(i, data1, length - 4)
                                        continue
                                    else:
                                        continue
                else:
                    for i in interfaces:
                            if i != interface:
                                if port_state[i] == "listening":
                                    if i in trunk_ports:
                                        send_to_link(i, data, length)
                                        continue
                                    elif vlan_id == access_ports[i][1]:
                                        data1 = data[0:12] + data[16:]
                                        send_to_link(i, data1, length - 4)
                                        continue
                                    else:
                                        continue
                
            else: # coming from access port
                if is_unicast(dest_mac):
                    if dest_mac in Table:
                        if Table[dest_mac] in trunk_ports:
                            tagged_frame = data[0:12] + create_vlan_tag(access_ports[interface][1]) + data[12:]
                            send_to_link(Table[dest_mac], tagged_frame, length+4)
                            continue
                        else:
                            if access_ports[Table[dest_mac]][1] == access_ports[interface][1]:
                                send_to_link(Table[dest_mac], data, length)
                                continue
                            else:
                                continue
                    else:
                        for i in interfaces:
                            if i != interface:
                                if port_state[i] == "listening":
                                    if i in trunk_ports:
                                        tagged_frame = data[0:12] + create_vlan_tag(access_ports[interface][1]) + data[12:]
                                        send_to_link(i, tagged_frame, length+4)
                                        continue
                                    elif access_ports[i][1] == access_ports[interface][1]:
                                        send_to_link(i, data, length)
                                        continue
                                    else:
                                        continue
                else:
                    for i in interfaces:
                            if i != interface:
                                if port_state[i] == "listening":
                                    if i in trunk_ports:
                                        tagged_frame = data[0:12] + create_vlan_tag(access_ports[interface][1]) + data[12:]
                                        send_to_link(i, tagged_frame, length+4)
                                        continue
                                    elif access_ports[i][1] == access_ports[interface][1]:
                                        send_to_link(i, data, length)
                                        continue
                                    else:
                                        continue


        # TODO: Implement STP support

        # data is of type bytes.
        # send_to_link(i, data, length)

if __name__ == "__main__":
    main()