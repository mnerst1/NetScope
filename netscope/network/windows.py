"""Windows IP Helper API, no elevation, WMI service or translated command output required."""
import ctypes as C
import socket
from ctypes import wintypes as W


class SocketAddress(C.Structure):
    _fields_=[('address',C.c_void_p),('length',C.c_int)]


class AddressNode(C.Structure):
    pass


AddressNode._fields_=[('alignment',C.c_ulonglong),('next',C.POINTER(AddressNode)),('socket',SocketAddress)]


class Adapter(C.Structure):
    pass


Adapter._fields_=[('length',W.ULONG),('index',W.DWORD),('next',C.POINTER(Adapter)),('adapter_name',C.c_char_p),
 ('unicast',C.c_void_p),('anycast',C.c_void_p),('multicast',C.c_void_p),('dns_servers',C.POINTER(AddressNode)),
 ('dns_suffix',W.LPWSTR),('description',W.LPWSTR),('friendly_name',W.LPWSTR),('mac',C.c_ubyte*8),
 ('mac_length',W.ULONG),('flags',W.ULONG),('mtu',W.ULONG),('if_type',W.DWORD),('oper_status',C.c_int),
 ('ipv6_index',W.ULONG),('zone_indices',W.ULONG*16),('prefix',C.c_void_p),
 ('tx_speed',C.c_ulonglong),('rx_speed',C.c_ulonglong),('wins',C.c_void_p),('gateways',C.POINTER(AddressNode)),
 ('ipv4_metric',W.ULONG),('ipv6_metric',W.ULONG)]


def addresses(pointer):
    result=[]
    while pointer:
        node=pointer.contents
        if node.socket.address and node.socket.length>=8:
            raw=C.string_at(node.socket.address,node.socket.length)
            family=int.from_bytes(raw[:2],'little')
            if family==socket.AF_INET:
                result.append(socket.inet_ntop(socket.AF_INET,raw[4:8]))
            elif family==socket.AF_INET6 and len(raw)>=24:
                result.append(socket.inet_ntop(socket.AF_INET6,raw[8:24]))
        pointer=node.next
    return result


def configuration():
    api=C.WinDLL('iphlpapi').GetAdaptersAddresses
    api.argtypes=[W.ULONG,W.ULONG,C.c_void_p,C.POINTER(Adapter),C.POINTER(W.ULONG)]
    api.restype=W.ULONG
    size=W.ULONG(15360)
    for _ in range(3):
        buffer=C.create_string_buffer(size.value)
        pointer=C.cast(buffer,C.POINTER(Adapter))
        status=api(socket.AF_UNSPEC,0x0080,None,pointer,C.byref(size))
        if status==111:
            continue
        if status:
            raise OSError(status,'GetAdaptersAddresses failed')
        result={}
        while pointer:
            a=pointer.contents
            gateways=addresses(a.gateways) if a.length>=Adapter.gateways.offset+C.sizeof(C.c_void_p) else []
            gateway=next((v for v in gateways if ':' not in v),'')
            result[a.friendly_name]={'Gateway':gateway,'DNS':', '.join(addresses(a.dns_servers)),
                                     'Metric':a.ipv4_metric if a.length>=C.sizeof(Adapter) else 999,
                                     'Kind':'Wi-Fi' if a.if_type==71 else 'LAN'}
            pointer=a.next
        return result
    raise OSError('Adapter table changed repeatedly')
